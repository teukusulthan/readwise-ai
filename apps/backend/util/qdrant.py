import threading

from config.base import settings
from qdrant_client import QdrantClient


class QdrantService:

    instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            with cls._lock:
                if cls.instance is None:
                    if not settings.QDRANT_URL:
                        raise RuntimeError("QDRANT_URL is not configured (set BE_QDRANT_URL).")
                    cls.instance = QdrantClient(
                        url=settings.QDRANT_URL,
                        api_key=settings.QDRANT_API_KEY or None,
                    )
        return cls.instance
