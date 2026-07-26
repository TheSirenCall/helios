"""
SceneNode represents a node in the SceneGraph. A node's behavior is
defined entirely by the Components attached to it rather than by a
specialized subclass. Adding support for a new node type only requires
introducing a new Component, without changing the SceneNode hierarchy or
the systems built on top of it.
"""
from __future__ import annotations

import uuid as uuid_module
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, TypeVar

ComponentT = TypeVar("ComponentT")


@dataclass
class SceneNode:
    name: str
    uuid: str = field(default_factory=lambda: str(uuid_module.uuid4()))
    parent: Optional["SceneNode"] = None
    children: List["SceneNode"] = field(default_factory=list)

    visible: bool = True
    locked: bool = False
    selected: bool = False
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    user_data: Dict[str, Any] = field(default_factory=dict)

    components: Dict[Type, Any] = field(default_factory=dict)

    @property
    def path(self) -> str:
        if self.parent is None:
            return "/" + self.name if self.name else "/"
        parent_path = self.parent.path
        return (parent_path.rstrip("/") + "/" + self.name) if self.name else parent_path

    def add_child(self, child: "SceneNode") -> None:
        child.parent = self
        self.children.append(child)

    def add_component(self, component: ComponentT) -> ComponentT:
        self.components[type(component)] = component
        return component

    def get_component(self, component_type: Type[ComponentT]) -> Optional[ComponentT]:
        return self.components.get(component_type)

    def has_component(self, component_type: Type) -> bool:
        return component_type in self.components

    def walk(self):
        """Depth first iterator over this node and all descendants."""
        yield self
        for child in self.children:
            yield from child.walk()