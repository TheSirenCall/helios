"""
Manages the lifecycle of viewport tools, including registration,
lookup, and the currently active tool. This provides a central registry
for tools and keeps the rest of the application independent of specific
tool implementations.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from helios.tools.base import Tool


class ToolManager:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._active: Optional[Tool] = None

    def register_tool(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def activate(self, name: str, viewport=None) -> None:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        if self._active is not None and viewport is not None:
            self._active.on_deactivate(viewport)
        self._active = self._tools[name]
        if viewport is not None:
            self._active.on_activate(viewport)

    @property
    def active_tool(self) -> Optional[Tool]:
        return self._active

    def tool_names(self) -> List[str]:
        return list(self._tools.keys())