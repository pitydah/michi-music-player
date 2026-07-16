# ruff: noqa: F403
"""UI package redirect — all modules moved to legacy_widgets."""
from __future__ import annotations
import importlib
import logging

logger = logging.getLogger("michi.ui_shim")

_LEGACY_PREFIX = "legacy_widgets.ui"
_LEGACY_ARCHIVE_PREFIX = "legacy_widgets.ui_archive"
_LEGACY_CONTROLLER_PREFIX = "legacy_widgets.ui.controllers.legacy_controllers"

_MODULE_MAP: dict[str, str] = {}

_IGNORE = ("__init__", "__pycache__")


def __getattr__(name: str):
    if name.startswith("_"):
        raise AttributeError(name)
    for prefix in (_LEGACY_CONTROLLER_PREFIX, _LEGACY_PREFIX, _LEGACY_ARCHIVE_PREFIX):
        try:
            return importlib.import_module(f"{prefix}.{name}")
        except ImportError:
            continue
    raise AttributeError(f"Module ui.{name} not found in legacy_widgets")
