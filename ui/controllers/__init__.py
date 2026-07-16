"""Controller redirects — all real controllers moved to legacy_widgets.
These stubs preserve imports for ui/window.py."""
from __future__ import annotations

import importlib
import logging

logger = logging.getLogger("michi.ui.controllers")

_LEGACY_PREFIX = "legacy_widgets.ui.controllers.legacy_controllers"


def _resolve(name: str):
    module_path = f"{_LEGACY_PREFIX}.{name}"
    try:
        return importlib.import_module(module_path)
    except ImportError:
        logger.debug("Legacy controller not found: %s", module_path)
        return None


def __getattr__(name: str):
    if name.startswith("_"):
        raise AttributeError(name)
    mod = _resolve(name)
    if mod:
        return mod
    raise AttributeError(f"Controller {name} not found")


def resolve_section_config(section_key):
    from legacy_widgets.ui.controllers.legacy_controllers.navigation_controller import resolve_section_config as _rsc
    return _rsc(section_key)
