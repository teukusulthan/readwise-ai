import re
from dotenv import dotenv_values
from pydantic.v1 import BaseSettings, Field, root_validator, validator
from dotenv import load_dotenv
from loguru import logger
import os
from typing import Optional

logger.debug("Status load env {e}", e=load_dotenv(".env", override=True))

# All env keys in `.env` / `.env.example` are namespaced with this prefix
# (e.g. BE_MONGO_URI). Field names in `BaseSetting` stay unprefixed, so app
# code keeps reading `settings.MONGO_URI`.
ENV_PREFIX = "BE_"

MIN_SECRET_LENGTH = 32
_SECRET_HINT = 'generate one with: python -c "import secrets; print(secrets.token_urlsafe(48))"'


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
    # Service credential for system-to-system calls (the MCP server, seed scripts): a request whose
    # `X-Internal-Token` header equals it is authorised as the principal "service:internal" while
    # JWT_ACTIVE is true. It reads the shared catalog/search/ask but has no conversations of its own.
    # Empty = disabled. When set, at least 32 characters.
    INTERNAL_TOKEN: str = Field(default="")
    # /auth/register: true (default) = the boilerplate flow (MX + Proofy check, OTP mail over SMTP, then
    # /auth/verification). false = development only: the account is created at once, no mail is sent.
    AUTH_EMAIL_VERIFICATION: bool = Field(default=True)
    # Self-service sign-up. true (default) = /auth/register, /auth/verification and (when Google OAuth is
    # configured) /auth/google/register create accounts. false = every registration endpoint answers
    # 403 "Registration is closed."; existing accounts still log in (accounts are then made by an admin).
    AUTH_REGISTRATION_OPEN: bool = Field(default=True)
    # `Secure` flag of the auth cookies (`token`, `refresh_token`). true (default) = sent over HTTPS only (browsers
    # also accept them from http://localhost). false = development only, for plain-HTTP access from another host
    # (e.g. http://<LAN IP>:3000), where browsers drop Secure cookies and login cannot stick.
    AUTH_COOKIE_SECURE: bool = Field(default=True)

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
    # Per-route budgets (requests per minute, per authenticated user or else per client IP), on top of
    # the global limit above. 0 disables that route's limit. See middleware/route_limits.py.
    RATE_LIMIT_UPLOAD_PER_MINUTE: int = Field(default=20)
    RATE_LIMIT_CHAT_PER_MINUTE: int = Field(default=30)
    RATE_LIMIT_SEARCH_PER_MINUTE: int = Field(default=60)
    # Comma-separated CIDRs/IPs of reverse proxies whose X-Forwarded-For header is believed
    # (empty = never trust it; the socket peer is the client). See util/client_ip.py.
    TRUSTED_PROXIES: str = Field(default="")
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
    # Upload/reindex is refused with HTTP 429 while this many books already wait in `queued` (0 = no cap).
    INGESTION_MAX_QUEUED: int = Field(default=50)
    # Jobs left queued/processing by a restart are re-queued at startup while the book has been claimed
    # fewer than this many times; at the cap they are marked failed (0 = never resume, always fail).
    INGESTION_MAX_ATTEMPTS: int = Field(default=3)
    # Docling runs in a child process (a crash or runaway PDF cannot take the API down).
    # Wall-clock limit per parse; on timeout the child is killed and the book marked failed.
    INGESTION_PARSE_TIMEOUT_SECONDS: int = Field(default=1800)
    # Address-space cap for the child (RLIMIT_AS), in MB; 0 = no cap. Virtual memory: Docling needed
    # more than 6144 for a 3-page PDF (12288 worked).
    INGESTION_PARSE_MAX_MEMORY_MB: int = Field(default=0)
    # The child is replaced after this many parses: bounds leaks, amortises the model load.
    INGESTION_PARSE_TASKS_PER_CHILD: int = Field(default=20)
    DOCLING_DO_OCR: bool = Field(default=False)
    # When a parse with OCR off yields no text (scanned PDF), parse that book once more with OCR on.
    DOCLING_OCR_FALLBACK: bool = Field(default=True)
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
    # Search fetches topK × this many candidates (same threshold), then keeps topK with at most
    # RETRIEVAL_MAX_PER_SECTION passages per section (book + heading path): near-duplicate passages
    # of one chapter otherwise take every slot and the chapter that answers is missed.
    # RETRIEVAL_MAX_PER_SECTION=0 disables the cap (plain top-k).
    RETRIEVAL_CANDIDATE_MULTIPLIER: int = Field(default=4)
    RETRIEVAL_MAX_PER_SECTION: int = Field(default=2)

    # Answer policy. True (hybrid): books first and cited, plus the model's general knowledge in a separate,
    # labeled section — and a labeled general-knowledge answer when the books have nothing. False (strict):
    # answer only from the passages, otherwise say "not enough information".
    RAG_ALLOW_GENERAL_KNOWLEDGE: bool = Field(default=True)

    # Resumable chat sessions in Redis (service/chat_session.py): how long a session's events stay
    # replayable after its last activity, and after how many seconds without a heartbeat a
    # "running" session counts as dead (its server process stopped).
    CHAT_SESSION_TTL_SECONDS: int = Field(default=3600)
    CHAT_SESSION_STALE_SECONDS: int = Field(default=30)
    # Answers generated at the same time (across all users and workers); beyond it a new chat turn gets
    # HTTP 429 (0 = no cap).
    CHAT_MAX_CONCURRENT_SESSIONS: int = Field(default=20)

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
    # Passed to LiteLLM on every request: whole-request timeout and retries on transient failures.
    LLM_TIMEOUT_SECONDS: float = Field(default=120)
    LLM_NUM_RETRIES: int = Field(default=2)
    # Streaming only: max wait from request start to the first content/reasoning token.
    LLM_FIRST_TOKEN_TIMEOUT_SECONDS: float = Field(default=90)

    # Book metadata import
    OPENLIBRARY_BASE_URL: str = Field(default="https://openlibrary.org")

    @validator("*", pre=True)
    def empty_optional_to_none(cls, value, field):
        # `BE_SMTP_PORT=` in .env means "unset", not an invalid integer.
        if value == "" and field.allow_none:
            return None
        return value

    @validator("TRUSTED_PROXIES")
    def trusted_proxies_are_cidrs(cls, value):
        import ipaddress

        for item in (value or "").split(","):
            if item.strip():
                try:
                    ipaddress.ip_network(item.strip(), strict=False)
                except ValueError:
                    raise ValueError(f"{ENV_PREFIX}TRUSTED_PROXIES: {item.strip()!r} is not an IP address or CIDR") from None
        return value

    @root_validator(skip_on_failure=True)
    def secrets_are_strong_when_active(cls, values):
        # PyJWT signs happily with an empty key, so an unset secret would silently mint forgeable tokens.
        if values.get("JWT_ACTIVE") and len(values.get("JWT_SECRET") or "") < MIN_SECRET_LENGTH:
            raise ValueError(
                f"{ENV_PREFIX}JWT_SECRET must be at least {MIN_SECRET_LENGTH} characters when "
                f"{ENV_PREFIX}JWT_ACTIVE is true; {_SECRET_HINT}"
            )
        internal_token = values.get("INTERNAL_TOKEN") or ""
        if internal_token and len(internal_token) < MIN_SECRET_LENGTH:
            raise ValueError(
                f"{ENV_PREFIX}INTERNAL_TOKEN must be empty (disabled) or at least {MIN_SECRET_LENGTH} "
                f"characters; {_SECRET_HINT}"
            )
        # ENC_SECRET is used as an AES key: 48 chars (token_urlsafe(48)) would crash every response.
        if values.get("ENC_ACTIVE") and len(values.get("ENC_SECRET") or "") != MIN_SECRET_LENGTH:
            raise ValueError(
                f"{ENV_PREFIX}ENC_SECRET is an AES-256 key and must be exactly {MIN_SECRET_LENGTH} "
                'characters; generate one with: python -c "import secrets; print(secrets.token_hex(16))"'
            )
        return values

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
