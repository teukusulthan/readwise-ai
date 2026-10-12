"""
SQL access for `conversations` and `conversation_messages`. Only this module writes
SQL for chat history; all values go through psycopg parameters.
"""

import uuid
from typing import Iterable, Optional

from psycopg.types.json import Jsonb

from service import Services

MESSAGE_COLUMNS = {"role", "content", "mode", "grounded", "sources", "skipped_books", "model", "error", "book_ids"}
_JSON_COLUMNS = {"sources", "skipped_books"}


def parse_conversation_id(value) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise ValueError(f"Invalid conversation id: {value!r}") from None


def _uuid_list(values: Optional[Iterable]) -> list[uuid.UUID]:
    return [uuid.UUID(str(v)) for v in values or []]


class ConversationRepository:
    def __init__(self, pool=None):
        self._pool = pool

    @property
    def pool(self):
        return self._pool or Services.postgres()

    # ── conversations ────────────────────────────────────────────────

    def create(self, title: str, book_ids: Optional[Iterable] = None) -> dict:
        with self.pool.connection() as conn:
            return conn.execute(
                "INSERT INTO conversations (title, book_ids) VALUES (%s, %s) RETURNING *",
                (title, _uuid_list(book_ids)),
            ).fetchone()

    def get(self, conversation_id) -> Optional[dict]:
        with self.pool.connection() as conn:
            return conn.execute(
                "SELECT * FROM conversations WHERE id = %s", (parse_conversation_id(conversation_id),)
            ).fetchone()

    def list_recent(self, page: int = 1, size: int = 50) -> tuple[list[dict], int]:
        with self.pool.connection() as conn:
            rows = conn.execute(
                "SELECT c.*, (SELECT count(*) FROM conversation_messages m WHERE m.conversation_id = c.id)"
                " AS message_count FROM conversations c ORDER BY c.updated_at DESC, c.id"
                " LIMIT %s OFFSET %s",
                (size, (page - 1) * size),
            ).fetchall()
            total = conn.execute("SELECT count(*) AS total FROM conversations").fetchone()["total"]
        return rows, total

    def rename(self, conversation_id, title: str) -> Optional[dict]:
        with self.pool.connection() as conn:
            return conn.execute(
                "UPDATE conversations SET title = %s, updated_at = now() WHERE id = %s RETURNING *",
                (title, parse_conversation_id(conversation_id)),
            ).fetchone()

    def delete(self, conversation_id) -> Optional[dict]:
        with self.pool.connection() as conn:
            return conn.execute(
                "DELETE FROM conversations WHERE id = %s RETURNING *", (parse_conversation_id(conversation_id),)
            ).fetchone()

    # ── messages ─────────────────────────────────────────────────────

    def add_message(self, conversation_id, fields: dict) -> dict:
        """Append a message and bump the conversation (and its book scope, for user messages)."""
        unknown = set(fields) - MESSAGE_COLUMNS
        if unknown:
            raise ValueError(f"Unknown message fields: {sorted(unknown)}")
        values = {
            key: Jsonb(value) if key in _JSON_COLUMNS else _uuid_list(value) if key == "book_ids" else value
            for key, value in fields.items()
        }
        columns = ["conversation_id", *values]
        params = {"conversation_id": parse_conversation_id(conversation_id), **values}
        insert = "INSERT INTO conversation_messages ({}) VALUES ({}) RETURNING *".format(
            ", ".join(columns), ", ".join(f"%({c})s" for c in columns)  # columns come from MESSAGE_COLUMNS only
        )
        with self.pool.connection() as conn:
            row = conn.execute(insert, params).fetchone()
            if fields.get("role") == "user":
                conn.execute("UPDATE conversations SET updated_at = now(), book_ids = %(book_ids)s WHERE id = %(id)s",
                             {"book_ids": values.get("book_ids", []), "id": params["conversation_id"]})
            else:
                conn.execute("UPDATE conversations SET updated_at = now() WHERE id = %s", (params["conversation_id"],))
        return row

    def messages(self, conversation_id) -> list[dict]:
        with self.pool.connection() as conn:
            return conn.execute(
                "SELECT * FROM conversation_messages WHERE conversation_id = %s ORDER BY seq",
                (parse_conversation_id(conversation_id),),
            ).fetchall()

    def recent_messages(self, conversation_id, limit: int) -> list[dict]:
        """The last `limit` messages, oldest first."""
        with self.pool.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM conversation_messages WHERE conversation_id = %s ORDER BY seq DESC LIMIT %s",
                (parse_conversation_id(conversation_id), limit),
            ).fetchall()
        return list(reversed(rows))
