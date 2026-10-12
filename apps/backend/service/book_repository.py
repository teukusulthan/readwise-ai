"""
SQL access for the `books` table. Only this module writes SQL for books;
services call these methods and never build queries themselves.

All values go through psycopg parameters (%s / named placeholders), never string
formatting, so user input can't change the query (SQL injection). Column names
used in dynamic UPDATE/ORDER BY come from fixed whitelists below.
"""

import uuid
from typing import Iterable, Optional

from psycopg import sql
from psycopg.errors import UniqueViolation

from service import Services

INGESTION_STATUSES = ("none", "queued", "processing", "indexed", "failed")
# While a book is in one of these, the ingestion worker owns its document and vectors.
BUSY_STATUSES = ("queued", "processing")

# Columns callers may set through insert()/update().
WRITABLE_COLUMNS = {
    "title", "authors", "description", "isbn", "cover_url", "publisher", "published_year",
    "language", "subjects", "metadata_source", "external_id",
    "file_name", "file_path", "file_sha256", "file_size_bytes", "page_count",
    "ingestion_status", "ingestion_error", "chunk_count", "embedding_model", "indexed_at",
}

SORTABLE_COLUMNS = {"createdAt": "created_at", "updatedAt": "updated_at", "title": "title",
                    "publishedYear": "published_year", "indexedAt": "indexed_at"}


class DuplicateBookError(Exception):
    """A unique constraint (ISBN, file hash, external id) would be violated."""


def parse_book_id(value) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise ValueError(f"Invalid book id: {value!r}") from None


class BookRepository:
    def __init__(self, pool=None):
        # `pool` is injectable for tests; production uses the shared pool.
        self._pool = pool

    @property
    def pool(self):
        return self._pool or Services.postgres()

    # ── reads ─────────────────────────────────────────────────────────

    def get(self, book_id) -> Optional[dict]:
        with self.pool.connection() as conn:
            return conn.execute("SELECT * FROM books WHERE id = %s", (parse_book_id(book_id),)).fetchone()

    def get_many(self, book_ids: Iterable) -> list[dict]:
        ids = [parse_book_id(b) for b in book_ids]
        if not ids:
            return []
        with self.pool.connection() as conn:
            return conn.execute(
                "SELECT id, title, ingestion_status FROM books WHERE id = ANY(%s)", (ids,)
            ).fetchall()

    def catalog(self) -> list[dict]:
        """Identity, catalog details and status of every book (small table): retrieval scoping + book mentions."""
        with self.pool.connection() as conn:
            return conn.execute(
                "SELECT id, title, authors, published_year, description, ingestion_status FROM books ORDER BY title, id"
            ).fetchall()

    def indexed_ids(self) -> list[str]:
        with self.pool.connection() as conn:
            rows = conn.execute("SELECT id FROM books WHERE ingestion_status = 'indexed'").fetchall()
        return [str(row["id"]) for row in rows]

    def find_by(self, column: str, value) -> Optional[dict]:
        if column not in ("isbn", "file_sha256", "external_id"):
            raise ValueError(f"Cannot look up books by {column}")
        query = sql.SQL("SELECT * FROM books WHERE {} = %s LIMIT 1").format(sql.Identifier(column))
        with self.pool.connection() as conn:
            return conn.execute(query, (value,)).fetchone()

    def list(
        self,
        search: Optional[str] = None,
        statuses: Optional[Iterable[str]] = None,
        page: int = 1,
        size: int = 10,
        order_by: str = "createdAt",
        order: str = "desc",
    ) -> tuple[list[dict], int]:
        conditions, params = [], {}
        if search and search.strip():
            # Case-insensitive match on title, any author, ISBN or publisher.
            conditions.append(
                "(title ILIKE %(q)s OR isbn ILIKE %(q)s OR publisher ILIKE %(q)s"
                " OR EXISTS (SELECT 1 FROM unnest(authors) a WHERE a ILIKE %(q)s))"
            )
            params["q"] = f"%{_escape_like(search.strip())}%"
        if statuses:
            statuses = list(statuses)
            unknown = set(statuses) - set(INGESTION_STATUSES)
            if unknown:
                raise ValueError(f"Unknown ingestion status: {sorted(unknown)}")
            conditions.append("ingestion_status = ANY(%(statuses)s)")
            params["statuses"] = statuses

        where = sql.SQL(" WHERE " + " AND ".join(conditions)) if conditions else sql.SQL("")
        sort_column = SORTABLE_COLUMNS.get(order_by, "created_at")
        direction = sql.SQL("ASC" if str(order).lower() == "asc" else "DESC")
        params.update(limit=size, offset=(page - 1) * size)

        rows_query = sql.SQL("SELECT * FROM books{} ORDER BY {} {} NULLS LAST, id LIMIT %(limit)s OFFSET %(offset)s").format(
            where, sql.Identifier(sort_column), direction
        )
        count_query = sql.SQL("SELECT count(*) AS total FROM books{}").format(where)
        with self.pool.connection() as conn:
            rows = conn.execute(rows_query, params).fetchall()
            total = conn.execute(count_query, params).fetchone()["total"]
        return rows, total

    # ── writes ────────────────────────────────────────────────────────

    def insert(self, fields: dict) -> dict:
        _check_columns(fields)
        columns = list(fields)
        query = sql.SQL("INSERT INTO books ({}) VALUES ({}) RETURNING *").format(
            sql.SQL(", ").join(map(sql.Identifier, columns)),
            sql.SQL(", ").join(sql.Placeholder(c) for c in columns),
        )
        with self.pool.connection() as conn:
            try:
                return conn.execute(query, fields).fetchone()
            except UniqueViolation as error:
                raise DuplicateBookError(_duplicate_message(error)) from error

    def update(self, book_id, fields: dict) -> Optional[dict]:
        _check_columns(fields)
        if not fields:
            return self.get(book_id)
        return self._update_where(book_id, fields)

    def transition_status(self, book_id, to_status: str, from_statuses: Iterable[str], **fields) -> Optional[dict]:
        """
        Atomically move a book to `to_status` only if it is currently in one of
        `from_statuses`. Returns the updated row, or None if the book was not in an
        allowed state (e.g. a second worker already claimed it).
        """
        _check_columns(fields)
        fields["ingestion_status"] = to_status
        query = sql.SQL(
            "UPDATE books SET {}, updated_at = now() "
            "WHERE id = %(id)s AND ingestion_status = ANY(%(from_statuses)s) RETURNING *"
        ).format(_assignments(fields))
        params = {**fields, "id": parse_book_id(book_id), "from_statuses": list(from_statuses)}
        with self.pool.connection() as conn:
            return conn.execute(query, params).fetchone()

    def attach_document(self, book_id, fields: dict) -> Optional[dict]:
        """
        Set a book's document fields (hash, path, status, …) in one statement, only if it has no
        document yet. Returns the updated row, or None if the book is gone or already has a document
        (a concurrent attach won).
        """
        _check_columns(fields)
        return self._update_where(book_id, fields, condition=sql.SQL("file_sha256 IS NULL"))

    def fail_interrupted(self) -> int:
        """Mark jobs left `queued`/`processing` by a previous process as failed (they died with it)."""
        with self.pool.connection() as conn:
            cursor = conn.execute(
                "UPDATE books SET ingestion_status = 'failed', "
                "ingestion_error = 'Ingestion was interrupted (server restart). Retry with reindex.', "
                "updated_at = now() WHERE ingestion_status IN ('queued', 'processing')"
            )
            return cursor.rowcount

    def delete_if_idle(self, book_id) -> Optional[dict]:
        """
        Delete the book unless the ingestion worker owns it (queued/processing), in one statement,
        so a reindex claimed between a status check and the delete can't be deleted under the worker.
        Returns the deleted row, or None if the book is missing or busy.
        """
        with self.pool.connection() as conn:
            return conn.execute(
                "DELETE FROM books WHERE id = %s AND NOT (ingestion_status = ANY(%s)) RETURNING *",
                (parse_book_id(book_id), list(BUSY_STATUSES)),
            ).fetchone()

    def _update_where(self, book_id, fields: dict, condition: Optional[sql.Composable] = None) -> Optional[dict]:
        """
        UPDATE one book's (already checked) `fields`, only if the extra `condition` holds.
        Returns the updated row, or None if no row matched; unique violations -> DuplicateBookError.
        """
        where = sql.SQL("id = %(id)s") if condition is None else sql.SQL("id = %(id)s AND {}").format(condition)
        query = sql.SQL("UPDATE books SET {}, updated_at = now() WHERE {} RETURNING *").format(
            _assignments(fields), where
        )
        with self.pool.connection() as conn:
            try:
                return conn.execute(query, {**fields, "id": parse_book_id(book_id)}).fetchone()
            except UniqueViolation as error:
                raise DuplicateBookError(_duplicate_message(error)) from error


def _check_columns(fields: dict):
    unknown = set(fields) - WRITABLE_COLUMNS
    if unknown:
        raise ValueError(f"Unknown book fields: {sorted(unknown)}")


def _assignments(fields: dict) -> sql.Composed:
    """`col = %(col)s, …` for whitelisted column names."""
    return sql.SQL(", ").join(sql.SQL("{} = {}").format(sql.Identifier(c), sql.Placeholder(c)) for c in fields)


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _duplicate_message(error: UniqueViolation) -> str:
    constraint = getattr(error.diag, "constraint_name", "") or ""
    if "isbn" in constraint:
        return "A book with this ISBN already exists."
    if "sha256" in constraint:
        return "This file has already been uploaded."
    if "external" in constraint:
        return "This book has already been imported."
    return "Duplicate book."
