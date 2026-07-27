"""
Central manager for renderer shader programs.

Compiles shader programs once during initialization and provides
name based lookup for render passes. Keeping lookup centralized allows
future hot reloading by replacing program instances without requiring
passes to manage shader lifetimes directly.
"""
from __future__ import annotations

from typing import Dict, Tuple

from helios.renderers.opengl.shader_program import ShaderProgram

_LIT_VERTEX_SRC = """
#version 330 core
layout(location = 0) in vec3 a_position;
layout(location = 1) in vec3 a_normal;
layout(location = 2) in vec3 a_color;

uniform mat4 u_view;
uniform mat4 u_projection;

out vec3 v_normal;
out vec3 v_world_pos;
out vec3 v_color;

void main() {
    v_world_pos = a_position;
    v_normal = a_normal;
    v_color = a_color;
    gl_Position = u_projection * u_view * vec4(a_position, 1.0);
}
"""

_LIT_FRAGMENT_SRC = """
#version 330 core
in vec3 v_normal;
in vec3 v_world_pos;
in vec3 v_color;
out vec4 frag_color;

uniform vec3 u_light_pos;

void main() {
    vec3 n = normalize(v_normal);
    vec3 l = normalize(u_light_pos - v_world_pos);
    float diffuse = max(dot(n, l), 0.0);
    vec3 color = v_color * (0.25 + 0.75 * diffuse);
    frag_color = vec4(color, 1.0);
}
"""

_UNLIT_VERTEX_SRC = """
#version 330 core
layout(location = 0) in vec3 a_position;

uniform mat4 u_view;
uniform mat4 u_projection;

void main() {
    gl_Position = u_projection * u_view * vec4(a_position, 1.0);
}
"""

_UNLIT_FRAGMENT_SRC = """
#version 330 core
out vec4 frag_color;
uniform vec3 u_base_color;

void main() {
    frag_color = vec4(u_base_color, 1.0);
}
"""

_BUILTIN_SOURCES: Dict[str, Tuple[str, str]] = {
    "lit": (_LIT_VERTEX_SRC, _LIT_FRAGMENT_SRC),
    "unlit": (_UNLIT_VERTEX_SRC, _UNLIT_FRAGMENT_SRC),
}


class ShaderManager:
    def __init__(self):
        self._programs: Dict[str, ShaderProgram] = {}

    def initialize(self) -> None:
        for name, (vertex_src, fragment_src) in _BUILTIN_SOURCES.items():
            self._programs[name] = ShaderProgram(vertex_src, fragment_src, label=name)

    def get(self, name: str) -> ShaderProgram:
        return self._programs[name]

    def reload_all(self) -> None:
        """
        Recompiles all managed shader programs and replaces the active program
        instances. Intended as the entry point for future shader hot reload
        support.
        """
        for name, (vertex_src, fragment_src) in _BUILTIN_SOURCES.items():
            old = self._programs.get(name)
            self._programs[name] = ShaderProgram(vertex_src, fragment_src, label=name)
            if old is not None:
                old.destroy()

    def destroy(self) -> None:
        for program in self._programs.values():
            program.destroy()
        self._programs.clear()