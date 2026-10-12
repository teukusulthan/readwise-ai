import threading

from config.base import settings
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


class PostgresService:
    """
    Process-wide psycopg 3 connection pool.

    Usage:
        with Services.postgres().connection() as conn:
            conn.execute("SELECT 1")

    Pool sizing: sync endpoints and the ingestion worker run on a thread pool of
    `MAX_THREADS_WORKERS` threads (default 64), but each request holds a connection only
    for the duration of its queries. `POSTGRES_POOL_MAX_SIZE` (default 10) is therefore
    deliberately far smaller than the thread count: excess threads wait on the pool
    instead of opening more server connections. Raise it if requests queue on the pool.

    Creation is double-checked under a lock so concurrent first requests build one pool.
    """

    instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            with cls._lock:
                if cls.instance is None:
                    if not settings.POSTGRES_URI:
                        raise RuntimeError("POSTGRES_URI is not configured (set BE_POSTGRES_URI).")
                    cls.instance = ConnectionPool(
                        conninfo=settings.POSTGRES_URI,
                        min_size=settings.POSTGRES_POOL_MIN_SIZE,
                        max_size=settings.POSTGRES_POOL_MAX_SIZE,
                        kwargs={"row_factory": dict_row},
                        open=True,
                        name="backend",
                    )
        return cls.instance
