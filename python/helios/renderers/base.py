"""
Backend agnostic renderer interface.

The viewport interacts only with this interface and passes a RenderScene
prepared by SceneExtractor. Required methods cover the core rendering
lifecycle, while optional capabilities provide extension points for
features such as picking and viewport interaction without forcing every
backend to implement them immediately.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence, Tuple

from helios.core.camera import CameraState
from helios.core.picking import PickingResult, SelectionMode
from helios.core.render_scene import RenderScene


class Renderer(ABC):
    @abstractmethod
    def initialize(self) -> None: ...

    @abstractmethod
    def resize(self, width: int, height: int) -> None: ...

    @abstractmethod
    def draw(self, render_scene: RenderScene, camera: CameraState) -> None: ...

    def pick(
        self,
        screen_x: int,
        screen_y: int,
        viewport_width: int,
        viewport_height: int,
        camera: CameraState,
        render_scene: RenderScene,
        mode: SelectionMode = SelectionMode.OBJECT,
    ) -> PickingResult:
        """
        Returns the object hit at the given screen position.

        Returns a PickingResult with path=None when no object is hit. Backends
        without picking support use the default implementation, which always
        returns a miss.
        """
        return PickingResult()

    def frame(self, bounding_box: Optional[Sequence[Tuple[float, float, float]]], camera: CameraState) -> None:
        """
        Frames the camera to fit the given bounding box.

        The default implementation restores the standard camera framing when a
        backend does not provide custom bounds fitting.
        """
        camera.reset()

    def highlight(self, node_paths: Sequence[str]) -> None:
        """
        Sets the scene nodes to highlight during the next render.

        Accepts zero or more node paths for selection outlining. The default
        implementation does nothing for backends that do not support selection
        highlighting.
        """
        return None

    def hover(self, node_path: Optional[str]) -> None:
        """
        Updates the currently hovered node for viewport feedback.

        Pass None to clear the hover state. Hover rendering is separate from
        selection highlighting and is a no op for backends without hover support.
        """
        return None

    def draw_overlay(self, camera: CameraState) -> None:
        """
        Renders viewport helpers such as grids and axes.

        The default implementation is a no op. Backends may expose these as a
        separate capability or integrate them directly into their main render
        pipeline.
        """
        return None

    def draw_gizmo(self, node_path: Optional[str], camera: CameraState) -> None:
        """
        Renders viewport manipulation gizmos.

        Provides an extension point for future Move, Rotate, and Scale
        manipulators. The default implementation is a no op for backends that do
        not support gizmo rendering.
        """
        return None

    def destroy(self) -> None:
        """
        Releases renderer owned resources.

        The default implementation is a no op for backends without explicit
        resource management. Backends that allocate GPU resources should
        override this method and release them while their graphics context is
        active.
        """
        return None