"""
Composition root
"""

from __future__ import annotations

from pathlib import Path

from helios.assets.browser.service import AssetBrowserService
from helios.core.configuration.config import Configuration
from helios.core.configuration.settings import SettingsManager
from helios.core.events.bus import EventBus
from helios.core import logging_bridge
from helios.core.notifications import NotificationService
from helios.core.selection import SelectionService
from helios.core.services.registry import ServiceRegistry
from helios.core.theme import ThemeManager
from helios.core.workspace import WorkspaceManager
from helios.plugins.registry import PluginRegistry, default_registry
from helios.services.camera import CameraService
from helios.tools.manager import ToolManager
from helios.tools.select import SelectTool
from helios.tools.stubs import BoxSelectTool, MeasureTool, MoveTool, RotateTool, ScaleTool


class ApplicationContext:
    def __init__(self, config_dir: str = "config", user_data_dir: str = "~/.helios"):
        user_data_path = Path(user_data_dir).expanduser()
        config_path = Path(config_dir)

        self.events = EventBus()
        self.services = ServiceRegistry()

        self.configuration = Configuration.load([
            str(config_path / "application.yaml"),
            str(config_path / "studio.yaml"),
            str(config_path / "project.yaml"),
        ])
        self.settings = SettingsManager(str(user_data_path / "settings.yaml"), event_bus=self.events)
        self.themes = ThemeManager(event_bus=self.events, default=self.settings.get("theme.name", "dark"))
        self.workspaces = WorkspaceManager(str(user_data_path / "workspaces"), event_bus=self.events)
        self.notifications = NotificationService(self.events)
        self.selection = SelectionService(self.events)
        self.asset_browser = AssetBrowserService(
            str(config_path / "asset_browser.yaml"),
            variables={"PROJECT_ROOT": self.configuration.get("project.root", str(Path.cwd()))},
        )
        self.plugins: PluginRegistry = default_registry

        self.cameras = CameraService()

        self.tools = ToolManager()
        self.tools.register_tool(SelectTool())
        self.tools.register_tool(MoveTool())
        self.tools.register_tool(RotateTool())
        self.tools.register_tool(ScaleTool())
        self.tools.register_tool(MeasureTool())
        self.tools.register_tool(BoxSelectTool())
        self.tools.activate("select")

        logging_bridge.install(self.events)

        self.services.register(EventBus, self.events)
        self.services.register(Configuration, self.configuration)
        self.services.register(SettingsManager, self.settings)
        self.services.register(ThemeManager, self.themes)
        self.services.register(WorkspaceManager, self.workspaces)
        self.services.register(NotificationService, self.notifications)
        self.services.register(SelectionService, self.selection)
        self.services.register(AssetBrowserService, self.asset_browser)
        self.services.register(PluginRegistry, self.plugins)
        self.services.register(CameraService, self.cameras)
        self.services.register(ToolManager, self.tools)