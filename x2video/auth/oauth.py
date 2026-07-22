"""Grok / xAI OAuth2 authorization-code + PKCE login (browser loopback).

Flow matches Grok Build and similar tools:

1. Start a local HTTP callback on ``127.0.0.1:<port>/callback``
2. Open the authorize URL in the browser (accounts.x.ai consent)
3. User clicks Allow; browser redirects with ``?code=...&state=...``
4. Exchange code + PKCE verifier for access/refresh tokens
5. Persist under ``~/.config/x2video/grok_auth.json``

The public desktop client_id is intentional — same as the official Grok CLI.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from x2video.auth.store import auth_file_path, delete_auth, read_auth, write_auth

# Public Grok CLI / Grok Build OAuth client (not a secret).
XAI_OAUTH_CLIENT_ID = "b1a00492-073a-47ea-816f-4c329264a828"
XAI_OAUTH_SCOPE = "openid profile email offline_access grok-cli:access api:access"
XAI_OAUTH_ISSUER = "https://auth.x.ai"
XAI_OAUTH_DISCOVERY_URL = f"{XAI_OAUTH_ISSUER}/.well-known/openid-configuration"
# Prefer the well-known fixed port used by Grok CLI; fall back to ephemeral.
XAI_OAUTH_PREFERRED_PORT = 56121
XAI_OAUTH_REDIRECT_HOST = "127.0.0.1"
XAI_OAUTH_REDIRECT_PATH = "/callback"
XAI_OAUTH_EXPIRY_SKEW_SECONDS = 120
XAI_OAUTH_CALLBACK_TIMEOUT_SECONDS = 300
XAI_OAUTH_REFERRER = "x2video"
XAI_API_BASE = "https://api.x.ai/v1"

_REFRESH_LOCK = threading.Lock()


class GrokAuthError(Exception):
    """Base error for Grok OAuth failures."""


class GrokLoginRequiredError(GrokAuthError):
    """No usable credentials — user must run ``x2video auth login``."""


class _CallbackHandler(BaseHTTPRequestHandler):
    server: "_CallbackServer"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != XAI_OAUTH_REDIRECT_PATH:
            self.send_response(404)
            self.end_headers()
            return

        params = parse_qs(parsed.query)
        result = {
            "code": params.get("code", [None])[0],
            "state": params.get("state", [None])[0],
            "error": params.get("error", [None])[0],
            "error_description": params.get("error_description", [None])[0],
        }
        self.server.callback_result = result

        if result["state"] != self.server.expected_state:
            self._respond(
                400,
                "<h1>Authorization state mismatch</h1><p>You can close this tab.</p>",
            )
            return

        if result["error"]:
            desc = result.get("error_description") or result["error"]
            self._respond(
                400,
                f"<h1>Authorization failed</h1><p>{_html_escape(desc)}</p>"
                "<p>You can close this tab.</p>",
            )
            return

        self._respond(
            200,
            "<h1>X2Video authorization received</h1>"
            "<p>You can close this tab and return to the terminal.</p>",
        )

    def _respond(self, status: int, body_html: str) -> None:
        body = (
            f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
            f"<title>X2Video Auth</title></head><body>{body_html}</body></html>"
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


class _CallbackServer(HTTPServer):
    expected_state: str
    callback_result: dict[str, str | None] | None


def _html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode()
    )
    return verifier, challenge


def _validate_xai_endpoint(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or (host != "x.ai" and not host.endswith(".x.ai")):
        raise GrokAuthError(f"Unexpected OAuth endpoint host: {url}")
    return url


def _discover(client: httpx.Client) -> dict[str, str]:
    try:
        resp = client.get(
            XAI_OAUTH_DISCOVERY_URL,
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise GrokAuthError(f"OAuth discovery failed: {exc}") from exc
    try:
        data = resp.json()
    except ValueError as exc:
        raise GrokAuthError("OAuth discovery response was not valid JSON") from exc
    auth_ep = data.get("authorization_endpoint")
    token_ep = data.get("token_endpoint")
    if not auth_ep or not token_ep:
        raise GrokAuthError("OAuth discovery missing authorization/token endpoints")
    return {
        "authorization_endpoint": _validate_xai_endpoint(str(auth_ep)),
        "token_endpoint": _validate_xai_endpoint(str(token_ep)),
    }


def _build_authorize_url(
    authorization_endpoint: str,
    *,
    redirect_uri: str,
    challenge: str,
    state: str,
    nonce: str,
) -> str:
    # Prefer auth.x.ai authorize path used by Grok CLI / hermes loopback flow.
    # Discovery may return accounts.x.ai; both work, but /oauth2/authorize is the
    # documented code-flow entry for this public client.
    endpoint = authorization_endpoint
    if "accounts.x.ai" in endpoint or endpoint.rstrip("/").endswith("/oauth2/auth"):
        # Normalize to the authorize path expected by the public client.
        endpoint = "https://auth.x.ai/oauth2/authorize"
    params = {
        "response_type": "code",
        "client_id": XAI_OAUTH_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": XAI_OAUTH_SCOPE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "nonce": nonce,
        "plan": "generic",
        "referrer": XAI_OAUTH_REFERRER,
    }
    return f"{endpoint}?{urlencode(params)}"


def _start_callback_server(state: str) -> tuple[_CallbackServer, str]:
    last_error: OSError | None = None
    for port in (XAI_OAUTH_PREFERRED_PORT, 0):
        try:
            server = _CallbackServer(
                (XAI_OAUTH_REDIRECT_HOST, port),
                _CallbackHandler,
            )
            server.expected_state = state
            server.callback_result = None
            actual_port = server.server_address[1]
            redirect_uri = (
                f"http://{XAI_OAUTH_REDIRECT_HOST}:{actual_port}{XAI_OAUTH_REDIRECT_PATH}"
            )
            return server, redirect_uri
        except OSError as exc:
            last_error = exc
    raise GrokAuthError(f"Could not start OAuth callback server: {last_error}")


def _wait_for_callback(server: _CallbackServer) -> dict[str, str | None]:
    server.timeout = 1.0
    deadline = time.time() + XAI_OAUTH_CALLBACK_TIMEOUT_SECONDS
    try:
        while time.time() < deadline:
            server.handle_request()
            if server.callback_result is not None:
                return server.callback_result
    finally:
        server.server_close()
    raise GrokAuthError(
        f"Timed out waiting for browser authorization "
        f"({XAI_OAUTH_CALLBACK_TIMEOUT_SECONDS}s). Run `x2video auth login` again."
    )


def _exchange_token(
    client: httpx.Client,
    token_endpoint: str,
    data: dict[str, str],
) -> dict[str, Any]:
    try:
        resp = client.post(
            token_endpoint,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data=data,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise GrokAuthError(
            f"Token request failed: HTTP {exc.response.status_code} {exc.response.text}"
        ) from exc
    except httpx.HTTPError as exc:
        raise GrokAuthError(f"Token request failed: {exc}") from exc
    try:
        body = resp.json()
    except ValueError as exc:
        raise GrokAuthError("Token response was not valid JSON") from exc
    if not isinstance(body, dict):
        raise GrokAuthError("Token response was not an object")
    return body


def _build_auth_record(
    token_payload: dict[str, Any],
    token_endpoint: str,
    *,
    fallback_refresh_token: str | None = None,
) -> dict[str, Any]:
    access_token = token_payload.get("access_token")
    refresh_token = token_payload.get("refresh_token") or fallback_refresh_token
    if not access_token:
        raise GrokAuthError("Token response missing access_token")
    if not refresh_token:
        raise GrokAuthError("Token response missing refresh_token")
    expires_in = token_payload.get("expires_in") or 3600
    try:
        expires_at = int(time.time() + int(expires_in))
    except (TypeError, ValueError):
        expires_at = int(time.time() + 3600)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "id_token": token_payload.get("id_token"),
        "token_type": token_payload.get("token_type") or "Bearer",
        "scope": token_payload.get("scope"),
        "token_endpoint": token_endpoint,
        "expires_at": expires_at,
        "obtained_at": int(time.time()),
    }


def _is_expired(auth_data: dict[str, Any], *, skew: int = XAI_OAUTH_EXPIRY_SKEW_SECONDS) -> bool:
    expires_at = auth_data.get("expires_at")
    if expires_at is None:
        return True
    try:
        return time.time() >= float(expires_at) - skew
    except (TypeError, ValueError):
        return True


def _refresh_tokens(
    client: httpx.Client,
    auth_data: dict[str, Any],
    *,
    path: Path | None = None,
) -> dict[str, Any]:
    token_endpoint = auth_data.get("token_endpoint")
    if not token_endpoint:
        token_endpoint = _discover(client)["token_endpoint"]
    token_endpoint = _validate_xai_endpoint(str(token_endpoint))
    refresh_token = auth_data.get("refresh_token")
    if not refresh_token:
        raise GrokLoginRequiredError(
            "Refresh token missing. Run `x2video auth login`."
        )
    payload = _exchange_token(
        client,
        token_endpoint,
        {
            "grant_type": "refresh_token",
            "refresh_token": str(refresh_token),
            "client_id": XAI_OAUTH_CLIENT_ID,
        },
    )
    refreshed = _build_auth_record(
        payload,
        token_endpoint,
        fallback_refresh_token=str(refresh_token),
    )
    write_auth(refreshed, path=path)
    return refreshed


def login(
    *,
    force: bool = False,
    no_browser: bool = False,
    auth_path: Path | None = None,
    http_client: httpx.Client | None = None,
    open_browser: Any = webbrowser.open,
) -> dict[str, Any]:
    """Run the browser OAuth PKCE flow and store credentials.

    Args:
        force: Re-login even if a valid session already exists.
        no_browser: Print the URL instead of opening a browser.
        auth_path: Optional override for the credentials file path.
        http_client: Optional shared httpx client (tests).
        open_browser: Callable used to open the authorize URL (tests).

    Returns:
        The stored auth record (includes access_token / refresh_token).
    """
    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=30.0)
    path = auth_path or auth_file_path()

    try:
        existing = read_auth(path)
        if existing and not force and existing.get("access_token"):
            if not _is_expired(existing):
                return existing
            if existing.get("refresh_token"):
                try:
                    return _refresh_tokens(client, existing, path=path)
                except GrokAuthError:
                    pass

        discovery = _discover(client)
        verifier, challenge = _pkce_pair()
        state = uuid.uuid4().hex
        nonce = uuid.uuid4().hex
        server, redirect_uri = _start_callback_server(state)
        authorize_url = _build_authorize_url(
            discovery["authorization_endpoint"],
            redirect_uri=redirect_uri,
            challenge=challenge,
            state=state,
            nonce=nonce,
        )

        opened = False
        if not no_browser:
            try:
                opened = bool(open_browser(authorize_url))
            except Exception:
                opened = False
        if no_browser or not opened:
            print("Open this URL in your browser to authorize X2Video:\n")
            print(authorize_url)
            print()
        else:
            print("Browser opened for Grok authorization.")
            print("If nothing opened, visit this URL:\n")
            print(authorize_url)
            print()
        print(f"Waiting for callback on {redirect_uri} ...")

        result = _wait_for_callback(server)
        if result.get("state") != state:
            raise GrokAuthError("OAuth state mismatch")
        if result.get("error"):
            desc = result.get("error_description") or result["error"]
            raise GrokAuthError(f"Authorization failed: {desc}")
        code = result.get("code")
        if not code:
            raise GrokAuthError("Authorization failed: no code returned")

        token_payload = _exchange_token(
            client,
            discovery["token_endpoint"],
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": XAI_OAUTH_CLIENT_ID,
                "code_verifier": verifier,
            },
        )
        auth_data = _build_auth_record(token_payload, discovery["token_endpoint"])
        write_auth(auth_data, path=path)
        return auth_data
    finally:
        if owns_client:
            client.close()


def get_access_token(
    *,
    auth_path: Path | None = None,
    http_client: httpx.Client | None = None,
    force_refresh: bool = False,
) -> str:
    """Return a valid access token, refreshing if needed.

    Raises:
        GrokLoginRequiredError: when no credentials exist or refresh fails.
    """
    path = auth_path or auth_file_path()
    auth_data = read_auth(path)
    if not auth_data:
        raise GrokLoginRequiredError(
            "Not logged in. Run `x2video auth login` to connect your SuperGrok "
            "subscription."
        )

    access = auth_data.get("access_token")
    if access and not force_refresh and not _is_expired(auth_data):
        return str(access)

    if not auth_data.get("refresh_token"):
        raise GrokLoginRequiredError(
            "Session expired and no refresh token. Run `x2video auth login`."
        )

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=30.0)
    try:
        with _REFRESH_LOCK:
            # Re-read under lock in case another thread refreshed.
            current = read_auth(path) or auth_data
            access = current.get("access_token")
            if access and not force_refresh and not _is_expired(current):
                return str(access)
            try:
                refreshed = _refresh_tokens(client, current, path=path)
            except GrokAuthError as exc:
                raise GrokLoginRequiredError(
                    f"Token refresh failed ({exc}). Run `x2video auth login`."
                ) from exc
            return str(refreshed["access_token"])
    finally:
        if owns_client:
            client.close()


def get_status(*, auth_path: Path | None = None) -> dict[str, Any]:
    """Return a non-secret summary of the stored session."""
    path = auth_path or auth_file_path()
    data = read_auth(path)
    if not data:
        return {
            "logged_in": False,
            "path": str(path),
            "expires_at": None,
            "expired": None,
            "has_refresh_token": False,
        }
    expires_at = data.get("expires_at")
    expired = _is_expired(data, skew=0) if expires_at is not None else True
    return {
        "logged_in": True,
        "path": str(path),
        "expires_at": expires_at,
        "expired": expired,
        "has_refresh_token": bool(data.get("refresh_token")),
        "token_type": data.get("token_type"),
        "scope": data.get("scope"),
    }


def clear_credentials(*, auth_path: Path | None = None) -> bool:
    """Remove stored credentials. Returns True if a file was deleted."""
    return delete_auth(auth_path or auth_file_path())


def logout(*, auth_path: Path | None = None) -> bool:
    """Alias for :func:`clear_credentials`."""
    return clear_credentials(auth_path=auth_path)
