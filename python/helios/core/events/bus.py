"""
Lightweight, synchronous publish/subscribe event bus.

Modules communicate through named event types rather than holding direct
references to each other ( the Timeline publishes FrameChanged without knowing
whether a Viewport, an Inspector, a Python console, or an Asset Browser is listening).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, DefaultDict, List, Type, TypeVar

logger = logging.getLogger(__name__)

EventT = TypeVar("EventT", bound="Event")
Handler = Callable[[EventT], None]


@dataclass(frozen=True)
class Event:
    """Base class for all events."""


class EventBus:
    """
    one EventBus is created by the ApplicationContext composition root
    and passed to whatever needs it.
    That keeps dependencies explicit and keeps tests possible without global state.
    """

    def __init__(self) -> None:
        self._handlers: DefaultDict[Type[Event], List[Handler]] = defaultdict(list)

    def subscribe(self, event_type: Type[EventT], handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: Type[EventT], handler: Handler) -> None:
        handlers = self._handlers.get(event_type)
        if handlers and handler in handlers:
            handlers.remove(handler)

    def publish(self, event: Event) -> None:
        """
        Dispatch to every handler registered for the event's exact
        type. Handler exceptions are logged rather than propagated.
        """

        handlers = list(self._handlers.get(type(event), ()))
        logger.debug("EventBus: publishing %s to %d handler(s)", type(event).__name__, len(handlers))
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception("EventBus: handler for %s raised", type(event).__name__)