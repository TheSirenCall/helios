"""
Asset data model. A FilesystemProvider and a ShotGridProvider both return these same types,
so the AssetBrowser UI and AssetBrowserService never need to know which provider an Asset came from.

"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Asset:
    name: str
    path: str
    asset_type: str = "unknown"  # this can be anything like "folder", "usd", "texture"
    thumbnail_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AssetVersion:
    version: str
    path: str
    metadata: Dict[str, Any] = field(default_factory=dict)