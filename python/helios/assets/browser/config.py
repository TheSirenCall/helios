"""
Loads the asset_browser.yaml template into a list of AssetSource definitions.
This is a very simple implementation at the moment.

TODO: Sources will always be organised in a more complex manner, I need to automate asset name search,
This is should also work for shot and sequence publishes or any other type

Example asset_browser.yaml:

    sources:
      - name: Characters
        provider: filesystem
        root: ${PROJECT_ROOT}/Assets/Characters
      - name: Environments
        provider: filesystem
        root: ${PROJECT_ROOT}/Assets/Environments
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from helios.core.configuration.config import substitute_variables


@dataclass(frozen=True)
class AssetSource:
    name: str
    provider: str
    root: str

def load_sources(path: str, variables: Optional[Dict[str, str]] = None) -> List[AssetSource]:
    file_path = Path(path)
    if not file_path.is_file():
        return []
    with file_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    data = substitute_variables(data, variables or {})
    return [AssetSource(**entry) for entry in data.get("sources", [])]