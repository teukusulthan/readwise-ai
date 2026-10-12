from types import SimpleNamespace

import pytest

import service.llm as llm
from util.http_errors import ServiceUnavailableError


@pytest.fixture
def configured(settings, monkeypatch):
    monkeypatch.setattr(settings, "LLM_MODEL", "openrouter/openai/gpt-oss-120b")
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")


def _fake_agent(monkeypatch, output):
    from agno.agent import Agent

    monkeypatch.setattr(Agent, "run", lambda self, prompt, **kw: output)


def test_returns_model_text(configured, monkeypatch):
    _fake_agent(monkeypatch, SimpleNamespace(status=SimpleNamespace(value="COMPLETED"), content="It was 1847 [1]."))
    assert llm.agno_generator()("system", "user") == "It was 1847 [1]."


@pytest.mark.parametrize("detail, expected", [
    ('litellm.AuthenticationError: OpenrouterException - {"error":{"code":401}}', "rejected the API key"),
    ("litellm.RateLimitError: 429 Too Many Requests", "rate-limited"),
    ("litellm.NotFoundError: model not found", "was not found"),
    ("something else broke", "See server logs"),
])
def test_agno_error_output_is_never_returned_as_an_answer(configured, monkeypatch, detail, expected):
    # Agno reports provider failures as a RunOutput with status ERROR instead of raising.
    _fake_agent(monkeypatch, SimpleNamespace(status=SimpleNamespace(value="ERROR"), content=detail))
    with pytest.raises(ServiceUnavailableError, match=expected) as raised:
        llm.agno_generator()("system", "user")
    assert "Openrouter" not in str(raised.value)  # provider internals stay in the logs


def test_requires_configured_model(settings, monkeypatch):
    monkeypatch.setattr(settings, "LLM_MODEL", None)
    with pytest.raises(ServiceUnavailableError):
        llm.agno_generator()


def test_unset_sampling_params_are_not_sent(settings, monkeypatch):
    """Models with fixed sampling (e.g. Kimi Code) reject any temperature/top_p: empty settings send none."""
    from service.llm import _model

    monkeypatch.setattr(settings, "LLM_MODEL", "openai/kimi-for-coding")
    monkeypatch.setattr(settings, "LLM_TEMPERATURE", None)
    monkeypatch.setattr(settings, "LLM_TOP_P", None)
    params = _model().get_request_params()
    assert "temperature" not in params and "top_p" not in params

    monkeypatch.setattr(settings, "LLM_TEMPERATURE", 0.2)
    monkeypatch.setattr(settings, "LLM_TOP_P", 0.9)
    params = _model().get_request_params()
    assert params["temperature"] == 0.2 and params["top_p"] == 0.9
