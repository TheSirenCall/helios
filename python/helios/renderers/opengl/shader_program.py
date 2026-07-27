"""
Wrapper around a linked GLSL program.

Caches uniform locations by name so render code can set uniforms without
repeating glGetUniformLocation calls during frame rendering.
"""
from __future__ import annotations

from typing import Dict

import numpy as np
import OpenGL.GL as gl

from helios.renderers.opengl.shader import Shader


class ShaderLinkError(RuntimeError):
    pass


class ShaderProgram:
    def __init__(self, vertex_src: str, fragment_src: str, label: str = ""):
        self.label = label
        vertex = Shader(gl.GL_VERTEX_SHADER, vertex_src, f"{label}:vertex")
        fragment = Shader(gl.GL_FRAGMENT_SHADER, fragment_src, f"{label}:fragment")
        self.handle = gl.glCreateProgram()
        gl.glAttachShader(self.handle, vertex.handle)
        gl.glAttachShader(self.handle, fragment.handle)
        gl.glLinkProgram(self.handle)
        vertex.destroy()
        fragment.destroy()

        if not gl.glGetProgramiv(self.handle, gl.GL_LINK_STATUS):
            log = gl.glGetProgramInfoLog(self.handle)
            log = log.decode("utf-8", "replace") if isinstance(log, bytes) else str(log)
            gl.glDeleteProgram(self.handle)
            raise ShaderLinkError(f"Shader link failed ({label}):\n{log}")

        self._uniform_locations: Dict[str, int] = {}

    def use(self) -> None:
        gl.glUseProgram(self.handle)

    def _location(self, name: str) -> int:
        if name not in self._uniform_locations:
            self._uniform_locations[name] = gl.glGetUniformLocation(self.handle, name)
        return self._uniform_locations[name]

    def set_mat4(self, name: str, matrix: np.ndarray) -> None:
        """
        Uploads application matrices to GLSL using the renderer's row-major
        matrix convention.

        The transpose flag handles the conversion required by OpenGL, allowing
        callers to pass matrices directly without performing manual transposes.
        """
        loc = self._location(name)
        if loc != -1:
            gl.glUniformMatrix4fv(loc, 1, gl.GL_TRUE, matrix.astype(np.float32))

    def set_vec3(self, name: str, value) -> None:
        loc = self._location(name)
        if loc != -1:
            gl.glUniform3f(loc, *value)

    def set_vec4(self, name: str, value) -> None:
        loc = self._location(name)
        if loc != -1:
            gl.glUniform4f(loc, *value)

    def set_float(self, name: str, value: float) -> None:
        loc = self._location(name)
        if loc != -1:
            gl.glUniform1f(loc, value)

    def destroy(self) -> None:
        gl.glDeleteProgram(self.handle)