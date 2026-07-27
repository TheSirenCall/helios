"""
Central registry for dynamically loaded plugins.

Subsystems register implementations through a common interface, allowing
features such as importers and renderers to be extended without changes
to the application core. Plugin discovery loads modules from a configured
directory and lets them perform their own registration.
"""
from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Dict, List, Type

from helios.importers.base import SceneImporter
from helios.renderers.base import Renderer


class PluginRegistry:
    def __init__(self):
        self._importers: List[Type[SceneImporter]] = []
        self._renderers: Dict[str, Type[Renderer]] = {}

    def register_importer(self, importer_cls: Type[SceneImporter]) -> None:
        self._importers.append(importer_cls)

    def register_renderer(self, name: str, renderer_cls: Type[Renderer]) -> None:
        self._renderers[name] = renderer_cls

    def importer_for(self, path: str) -> SceneImporter:
        for importer_cls in self._importers:
            if importer_cls.can_load(path):
                return importer_cls()
        raise ValueError(f"No registered importer can load: {path}")

    def renderer(self, name: str = "opengl") -> Renderer:
        return self._renderers[name]()

    def discover(self, plugins_dir: str) -> None:
        plugins_path = Path(plugins_dir)
        if not plugins_path.is_dir():
            return
        for module_info in pkgutil.iter_modules([str(plugins_path)]):
            module = importlib.import_module(f"{plugins_path.name}.{module_info.name}")
            register_fn = getattr(module, "register", None)
            if callable(register_fn):
                register_fn(self)


default_registry = PluginRegistry()


def _register_builtins() -> None:
    from helios.importers.usd_importer import USDImporter
    from helios.renderers.opengl.renderer import OpenGLRenderer

    default_registry.register_importer(USDImporter)
    default_registry.register_renderer("opengl", OpenGLRenderer)


_register_builtins()