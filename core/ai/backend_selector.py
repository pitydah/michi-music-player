from __future__ import annotations

import logging
from typing import Any

from core.ai.backends.base import LocalModelBackend
from core.ai.backends.calico import CalicoBackend
from core.ai.backends.munchkin import MunchkinBackend
from core.ai.backends.carey import CareyBackend
from core.ai.backends.maine_coon import MaineCoonBackend
from core.ai.backends.sphynx import SphynxBackend

logger = logging.getLogger("michi.backend_selector")

_BACKEND_PRIORITY: list[type[LocalModelBackend]] = [
    SphynxBackend,
    MaineCoonBackend,
    CareyBackend,
    MunchkinBackend,
    CalicoBackend,
]

_BACKEND_NAMES: dict[str, type[LocalModelBackend]] = {
    "calico": CalicoBackend,
    "munchkin": MunchkinBackend,
    "carey": CareyBackend,
    "maine_coon": MaineCoonBackend,
    "sphynx": SphynxBackend,
}


class BackendSelector:
    def __init__(self, model_manager: Any | None = None) -> None:
        self._model_manager = model_manager
        self._backends: dict[str, LocalModelBackend] = {}
        self._active_name: str = "calico"

    def _get_or_create(self, name: str) -> LocalModelBackend:
        if name not in self._backends:
            cls = _BACKEND_NAMES.get(name, CalicoBackend)
            if name in ("munchkin", "carey", "maine_coon"):
                self._backends[name] = cls(model_manager=self._model_manager)
            else:
                self._backends[name] = cls()
        return self._backends[name]

    @property
    def active(self) -> LocalModelBackend:
        return self._get_or_create(self._active_name)

    def set_active(self, name: str) -> None:
        if name not in _BACKEND_NAMES:
            logger.warning("Unknown backend '%s', falling back to calico", name)
            name = "calico"
        self._active_name = name
        logger.info("Active backend set to '%s'", name)

    def auto_fallback(self) -> LocalModelBackend:
        current = self.active
        if current.is_available():
            return current

        for cls in _BACKEND_PRIORITY:
            for bname, bcls in _BACKEND_NAMES.items():
                if bcls is cls:
                    backend = self._get_or_create(bname)
                    if backend.is_available():
                        logger.info("Auto-fallback: %s -> %s", self._active_name, bname)
                        self._active_name = bname
                        return backend
        self._active_name = "calico"
        return self._get_or_create("calico")

    def available_backends(self) -> dict[str, bool]:
        result: dict[str, bool] = {}
        for name in _BACKEND_NAMES:
            backend = self._get_or_create(name)
            result[name] = backend.is_available()
        return result

    def get_backend(self, name: str) -> LocalModelBackend | None:
        if name not in _BACKEND_NAMES:
            return None
        return self._get_or_create(name)
