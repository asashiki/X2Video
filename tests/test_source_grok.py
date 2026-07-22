"""Tests for SuperGrok X Search source parsing and factory wiring."""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx
import pytest

from x2video.auth.store import write_auth
from x2video.config.schema import HardFilterConfig, SourceConfig, X2VideoConfig
from x2video.source.factory import create_source
from x2video.source.grok import (
    GrokXSearchSource,
    _extract_output_text,
    _parse_tweets_payload,
    _to_candidate,
)
from x2video.source.x_mcp import XMCPSource


def test_parse_tweets_payload_object() -> None:
    text = json.dumps(
        {
            "tweets": [
                {
                    "id": "123",
                    "text": "hello AI",
                    "author_username": "alice",
                    "likes": 10,
                }
            ]
        }
    )
    items = _parse_tweets_payload(text)
    assert len(items) == 1
    assert items[0]["id"] == "123"


def test_parse_tweets_payload_fenced() -> None:
    text = '```json\n{"tweets":[{"id":"1","text":"x"}]}\n```'
    items = _parse_tweets_payload(text)
    assert items[0]["id"] == "1"


def test_to_candidate_builds_url() -> None:
    c = _to_candidate(
        {
            "id": "99",
            "text": "hi",
            "author_username": "bob",
            "likes": "42",
            "retweets": 3,
        }
    )
    assert c is not None
    assert c.id == "99"
    assert c.likes == 42
    assert c.retweets == 3
    assert c.url == "https://x.com/bob/status/99"


def test_extract_output_text_from_output_list() -> None:
    payload = {
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": '{"tweets":[]}'}],
            }
        ]
    }
    assert _extract_output_text(payload) == '{"tweets":[]}'


def test_create_source_dispatch() -> None:
    cfg = X2VideoConfig(source=SourceConfig(provider="grok"))
    src = create_source(cfg)
    assert isinstance(src, GrokXSearchSource)
    assert src.name == "grok"

    cfg2 = X2VideoConfig(source=SourceConfig(provider="x_mcp"))
    src2 = create_source(cfg2)
    assert isinstance(src2, XMCPSource)


def test_grok_fetch_happy_path(tmp_path: Path) -> None:
    path = tmp_path / "auth.json"
    write_auth(
        {
            "access_token": "tok",
            "refresh_token": "rt",
            "expires_at": int(time.time()) + 3600,
            "token_endpoint": "https://auth.x.ai/oauth2/token",
        },
        path=path,
    )

    sample = {
        "tweets": [
            {
                "id": "111",
                "text": "Big model drop",
                "created_at": "2026-07-22T12:00:00Z",
                "author_id": "1",
                "author_name": "Alice",
                "author_username": "alice",
                "author_avatar_url": "",
                "author_verified": True,
                "likes": 500,
                "retweets": 50,
                "replies": 10,
                "views": 10000,
                "url": "https://x.com/alice/status/111",
                "lang": "en",
                "media_urls": [],
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/responses")
        assert request.headers["Authorization"] == "Bearer tok"
        body = json.loads(request.content.decode())
        assert body["tools"][0]["type"] == "x_search"
        assert "from_date" in body["tools"][0]
        return httpx.Response(
            200,
            json={
                "output_text": json.dumps(sample),
            },
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        src = GrokXSearchSource(
            model="grok-test",
            auth_path=path,
            http_client=client,
            min_likes=100,
            min_retweets=10,
        )
        results = src.fetch(["AI"], time_window_hours=24, max_results=10)

    assert len(results) == 1
    assert results[0].id == "111"
    assert results[0].author_username == "alice"
    assert results[0].likes == 500


def test_x_mcp_requires_token() -> None:
    src = XMCPSource(bearer_token="")
    with pytest.raises(RuntimeError, match="X_BEARER_TOKEN"):
        src.fetch(["AI"])
