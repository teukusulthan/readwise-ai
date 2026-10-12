"""
Client IP of a request, honouring X-Forwarded-For only from trusted reverse proxies.

Behind a proxy every request arrives from the proxy's address, so per-client limits would share one
bucket. When the socket peer is inside BE_TRUSTED_PROXIES, the client is the right-most
X-Forwarded-For address that is not itself a trusted proxy (left-hand entries are client-supplied and
spoofable). From any other peer the header is ignored.
"""

import ipaddress
from functools import lru_cache

from starlette.types import Scope

from config.base import settings


@lru_cache(maxsize=8)
def _networks(raw: str) -> tuple:
    return tuple(ipaddress.ip_network(item.strip(), strict=False) for item in raw.split(",") if item.strip())


def _is_trusted(address: str, networks: tuple) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return any(ip in network for network in networks)


def client_ip(scope: Scope) -> str:
    client = scope.get("client")
    peer = client[0] if client else "unknown"
    networks = _networks(settings.TRUSTED_PROXIES or "")
    if not networks or not _is_trusted(peer, networks):
        return peer

    forwarded = b",".join(value for name, value in scope.get("headers", []) if name == b"x-forwarded-for")
    for part in reversed(forwarded.decode("latin-1").split(",")):
        address = part.strip()
        if not address:
            continue
        try:
            ipaddress.ip_address(address)
        except ValueError:
            return peer  # malformed hop: don't guess
        if not _is_trusted(address, networks):
            return address
    return peer
