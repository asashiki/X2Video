"""Tool wrappers around the stable v0.1 pipeline stages."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Any, Callable

from x2video.config.schema import X2VideoConfig
from x2video.domain.models import Artifact
from x2video.pipeline.card import run_card
from x2video.pipeline.curate import run_curate
from x2video.pipeline.fetch import run_fetch
from x2video.pipeline.render import run_render
from x2video.pipeline.script import run_script
from x2video.tools.base import AgentTool, ToolContext, ToolResult


class LegacyPipelineTool(AgentTool):
    def __init__(
        self,
        *,
        name: str,
        stage: str,
        config: X2VideoConfig,
        operation: Callable[..., Any],
        is_async: bool = False,
    ) -> None:
        self.name = name
        self.stage = stage
        self.config = config
        self.operation = operation
        self.is_async = is_async

    async def execute(self, context: ToolContext) -> ToolResult:
        date = context.payload.get("date")
        kwargs = dict(context.payload.get("stage_options") or {})
        kwargs["date"] = date
        if self.is_async:
            result = await self.operation(self.config, **kwargs)
        else:
            result = await asyncio.to_thread(self.operation, self.config, **kwargs)
        artifacts = _result_artifacts(context.run_id, self.stage, result)
        return ToolResult(
            summary=f"Legacy {self.stage} completed",
            artifacts=artifacts,
            payload=_summarize(result),
        )


def register_legacy_tools(registry: Any, config: X2VideoConfig) -> None:
    definitions: list[tuple[str, str, Callable[..., Any], bool]] = [
        ("legacy.fetch", "fetch", run_fetch, False),
        ("legacy.curate", "curate", run_curate, True),
        ("legacy.card", "card", run_card, False),
        ("legacy.script", "script", run_script, True),
        ("legacy.render", "render", run_render, True),
    ]
    for name, stage, operation, is_async in definitions:
        registry.register(
            LegacyPipelineTool(
                name=name,
                stage=stage,
                config=config,
                operation=operation,
                is_async=is_async,
            )
        )


def _result_artifacts(run_id: str, stage: str, result: Any) -> list[Artifact]:
    if not isinstance(result, dict):
        return []
    paths: list[Path] = []
    for value in result.values():
        if isinstance(value, Path):
            paths.append(value)
        elif isinstance(value, str) and ("/" in value or "\\" in value):
            path = Path(value)
            if path.exists():
                paths.append(path)
    artifacts = []
    for path in paths:
        digest = hashlib.sha256(str(path).encode()).hexdigest()
        artifacts.append(
            Artifact(
                run_id=run_id,
                kind=f"legacy.{stage}",
                path=str(path),
                input_hash=digest,
            )
        )
    return artifacts


def _summarize(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {"result_type": type(result).__name__}
    safe: dict[str, Any] = {}
    for key, value in result.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
        elif isinstance(value, Path):
            safe[key] = str(value)
        elif isinstance(value, list):
            safe[key] = len(value)
    return safe

