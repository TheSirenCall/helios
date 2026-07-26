"""
Base interface for renderer passes.

Each pass encapsulates a specific rendering stage, while the renderer
controls execution order and lifecycle. New rendering features can be
added by implementing a pass rather than modifying the main render loop.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from helios.core.camera import CameraState
from helios.core.render_scene import RenderScene


class PassContext:

    def __init__(
        self,
        render_scene: RenderScene,
        camera: CameraState,
        view_matrix: np.ndarray,
        projection_matrix: np.ndarray,
        shaders,
        state_manager,
        stats,
    ):
        self.render_scene = render_scene
        self.camera = camera
        self.view_matrix = view_matrix
        self.projection_matrix = projection_matrix
        self.shaders = shaders
        self.state_manager = state_manager
        self.stats = stats


class RenderPass(ABC):
    @abstractmethod
    def execute(self, ctx: PassContext) -> None: ...