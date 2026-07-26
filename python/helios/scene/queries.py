"""
SceneQuery provides a read only interface for querying a SceneGraph.
It centralizes common query logic so callers don't need to traverse the
graph manually, while allowing future optimizations such as indexing or
caching behind a consistent API.
"""
from __future__ import annotations

from typing import Callable, List, Optional, Type

from helios.scene.components.mesh import MeshComponent
from helios.scene.components.skeleton import SkeletonComponent
from helios.scene.graph import SceneGraph
from helios.scene.node import SceneNode


class SceneQuery:
    def __init__(self, graph: SceneGraph):
        self._graph = graph

    def find(self, predicate: Callable[[SceneNode], bool]) -> List[SceneNode]:
        return [node for node in self._graph.walk() if predicate(node)]

    def find_by_name(self, name: str) -> List[SceneNode]:
        return self.find(lambda n: n.name == name)

    def find_by_uuid(self, node_uuid: str) -> Optional[SceneNode]:
        return self._graph.find_by_uuid(node_uuid)

    def find_by_path(self, path: str) -> Optional[SceneNode]:
        return self._graph.find_by_path(path)

    def find_by_type(self, component_type: Type) -> List[SceneNode]:
        return self.find(lambda n: n.has_component(component_type))

    def find_by_tag(self, tag: str) -> List[SceneNode]:
        return self.find(lambda n: tag in n.tags)

    def find_selected(self) -> List[SceneNode]:
        return self.find(lambda n: n.selected)

    def find_visible(self) -> List[SceneNode]:
        return self.find(lambda n: n.visible)

    def find_meshes(self) -> List[SceneNode]:
        return self.find_by_type(MeshComponent)

    def find_skinned(self) -> List[SceneNode]:
        return self.find_by_type(SkeletonComponent)

    def find_materials(self) -> List[SceneNode]:
        return []  # no MaterialComponent yet, placeholder extension point

    def find_lights(self) -> List[SceneNode]:
        return []  # no LightComponent yet, placeholder extension point