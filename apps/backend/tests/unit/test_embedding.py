import json

import httpx
import pytest

from util.embedding import EmbeddingClient, EmbeddingError

DIM = 4


def _vector(seed: int) -> list[float]:
    return [float(seed)] * DIM


def _make_client(handler, **overrides) -> EmbeddingClient:
    options = dict(base_url="http://embed.test/v1", model="test-model", dimensions=DIM, batch_size=3,
                   max_retries=2, backoff_seconds=0, transport=httpx.MockTransport(handler))
    options.update(overrides)
    return EmbeddingClient(**options)


def _ok(request: httpx.Request, shuffle: bool = False) -> httpx.Response:
    body = json.loads(request.content)
    data = [{"object": "embedding", "index": i, "embedding": _vector(len(text))} for i, text in enumerate(body["input"])]
    if shuffle:
        data.reverse()
    return httpx.Response(200, json={"object": "list", "data": data, "model": body["model"],
                                     "usage": {"prompt_tokens": 1, "total_tokens": 1}})


def test_documents_are_batched_and_order_preserved():
    batches = []

    def handler(request):
        batches.append(json.loads(request.content)["input"])
        return _ok(request, shuffle=True)

    texts = ["a" * n for n in range(1, 8)]  # 7 texts, batch size 3 -> 3 + 3 + 1
    vectors = _make_client(handler).embed_documents(texts)

    assert [len(batch) for batch in batches] == [3, 3, 1]
    assert vectors == [_vector(len(text)) for text in texts]


def test_request_sends_model_and_dimensions():
    seen = {}

    def handler(request):
        seen.update(json.loads(request.content))
        assert request.url.path == "/v1/embeddings"
        return _ok(request)

    _make_client(handler).embed_documents(["hello"])
    assert seen["model"] == "test-model" and seen["dimensions"] == DIM


def test_query_instruction_applied_to_queries_only():
    inputs = []

    def handler(request):
        inputs.extend(json.loads(request.content)["input"])
        return _ok(request)

    client = _make_client(handler, query_instruction="Find book passages")
    client.embed_query("what is dune?")
    client.embed_documents(["dune is a novel"])
    assert inputs == ["Instruct: Find book passages\nQuery: what is dune?", "dune is a novel"]


@pytest.mark.parametrize("texts", [[], [""], ["ok", "   "]])
def test_empty_input_rejected_without_calling_service(texts):
    def handler(request):
        raise AssertionError("service must not be called")

    with pytest.raises(ValueError):
        _make_client(handler).embed_documents(texts)


def test_transient_errors_are_retried():
    responses = iter([httpx.Response(503), httpx.Response(429)])

    def handler(request):
        return next(responses, None) or _ok(request)

    assert _make_client(handler).embed_documents(["x"]) == [_vector(1)]


def test_connection_errors_are_retried_then_give_up():
    calls = []

    def handler(request):
        calls.append(1)
        raise httpx.ConnectError("refused")

    with pytest.raises(EmbeddingError, match="after 3 attempts"):
        _make_client(handler, max_retries=2).embed_documents(["x"])
    assert len(calls) == 3


def test_validation_errors_are_not_retried():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(413, json={"message": "batch size 33 > maximum allowed batch size 32"})

    with pytest.raises(EmbeddingError, match="413"):
        _make_client(handler).embed_documents(["x"])
    assert len(calls) == 1


def test_dimension_mismatch_is_rejected():
    def handler(request):
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.1, 0.2]}]})

    with pytest.raises(EmbeddingError, match="dimensions"):
        _make_client(handler).embed_documents(["x"])


def test_ping_uses_root_health_endpoint():
    paths = []

    def handler(request):
        paths.append(request.url.path)
        return httpx.Response(200)

    _make_client(handler).ping()
    assert paths == ["/health"]
