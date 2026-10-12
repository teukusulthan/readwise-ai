import re
from dotenv import dotenv_values
from pydantic.v1 import BaseSettings, Field, validator
from dotenv import load_dotenv
from loguru import logger
import os
from typing import Optional

logger.debug("Status load env {e}", e=load_dotenv(".env", override=True))

# All env keys in `.env` / `.env.example` are namespaced with this prefix
# (e.g. BE_MONGO_URI). Field names in `BaseSetting` stay unprefixed, so app
# code keeps reading `settings.MONGO_URI`.
ENV_PREFIX = "BE_"


def strip_env_prefix(key):
    return key[len(ENV_PREFIX):] if key.startswith(ENV_PREFIX) else key


def build_routers(routers):
    result = {}
    for router in routers.split(","):
        selected_end_point = re.findall(r"\[([^\]]+)\]", router)
        if selected_end_point:
            router = router.split("[")[0]
            result[router] = selected_end_point[0].split(":")
        else:
            result[router] = None

    return result


class BaseSetting(BaseSettings):
    
    EXCLUDE_UPLOAD_EXTENSIONS: Optional[str] = Field(default=None)
    
    KAFKA_SERVER: Optional[str] = Field(default=None)
    KAFKA_TOPIC_FILE_EXTRACTION: Optional[str] = Field(default=None)
    KAFKA_MAX_REQUEST: Optional[int] = Field(default=1048576)

    MONGO_URI: str
    MONGO_DB: str
    
    
    MONGO_COLLECTION_USER: str
    MONGO_COLLECTION_GROUP: str   
    MONGO_COLLECTION_PERMISSION: str
    MONGO_COLLECTION_ROLE: str

    MONGO_COLLECTION_UPLOAD: str
    MONGO_COLLECTION_CONNECTION: str

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str
    REDIS_DB: int

    GOOGLE_CLIENT_ID: Optional[str] = Field(default=None)
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(default=None)


    JWT_SECRET: str
    JWT_ALGORITH: str
    JWT_EXPIRED: int
    JWT_REFRESH: int = Field(default=604800)
    JWT_ACTIVE: bool

    BASE_RESPONSE_CASE: str

    ACTIVE_ROUTERS: dict
    ENABLED_ROUTERS: str = Field(default="")


    PROOFY_API_KEY: Optional[str] = Field(default=None)
    PROOFY_URL: Optional[str] = Field(default=None)

    ENC_ACTIVE: bool = Field(default=False)
    ENC_SECRET: str
    ENC_SECRET_PERMISSION: str

    RATE_LIMIT: int = Field(default=100000)
    RATE_LIMIT_WINDOW: int = Field(default=60)
    ACCOUNT_LOCK_TIME: int = Field(default=600)
    ACCOUNT_FAIL_LIMIT: int = Field(default=5)

    COPYRIGHT: str = Field(
        default="Copyright (c) 2026 Readwise AI. All Rights Reserved."
    )


    MAX_THREADS_WORKERS: int = Field(default=64)
    SMTP_EMAIL: Optional[str] = Field(default=None)
    SMTP_PASSWORD: Optional[str] = Field(default=None)
    SMTP_HOST: Optional[str] = Field(default=None)
    SMTP_PORT: Optional[int] = Field(default=None)
    SMTP_USE_TLS: Optional[bool] = Field(default=None)
    SMTP_TYPE: Optional[str] = Field(default=None)
    SMTP_SENDER: Optional[str] = Field(default=None)
    S3FS_KEY: Optional[str] = Field(default=None)
    S3FS_SECRET: Optional[str] = Field(default=None)
    S3FS_END_POINT: Optional[str] = Field(default=None)
    S3FS_PATH_AGENT: Optional[str] = Field(default=None)

    # HTTP hardening
    # Comma-separated allowed browser origins. "*" disables credentialed CORS.
    CORS_ORIGINS: str = Field(default="http://localhost:3000,http://localhost:3001")
    # Session cookie secret (Google OAuth flow). Must differ from JWT_SECRET.
    SESSION_SECRET: Optional[str] = Field(default=None)
    MAX_REQUEST_BODY_MB: int = Field(default=100)
    MAX_UPLOAD_SIZE_MB: int = Field(default=100)
    RATE_LIMIT_ACTIVE: bool = Field(default=True)

    # PostgreSQL — relational data for new domains
    POSTGRES_URI: Optional[str] = Field(default=None)
    POSTGRES_POOL_MIN_SIZE: int = Field(default=1)
    POSTGRES_POOL_MAX_SIZE: int = Field(default=10)

    # Qdrant — vector store
    QDRANT_URL: Optional[str] = Field(default=None)
    QDRANT_API_KEY: Optional[str] = Field(default=None)

    # Company embedding service — Hugging Face TEI, OpenAI-compatible /v1/embeddings
    ENGINE_EMBEDDING_BASE_URL: Optional[str] = Field(default=None)
    ENGINE_EMBEDDING_MODEL: Optional[str] = Field(default=None)
    ENGINE_EMBEDDING_DIMENSIONS: int = Field(default=1024)
    # Server-side limit is 32 inputs per request (TEI max_client_batch_size).
    ENGINE_EMBEDDING_BATCH_SIZE: int = Field(default=32)
    ENGINE_EMBEDDING_TIMEOUT_SECONDS: float = Field(default=60)
    ENGINE_EMBEDDING_MAX_RETRIES: int = Field(default=3)
    # Instruction prepended to search queries only (Qwen3 format: "Instruct: <task>\nQuery: <text>").
    # Measured on the sample book: relevant top scores 0.53-0.77 vs off-topic <= 0.39 with it,
    # 0.42-0.72 vs 0.34 without. Empty = queries embedded as-is.
    ENGINE_EMBEDDING_QUERY_INSTRUCTION: Optional[str] = Field(
        default="Given a question, retrieve passages from a book that answer the question"
    )

    # Book library — storage & ingestion
    # Uploaded PDFs live here as <book_id>.pdf (relative paths resolve from apps/backend/).
    BOOK_STORAGE_DIR: str = Field(default="storage/books")
    MAX_PDF_PAGES: int = Field(default=1500)
    QDRANT_COLLECTION: str = Field(default="book_chunks")
    # Chunk size in tokens of the embedding model's tokenizer (HybridChunker).
    CHUNK_MAX_TOKENS: int = Field(default=512)
    # Hugging Face tokenizer matching ENGINE_EMBEDDING_MODEL, used to size chunks.
    CHUNK_TOKENIZER: str = Field(default="Qwen/Qwen3-Embedding-0.6B")
    # Docling is CPU/RAM heavy — keep concurrent ingestions low.
    INGESTION_WORKERS: int = Field(default=1)
    DOCLING_DO_OCR: bool = Field(default=False)
    DOCLING_DO_TABLE_STRUCTURE: bool = Field(default=True)
    # Parse big PDFs in windows of N pages so memory stays bounded (a 152-page book parsed in one
    # go reached 3.2 GB RSS). Page numbers stay absolute; headings carry over between windows.
    DOCLING_PAGE_WINDOW: int = Field(default=20)
    # CPU threads Docling may use (the rest of the machine stays responsive).
    DOCLING_NUM_THREADS: int = Field(default=8)
    # Pages the layout model processes per batch. Measured fastest at 1 on an 8-core CPU (higher
    # values use more RAM and were slower); output is identical.
    DOCLING_LAYOUT_BATCH_SIZE: int = Field(default=1)

    # Retrieval
    RETRIEVAL_TOP_K: int = Field(default=8)
    # Chunks scoring below this cosine similarity are treated as irrelevant.
    RETRIEVAL_MIN_SCORE: float = Field(default=0.45)

    # Answer policy. True (hybrid): books first and cited, plus the model's general knowledge in a separate,
    # labeled section — and a labeled general-knowledge answer when the books have nothing. False (strict):
    # answer only from the passages, otherwise say "not enough information".
    RAG_ALLOW_GENERAL_KNOWLEDGE: bool = Field(default=True)

    # Resumable chat sessions in Redis (service/chat_session.py): how long a session's events stay
    # replayable after its last activity, and after how many seconds without a heartbeat a
    # "running" session counts as dead (its server process stopped).
    CHAT_SESSION_TTL_SECONDS: int = Field(default=3600)
    CHAT_SESSION_STALE_SECONDS: int = Field(default=30)

    # Chat: earlier question/answer pairs given to the LLM so follow-up questions make sense.
    CHAT_HISTORY_TURNS: int = Field(default=3)

    # LLM (LiteLLM model string, e.g. "openai/gpt-4o-mini", "openrouter/<model>")
    LLM_MODEL: Optional[str] = Field(default=None)
    LLM_API_KEY: Optional[str] = Field(default=None)
    LLM_API_BASE: Optional[str] = Field(default=None)
    # Empty = don't send it (provider default). Some models only accept their own fixed values.
    LLM_TEMPERATURE: Optional[float] = Field(default=0.1)
    LLM_TOP_P: Optional[float] = Field(default=None)
    # Reasoning models (e.g. Nemotron) spend part of this on hidden "thinking" (measured: 300-1300 tokens),
    # so a small budget can leave an empty or cut-off answer.
    LLM_MAX_TOKENS: int = Field(default=4000)

    # Book metadata import
    OPENLIBRARY_BASE_URL: str = Field(default="https://openlibrary.org")

    @validator("*", pre=True)
    def empty_optional_to_none(cls, value, field):
        # `BE_SMTP_PORT=` in .env means "unset", not an invalid integer.
        if value == "" and field.allow_none:
            return None
        return value

    class Config:
        env_file = ".env"
        env_prefix = ENV_PREFIX


class Setting:
    instance = None

    def __new__(cls, *args, **kwargs):
        global settings
        if cls.instance is None:
            if kwargs.get("file"):
                file_env = dotenv_values(kwargs["file"])
                current_env = BaseSetting().dict()
                env_values = {}
                for _key in file_env.keys():
                    if not _key.startswith(ENV_PREFIX):
                        logger.warning(
                            "Ignoring env key {k} — expected {p} prefix", k=_key, p=ENV_PREFIX
                        )
                        continue
                    _field = strip_env_prefix(_key)
                    if _field in current_env:
                        env_values[_field] = os.getenv(_key, "")

                if kwargs.get("update_env"):
                    new_env = {}
                    for env in kwargs.get("update_env").split(" "):
                        _key, _, _value = env.partition("=")
                        _field = strip_env_prefix(_key)
                        if _field in env_values:
                            new_env[_field] = _value
                    env_values.update(new_env)

                if kwargs.get("routers"):
                    env_values["ACTIVE_ROUTERS"] = build_routers(kwargs.get("routers"))
                else:
                    env_values["ACTIVE_ROUTERS"] = ""
                cls.instance = BaseSetting(**env_values)
                settings = cls.instance
        return cls.instance


settings = Setting()
