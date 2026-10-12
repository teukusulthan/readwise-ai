from config.base import settings
from pymongo import MongoClient


class MongoService:

    instance = None

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = MongoClient(settings.MONGO_URI)
        return cls.instance
