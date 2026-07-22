"""Unit tests for Grok OAuth helpers (no live network)."""

from __future__ import annotations

import base64
import hashlib
import json
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from x2video.auth import oauth
from x2video.auth.store import read_auth, write_auth


def test_pkce_pair_s256_shape() -> None:
    verifier, challenge = oauth._pkce_pair()
    assert len(verifier) >= 43
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode()
    )
    assert challenge == expected


def test_build_authorize_url_contains_required_params() -> None:
    url = oauth._build_authorize_url(
        "https://auth.x.ai/oauth2/authorize",
        redirect_uri="http://127.0.0.1:56121/callback",
        challenge="abc",
        state="state123",
        nonce="nonce456",
    )
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    assert qs["response_type"] == ["code"]
    assert qs["client_id"] == [oauth.XAI_OAUTH_CLIENT_ID]
    assert qs["redirect_uri"] == ["http://127.0.0.1:56121/callback"]
    assert "openid" in qs["scope"][0]
    assert "api:access" in qs["scope"][0]
    assert qs["code_challenge"] == ["abc"]
    assert qs["code_challenge_method"] == ["S256"]
    assert qs["state"] == ["state123"]
    assert qs["nonce"] == ["nonce456"]
    assert qs["referrer"] == [oauth.XAI_OAUTH_REFERRER]


def test_validate_xai_endpoint_rejects_foreign_host() -> None:
    with pytest.raises(oauth.GrokAuthError):
        oauth._validate_xai_endpoint("https://evil.example/oauth/token")


def test_write_and_read_auth_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "grok_auth.json"
    record = {
        "access_token": "at",
        "refresh_token": "rt",
        "expires_at": int(time.time()) + 3600,
        "token_endpoint": "https://auth.x.ai/oauth2/token",
    }
    write_auth(record, path=path)
    loaded = read_auth(path)
    assert loaded is not None
    assert loaded["access_token"] == "at"
    assert loaded["refresh_token"] == "rt"


def test_get_access_token_returns_cached(tmp_path: Path) -> None:
    path = tmp_path / "grok_auth.json"
    write_auth(
        {
            "access_token": "fresh-token",
            "refresh_token": "rt",
            "expires_at": int(time.time()) + 3600,
            "token_endpoint": "https://auth.x.ai/oauth2/token",
        },
        path=path,
    )
    token = oauth.get_access_token(auth_path=path)
    assert token == "fresh-token"


def test_get_access_token_refreshes_when_expired(tmp_path: Path) -> None:
    path = tmp_path / "grok_auth.json"
    write_auth(
        {
            "access_token": "old",
            "refresh_token": "rt-1",
            "expires_at": int(time.time()) - 10,
            "token_endpoint": "https://auth.x.ai/oauth2/token",
        },
        path=path,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/token")
        body = parse_qs(request.content.decode())
        assert body["grant_type"] == ["refresh_token"]
        assert body["refresh_token"] == ["rt-1"]
        assert body["client_id"] == [oauth.XAI_OAUTH_CLIENT_ID]
        return httpx.Response(
            200,
            json={
                "access_token": "new-access",
                "refresh_token": "rt-2",
                "expires_in": 3600,
                "token_type": "Bearer",
            },
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        token = oauth.get_access_token(auth_path=path, http_client=client)

    assert token == "new-access"
    stored = read_auth(path)
    assert stored is not None
    assert stored["access_token"] == "new-access"
    assert stored["refresh_token"] == "rt-2"


def test_get_access_token_requires_login(tmp_path: Path) -> None:
    path = tmp_path / "missing.json"
    with pytest.raises(oauth.GrokLoginRequiredError):
        oauth.get_access_token(auth_path=path)


def test_login_pkce_flow_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive login() with a mock token server and a fake browser that hits callback."""
    path = tmp_path / "grok_auth.json"
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("openid-configuration"):
            return httpx.Response(
                200,
                json={
                    "authorization_endpoint": "https://auth.x.ai/oauth2/authorize",
                    "token_endpoint": "https://auth.x.ai/oauth2/token",
                },
            )
        if request.url.path.endswith("/token"):
            body = parse_qs(request.content.decode())
            assert body["grant_type"] == ["authorization_code"]
            assert body["code"] == ["auth-code-1"]
            assert body["code_verifier"][0]
            assert body["client_id"] == [oauth.XAI_OAUTH_CLIENT_ID]
            return httpx.Response(
                200,
                json={
                    "access_token": "login-access",
                    "refresh_token": "login-refresh",
                    "expires_in": 7200,
                    "token_type": "Bearer",
                    "scope": oauth.XAI_OAUTH_SCOPE,
                },
            )
        return httpx.Response(404, text="not found")

    def fake_open(url: str) -> bool:
        captured["url"] = url
        qs = parse_qs(urlparse(url).query)
        state = qs["state"][0]
        redirect = qs["redirect_uri"][0]
        # Hit the local callback the same way the browser would.
        with httpx.Client() as c:
            r = c.get(redirect, params={"code": "auth-code-1", "state": state})
            assert r.status_code == 200
        return True

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        result = oauth.login(
            force=True,
            auth_path=path,
            http_client=client,
            open_browser=fake_open,
        )

    assert result["access_token"] == "login-access"
    assert result["refresh_token"] == "login-refresh"
    assert "code_challenge" in captured["url"]
    assert read_auth(path)["access_token"] == "login-access"


def test_status_and_logout(tmp_path: Path) -> None:
    path = tmp_path / "grok_auth.json"
    assert oauth.get_status(auth_path=path)["logged_in"] is False
    write_auth(
        {
            "access_token": "a",
            "refresh_token": "r",
            "expires_at": int(time.time()) + 1000,
        },
        path=path,
    )
    st = oauth.get_status(auth_path=path)
    assert st["logged_in"] is True
    assert st["expired"] is False
    assert oauth.logout(auth_path=path) is True
    assert oauth.get_status(auth_path=path)["logged_in"] is False
