"""
Represents a compiled GLSL shader stage.

Responsible only for compilation and diagnostics. ShaderProgram owns the
linking process and manages shader stage lifetime, releasing individual
shader objects once the program has been successfully linked.
"""
from __future__ import annotations

import OpenGL.GL as gl


class ShaderCompileError(RuntimeError):
    pass


class Shader:
    def __init__(self, stage: int, source: str, label: str = ""):
        self.stage = stage
        self.label = label
        self.handle = gl.glCreateShader(stage)
        gl.glShaderSource(self.handle, source)
        gl.glCompileShader(self.handle)
        if not gl.glGetShaderiv(self.handle, gl.GL_COMPILE_STATUS):
            log = gl.glGetShaderInfoLog(self.handle)
            log = log.decode("utf-8", "replace") if isinstance(log, bytes) else str(log)
            gl.glDeleteShader(self.handle)
            raise ShaderCompileError(f"Shader compile failed ({label or stage}):\n{log}")

    def destroy(self) -> None:
        gl.glDeleteShader(self.handle)