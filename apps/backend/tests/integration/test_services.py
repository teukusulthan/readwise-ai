"""Runs only against the docker compose stack: `uv run pytest -m integration`."""

import pytest

from service.health import Health

pytestmark = pytest.mark.integration


def test_all_backing_services_ready(settings, monkeypatch):
    monkeypatch.setattr(settings, "POSTGRES_URI", "postgresql://library:library@localhost:5433/library")
    monkeypatch.setattr(settings, "QDRANT_URL", "http://localhost:6333")
    checks = Health().check_all()
    # The embedding service is external to compose; it is covered by tests/external.
    compose_checks = {name: checks[name] for name in ("mongo", "redis", "postgres", "qdrant")}
    assert all(check["status"] == "ok" for check in compose_checks.values()), checks
