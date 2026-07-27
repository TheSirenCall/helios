"""
USD importer implementation.

Builds a SceneGraph from a USD stage, preserving the scene hierarchy and
translating USD primitives into the application's scene representation.
All interaction with the USD API is contained within this module.
"""
from __future__ import annotations

import logging
import traceback
from typing import Dict

import numpy as np
from pxr import Usd, UsdGeom, UsdSkel, Vt

from helios.core.material import Material
from helios.core.scene import AnimatedMeshSource, MeshSample
from helios.importers.base import SceneImporter
from helios.scene.components.material import MaterialComponent
from helios.scene.components.mesh import MeshComponent
from helios.scene.components.skeleton import SkeletonComponent
from helios.scene.components.transform import TransformComponent
from helios.scene.graph import SceneGraph
from helios.scene.node import SceneNode

logger = logging.getLogger(__name__)


class _ImportDiagnosticsHandler(logging.Handler):
    """
    Collects warning and error log records during a single import operation.

    Captured messages are attached to the resulting SceneGraph, making
    import diagnostics available independently of the logging system. The
    handler is scoped to a single load operation and observes log records
    without affecting other handlers.
    """

    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())

DEFAULT_PURPOSES = (UsdGeom.Tokens.default_, UsdGeom.Tokens.render)

class _StageFrameCache:
    """
    Caches UsdGeom.XformCache instances by frame for a USD stage.

    The cache retains the underlying stage for its lifetime, ensuring USD
    objects referenced by the imported scene remain valid after loading.
    """

    __slots__ = ("stage", "_frame", "_xform_cache")

    def __init__(self, stage):
        self.stage = stage
        self._frame = None
        self._xform_cache = None

    def xform_cache_for(self, frame: float):
        if self._frame != frame or self._xform_cache is None:
            self._xform_cache = UsdGeom.XformCache(Usd.TimeCode(frame))
            self._frame = frame
        return self._xform_cache

def _gf_matrix_to_numpy(matrix) -> np.ndarray:
    """Convert a Gf.Matrix4d (row vector convention: p' = p * M) to a 4x4 numpy array."""
    return np.array([[matrix[i][j] for j in range(4)] for i in range(4)], dtype=np.float64)

def _transform_points(points: np.ndarray, matrix4x4: np.ndarray) -> np.ndarray:
    if points.shape[0] == 0:
        return points
    homogeneous = np.hstack([points, np.ones((points.shape[0], 1))])
    return (homogeneous @ matrix4x4)[:, :3]


def _transform_normals(normals: np.ndarray, matrix4x4: np.ndarray) -> np.ndarray:

    # Transform normals using the inverse transpose of the upper left 3x3
    # matrix. This preserves correct normal direction when parent transforms
    # contain non uniform scaling.
    if normals.shape[0] == 0:
        return normals
    m3 = matrix4x4[:3, :3]
    try:
        normal_matrix = np.linalg.inv(m3).T
    except np.linalg.LinAlgError:
        normal_matrix = m3
    out = normals @ normal_matrix
    norms = np.linalg.norm(out, axis=1)
    flat = norms < 1e-9
    out[~flat] /= norms[~flat, None]
    out[flat] = (0.0, 1.0, 0.0)
    return out


def _query_is_valid(query) -> bool:
    """
    Checks validity for USD skeleton query objects.

    Different pxr Python builds expose validity differently, with some query
    types providing IsValid() and others only supporting boolean evaluation.
    This helper provides a consistent validity check across implementations.
    """
    if query is None:
        return False
    is_valid_fn = getattr(query, "IsValid", None)
    if is_valid_fn is not None:
        return bool(is_valid_fn())
    return bool(query)

def _find_bound_skeleton_prim(prim):
    """
    Resolves the Skeleton prim bound to a USD prim.

    Walks the prim hierarchy to find the nearest locally authored
    skel:skeleton relationship and resolves it to the referenced Skeleton.
    The resolution is implemented using low level USD APIs to maintain
    compatibility across pxr Python builds.
    """
    current = prim
    while current and current.IsValid() and not current.IsPseudoRoot():
        targets = UsdSkel.BindingAPI(current).GetSkeletonRel().GetTargets()
        if targets:
            return current.GetStage().GetPrimAtPath(targets[0])
        current = current.GetParent()
    return None


def _extract_material(mesh, num_points: int) -> MaterialComponent:
    """
    Extracts basic material data from USD display primvars.

    Constant and vertex interpolated displayColor and displayOpacity values
    are converted into the application's Material representation. Other
    interpolation modes are detected but require additional face to vertex
    mapping before they can be represented correctly, so they are not
    expanded here. Texture backed materials are not currently supported.
    """
    base_color = (0.7, 0.7, 0.7)
    opacity = 1.0
    vertex_colors = None

    try:
        primvars_api = UsdGeom.PrimvarsAPI(mesh.GetPrim())
        color_primvar = primvars_api.GetPrimvar("displayColor")
        if color_primvar and color_primvar.HasValue():
            values = color_primvar.Get()
            interpolation = color_primvar.GetInterpolation()
            if values:
                if interpolation == UsdGeom.Tokens.constant:
                    base_color = tuple(values[0])
                elif interpolation == UsdGeom.Tokens.vertex and len(values) == num_points:
                    vertex_colors = np.array(values, dtype=np.float32)
                else:
                    logger.warning(
                        "%s: displayColor has '%s' interpolation, using its "
                        "first value as a constant color rather than correctly "
                        "expanding per face/per face vertex colors (not yet "
                        "implemented)", mesh.GetPrim().GetPath(), interpolation,
                    )
                    base_color = tuple(values[0])

        opacity_primvar = primvars_api.GetPrimvar("displayOpacity")
        if opacity_primvar and opacity_primvar.HasValue():
            opacity_values = opacity_primvar.Get()
            if opacity_values:
                opacity = float(opacity_values[0])
    except Exception as exc:
        logger.warning(
            "%s: failed to read displayColor/displayOpacity, using default "
            "gray %s", mesh.GetPrim().GetPath(), exc,
        )

    return MaterialComponent(
        material=Material(base_color=base_color, opacity=opacity),
        vertex_colors=vertex_colors,
    )


class USDAnimatedMesh(AnimatedMeshSource):
    """
    Resolves animated world space geometry for a USD mesh.

    Combines transform animation and optional skeletal deformation into the
    final point and normal data consumed by the scene pipeline.
    """

    def __init__(self, mesh, frame_cache: _StageFrameCache,
                 face_vertex_counts, face_vertex_indices, num_points: int):
        self.mesh = mesh
        self.frame_cache = frame_cache
        self.face_vertex_counts = face_vertex_counts
        self.face_vertex_indices = face_vertex_indices
        self.num_points = num_points
        self.is_skinned = False
        self.skinning_query = None
        self.skel_query = None
        self.skeleton_prim = None
        self.rest_points = None

    def sample(self, frame: float) -> MeshSample:
        time_code = Usd.TimeCode(frame)

        skinned_this_frame = False
        skin_failed = False
        if self.is_skinned:
            points = self._compute_skinned_points(time_code)
            skinned_this_frame = points is not None
            skin_failed = not skinned_this_frame
            # Skinning is evaluated in skeleton space: geomBindTransform converts
            # mesh-local rest data into that space, and joint matrices are applied
            # there. Apply the Skeleton prim's local-to-world transform afterwards
            # to obtain final world-space positions.
            world_matrix = _gf_matrix_to_numpy(
                self.frame_cache.xform_cache_for(frame).GetLocalToWorldTransform(self.skeleton_prim)
            )
        else:
            points = self.mesh.GetPointsAttr().Get(time_code)
            world_matrix = _gf_matrix_to_numpy(
                self.frame_cache.xform_cache_for(frame).GetLocalToWorldTransform(self.mesh.GetPrim())
            )

        if not points or len(points) != self.num_points:
            if skin_failed:
                reason = "skinning failed to produce points"
            elif not points:
                reason = "no valid points sample at this frame (invalid/missing time sample)"
            else:
                reason = (
                    f"point count changed at this frame ({len(points)} vs "
                    f"{self.num_points} at import) topology varying animation "
                    f"is not supported"
                )
            logger.warning(
                "%s: frame %.3f  %s; rendering zeroed geometry",
                self.mesh.GetPrim().GetPath(), frame, reason,
            )
            zeros = np.zeros((self.num_points, 3), dtype=np.float64)
            return MeshSample(vertices=zeros, normals=zeros)

        local_pts = np.array(points, dtype=np.float64)
        world_pts = _transform_points(local_pts, world_matrix)

        authored = None if skinned_this_frame else self.mesh.GetNormalsAttr().Get(time_code)
        if authored and len(authored) == self.num_points:
            authored_np = np.array(authored, dtype=np.float64)
            norms = np.linalg.norm(authored_np, axis=1)
            flat = norms < 1e-6
            authored_np[~flat] /= norms[~flat, None]
            authored_np[flat] = (0.0, 1.0, 0.0)
            world_normals = _transform_normals(authored_np, world_matrix)
        else:
            world_normals = self._compute_vertex_normals(world_pts)

        return MeshSample(vertices=world_pts, normals=world_normals)

    def _compute_skinned_points(self, time_code):

        try:
            joint_xforms = self.skel_query.ComputeSkinningTransforms(time_code)
            out_points = Vt.Vec3fArray(self.rest_points)
            success = self.skinning_query.ComputeSkinnedPoints(joint_xforms, out_points, time_code)
            if success is False:
                logger.warning(
                    "%s: ComputeSkinnedPoints returned False at frame %.3f "
                    "(invalid joint transforms or rest point/joint count mismatch)",
                    self.mesh.GetPrim().GetPath(), float(time_code.GetValue()),
                )
                return None
            return out_points
        except Exception as exc:
            logger.error(
                "%s: skinning failed at frame %.3f -- %s",
                self.mesh.GetPrim().GetPath(), float(time_code.GetValue()), exc,
            )
            return None

    def _compute_vertex_normals(self, world_vertices: np.ndarray) -> np.ndarray:
        normals = np.zeros_like(world_vertices)
        idx = 0
        for count in self.face_vertex_counts:
            if count >= 3:
                face_indices = self.face_vertex_indices[idx:idx + count]
                v0, v1, v2 = (world_vertices[face_indices[i]] for i in range(3))
                face_normal = np.cross(v1 - v0, v2 - v0)
                norm = np.linalg.norm(face_normal)
                if norm > 1e-6:
                    face_normal = face_normal / norm
                    for i in face_indices:
                        normals[i] += face_normal
            idx += count
        norms = np.linalg.norm(normals, axis=1)
        flat = norms < 1e-6
        normals[~flat] /= norms[~flat, None]
        normals[flat] = (0.0, 1.0, 0.0)
        return normals


class USDImporter(SceneImporter):
    """Builds a SceneGraph from a 'EXTENSIONS' file."""

    EXTENSIONS = (".usd", ".usda", ".usdc", ".usdz")

    @classmethod
    def can_load(cls, path: str) -> bool:
        return path.lower().endswith(cls.EXTENSIONS)

    def load(self, path: str) -> SceneGraph:
        """
        Wraps the import operation with diagnostic collection.

        A temporary logging handler captures WARNING and ERROR messages during
        the load and attaches them to the resulting SceneGraph. The handler is
        removed after the operation completes, including when an exception is
        raised.
        """
        diagnostics_handler = _ImportDiagnosticsHandler()
        logger.addHandler(diagnostics_handler)
        try:
            graph = self._load_impl(path)
            graph.import_warnings = list(diagnostics_handler.messages)
            return graph
        finally:
            logger.removeHandler(diagnostics_handler)

    def _load_impl(self, path: str) -> SceneGraph:
        stage = Usd.Stage.Open(path)
        if not stage:
            raise ValueError(f"Failed to open USD file: {path}")

        start, end = stage.GetStartTimeCode(), stage.GetEndTimeCode()
        if start == end:
            start, end = self._compute_time_range(stage)
            if start == end:
                logger.warning(
                    "%s: no time-varying attributes found on stage; importing "
                    "as a static single frame scene", path,
                )
        fps = stage.GetFramesPerSecond() or stage.GetTimeCodesPerSecond() or 24.0

        # Always create a numeric TimeCode from start_frame. Using a truthiness
        # check here would treat frame 0 as missing and fall back to the USD
        # default time code, which reads non time sampled defaults instead of
        # the animated values.
        start_frame = float(start)
        time_code = Usd.TimeCode(start_frame)

        frame_cache = _StageFrameCache(stage)
        xform_cache = frame_cache.xform_cache_for(start_frame)

        # Populate UsdSkelCache entries for discovered SkelRoots upfront. Any
        # later Populate() calls for the same root are harmless and reuse the
        # existing cache state, allowing meshes outside the initial traversal
        # path to resolve their skeleton data lazily.
        skel_cache = UsdSkel.Cache()
        for prim in stage.Traverse():
            if prim.IsA(UsdSkel.Root):
                skel_cache.Populate(UsdSkel.Root(prim), Usd.PrimDefaultPredicate)

        graph = SceneGraph(frame_range=(float(start), float(end)), fps=float(fps))
        path_to_node: Dict[str, SceneNode] = {}

        def node_for_prim(prim) -> SceneNode:
            """
            Builds scene nodes from the USD hierarchy.

            Nodes are created lazily by following USD prim ancestry, preserving the
            stage's actual parent child relationships instead of reconstructing the
            hierarchy from path strings.
            """
            prim_path = str(prim.GetPath())
            existing = path_to_node.get(prim_path)
            if existing is not None:
                return existing
            parent_prim = prim.GetParent()
            if parent_prim and parent_prim.IsValid() and not parent_prim.IsPseudoRoot():
                parent_node = node_for_prim(parent_prim)
            else:
                parent_node = graph.root
            node = SceneNode(name=prim.GetName())
            parent_node.add_child(node)
            path_to_node[prim_path] = node
            graph.register(node)
            return node

        bbox_min = np.array([float("inf")] * 3)
        bbox_max = np.array([float("-inf")] * 3)

        for prim in stage.Traverse():
            if not prim.IsA(UsdGeom.Mesh):
                continue

            imageable = UsdGeom.Imageable(prim)
            if imageable.ComputeVisibility(time_code) == UsdGeom.Tokens.invisible:
                continue
            if imageable.ComputePurpose() not in DEFAULT_PURPOSES:
                continue

            mesh = UsdGeom.Mesh(prim)
            points = mesh.GetPointsAttr().Get(time_code)
            face_vertex_counts = mesh.GetFaceVertexCountsAttr().Get()
            face_vertex_indices = mesh.GetFaceVertexIndicesAttr().Get()
            if not (points and face_vertex_counts and face_vertex_indices):
                missing = [n for n, v in (
                    ("points", points),
                    ("faceVertexCounts", face_vertex_counts),
                    ("faceVertexIndices", face_vertex_indices),
                ) if not v]
                logger.warning(
                    "%s: skipping, missing required attribute(s) %s at frame "
                    "%.3f (invalid prim hierarchy or unauthored geometry)",
                    prim.GetPath(), missing, start_frame,
                )
                continue

            world_matrix = _gf_matrix_to_numpy(xform_cache.GetLocalToWorldTransform(prim))
            local_pts = np.array(points, dtype=np.float64)
            world_pts = _transform_points(local_pts, world_matrix)
            for wp in world_pts:
                for i in range(3):
                    bbox_min[i] = min(bbox_min[i], wp[i])
                    bbox_max[i] = max(bbox_max[i], wp[i])

            node = node_for_prim(prim)
            node.add_component(TransformComponent(
                resolve_world_matrix=lambda frame, p=prim: _gf_matrix_to_numpy(
                    frame_cache.xform_cache_for(frame).GetLocalToWorldTransform(p)
                )
            ))
            node.add_component(_extract_material(mesh, len(points)))

            animated_mesh = USDAnimatedMesh(
                mesh, frame_cache, face_vertex_counts, face_vertex_indices, len(points)
            )

            self._bind_skinning(prim, mesh, points, skel_cache, animated_mesh, node)

            # Keep indices local to each mesh. The combined scene buffer applies
            # offsets only for included geometry, so hidden nodes do not create
            # unused index ranges.
            triangle_indices = []
            idx = 0
            for count in face_vertex_counts:
                if count == 3:
                    triangle_indices.extend(face_vertex_indices[idx + i] for i in range(3))
                elif count == 4:
                    a, b, c, d = (face_vertex_indices[idx + i] for i in range(4))
                    triangle_indices.extend([a, b, c, a, c, d])
                elif count > 4:
                    for i in range(1, count - 1):
                        triangle_indices.extend([
                            face_vertex_indices[idx],
                            face_vertex_indices[idx + i],
                            face_vertex_indices[idx + i + 1],
                        ])
                idx += count

            node.add_component(MeshComponent(
                num_vertices=len(points),
                triangle_indices=np.array(triangle_indices, dtype=np.uint32),
                source=animated_mesh,
            ))

        if path_to_node and not np.any(np.isinf(bbox_min)):
            graph.center = (bbox_min + bbox_max) / 2.0
            max_extent = float(np.max(bbox_max - bbox_min))
            graph.scale = 2.0 / max_extent if max_extent > 1e-9 else 1.0
            corners = [
                [bbox_min[0], bbox_min[1], bbox_min[2]], [bbox_max[0], bbox_min[1], bbox_min[2]],
                [bbox_max[0], bbox_max[1], bbox_min[2]], [bbox_min[0], bbox_max[1], bbox_min[2]],
                [bbox_min[0], bbox_min[1], bbox_max[2]], [bbox_max[0], bbox_min[1], bbox_max[2]],
                [bbox_max[0], bbox_max[1], bbox_max[2]], [bbox_min[0], bbox_max[1], bbox_max[2]],
            ]
            graph.bounding_box = [tuple((np.array(c) - graph.center) * graph.scale) for c in corners]

        return graph

    @staticmethod
    def _bind_skinning(prim, mesh, points, skel_cache, animated_mesh, node) -> None:
        """
        Resolves UsdSkel binding for a mesh prim.

        UsdSkel bindings can vary across USD builds, so failures are handled
        locally. An invalid or unsupported skinning setup affects only the
        current mesh rather than the entire import process.
        """
        try:
            USDImporter._resolve_skinning(prim, mesh, points, skel_cache, animated_mesh, node)
        except Exception:
            logger.exception(
                "%s: exception while resolving skeleton binding, rendering "
                "as a plain rigid mesh instead", prim.GetPath(),
            )
            animated_mesh.is_skinned = False

    @staticmethod
    def _resolve_skinning(prim, mesh, points, skel_cache, animated_mesh, node) -> None:
        """
        Resolves skinning bindings and animation data for a USD skeleton.

        Keeps binding resolution separate from the surrounding geometry and
        hierarchy processing so failures and diagnostics remain isolated.
        """
        skel_root = UsdSkel.Root.Find(prim)
        if not skel_root:
            # No SkelRoot ancestor means this mesh is not part of a skinned
            # hierarchy. This is a normal case for non deformable scene geometry.
            return

        skel_cache.Populate(skel_root, Usd.PrimDefaultPredicate)
        skinning_query = skel_cache.GetSkinningQuery(prim)
        # Use GetSkinningQuery() for binding resolution. UsdSkel bindings are
        # commonly authored on an ancestor SkelRoot and inherited by meshes.
        # Checking the relationship directly only finds local bindings, causing
        # valid skinned meshes to be treated as rigid geometry.
        if not _query_is_valid(skinning_query):
            # No resolved skeleton binding. This is a rigid mesh, not an error.
            return

        # Resolve the Skeleton manually for pxr compatibility. Some USD Python
        # builds do not expose skinning_query.GetSkeleton().
        skeleton_prim = _find_bound_skeleton_prim(prim)
        if not skeleton_prim or not skeleton_prim.IsValid():
            logger.warning(
                "%s: skinning query resolved but no bound skeleton prim could be found",
                prim.GetPath(),
            )
            return

        skel_query = skel_cache.GetSkelQuery(UsdSkel.Skeleton(skeleton_prim))
        if not _query_is_valid(skel_query):
            logger.warning("%s: has a skeleton binding but an invalid skeleton query", prim.GetPath())
            return

        anim_query = skel_query.GetAnimQuery()
        if not _query_is_valid(anim_query):
            logger.warning(
                "%s: skeleton %s has no valid animation source. "
                     "Joint deformation will remain in the bind pose regardless of frame. "
                     "Any visible motion is coming from the SkelRoot or ancestor transform, "
                     "not skeletal animation. Check the Skeleton's skel:animationSource "
                     "relationship in the USD file.",
                prim.GetPath(), skeleton_prim.GetPath(),
            )
        else:
            skel_joint_order = getattr(skel_query, "GetJointOrder", lambda: None)()
            anim_joint_order = getattr(anim_query, "GetJointOrder", lambda: None)()
            if skel_joint_order is not None and anim_joint_order is not None:
                # ComputeSkinningTransforms() matches joints by name/path rather than by
                # array position. Extra joints in the animation source are valid and can
                # be ignored; only missing animation entries for Skeleton joints indicate
                # a problem, since those joints cannot be driven.
                missing_from_anim = set(skel_joint_order) - set(anim_joint_order)
                if missing_from_anim:
                    logger.warning(
                        "%s: skeleton %s has %d joint(s) with no matching "
                        "entry in its animation source's joint order "
                        "those joints will stay in bind pose: %s",
                        prim.GetPath(), skeleton_prim.GetPath(),
                        len(missing_from_anim), sorted(missing_from_anim),
                    )

        animated_mesh.is_skinned = True
        animated_mesh.skinning_query = skinning_query
        animated_mesh.skel_query = skel_query
        animated_mesh.skeleton_prim = skeleton_prim

        # Rest geometry must come from the unanimated mesh data, not the current
        # frame. Prefer the default value, then the first available time sample,
        # and only use the current frame as a final fallback when no rest data is available.
        rest_points = mesh.GetPointsAttr().Get()
        if rest_points is None:
            samples = mesh.GetPointsAttr().GetTimeSamples()
            if samples:
                rest_points = mesh.GetPointsAttr().Get(samples[0])
        if rest_points is None:
            rest_points = points
        animated_mesh.rest_points = Vt.Vec3fArray([tuple(p) for p in rest_points])

        node.add_component(SkeletonComponent(
            skeleton_path=str(skeleton_prim.GetPath())
        ))

    @staticmethod
    def _compute_time_range(stage):
        min_t, max_t = float("inf"), float("-inf")
        for prim in stage.Traverse():
            for attr in prim.GetAttributes():
                if attr.ValueMightBeTimeVarying():
                    times = attr.GetTimeSamples()
                    if times:
                        min_t = min(min_t, min(times))
                        max_t = max(max_t, max(times))
        if min_t == float("inf"):
            return 0, 0
        return min_t, max_t