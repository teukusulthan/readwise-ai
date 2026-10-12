import pymongo
from loguru import logger

from config.base import settings
from service import Services


class Health:
    """Readiness checks for backing services. Errors are reported by type only, never by message."""

    def check_all(self) -> dict:
        return {
            "mongo": self._run(self._mongo),
            "redis": self._run(self._redis),
            "postgres": self._run(self._postgres, configured=bool(settings.POSTGRES_URI)),
            "qdrant": self._run(self._qdrant, configured=bool(settings.QDRANT_URL)),
            "embedding": self._run(self._embedding, configured=bool(settings.ENGINE_EMBEDDING_BASE_URL)),
        }

    @staticmethod
    def _run(check, configured: bool = True) -> dict:
        if not configured:
            return {"status": "not_configured"}
        try:
            check()
            return {"status": "ok"}
        except Exception as error:
            logger.warning("Health check {name} failed: {error!r}", name=check.__name__, error=error)
            return {"status": "error", "error": type(error).__name__}

    @staticmethod
    def _mongo():
        with pymongo.timeout(3):
            Services.mongo().admin.command("ping")

    @staticmethod
    def _redis():
        Services.redis().ping()

    @staticmethod
    def _postgres():
        with Services.postgres().connection(timeout=3) as conn:
            conn.execute("SELECT 1")

    @staticmethod
    def _qdrant():
        Services.qdrant().get_collections()

    @staticmethod
    def _embedding():
        Services.embedding().ping()
