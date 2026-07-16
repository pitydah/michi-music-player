"""Michi controllers — moved to legacy_widgets."""
from __future__ import annotations


def __getattr__(name):
    if name.startswith("_"):
        raise AttributeError(name)
    import importlib
    try:
        mod = importlib.import_module(f"legacy_widgets.ui.controllers.michi.{name}")
        return mod
    except ImportError as exc:
        raise AttributeError(f"Michi controller {name} not found") from exc
