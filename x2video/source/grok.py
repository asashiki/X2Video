"""Fetch candidates via SuperGrok OAuth + official X Search tool.

Uses the xAI Responses API with the server-side ``x_search`` tool.
Token consumption is billed against the SuperGrok / X Premium+
subscription attached to the OAuth session — not X Developer API.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from x2video.auth.oauth import XAI_API_BASE, GrokLoginRequiredError, get_access_token
from x2video.source.models import CandidateTweet

# Default model for subscription-backed X Search. Overridable via config.
DEFAULT_GROK_SEARCH_MODEL = "grok-4-1-fast-reasoning"

_CANDIDATE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "tweets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "text": {"type": "string"},
                    "created_at": {"type": "string"},
                    "author_id": {"type": "string"},
                    "author_name": {"type": "string"},
                    "author_username": {"type": "string"},
                    "author_avatar_url": {"type": "string"},
                    "author_verified": {"type": "boolean"},
                    "likes": {"type": "integer"},
                    "retweets": {"type": "integer"},
                    "replies": {"type": "integer"},
                    "views": {"type": "integer"},
                    "url": {"type": "string"},
                    "lang": {"type": "string"},
                    "media_urls": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "id",
                    "text",
                    "created_at",
                    "author_id",
                    "author_name",
                    "author_username",
                    "author_avatar_url",
                    "author_verified",
                    "likes",
                    "retweets",
                    "replies",
                    "views",
                    "url",
                    "lang",
                    "media_urls",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["tweets"],
    "additionalProperties": False,
}


def _date_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _build_prompt(
    keywords: list[str],
    *,
    time_window_hours: int,
    max_results: int,
    min_likes: int,
    min_retweets: int,
) -> str:
    kw = ", ".join(f'"{k}"' for k in keywords)
    return (
        "You are a data-collection agent for a short-video pipeline.\n"
        "Use the X Search tool to find RECENT posts matching these topic keywords:\n"
        f"  {kw}\n\n"
        f"Time window: last {time_window_hours} hours.\n"
        f"Prefer posts with at least {min_likes} likes and {min_retweets} retweets "
        "when available; still return lower-engagement posts if the window is sparse.\n"
        f"Return at most {max_results} distinct posts.\n"
        "Exclude pure retweets without commentary when possible.\n"
        "For each post fill ALL fields accurately from X Search results:\n"
        "  id, text, created_at (ISO8601), author_id, author_name, author_username,\n"
        "  author_avatar_url, author_verified, likes, retweets, replies, views,\n"
        "  url (https://x.com/<user>/status/<id>), lang, media_urls.\n"
        "If a metric is unknown, use 0. If a string is unknown, use an empty string.\n"
        "Do not invent post ids or engagement numbers that are not in the search data.\n"
    )


def _extract_output_text(payload: dict[str, Any]) -> str:
    """Pull assistant text out of a Responses API payload."""
    # Newer Responses API: top-level output_text
    if isinstance(payload.get("output_text"), str) and payload["output_text"].strip():
        return payload["output_text"]

    chunks: list[str] = []
    for item in payload.get("output") or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") in {"message", "output_message"} or item.get("role") == "assistant":
            for part in item.get("content") or []:
                if not isinstance(part, dict):
                    continue
                ptype = part.get("type")
                if ptype in {"output_text", "text"} and isinstance(part.get("text"), str):
                    chunks.append(part["text"])
                elif isinstance(part.get("text"), dict) and isinstance(
                    part["text"].get("value"), str
                ):
                    chunks.append(part["text"]["value"])
        # Some payloads nest message under content only
        if item.get("type") == "output_text" and isinstance(item.get("text"), str):
            chunks.append(item["text"])
    if chunks:
        return "\n".join(chunks)

    # Fallback: choices-style (compat)
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(msg, dict) and isinstance(msg.get("content"), str):
            return msg["content"]
    return ""


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", text)
    if fence:
        return fence.group(1).strip()
    return text


def _parse_tweets_payload(text: str) -> list[dict[str, Any]]:
    cleaned = _strip_json_fence(text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to locate a JSON object/array substring
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(cleaned[start : end + 1])
        else:
            raise

    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        tweets = data.get("tweets") or data.get("posts") or data.get("candidates")
        if isinstance(tweets, list):
            return [x for x in tweets if isinstance(x, dict)]
        # Single tweet object?
        if "id" in data and "text" in data:
            return [data]
    return []


def _coerce_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


def _id_from_url(url: str) -> str:
    m = re.search(r"/status(?:es)?/(\d+)", url)
    return m.group(1) if m else ""


def _to_candidate(item: dict[str, Any]) -> CandidateTweet | None:
    text = str(item.get("text") or item.get("full_text") or "").strip()
    url = str(item.get("url") or item.get("permalink") or "").strip()
    tid = str(item.get("id") or item.get("tweet_id") or item.get("post_id") or "").strip()
    if not tid and url:
        tid = _id_from_url(url)
    if not tid and not text:
        return None
    if not tid:
        # Last resort: stable hash-like id from text snippet
        tid = f"unknown-{abs(hash(text)) % 10**12}"

    username = str(
        item.get("author_username")
        or item.get("username")
        or item.get("screen_name")
        or ""
    ).lstrip("@")
    if not url and username and tid.isdigit():
        url = f"https://x.com/{username}/status/{tid}"

    media = item.get("media_urls") or item.get("media") or []
    if isinstance(media, str):
        media = [media]
    media_urls = [str(m) for m in media if m]

    return CandidateTweet(
        id=tid,
        text=text,
        created_at=str(item.get("created_at") or ""),
        author_id=str(item.get("author_id") or ""),
        author_name=str(item.get("author_name") or item.get("name") or ""),
        author_username=username,
        author_avatar_url=str(
            item.get("author_avatar_url") or item.get("profile_image_url") or ""
        ),
        author_verified=bool(item.get("author_verified") or item.get("verified") or False),
        likes=_coerce_int(item.get("likes") if "likes" in item else item.get("favorite_count")),
        retweets=_coerce_int(
            item.get("retweets") if "retweets" in item else item.get("retweet_count")
        ),
        replies=_coerce_int(
            item.get("replies") if "replies" in item else item.get("reply_count")
        ),
        views=_coerce_int(item.get("views") if "views" in item else item.get("view_count")),
        url=url,
        lang=str(item.get("lang") or ""),
        media_urls=media_urls,
        raw=item,
    )


class GrokXSearchSource:
    """SuperGrok OAuth-backed candidate source using the X Search tool."""

    name = "grok"

    def __init__(
        self,
        *,
        model: str = DEFAULT_GROK_SEARCH_MODEL,
        api_base: str = XAI_API_BASE,
        min_likes: int = 0,
        min_retweets: int = 0,
        auth_path: Path | None = None,
        http_client: httpx.Client | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.model = model
        self.api_base = api_base.rstrip("/")
        self.min_likes = min_likes
        self.min_retweets = min_retweets
        self.auth_path = auth_path
        self._http_client = http_client
        self.timeout = timeout

    def fetch(
        self,
        keywords: list[str],
        *,
        time_window_hours: int = 24,
        max_results: int = 50,
    ) -> list[CandidateTweet]:
        if not keywords:
            raise ValueError("keywords must not be empty")

        owns_client = self._http_client is None
        client = self._http_client or httpx.Client(timeout=self.timeout)
        try:
            token = get_access_token(auth_path=self.auth_path, http_client=client)
            now = datetime.now(timezone.utc)
            from_date = _date_str(now - timedelta(hours=time_window_hours))
            to_date = _date_str(now + timedelta(days=1))

            prompt = _build_prompt(
                keywords,
                time_window_hours=time_window_hours,
                max_results=max_results,
                min_likes=self.min_likes,
                min_retweets=self.min_retweets,
            )
            body: dict[str, Any] = {
                "model": self.model,
                "input": prompt,
                "tools": [
                    {
                        "type": "x_search",
                        "from_date": from_date,
                        "to_date": to_date,
                    }
                ],
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "candidate_tweets",
                        "schema": _CANDIDATE_JSON_SCHEMA,
                        "strict": True,
                    }
                },
            }

            try:
                payload = self._post_responses(client, token, body)
            except httpx.HTTPStatusError as first_err:
                # Some models / tiers reject strict json_schema + tools; retry plain JSON.
                if first_err.response.status_code in {400, 422}:
                    body.pop("text", None)
                    body["input"] = (
                        prompt
                        + "\nRespond with ONLY a JSON object of the form "
                        '{"tweets":[...]} and no other prose.\n'
                    )
                    payload = self._post_responses(client, token, body)
                else:
                    raise

            text = _extract_output_text(payload)
            if not text:
                raise RuntimeError(
                    "Grok X Search returned an empty response. "
                    "Check model access for this SuperGrok session."
                )

            try:
                raw_items = _parse_tweets_payload(text)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"Could not parse Grok X Search JSON: {exc}\n---\n{text[:800]}"
                ) from exc

            candidates: list[CandidateTweet] = []
            seen: set[str] = set()
            for item in raw_items:
                c = _to_candidate(item)
                if c is None or c.id in seen:
                    continue
                seen.add(c.id)
                candidates.append(c)
                if len(candidates) >= max_results:
                    break
            return candidates
        except GrokLoginRequiredError:
            raise
        finally:
            if owns_client:
                client.close()

    def _post_responses(
        self,
        client: httpx.Client,
        token: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        url = f"{self.api_base}/responses"
        resp = client.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=body,
        )
        if resp.status_code == 401:
            # One refresh retry
            token = get_access_token(
                auth_path=self.auth_path,
                http_client=client,
                force_refresh=True,
            )
            resp = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=body,
            )
        if resp.status_code >= 400:
            detail = resp.text[:500]
            if resp.status_code == 403:
                raise RuntimeError(
                    "Grok API returned HTTP 403 — this SuperGrok session may not "
                    "have OAuth API access for the selected model. "
                    f"Detail: {detail}"
                )
            resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected Grok API response shape")
        return data
