from config.base import settings
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


class PostgresService:
    """
    Process-wide psycopg 3 connection pool.

    Usage:
        with Services.postgres().connection() as conn:
            conn.execute("SELECT 1")
    """

    instance = None

    def __new__(cls, *args, **kwargs):
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
