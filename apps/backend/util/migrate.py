"""
Minimal SQL migration runner.

Applies `migrations/NNN_name.sql` files in filename order, each in its own
transaction, and records them in `schema_migrations`. Already-applied files are
skipped, so running it again is safe. A Postgres advisory lock prevents two
processes (e.g. several uvicorn workers) from migrating at the same time.

    uv run python -m util.migrate
"""

import hashlib
from pathlib import Path

from loguru import logger

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
_LOCK_KEY = 7_401_001  # arbitrary constant shared by every process of this app


def _checksum(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


def migrate(pool, migrations_dir: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply pending migrations. Returns the names of files applied in this run."""
    files = sorted(migrations_dir.glob("*.sql"))
    applied_now = []

    with pool.connection() as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (_LOCK_KEY,))
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    name       text PRIMARY KEY,
                    checksum   text NOT NULL,
                    applied_at timestamptz NOT NULL DEFAULT now()
                )
                """
            )
            conn.commit()
            done = {
                row["name"]: row["checksum"]
                for row in conn.execute("SELECT name, checksum FROM schema_migrations").fetchall()
            }
            conn.commit()  # end the read transaction so each migration below is its own transaction

            for path in files:
                sql = path.read_text(encoding="utf-8")
                if path.name in done:
                    if done[path.name] != _checksum(sql):
                        logger.warning(
                            "Migration {name} was edited after it was applied — create a new migration instead.",
                            name=path.name,
                        )
                    continue
                with conn.transaction():
                    conn.execute(sql)
                    conn.execute(
                        "INSERT INTO schema_migrations (name, checksum) VALUES (%s, %s)",
                        (path.name, _checksum(sql)),
                    )
                applied_now.append(path.name)
                logger.info("Applied migration {name}", name=path.name)
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (_LOCK_KEY,))
            conn.commit()

    return applied_now


if __name__ == "__main__":
    from config.base import Setting

    Setting(file=".env")
    from service import Services

    applied = migrate(Services.postgres())
    logger.info("Migrations applied: {applied}", applied=applied or "none (up to date)")
