"""
Displays and interacts with the current scene.

The viewport owns the camera, renders the scene through
SceneExtractor, and dispatches user input to the tool system. Camera
navigation is always available, while editing and selection are handled
by the active tool.

The viewport depends only on the SceneGraph and renderer interfaces,
remaining independent of scene importers and file formats.
"""
from __future__ import annotations

import logging
from typing import Optional

from PySide6 import QtCore
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from helios.core.camera import CameraState
from helios.core.events.bus import EventBus
from helios.core.events.events import RenderStatsUpdated, SceneModified, SelectionChanged
from helios.core.render_scene import RenderScene
from helios.core.scene_extractor import SceneExtractor
from helios.core.selection import SelectionService
from helios.renderers.base import Renderer
from helios.scene.graph import SceneGraph
from helios.tools.light import LightTool
from helios.tools.manager import ToolManager
from helios.tools.orbit import OrbitTool
from helios.tools.pan import PanTool
from helios.tools.zoom import ZoomTool

logger = logging.getLogger(__name__)


class SceneViewport(QOpenGLWidget):
    def __init__(self, renderer: Renderer, event_bus: EventBus,
                 selection_service: SelectionService, tool_manager: ToolManager, parent=None):
        super().__init__(parent)
        # QOpenGLWidget defaults to Qt.NoFocus and without this,
        # keyPressEvent (Q/W/E/R tool switch, Escape to clear) would
        # silently never fire, no matter how correct its body is.
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.renderer = renderer
        self.camera = CameraState()
        self.event_bus = event_bus
        self.selection_service = selection_service
        self.tool_manager = tool_manager
        self.extractor = SceneExtractor()

        # Always on camera navigation, independent of the active tool
        # Alt+drag orbit/pan/zoom and Ctrl+drag light work no matter
        # which manipulation tool (Select, future Move/Rotate/Scale) is active.
        self._nav_tools = [OrbitTool(), PanTool(), ZoomTool(), LightTool()]

        self.scene: Optional[SceneGraph] = None
        self.current_frame = 0.0

        event_bus.subscribe(SelectionChanged, self._on_selection_changed)
        event_bus.subscribe(SceneModified, self._on_scene_modified)

    def initializeGL(self):
        self.renderer.initialize()
        self.resizeGL(self.width(), self.height())

    def resizeGL(self, w, h):
        self.renderer.resize(w, h)

    def paintGL(self):
        render_scene = self.extractor.extract(self.scene, self.current_frame)
        self.renderer.draw(render_scene, self.camera)
        self._publish_render_stats()

    def _publish_render_stats(self) -> None:
        """
        Publishes renderer statistics when supported by the active backend.

        Statistics are an optional renderer capability rather than part of the
        Renderer interface, allowing backends to expose implementation specific
        metrics or omit them entirely.
        """
        stats = getattr(self.renderer, "stats", None)
        if stats is None:
            return
        fps = 1000.0 / stats.cpu_frame_ms if stats.cpu_frame_ms > 0 else 0.0
        self.event_bus.publish(RenderStatsUpdated(
            cpu_frame_ms=stats.cpu_frame_ms, fps=fps,
            draw_calls=stats.draw_calls, triangles=stats.triangles, vertices=stats.vertices,
            buffer_uploads=stats.buffer_uploads, uploaded_vertices=stats.uploaded_vertices,
            shader_switches=stats.shader_switches,
        ))

    def current_render_scene(self) -> RenderScene:
        """
        Returns the most recently extracted RenderScene.

        Rendering and viewport tools share the same cached scene, ensuring they
        operate on the same data without triggering additional extraction.
        """
        return self.extractor.extract(self.scene, self.current_frame)

    def set_scene(self, scene: Optional[SceneGraph]):
        self.scene = scene
        self.reset_camera()
        if scene is not None:
            self.set_frame(scene.frame_range[0])
        else:
            self.update()

    def set_frame(self, frame: float):
        self.current_frame = frame
        self.update()

    def reset_camera(self):
        """
        Restores the default camera framing.

        The scene uses a normalized coordinate space, so the default camera
        always frames it without requiring scene dependent calculations.
        """
        self.camera.reset()
        self.update()

    def cleanup(self) -> None:
        """
        Releases renderer GPU resources.

        This should be called before the viewport is destroyed. The viewport
        makes its OpenGL context current to ensure resources are released
        correctly.
        """
        self.makeCurrent()
        try:
            self.renderer.destroy()
        finally:
            self.doneCurrent()

    def _on_selection_changed(self, event: SelectionChanged) -> None:
        logger.debug("SceneViewport: SelectionChanged -> highlight(%s)", event.selected_paths)
        self.renderer.highlight(event.selected_paths)

        # Keep SceneNode.selected synchronized with SelectionService.
        # SelectionService owns the selection state, while SceneGraph queries
        # rely on the per-node selected flag.
        if self.scene is not None:
            selected_set = set(event.selected_paths)
            for node in self.scene.walk():
                node.selected = node.path in selected_set

        self.update()

    def _on_scene_modified(self, _event: SceneModified) -> None:
        """
        Invalidates the extracted scene cache.

        Scene edits can change the sampled output without changing the scene
        identity or current frame, so cached render data must be discarded after
        in-place modifications.
        """
        self.extractor.invalidate()
        self.update()

    # Event dispatch. Input events are forwarded to the navigation tools
    # and the active tool; interaction logic is implemented by the tools,
    # not the viewport.
    def mousePressEvent(self, event):
        self.setFocus(QtCore.Qt.FocusReason.MouseFocusReason)
        logger.debug("SceneViewport: mousePressEvent at %s, active tool=%s",
                     event.position(), self.tool_manager.active_tool)
        for tool in self._nav_tools:
            tool.on_mouse_press(self, event)
        if self.tool_manager.active_tool is not None:
            self.tool_manager.active_tool.on_mouse_press(self, event)

    def mouseMoveEvent(self, event):
        for tool in self._nav_tools:
            tool.on_mouse_move(self, event)
        if self.tool_manager.active_tool is not None:
            self.tool_manager.active_tool.on_mouse_move(self, event)

    def mouseReleaseEvent(self, event):
        logger.debug("SceneViewport: mouseReleaseEvent at %s", event.position())
        for tool in self._nav_tools:
            tool.on_mouse_release(self, event)
        if self.tool_manager.active_tool is not None:
            self.tool_manager.active_tool.on_mouse_release(self, event)

    def wheelEvent(self, event):
        for tool in self._nav_tools:
            tool.on_wheel(self, event)
        if self.tool_manager.active_tool is not None:
            self.tool_manager.active_tool.on_wheel(self, event)

    def keyPressEvent(self, event):
        key = event.key()
        tool_for_key = {
            QtCore.Qt.Key.Key_Q: "select",
            QtCore.Qt.Key.Key_W: "move",
            QtCore.Qt.Key.Key_E: "rotate",
            QtCore.Qt.Key.Key_R: "scale",
        }.get(key)
        if tool_for_key is not None:
            try:
                self.tool_manager.activate(tool_for_key, self)
                logger.debug("SceneViewport: switched active tool to '%s'", tool_for_key)
            except KeyError:
                pass
            return
        if key == QtCore.Qt.Key.Key_Escape:
            self.selection_service.clear()
            return
        super().keyPressEvent(event)