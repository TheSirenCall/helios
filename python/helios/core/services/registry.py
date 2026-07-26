"""
Typed access to application wide services.
"""

from __future__ import annotations

from typing import Dict, Type, TypeVar

T = TypeVar("T")


class ServiceNotRegisteredError(KeyError):
    pass


class ServiceRegistry:
    def __init__(self) -> None:
        self._services: Dict[Type, object] = {}

    def register(self, service_type: Type[T], instance: T) -> None:
        self._services[service_type] = instance

    def get(self, service_type: Type[T]) -> T:
        try:
            return self._services[service_type]
        except KeyError as exc:
            raise ServiceNotRegisteredError(
                f"{service_type.__name__} is not registered on this ServiceRegistry"
            ) from exc

    def has(self, service_type: Type) -> bool:
        return service_type in self._services