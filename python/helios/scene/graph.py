"""
SceneGraph is the single source of truth for the scene structure. It is
built by an importer and consumed by the rest of the application, including
the Outliner, Viewport, Inspector, Statistics, and future validation tools.
These systems work exclusively with the SceneGraph and never traverse the raw
prims or nodes of a specific file format directly.

This replaces the old flat Scene/SceneMesh model with a proper hierarchy of
SceneNodes, each containing one or more Components, instead of relying on a
flat list of meshes and reconstructing the hierarchy from path strings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

import numpy as np

from helios.core.render_scene import NodeRange
from helios.scene.components.material import MaterialComponent
from helios.scene.components.mesh import MeshComponent
from helios.scene.components.transform_override import TransformOverrideComponent
from helios.scene.node import SceneNode


@dataclass
class SceneGraph:
    root: SceneNode = field(default_factory=lambda: SceneNode(name=""))
    frame_range: Tuple[float, float] = (0.0, 1.0)
    fps: float = 24.0

    # Normalize the model once at import time. This avoids visible
    # recentering or rescaling as the animation plays.
    center: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))
    scale: float = 1.0
    bounding_box: Optional[Sequence[Tuple[float, float, float]]] = None
    # Warnings captured from the importer while loading the scene, including
    # missing skeleton bindings, missing animation sources, joint order
    # mismatches, and invalid time samples. They are stored here so the
    # Diagnostics panel can present the results directly instead of
    # duplicating the importer's validation logic.
    import_warnings: List[str] = field(default_factory=list)

    _by_uuid: Dict[str, SceneNode] = field(default_factory=dict, repr=False)
    _by_path: Dict[str, SceneNode] = field(default_factory=dict, repr=False)

    def register(self, node: SceneNode) -> None:
        """
        Called by importers whenever a node is created to keep the lookup
        tables up to date, allowing find_by_uuid() and find_by_path() to
        perform constant-time lookups.
        """
        self._by_uuid[node.uuid] = node
        self._by_path[node.path] = node

    def find_by_uuid(self, node_uuid: str) -> Optional[SceneNode]:
        return self._by_uuid.get(node_uuid)

    def find_by_path(self, path: str) -> Optional[SceneNode]:
        return self._by_path.get(path)

    def walk(self) -> Iterator[SceneNode]:
        yield from self.root.walk()

    def sample(self, frame: float):
        """
        Builds renderer-ready geometry for the current frame by collecting all
        visible MeshComponents, applying any TransformOverrideComponents,
        normalizing the result, and concatenating it into a single set of
        vertex, normal, index, and color buffers.

        NodeRanges map each node to its portion of the combined buffers for
        picking, highlighting, and selection outlines. Colors are resolved from
        the MaterialComponent, using per-vertex colors when available or the
        material's base color otherwise, so the renderer always receives a
        complete color buffer.

        Mesh indices are local to each mesh and are remapped as the combined
        buffers are built, preventing gaps when nodes are hidden.
        """
        vertex_chunks, normal_chunks, index_chunks, color_chunks = [], [], [], []
        node_ranges: List[NodeRange] = []
        vertex_offset = 0
        index_offset = 0

        for node in self.walk():
            if not node.visible:
                continue
            mesh = node.get_component(MeshComponent)
            if mesh is None:
                continue

            mesh_sample = mesh.source.sample(frame)
            vertices = mesh_sample.vertices
            normals = mesh_sample.normals

            override = node.get_component(TransformOverrideComponent)
            if override is not None and vertices.shape[0] > 0:
                homogeneous = np.hstack([vertices, np.ones((vertices.shape[0], 1))])
                vertices = (homogeneous @ override.matrix.T)[:, :3]

            material = node.get_component(MaterialComponent)
            if (material is not None and material.vertex_colors is not None
                    and len(material.vertex_colors) == mesh.num_vertices):
                colors = material.vertex_colors
            else:
                base_color = material.material.base_color if material is not None else (0.7, 0.7, 0.7)
                colors = np.tile(np.array(base_color, dtype=np.float32), (mesh.num_vertices, 1))

            vertex_chunks.append(vertices)
            normal_chunks.append(normals)
            color_chunks.append(colors)
            index_chunks.append(mesh.triangle_indices + vertex_offset)
            node_ranges.append(NodeRange(
                path=node.path,
                vertex_start=vertex_offset, vertex_count=mesh.num_vertices,
                index_start=index_offset, index_count=len(mesh.triangle_indices),
            ))
            vertex_offset += mesh.num_vertices
            index_offset += len(mesh.triangle_indices)

        if not vertex_chunks:
            empty3 = np.zeros((0, 3), dtype=np.float32)
            return empty3, empty3, np.array([], dtype=np.uint32), [], empty3

        vertices = np.concatenate(vertex_chunks, axis=0)
        normals = np.concatenate(normal_chunks, axis=0)
        colors = np.concatenate(color_chunks, axis=0)
        triangle_indices = np.concatenate(index_chunks, axis=0).astype(np.uint32)
        vertices = (vertices - self.center) * self.scale

        # Report node ranges in normalized space so all picking and
        # highlighting operations use the same coordinates as rendering.
        return (
            vertices.astype(np.float32), normals.astype(np.float32),
            triangle_indices, node_ranges, colors.astype(np.float32),
        )