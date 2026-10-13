import httpx
import pytest
from fastmcp import Client

from server import LibraryClient, Settings, create_server


def envelope(data, *, pagination=None, message="Success", code=200):
    meta = {"status": True, "responseCode": code, "message": message}
    if pagination is not None:
        meta["pagination"] = pagination
    return {"metaData": meta, "data": data}


def failure(message, code):
    return {"metaData": {"status": False, "responseCode": code, "message": message}, "data": None}


class Backend:
    """Records requests and answers with a canned response."""

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.response: httpx.Response | Exception = httpx.Response(200, json=envelope([]))

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]


@pytest.fixture
def backend():
    return Backend()


@pytest.fixture
def settings():
    return Settings(api_url="http://backend.test", internal_token="t" * 40)


@pytest.fixture
async def client(backend, settings):
    mcp = create_server(LibraryClient(settings, transport=httpx.MockTransport(backend)))
    async with Client(mcp) as c:
        yield c
