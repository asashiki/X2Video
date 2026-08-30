"""Explicit registry; tools cannot be invoked unless registered."""

from x2video.tools.base import AgentTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> AgentTool:
        if not tool.name:
            raise ValueError("Tool name cannot be empty")
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool
        return tool

    def get(self, name: str) -> AgentTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Tool is not registered: {name}") from exc

    def names(self) -> list[str]:
        return sorted(self._tools)

