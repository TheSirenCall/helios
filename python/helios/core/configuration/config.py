"""
YAML configuration framework.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, TypeVar

import yaml

T = TypeVar("T")

_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

def substitute_variables(value: Any, variables: Dict[str, str]) -> Any:
    """Recursively expand ${VAR} references in strings/dicts/lists against variables."""
    if isinstance(value, str):
        def replace(match: "re.Match[str]") -> str:
            name = match.group(1)
            return variables.get(name, os.environ.get(name, match.group(0)))
        return _VAR_PATTERN.sub(replace, value)
    if isinstance(value, dict):
        return {k: substitute_variables(v, variables) for k, v in value.items()}
    if isinstance(value, list):
        return [substitute_variables(v, variables) for v in value]
    return value

_substitute = substitute_variables

def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


class Configuration:
    """
    Layering:
        Configuration.load([
            "config/application.yaml",   # framework defaults
            "config/studio.yaml",        # studio overrides
            "config/project.yaml",       # project specific overrides
        ])
    Later paths override earlier ones (missing files are skipped, so a
    project without its own project.yaml can just inherit the studio/app
    defaults).
    """

    def __init__(self, data: Optional[Dict[str, Any]] = None,
                 variables: Optional[Dict[str, str]] = None):
        self._variables = dict(variables or {})
        self._variables.setdefault("USER", os.environ.get("USER", os.environ.get("USERNAME", "")))
        self._variables.setdefault("HOME", str(Path.home()))
        self._data = _substitute(data or {}, self._variables)

    @classmethod
    def load(cls, paths: Iterable[str], variables: Optional[Dict[str, str]] = None) -> "Configuration":
        merged: Dict[str, Any] = {}
        for path in paths:
            file_path = Path(path)
            if not file_path.is_file():
                continue
            with file_path.open("r", encoding="utf-8") as handle:
                layer = yaml.safe_load(handle) or {}
            merged = _deep_merge(merged, layer)
        return cls(merged, variables)

    def get(self, dotted_key: str, default: Optional[T] = None) -> T:
        node: Any = self._data
        for part in dotted_key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def require(self, dotted_key: str) -> Any:
        sentinel = object()
        value = self.get(dotted_key, sentinel)
        if value is sentinel:
            raise KeyError(f"Required configuration key missing: {dotted_key}")
        return value

    def as_dict(self) -> Dict[str, Any]:
        return self._data

    def reload(self, paths: Iterable[str]) -> "Configuration":
        return Configuration.load(paths, self._variables)