from config.base import settings
import redis
from redis.asyncio import Redis as AsyncRedis


class RedisService:

    instance = None

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = redis.Redis(host=settings.REDIS_HOST,
                                       port=settings.REDIS_PORT,
                                       password=settings.REDIS_PASSWORD,
                                       decode_responses=True,
                                       db=settings.REDIS_DB)
        return cls.instance


class NewRedisService:
    def __init__(self, db=None):
        db = db if db is not None else settings.REDIS_DB
        self.client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
            db=db,
        )


class AsyncRedisService:

    instance = None

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = AsyncRedis(host=settings.REDIS_HOST,
                                       port=settings.REDIS_PORT,
                                       password=settings.REDIS_PASSWORD,
                                       decode_responses=True,
                                       db=settings.REDIS_DB)
        return cls.instance


class RedisConfigHandlerService:

    instance = None

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = redis.Redis(host=settings.REDIS_HOST,
                                       port=settings.REDIS_PORT,
                                       password=settings.REDIS_PASSWORD,
                                       decode_responses=True,
                                       db=settings.REDIS_DB_CONFIG_HANDLER)
        return cls.instance


class AsyncRedisAIAssistantService:

    instance = None

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = AsyncRedis(host=settings.REDIS_HOST_AI_ASSISTANT,
                                       port=settings.REDIS_PORT_AI_ASSISTANT,
                                       password=settings.REDIS_PASSWORD_AI_ASSISTANT,
                                       decode_responses=True,
                                       db=settings.REDIS_DB_AI_ASSISTANT,
                                       socket_keepalive=True,
                                       health_check_interval=30)
        return cls.instance
