import time
from typing import Optional

import httpx
from loguru import logger

from config.base import settings

# Status codes worth retrying: rate limiting and transient server/gateway errors.
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class EmbeddingError(Exception):
    pass


class EmbeddingClient:
    """
    Client for the company embedding service (Hugging Face TEI, OpenAI-compatible
    `POST {base_url}/embeddings`).

    - Splits input into batches of `batch_size` (the server rejects more than 32).
    - Retries timeouts, connection errors, 429 and 5xx with exponential backoff;
      validation errors (4xx) fail immediately.
    - Verifies every vector has `dimensions` entries, so a model/config mismatch can
      never be written into the vector store.
    - Vectors come back L2-normalised from the server — use cosine distance.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        dimensions: int,
        batch_size: int = 32,
        timeout: float = 60,
        max_retries: int = 3,
        query_instruction: Optional[str] = None,
        transport: Optional[httpx.BaseTransport] = None,
        backoff_seconds: float = 0.5,
    ):
        self.model = model
        self.dimensions = dimensions
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.query_instruction = query_instruction
        self.backoff_seconds = backoff_seconds
        self._http = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout, transport=transport)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed passages for indexing. Order of the result matches `texts`."""
        self._validate(texts)
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            vectors.extend(self._embed_batch(texts[start:start + self.batch_size]))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        """Embed a search query, applying the optional query instruction."""
        self._validate([text])
        if self.query_instruction:
            text = f"Instruct: {self.query_instruction}\nQuery: {text}"
        return self._embed_batch([text])[0]

    @staticmethod
    def _validate(texts: list[str]):
        if not texts:
            raise ValueError("No texts to embed.")
        empty = [i for i, text in enumerate(texts) if not text or not text.strip()]
        if empty:
            raise ValueError(f"Cannot embed empty text at positions {empty[:10]}.")

    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        payload = {"input": batch, "model": self.model, "dimensions": self.dimensions}
        body = self._post_with_retry(payload)

        data = sorted(body.get("data", []), key=lambda item: item["index"])
        if len(data) != len(batch):
            raise EmbeddingError(f"Expected {len(batch)} embeddings, got {len(data)}.")

        vectors = [item["embedding"] for item in data]
        for vector in vectors:
            if len(vector) != self.dimensions:
                raise EmbeddingError(
                    f"Embedding has {len(vector)} dimensions, expected {self.dimensions}. "
                    "Check ENGINE_EMBEDDING_MODEL / ENGINE_EMBEDDING_DIMENSIONS."
                )
        return vectors

    def _post_with_retry(self, payload: dict) -> dict:
        attempt = 0
        while True:
            try:
                response = self._http.post("/embeddings", json=payload)
                if response.status_code not in _RETRYABLE_STATUS:
                    if response.is_error:
                        raise EmbeddingError(
                            f"Embedding service returned {response.status_code}: {response.text[:300]}"
                        )
                    return response.json()
                failure = f"HTTP {response.status_code}"
            except (httpx.TimeoutException, httpx.TransportError) as error:
                failure = type(error).__name__

            if attempt >= self.max_retries:
                raise EmbeddingError(f"Embedding service unavailable after {attempt + 1} attempts ({failure}).")
            delay = self.backoff_seconds * (2 ** attempt)
            logger.warning(
                "Embedding request failed ({failure}), retry {n}/{max} in {delay:.1f}s",
                failure=failure, n=attempt + 1, max=self.max_retries, delay=delay,
            )
            time.sleep(delay)
            attempt += 1

    def ping(self):
        """Cheap liveness check: TEI's `GET /health` (served at the root, not under /v1)."""
        base = str(self._http.base_url).rstrip("/")
        root = base[: -len("/v1")] if base.endswith("/v1") else base
        self._http.get(f"{root}/health", timeout=3).raise_for_status()

    def close(self):
        self._http.close()


class EmbeddingService:

    instance = None

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            if not settings.ENGINE_EMBEDDING_BASE_URL or not settings.ENGINE_EMBEDDING_MODEL:
                raise RuntimeError(
                    "Embedding service is not configured "
                    "(set BE_ENGINE_EMBEDDING_BASE_URL and BE_ENGINE_EMBEDDING_MODEL)."
                )
            cls.instance = EmbeddingClient(
                base_url=settings.ENGINE_EMBEDDING_BASE_URL,
                model=settings.ENGINE_EMBEDDING_MODEL,
                dimensions=settings.ENGINE_EMBEDDING_DIMENSIONS,
                batch_size=settings.ENGINE_EMBEDDING_BATCH_SIZE,
                timeout=settings.ENGINE_EMBEDDING_TIMEOUT_SECONDS,
                max_retries=settings.ENGINE_EMBEDDING_MAX_RETRIES,
                query_instruction=settings.ENGINE_EMBEDDING_QUERY_INSTRUCTION or None,
            )
        return cls.instance
