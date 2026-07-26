"""
Computes scene statistics shared across the application.

Used by the Statistics panel for live metrics and the Diagnostics panel
for scene health reporting, ensuring both use the same traversal and
counting logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from helios.scene.components.material import MaterialComponent
from helios.scene.components.mesh import MeshComponent
from helios.scene.graph import SceneGraph
from helios.scene.queries import SceneQuery

# Estimated GPU memory used by vertex data. Assumes one float32 vec3 each
# for position, normal, and color. This is an approximation for
# diagnostics and does not include driver overhead or additional GPU
# buffers used elsewhere in the renderer.
_BYTES_PER_VERTEX = 3 * 3 * 4
_BYTES_PER_INDEX = 4


@dataclass
class SceneStats:
    node_count: int = 0
    mesh_count: int = 0
    vertex_count: int = 0
    triangle_count: int = 0
    skinned_mesh_count: int = 0
    material_count: int = 0
    vertex_colored_mesh_count: int = 0
    frame_range: Tuple[float, float] = (0.0, 1.0)
    fps: float = 24.0
    is_animated: bool = False
    estimated_gpu_memory_bytes: int = 0
    import_warnings: List[str] = field(default_factory=list)


def compute_scene_stats(graph: SceneGraph) -> SceneStats:
    query = SceneQuery(graph)
    mesh_nodes = query.find_meshes()

    node_count = sum(1 for _ in graph.walk())
    vertex_count = sum(n.get_component(MeshComponent).num_vertices for n in mesh_nodes)
    index_count = sum(len(n.get_component(MeshComponent).triangle_indices) for n in mesh_nodes)
    triangle_count = index_count // 3
    skinned_count = len(query.find_skinned())

    material_nodes = query.find_by_type(MaterialComponent)
    vertex_colored = sum(
        1 for n in material_nodes
        if n.get_component(MaterialComponent).vertex_colors is not None
    )

    estimated_bytes = vertex_count * _BYTES_PER_VERTEX + index_count * _BYTES_PER_INDEX

    return SceneStats(
        node_count=node_count,
        mesh_count=len(mesh_nodes),
        vertex_count=vertex_count,
        triangle_count=triangle_count,
        skinned_mesh_count=skinned_count,
        material_count=len(material_nodes),
        vertex_colored_mesh_count=vertex_colored,
        frame_range=graph.frame_range,
        fps=graph.fps,
        is_animated=graph.frame_range[0] != graph.frame_range[1],
        estimated_gpu_memory_bytes=estimated_bytes,
        import_warnings=list(graph.import_warnings),
    )