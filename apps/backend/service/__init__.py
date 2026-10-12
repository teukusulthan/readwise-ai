

from loguru import logger
from config.base import settings as settings_conf
from util.embedding import EmbeddingService
from util.mongo import MongoService
from util.postgres import PostgresService
from util.qdrant import QdrantService
from util.s3_filesystem import Boto3
from util.redis import (
    RedisService,
    AsyncRedisService,
    NewRedisService,
)

def change_fields(
    datum: dict, replace_fields: dict = {}, add_fields: dict = {}
) -> dict:
    for new_field, old_field in replace_fields.items():
        if old_field in datum:
            datum[new_field] = datum.pop(old_field)

    for new_field, value in add_fields.items():
        if isinstance(value, str) and str(value).startswith("$$"):
            value = datum.get(str(value).removeprefix("$$"), None)
        datum[new_field] = value

    return datum


def change_field_id(data, replace_fields: dict = {}, add_fields: dict = {}):
    if isinstance(data, list):
        for datum in data:
            replace_fields["id"] = "_id"
            datum = change_fields(datum, replace_fields, add_fields)

    elif isinstance(data, dict):
        replace_fields["id"] = "_id"
        data = change_fields(data, replace_fields, add_fields)

    return data


class BaseMongoRepository:
    def __init__(self):
        self.mongo = Services.mongo()

    def get_collection(self, collection_name: str, db: str = ""):
        db_name = db or settings_conf.MONGO_DB

        logger.info(
            f"{collection_name} Using 'default', with db : {db_name}"
        )

        return self.mongo[db_name][collection_name]

    def get_collection_by_db(self, db: str, collection_name: str):
        db_name = db

        logger.info(f"{collection_name} Using 'default', with db : {db_name}")

        return self.mongo[db_name][collection_name]

    def get_database(self, collection_name: str):
        db_name = settings_conf.MONGO_DB

        return self.mongo[db_name]

    def get_database_name(self, collection_name: str):
        db_name = settings_conf.MONGO_DB

        return db_name


class Services:


    @staticmethod
    def mongo():
        return MongoService()

    @staticmethod
    def postgres():
        return PostgresService()

    @staticmethod
    def qdrant():
        return QdrantService()

    @staticmethod
    def embedding():
        return EmbeddingService()

    @staticmethod
    def boto3():
        return Boto3()

    @staticmethod
    def redis():
        return RedisService()

    @staticmethod
    def new_redis(db: int = None):
        return NewRedisService(db=db)

    @staticmethod
    def a_redis():
        return AsyncRedisService()

