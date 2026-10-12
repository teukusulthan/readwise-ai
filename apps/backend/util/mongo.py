import threading

from config.base import settings
from pymongo import MongoClient


class MongoService:

    instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            with cls._lock:
                if cls.instance is None:
                    cls.instance = MongoClient(settings.MONGO_URI)
        return cls.instance
