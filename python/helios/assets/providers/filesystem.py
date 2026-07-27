"""
Filesystem AssetProvider. Recursively lists and searches a root directory on disk.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from helios.assets.models.asset import Asset
from helios.assets.providers.base import AssetProvider

_KNOWN_ASSET_EXTENSIONS = {
    ".usd", ".usda", ".usdc", ".usdz",
    ".fbx", ".abc", ".obj", ".gltf", ".glb", ".stl", ".ply",
}


class FilesystemProvider(AssetProvider):
    def __init__(self, root: str):
        self.root = Path(root)

    def list_assets(self, path: str = "") -> List[Asset]:
        directory = self.root / path if path else self.root
        if not directory.is_dir():
            return []
        assets: List[Asset] = []
        for entry in sorted(directory.iterdir()):
            assets.append(self._to_asset(entry))
        return assets

    def search(self, query: str) -> List[Asset]:
        if not self.root.is_dir():
            return []
        query_lower = query.lower()
        matches: List[Asset] = []
        for dirpath, _dirnames, filenames in os.walk(self.root):
            for filename in filenames:
                if query_lower in filename.lower():
                    matches.append(self._to_asset(Path(dirpath) / filename))
        return matches

    def get_metadata(self, asset: Asset) -> dict:
        path = Path(asset.path)
        if not path.exists():
            return {}
        stat = path.stat()
        return {"size_bytes": stat.st_size, "modified_time": stat.st_mtime}

    def _to_asset(self, entry: Path) -> Asset:
        asset_type = "folder" if entry.is_dir() else entry.suffix.lstrip(".").lower() or "file"
        return Asset(name=entry.name, path=str(entry), asset_type=asset_type)