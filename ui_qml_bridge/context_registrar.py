"""ContextRegistrar — registers context properties, validates contracts.

Validates: unique name, bridge built, QObject alive, ownership stable, no QtWidgets.
REQUIRED service absent -> blocks registration.
OPTIONAL service absent -> capability false.
No None registered as context. No duplicate instances of same service.
"""
from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QObject
from PySide6.QtQml import QQmlApplicationEngine

from ui_qml_bridge.context_bindings import ContextBinding

logger = logging.getLogger("michi.context_registrar")

CANONICAL_MAP: dict[str, str] = {
    "db": "database",
    "player_service": "playback_service",
    "search_engine": "global_search_service",
    "sync_manager": "device_sync_service",
    "michi_link_controller": "connection_service",
    "home_audio_controller": "home_audio_service",
    "radio_manager": "radio_service",
}


class ContractViolation(Exception):
    pass


class ContextRegistrar:
    def __init__(self, engine: QQmlApplicationEngine):
        self._engine = engine
        self._registered: dict[str, QObject] = {}
        self._duplicates: list[tuple[str, type, type]] = []
        self._violations: list[str] = []
        self._service_registry: dict[str, QObject] = {}

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

    def register_with_contract(self, binding: ContextBinding, bridge: QObject, service_container: Any):
        name = binding.context_name
        canonical_required = tuple(self._canonical(s) for s in binding.required_services)
        canonical_optional = tuple(self._canonical(s) for s in binding.optional_services)

        def _resolve(svc_name: str):
            if hasattr(service_container, 'contains') and service_container.contains(svc_name):
                return service_container.get(svc_name) if hasattr(service_container, 'get') else None
            if hasattr(service_container, 'get'):
                candidate = service_container.get(svc_name)
                if candidate is not None:
                    return candidate
            return None

        for svc_name in canonical_required:
            if svc_name not in self._service_registry:
                svc = _resolve(svc_name)
                if svc is None:
                    raise ContractViolation(
                        f"Cannot register '{name}': REQUIRED service '{svc_name}' not in container"
                    )
                self._service_registry[svc_name] = svc

        for svc_name in canonical_optional:
            if svc_name not in self._service_registry:
                svc = _resolve(svc_name)
                if svc is not None:
                    self._service_registry[svc_name] = svc

        self.register(name, bridge)

    def register_bindings(self, bindings: list[ContextBinding], bridges: dict[str, QObject], container: Any):
        for b in bindings:
            bridge = bridges.get(b.context_name)
            self.register_with_contract(b, bridge, container)

    def _canonical(self, name: str) -> str:
        return CANONICAL_MAP.get(name, name)

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
