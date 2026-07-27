"""
Asset Provider framework.
TODO: add ShotGridProvider, OpenAssetIOProvider, ftrackProvider, CloudProvider, etc
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional

from helios.assets.models.asset import Asset, AssetVersion


class AssetProvider(ABC):
    @abstractmethod
    def list_assets(self, path: str = "") -> List[Asset]:
        """List assets at path."""

    @abstractmethod
    def search(self, query: str) -> List[Asset]:
        """Search across everything this provider can see."""

    def get_thumbnail(self, asset: Asset) -> Optional[str]:
        """Return a local file path to a thumbnail image, or None."""
        return None

    def get_metadata(self, asset: Asset) -> Dict[str, object]:
        return {}

    def get_versions(self, asset: Asset) -> List[AssetVersion]:
        return []

    def get_dependencies(self, asset: Asset) -> List[Asset]:
        return []

    def watch(self, callback: Callable[[], None]) -> None:
        """Register a callback to be invoked when this provider's contents change. """
        return None

    def refresh(self) -> None:
        """Force any cached listing to be re-fetched."""
        return None