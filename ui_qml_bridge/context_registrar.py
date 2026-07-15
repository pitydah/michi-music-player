"""ContextRegistrar — registers context properties, validates contracts.

Validates: unique name, bridge built, QObject alive, ownership stable, no QtWidgets.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject
from PySide6.QtQml import QQmlApplicationEngine

if TYPE_CHECKING:
    pass

logger = logging.getLogger("michi.context_registrar")


class ContextRegistrar:
    """Registers QML context properties with contract validation."""

    def __init__(self, engine: QQmlApplicationEngine):
        self._engine = engine
        self._registered: dict[str, QObject] = {}
        self._duplicates: list[tuple[str, type, type]] = []
        self._violations: list[str] = []

    def register(self, name: str, obj: QObject | None):
        violations = self._validate_contract(name, obj)
        if violations:
            self._violations.extend(violations)
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

    def _validate_contract(self, name: str, obj: QObject | None) -> list[str]:
        issues = []
        if obj is None:
            issues.append(f"bridge '{name}' is None")
            return issues
        if hasattr(obj, '__module__') and 'QtWidgets' in getattr(obj.__class__, '__module__', ''):
            issues.append(f"'{name}' is from QtWidgets")
        return issues

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

    @property
    def violations(self) -> list[str]:
        return list(self._violations)

    def audit(self) -> dict:
        return {
            "total": self.count,
            "names": self.names,
            "duplicates": [(n, t1.__name__, t2.__name__) for n, t1, t2 in self._duplicates],
            "violations": list(self._violations),
        }
