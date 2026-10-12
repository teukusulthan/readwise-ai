import threading
import time

import pytest
from pydantic.v1 import ValidationError

import api
from config.base import BaseSetting
from config.routers import LEGACY_ROUTERS, LIBRARY_ROUTERS, select_routers

GOOD_SECRET = "x" * 32


def _mounted_paths(app):
    return {getattr(route, "path", "") for route in app.routes}


# --- router selection -------------------------------------------------------------

def test_default_mounts_library_routers_only():
    selected = select_routers("", None)
    assert selected == set(LIBRARY_ROUTERS)
    assert {"health", "auth", "book", "search", "chat", "conversation"} <= selected
    assert not selected & set(LEGACY_ROUTERS)


def test_explicit_env_list_mounts_exactly_that_plus_health():
    assert select_routers("auth, user", None) == {"auth", "user", "health"}
    assert "monitoring" in select_routers("monitoring", None)


def test_cli_routers_filter_the_default_and_can_opt_into_legacy():
    assert select_routers("", "auth,book") == {"auth", "book", "health"}
    assert select_routers("", "user[get-all:get-one]") == {"user", "health"}


def test_cli_routers_narrow_the_env_list():
    assert select_routers("auth,user,book", "auth") == {"auth", "health"}


def test_running_app_has_no_legacy_surface_by_default(app):
    paths = _mounted_paths(app)
    assert "/health" in paths
    assert "/monitoring/threadpool" not in paths
    assert not any(p.startswith(("/user", "/role", "/group", "/permission", "/upload")) for p in paths)
    assert any(p.startswith("/auth") for p in paths)
    assert any(p.startswith("/book") for p in paths)


# --- --reload flag ------------------------------------------------------------------

def test_reload_flag_defaults_to_off():
    parser = api.build_argument_parser()
    assert parser.parse_args([]).reload is False
    assert parser.parse_args(["--reload"]).reload is True
    assert parser.parse_args(["--port", "8025", "--reload"]).port == "8025"


# --- secret validation ----------------------------------------------------------------

@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("BE_JWT_ACTIVE", "true")
    monkeypatch.setenv("BE_JWT_SECRET", GOOD_SECRET)
    monkeypatch.setenv("BE_ENC_ACTIVE", "false")
    monkeypatch.setenv("BE_ENC_SECRET", "")
    return monkeypatch


def test_valid_secrets_are_accepted(env):
    assert BaseSetting().JWT_SECRET == GOOD_SECRET


@pytest.mark.parametrize("secret", ["", "short", "x" * 31])
def test_short_jwt_secret_fails_when_jwt_active(env, secret):
    env.setenv("BE_JWT_SECRET", secret)
    with pytest.raises(ValidationError) as err:
        BaseSetting()
    message = str(err.value)
    assert "BE_JWT_SECRET" in message
    assert "secrets.token_urlsafe(48)" in message


def test_short_jwt_secret_is_fine_when_jwt_inactive(env):
    env.setenv("BE_JWT_ACTIVE", "false")
    env.setenv("BE_JWT_SECRET", "")
    assert BaseSetting().JWT_ACTIVE is False


def test_short_enc_secret_fails_only_when_enc_active(env):
    env.setenv("BE_ENC_SECRET", "0123456789abcdef")
    assert BaseSetting().ENC_ACTIVE is False
    env.setenv("BE_ENC_ACTIVE", "true")
    with pytest.raises(ValidationError) as err:
        BaseSetting()
    assert "BE_ENC_SECRET" in str(err.value)
    env.setenv("BE_ENC_SECRET", "y" * 48)  # not a valid AES key size
    with pytest.raises(ValidationError):
        BaseSetting()
    env.setenv("BE_ENC_SECRET", "y" * 32)
    assert BaseSetting().ENC_SECRET == "y" * 32


# --- singletons under threads --------------------------------------------------------------

def _hammer(service_cls, monkeypatch, build_attr):
    created = []

    def slow_factory(*args, **kwargs):
        created.append(1)
        time.sleep(0.05)  # widen the race window
        return object()

    monkeypatch.setattr(service_cls, "instance", None)
    monkeypatch.setattr(build_attr[0], build_attr[1], slow_factory)
    results = []
    barrier = threading.Barrier(16)

    def worker():
        barrier.wait()
        results.append(service_cls())

    threads = [threading.Thread(target=worker) for _ in range(16)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(created) == 1
    assert len({id(r) for r in results}) == 1


def test_postgres_pool_is_created_once_under_threads(monkeypatch, settings):
    import util.postgres as module

    monkeypatch.setattr(settings, "POSTGRES_URI", "postgresql://u:p@localhost/db")
    _hammer(module.PostgresService, monkeypatch, (module, "ConnectionPool"))


def test_qdrant_client_is_created_once_under_threads(monkeypatch):
    import util.qdrant as module

    _hammer(module.QdrantService, monkeypatch, (module, "QdrantClient"))


def test_embedding_client_is_created_once_under_threads(monkeypatch, settings):
    import util.embedding as module

    monkeypatch.setattr(settings, "ENGINE_EMBEDDING_BASE_URL", "http://embed.invalid/v1")
    monkeypatch.setattr(settings, "ENGINE_EMBEDDING_MODEL", "model")
    _hammer(module.EmbeddingService, monkeypatch, (module, "EmbeddingClient"))


def test_redis_clients_are_created_once_under_threads(monkeypatch):
    import util.redis as module

    _hammer(module.RedisService, monkeypatch, (module.redis, "Redis"))
    _hammer(module.AsyncRedisService, monkeypatch, (module, "AsyncRedis"))
