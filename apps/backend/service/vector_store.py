"""
Qdrant storage for book chunks.

One collection (settings.QDRANT_COLLECTION), one point per chunk:
  id       deterministic uuid5(book_id, chunk_index) — re-ingesting overwrites, never duplicates
  vector   1024-dim embedding from the company embedding service (cosine distance)
  payload  book_id, book_title, chunk_index, text, headings, page_start, page_end, embedding_model
"""

import uuid
from dataclasses import dataclass, field
from typing import Iterable, Optional

from loguru import logger
from qdrant_client import QdrantClient, models

from config.base import settings
from service import Services

# Fixed namespace so the same (book, chunk) always maps to the same point id.
_POINT_NAMESPACE = uuid.UUID("6f1c2d1e-4b7a-4f0e-9a51-2d8f0c3b7e10")


def point_id(book_id, chunk_index: int) -> str:
    return str(uuid.uuid5(_POINT_NAMESPACE, f"{book_id}:{chunk_index}"))


@dataclass
class ChunkHit:
    score: float
    book_id: str
    book_title: str
    chunk_index: int
    text: str
    headings: list[str] = field(default_factory=list)
    page_start: Optional[int] = None
    page_end: Optional[int] = None


class VectorStore:
    def __init__(self, client: Optional[QdrantClient] = None, collection: Optional[str] = None,
                 dimensions: Optional[int] = None):
        self._client = client
        self.collection = collection or settings.QDRANT_COLLECTION
        self.dimensions = dimensions or settings.ENGINE_EMBEDDING_DIMENSIONS
        self._ready = False

    @property
    def client(self) -> QdrantClient:
        return self._client or Services.qdrant()

    def ensure_collection(self):
        """Create the collection + payload indexes on first use; verify the vector size otherwise."""
        if self._ready:
            return
        if self.client.collection_exists(self.collection):
            info = self.client.get_collection(self.collection)
            size = info.config.params.vectors.size
            if size != self.dimensions:
                raise RuntimeError(
                    f"Qdrant collection '{self.collection}' stores {size}-dim vectors but the embedding "
                    f"model produces {self.dimensions}. Use a new QDRANT_COLLECTION and re-index."
                )
        else:
            logger.info("Creating Qdrant collection {name}", name=self.collection)
            self.client.create_collection(
                self.collection,
                vectors_config=models.VectorParams(size=self.dimensions, distance=models.Distance.COSINE),
            )
            self.client.create_payload_index(self.collection, "book_id", models.PayloadSchemaType.KEYWORD)
            self.client.create_payload_index(self.collection, "chunk_index", models.PayloadSchemaType.INTEGER)
        self._ready = True

    def upsert_chunks(self, book_id, book_title: str, chunks: list[dict], vectors: list[list[float]],
                      embedding_model: str):
        """`chunks` items: {chunk_index, text, headings, page_start, page_end}."""
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        self.ensure_collection()
        points = [
            models.PointStruct(
                id=point_id(book_id, chunk["chunk_index"]),
                vector=vector,
                payload={
                    "book_id": str(book_id),
                    "book_title": book_title,
                    "embedding_model": embedding_model,
                    **chunk,
                },
            )
            for chunk, vector in zip(chunks, vectors)
        ]
        self.client.upsert(self.collection, points=points, wait=True)

    def delete_stale_chunks(self, book_id, keep_below: int):
        """After re-indexing into fewer chunks, remove the leftovers (chunk_index >= keep_below)."""
        self.ensure_collection()
        self.client.delete(
            self.collection,
            points_selector=models.FilterSelector(filter=models.Filter(must=[
                _book_filter(book_id),
                models.FieldCondition(key="chunk_index", range=models.Range(gte=keep_below)),
            ])),
            wait=True,
        )

    def delete_book(self, book_id):
        if not self.client.collection_exists(self.collection):
            return
        self.client.delete(
            self.collection,
            points_selector=models.FilterSelector(filter=models.Filter(must=[_book_filter(book_id)])),
            wait=True,
        )

    def count(self, book_id) -> int:
        if not self.client.collection_exists(self.collection):
            return 0
        return self.client.count(self.collection, count_filter=models.Filter(must=[_book_filter(book_id)])).count

    def search(self, vector: list[float], book_ids: Optional[Iterable[str]], limit: int,
               min_score: float) -> list[ChunkHit]:
        self.ensure_collection()
        query_filter = None
        if book_ids is not None:
            ids = [str(b) for b in book_ids]
            query_filter = models.Filter(must=[models.FieldCondition(key="book_id", match=models.MatchAny(any=ids))])
        response = self.client.query_points(
            self.collection,
            query=vector,
            query_filter=query_filter,
            limit=limit,
            score_threshold=min_score,
            with_payload=True,
        )
        return [
            ChunkHit(
                score=point.score,
                book_id=point.payload["book_id"],
                book_title=point.payload.get("book_title", ""),
                chunk_index=point.payload.get("chunk_index", 0),
                text=point.payload.get("text", ""),
                headings=point.payload.get("headings") or [],
                page_start=point.payload.get("page_start"),
                page_end=point.payload.get("page_end"),
            )
            for point in response.points
        ]


def _book_filter(book_id) -> models.FieldCondition:
    return models.FieldCondition(key="book_id", match=models.MatchValue(value=str(book_id)))
