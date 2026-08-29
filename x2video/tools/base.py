"""Typed boundary for deterministic and model-backed Agent tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from x2video.domain.models import Artifact


@dataclass(slots=True)
class ToolContext:
    run_id: str
    task_id: str
    work_dir: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolResult:
    summary: str
    artifacts: list[Artifact] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)
    cost_usd: float = 0.0
    llm_calls: int = 0


class AgentTool(ABC):
    name: str
    version = "1.0"

    @abstractmethod
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute once for an idempotent task boundary."""
        ...

