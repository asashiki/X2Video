"""Shared CLI helpers."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import TypeVar

import typer

T = TypeVar("T")


def die(message: str, code: int = 1) -> None:
    typer.secho(message, fg=typer.colors.RED, err=True)
    raise typer.Exit(code)


def run_async(coro: Coroutine[None, None, T]) -> T:
    return asyncio.run(coro)


def parse_indices(raw: str) -> list[int] | None:
    text = (raw or "").strip()
    if not text:
        return None
    out: list[int] = []
    for part in text.replace(" ", "").split(","):
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError:
            die(f"Not a number: {part}")
    return out or None
