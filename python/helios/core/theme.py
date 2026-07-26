"""
Centralizes the application's visual styling.

Widgets obtain colors, fonts, and stylesheets from the theme rather than
defining them locally, allowing the application's appearance to be
changed by swapping the active Theme.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from helios.core.events.bus import EventBus
from helios.core.events.events import ThemeChanged


@dataclass(frozen=True)
class Theme:
    name: str
    colors: Dict[str, str] = field(default_factory=dict)
    fonts: Dict[str, str] = field(default_factory=dict)
    icon_set: str = "default"


DARK_THEME = Theme(
    name="dark",
    colors={
        "background": "#2b2b2b",
        "surface": "#3a3a3a",
        "accent": "#78b4ff",
        "text": "#dddddd",
        "border": "#444444",
    },
    fonts={"default": "Inter, 10pt"},
)

LIGHT_THEME = Theme(
    name="light",
    colors={
        "background": "#f2f2f2",
        "surface": "#ffffff",
        "accent": "#2f6fed",
        "text": "#1a1a1a",
        "border": "#cccccc",
    },
    fonts={"default": "Inter, 10pt"},
)

_BUILTIN_THEMES = {theme.name: theme for theme in (DARK_THEME, LIGHT_THEME)}


class ThemeManager:
    def __init__(self, event_bus: Optional[EventBus] = None, default: str = "dark"):
        self._event_bus = event_bus
        self._themes: Dict[str, Theme] = dict(_BUILTIN_THEMES)
        self._current = self._themes.get(default, DARK_THEME)

    def register_theme(self, theme: Theme) -> None:
        """Plugins register additional Theme objects the same way
        importers/renderers register with the PluginRegistry."""
        self._themes[theme.name] = theme

    @property
    def current(self) -> Theme:
        return self._current

    def set_theme(self, name: str) -> None:
        if name not in self._themes:
            raise KeyError(f"Unknown theme: {name}")
        self._current = self._themes[name]
        if self._event_bus is not None:
            self._event_bus.publish(ThemeChanged(theme_name=name))

    def stylesheet(self) -> str:

        # TODO: expand this into a proper QSS styling
        c = self._current.colors
        return (
            f"QWidget {{ background-color: {c['background']}; color: {c['text']}; }}"
            f" QLineEdit, QSpinBox {{ background-color: {c['surface']}; border: 1px solid {c['border']}; }}"
            f" QPushButton {{ background-color: {c['surface']}; border: 1px solid {c['border']}; }}"
        )