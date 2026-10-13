"""Auth cookies: HttpOnly + SameSite=Lax always; `Secure` follows BE_AUTH_COOKIE_SECURE."""

import pytest
from fastapi import Response

from config.base import BaseSetting
from router.auth import delete_auth_cookies, set_auth_cookies


def _cookies(response: Response) -> dict[str, str]:
    headers = [v.decode() for k, v in response.raw_headers if k == b"set-cookie"]
    return {header.split("=", 1)[0]: header.lower() for header in headers}


@pytest.mark.parametrize("secure", [True, False])
def test_auth_cookies_follow_the_secure_setting(settings, monkeypatch, secure):
    monkeypatch.setattr(settings, "AUTH_COOKIE_SECURE", secure)
    response = Response()
    set_auth_cookies(response, "access", "refresh")
    cookies = _cookies(response)
    assert set(cookies) == {"token", "refresh_token"}
    for header in cookies.values():
        assert "httponly" in header and "samesite=lax" in header and "path=/" in header
        assert ("; secure" in header) is secure
    assert f"max-age={settings.JWT_EXPIRED}" in cookies["token"]
    assert f"max-age={settings.JWT_REFRESH}" in cookies["refresh_token"]

    cleared = Response()
    delete_auth_cookies(cleared)
    for header in _cookies(cleared).values():
        assert "max-age=0" in header and ("; secure" in header) is secure


def test_cookie_secure_defaults_to_true(monkeypatch):
    monkeypatch.delenv("BE_AUTH_COOKIE_SECURE", raising=False)
    assert BaseSetting().AUTH_COOKIE_SECURE is True
    monkeypatch.setenv("BE_AUTH_COOKIE_SECURE", "false")
    assert BaseSetting().AUTH_COOKIE_SECURE is False
