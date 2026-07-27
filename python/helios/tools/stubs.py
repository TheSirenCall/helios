"""
Placeholder implementations for the transform tools. Tool
registration and activation are in place, while interactive
manipulation will be added once the viewport gizmo and transform
interaction pipeline are implemented.
"""
from __future__ import annotations

from helios.tools.base import Tool


class MoveTool(Tool):
    name = "move"


class RotateTool(Tool):
    name = "rotate"


class ScaleTool(Tool):
    name = "scale"


class MeasureTool(Tool):
    """
    Placeholder implementation for a two click distance measurement
    tool. The tool is registered and ready to integrate with the picking and
    overlay systems once they are available.
    """
    name = "measure"


class BoxSelectTool(Tool):
    """
    Placeholder implementation for a rubber-band selection tool. The
    tool is registered and ready to integrate with the viewport's selection
    rectangle and picking systems once they are available.
    """
    name = "box_select"