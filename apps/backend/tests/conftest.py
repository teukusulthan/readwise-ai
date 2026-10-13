"""
Test bootstrap.

`config.base` loads `.env` from the current working directory and `api.py`
builds the settings singleton at import time, so the environment must be
fixed *before* `api` is imported:

- chdir into an empty temp dir so a developer's real `.env` is never loaded;
- provide every required BE_* key with throwaway test values.
"""

import os
import tempfile
from pathlib import Path

import pytest
from dotenv import dotenv_values

# Real embedding service for `-m external` tests. The host is internal and never committed:
# EMBEDDING_TEST_BASE_URL wins, else the developer's own (git-ignored) apps/backend/.env.
_REAL_EMBEDDING_BASE_URL = os.environ.get("EMBEDDING_TEST_BASE_URL") or dotenv_values(
    Path(__file__).resolve().parent.parent / ".env"
).get("BE_ENGINE_EMBEDDING_BASE_URL")

_TEST_ENV = {
    "BE_ACTIVE_ROUTERS": "{}",
    "BE_BASE_RESPONSE_CASE": "camelCase",
    "BE_JWT_ACTIVE": "true",
    "BE_JWT_ALGORITH": "HS256",
    "BE_JWT_EXPIRED": "3600",
    "BE_JWT_SECRET": "test-jwt-secret-not-for-production",
    "BE_SESSION_SECRET": "test-session-secret-not-for-production",
    "BE_ENC_ACTIVE": "false",
    "BE_ENC_SECRET": "0123456789abcdef",
    "BE_ENC_SECRET_PERMISSION": "0123456789abcdef",
    "BE_CORS_ORIGINS": "http://localhost:3000",
    "BE_RATE_LIMIT_ACTIVE": "false",
    # Tests log in many times from one address; the auth budget itself is tested in test_rate_limits.py.
    "BE_RATE_LIMIT_AUTH_PER_MINUTE": "0",
    "BE_MAX_REQUEST_BODY_MB": "1",
    "BE_MAX_UPLOAD_SIZE_MB": "1",
    "BE_MONGO_URI": "mongodb://localhost:27017/?serverSelectionTimeoutMS=500",
    "BE_MONGO_DB": "library_test",
    "BE_MONGO_COLLECTION_UPLOAD": "upload",
    "BE_MONGO_COLLECTION_CONNECTION": "connection",
    "BE_MONGO_COLLECTION_GROUP": "group",
    "BE_MONGO_COLLECTION_PERMISSION": "permission",
    "BE_MONGO_COLLECTION_USER": "user",
    "BE_MONGO_COLLECTION_ROLE": "role",
    "BE_REDIS_HOST": "localhost",
    "BE_REDIS_PORT": "6380",
    "BE_REDIS_PASSWORD": "",
    "BE_REDIS_DB": "15",
    "BE_S3FS_PATH_AGENT": "s3://library-test",
    # Book library — integration tests use a separate database and collection.
    "BE_POSTGRES_URI": "postgresql://library:library@localhost:5433/library_test",
    "BE_QDRANT_URL": "http://localhost:6333",
    "BE_QDRANT_COLLECTION": "book_chunks_test",
    "BE_BOOK_STORAGE_DIR": tempfile.mkdtemp(prefix="book-storage-"),
    "BE_LLM_MODEL": "",
}

for _key, _value in _TEST_ENV.items():
    os.environ.setdefault(_key, _value)

os.chdir(tempfile.mkdtemp(prefix="backend-tests-"))

import api  # noqa: E402  (must follow the environment setup above)


@pytest.fixture(scope="session")
def app():
    return api.app


@pytest.fixture(scope="session")
def settings():
    return api.settings


@pytest.fixture(scope="session")
def embedding_base_url():
    if not _REAL_EMBEDDING_BASE_URL:
        pytest.skip("set EMBEDDING_TEST_BASE_URL or BE_ENGINE_EMBEDDING_BASE_URL in apps/backend/.env")
    return _REAL_EMBEDDING_BASE_URL
