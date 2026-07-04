"""ContextRegistrar — registers context properties, detects duplicates, enables audit."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject
from PySide6.QtQml import QQmlApplicationEngine

if TYPE_CHECKING:
    pass

logger = logging.getLogger("michi.context_registrar")


class ContextRegistrar:
    """Registers QML context properties and detects duplicates."""

    def __init__(self, engine: QQmlApplicationEngine):
        self._engine = engine
        self._registered: dict[str, type] = {}
        self._duplicates: list[tuple[str, type, type]] = []

    def register(self, name: str, obj: QObject | None):
        if obj is None:
            logger.debug("ContextRegistrar: skipping None for '%s'", name)
            return
        if name in self._registered:
            existing_type = type(self._registered[name])
            new_type = type(obj)
            if existing_type is not new_type:
                self._duplicates.append((name, existing_type, new_type))
                logger.warning("ContextRegistrar: duplicate '%s' (%s -> %s)", name, existing_type.__name__, new_type.__name__)
            else:
                logger.debug("ContextRegistrar: re-registering '%s' (same type)", name)
        self._registered[name] = obj
        self._engine.rootContext().setContextProperty(name, obj)

    def register_dict(self, mapping: dict[str, QObject | None]):
        for name, obj in mapping.items():
            self.register(name, obj)

    @property
    def count(self) -> int:
        return len(self._registered)

    @property
    def names(self) -> list[str]:
        return sorted(self._registered.keys())

    @property
    def duplicates(self) -> list[tuple[str, type, type]]:
        return list(self._duplicates)

    def audit(self) -> dict:
        return {
            "total": self.count,
            "names": self.names,
            "duplicates": [(n, t1.__name__, t2.__name__) for n, t1, t2 in self._duplicates],
        }
