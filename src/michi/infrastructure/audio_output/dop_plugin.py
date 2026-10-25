"""Canonical discovery of the app-owned Gate B DoP plugin prefix."""

from __future__ import annotations

import os
from pathlib import Path


def installed_dop_prefix() -> Path | None:
    """Return the app-owned plugin directory, if it exists."""
    import michi

    root = Path(michi.__file__).resolve().parent / "native/gstreamer-1.0"
    return root if (root / "michidop.manifest.json").is_file() else None


def resolve_dop_prefix() -> Path:
    explicit = os.environ.get("MICHI_DOP_PLUGIN_PREFIX", "").strip()
    if explicit:
        return Path(explicit).resolve()
    installed = installed_dop_prefix()
    if installed is None:
        raise RuntimeError("DOP_RUNTIME_UNAVAILABLE: installed michidop not found")
    return installed.resolve()
