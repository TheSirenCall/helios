"""
Notification framework: information/warning/error messages and
progress reporting, published through the EventBus so any panel can render
them without the source of the notification knowing who's listening.
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass
from typing import Optional

from helios.core.events.bus import Event, EventBus


class NotificationLevel(enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class NotificationPosted(Event):
    id: str
    level: NotificationLevel
    message: str
    persistent: bool = False


@dataclass(frozen=True)
class NotificationDismissed(Event):
    id: str


@dataclass(frozen=True)
class ProgressUpdated(Event):
    id: str
    label: str
    fraction: Optional[float] = None  # None = indeterminate


class NotificationService:
    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus

    def info(self, message: str, persistent: bool = False) -> str:
        return self._post(NotificationLevel.INFO, message, persistent)

    def warning(self, message: str, persistent: bool = False) -> str:
        return self._post(NotificationLevel.WARNING, message, persistent)

    def error(self, message: str, persistent: bool = True) -> str:
        return self._post(NotificationLevel.ERROR, message, persistent)

    def progress(self, label: str, fraction: Optional[float] = None,
                 progress_id: Optional[str] = None) -> str:
        progress_id = progress_id or str(uuid.uuid4())
        self._event_bus.publish(ProgressUpdated(id=progress_id, label=label, fraction=fraction))
        return progress_id

    def dismiss(self, notification_id: str) -> None:
        self._event_bus.publish(NotificationDismissed(id=notification_id))

    def _post(self, level: NotificationLevel, message: str, persistent: bool) -> str:
        notification_id = str(uuid.uuid4())
        self._event_bus.publish(NotificationPosted(
            id=notification_id, level=level, message=message, persistent=persistent
        ))
        return notification_id