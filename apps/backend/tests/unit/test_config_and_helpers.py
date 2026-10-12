from datetime import date, datetime
import json

import pytest

from config.base import BaseSetting
from util.helper import date_converter


def test_empty_optional_env_values_become_none(monkeypatch):
    monkeypatch.setenv("BE_SMTP_PORT", "")
    monkeypatch.setenv("BE_SMTP_USE_TLS", "")
    monkeypatch.setenv("BE_POSTGRES_URI", "")
    s = BaseSetting()
    assert s.SMTP_PORT is None
    assert s.SMTP_USE_TLS is None
    assert s.POSTGRES_URI is None


def test_date_converter_serializes_dates():
    payload = {"at": datetime(2026, 1, 2, 3, 4, 5), "day": date(2026, 1, 2)}
    assert json.loads(json.dumps(payload, default=date_converter)) == {
        "at": "2026-01-02T03:04:05",
        "day": "2026-01-02",
    }


def test_date_converter_rejects_unknown_types():
    with pytest.raises(TypeError):
        json.dumps({"x": object()}, default=date_converter)
