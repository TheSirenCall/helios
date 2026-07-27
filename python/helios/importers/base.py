"""
Base interface for scene importers.

Importer implementations encapsulate format specific parsing, allowing
the rest of the application to work with a common scene representation
without depending on external file format libraries.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from helios.scene.graph import SceneGraph


class SceneImporter(ABC):
    @classmethod
    @abstractmethod
    def can_load(cls, path: str) -> bool:
        """Return True if this importer can handle the given file path."""

    @abstractmethod
    def load(self, path: str) -> SceneGraph:
        """Parse the file and return a fully populated, format agnostic SceneGraph."""