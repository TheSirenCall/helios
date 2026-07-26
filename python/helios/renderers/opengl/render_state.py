"""
Caches OpenGL render state between draw passes.

State changes are only applied when values differ from the current state,
reducing redundant glEnable/glDisable and other state-setting calls
during rendering. This keeps render passes independent while avoiding
unnecessary GPU driver calls.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import OpenGL.GL as gl


@dataclass(frozen=True)
class RenderState:
    depth_test: bool = True
    cull_face: bool = False
    wireframe: bool = False
    blend: bool = False
    line_width: float = 1.0


class RenderStateManager:
    def __init__(self):
        self._current: Optional[RenderState] = None

    def apply(self, state: RenderState) -> None:
        if state == self._current:
            return

        if self._current is None or state.depth_test != self._current.depth_test:
            (gl.glEnable if state.depth_test else gl.glDisable)(gl.GL_DEPTH_TEST)
        if self._current is None or state.cull_face != self._current.cull_face:
            (gl.glEnable if state.cull_face else gl.glDisable)(gl.GL_CULL_FACE)
        if self._current is None or state.wireframe != self._current.wireframe:
            gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_LINE if state.wireframe else gl.GL_FILL)
        if self._current is None or state.blend != self._current.blend:
            (gl.glEnable if state.blend else gl.glDisable)(gl.GL_BLEND)
            if state.blend:
                gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        if self._current is None or state.line_width != self._current.line_width:
            gl.glLineWidth(state.line_width)

        self._current = state