"""
Bridge between the standard logging module and the EventBus
"""
from __future__ import annotations

import logging

from helios.core.events.bus import EventBus
from helios.core.events.events import LogMessage


class EventBusLogHandler(logging.Handler):
    def __init__(self, event_bus: EventBus, level: int = logging.NOTSET):
        super().__init__(level)
        self._event_bus = event_bus

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
        except Exception:
            message = record.getMessage()
        self._event_bus.publish(LogMessage(
            level=record.levelname,
            message=message,
            logger_name=record.name,
            timestamp=record.created,
        ))


def install(event_bus: EventBus, logger_name: str = "", level: int = logging.INFO) -> EventBusLogHandler:

    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    handler = EventBusLogHandler(event_bus, level=level)
    logger.addHandler(handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(console_handler)

    return handler