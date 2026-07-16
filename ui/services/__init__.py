# ruff: noqa: F403
"""Services redirect — moved to legacy_widgets."""
from __future__ import annotations
import importlib


def __getattr__(name: str):
    if name.startswith("_"):
        raise AttributeError(name)
    try:
        return importlib.import_module(f"legacy_widgets.ui_archive.services.{name}")
    except ImportError:
        try:
            return importlib.import_module(f"legacy_widgets.ui.services.{name}")
        except ImportError as exc:
            raise AttributeError(f"Service {name} not found") from exc
