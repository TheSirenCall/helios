"""
Maintains the application's current selection state.

Acts as the single source of truth for selection. Changes are
propagated through the EventBus, allowing the viewport, outliner, and
other tools to remain synchronized without direct dependencies.
"""
from __future__ import annotations

import logging
from typing import Iterable, Tuple

from helios.core.events.bus import EventBus
from helios.core.events.events import SelectionChanged
from helios.core.picking import SelectionMode

logger = logging.getLogger(__name__)


class SelectionService:
    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        self._selected: Tuple[str, ...] = ()
        # Current selection mode (Object, Face, Edge, or Vertex).
        # Selection is currently stored as node paths regardless of mode. The
        # mode is tracked separately so editing tools have a stable interface as
        # component selection is introduced.
        self._mode: SelectionMode = SelectionMode.OBJECT

    @property
    def selected_paths(self) -> Tuple[str, ...]:
        return self._selected

    @property
    def mode(self) -> SelectionMode:
        return self._mode

    def set_mode(self, mode: SelectionMode) -> None:
        self._mode = mode

    def set_selection(self, paths: Iterable[str]) -> None:
        """
        Updates the current selection and publishes a SelectionChanged event.

        If the selection is unchanged, no event is emitted. This prevents
        feedback loops between components that synchronize selection through the
        EventBus.
        """
        new_paths = tuple(paths)
        if new_paths == self._selected:
            return
        self._selected = new_paths
        logger.debug("SelectionService: publishing SelectionChanged(%s)", new_paths)
        self._event_bus.publish(SelectionChanged(selected_paths=new_paths))

    def clear(self) -> None:
        self.set_selection(())