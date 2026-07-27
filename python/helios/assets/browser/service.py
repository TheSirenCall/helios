"""
Turns configured AssetSources into AssetProvider instances.

"""

from __future__ import annotations

from typing import Callable, Dict, List

from helios.assets.browser.config import AssetSource, load_sources
from helios.assets.models.asset import Asset
from helios.assets.providers.base import AssetProvider
from helios.assets.providers.filesystem import FilesystemProvider

_PROVIDER_FACTORIES: Dict[str, Callable[[AssetSource], AssetProvider]] = {
    "filesystem": lambda source: FilesystemProvider(source.root),
}


class AssetBrowserService:
    def __init__(self, config_path: str, variables: Dict[str, str] | None = None):
        self._sources = load_sources(config_path, variables)
        self._providers: Dict[str, AssetProvider] = {}
        for source in self._sources:
            factory = _PROVIDER_FACTORIES.get(source.provider)
            if factory is not None:
                self._providers[source.name] = factory(source)

    def source_names(self) -> List[str]:
        return list(self._providers.keys())

    def list_assets(self, source_name: str, path: str = "") -> List[Asset]:
        provider = self._providers.get(source_name)
        return provider.list_assets(path) if provider else []

    def search(self, query: str, source_name: str | None = None) -> List[Asset]:
        providers = (
            [self._providers[source_name]] if source_name and source_name in self._providers
            else list(self._providers.values())
        )
        results: List[Asset] = []
        for provider in providers:
            results.extend(provider.search(query))
        return results