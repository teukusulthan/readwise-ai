import httpx
import pytest

from server import LibraryClient, Settings, StaticBearerVerifier, build_for_transport

TOKEN = "s" * 40
INIT = {
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2025-03-26", "capabilities": {},
               "clientInfo": {"name": "t", "version": "0"}},
}
HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


async def test_verifier_accepts_only_the_exact_token():
    verifier = StaticBearerVerifier(TOKEN)
    assert await verifier.verify_token(TOKEN) is not None
    assert await verifier.verify_token(TOKEN + "x") is None
    assert await verifier.verify_token("") is None
    assert await verifier.verify_token("é" * 40) is None  # non-ascii must not raise


def test_http_transport_refuses_to_start_without_a_token():
    with pytest.raises(RuntimeError, match="MCP_BEARER_TOKEN is required"):
        build_for_transport("http", Settings(bearer_token=""))


def test_http_transport_refuses_a_short_token():
    with pytest.raises(RuntimeError, match="at least 32"):
        build_for_transport("http", Settings(bearer_token="short"))


def test_stdio_needs_no_token():
    assert build_for_transport("stdio", Settings(bearer_token="")).name == "library"


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer wrong"}, {"Authorization": f"Basic {TOKEN}"}, {"Authorization": "Bearer "}],
    ids=["missing", "wrong", "wrong-scheme", "empty"],
)
async def test_http_endpoint_rejects_bad_credentials(headers):
    app = build_for_transport("http", Settings(bearer_token=TOKEN)).http_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://mcp.test") as http:
        response = await http.post("/mcp", json=INIT, headers={**HEADERS, **headers})
    assert response.status_code == 401


async def test_http_endpoint_accepts_the_right_token():
    mcp = build_for_transport("http", Settings(bearer_token=TOKEN))
    app = mcp.http_app()
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://mcp.test") as http:
            response = await http.post("/mcp", json=INIT, headers={**HEADERS, "Authorization": f"Bearer {TOKEN}"})
    assert response.status_code == 200


def test_default_timeout_outlasts_the_backend_llm_retries():
    # Backend worst case for /chat/ask: BE_LLM_TIMEOUT_SECONDS (120) x (1 + BE_LLM_NUM_RETRIES (2)) = 360 s.
    assert Settings().timeout_seconds > 120 * 3
    assert Settings.from_env({}).timeout_seconds == Settings().timeout_seconds
    assert Settings.from_env({"LIBRARY_TIMEOUT_SECONDS": "90"}).timeout_seconds == 90
