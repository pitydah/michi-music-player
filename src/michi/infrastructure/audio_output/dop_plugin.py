"""Canonical discovery of the installed DoP GStreamer plugin.

Two installation shapes are valid and must resolve to the SAME canonical
directory (the directory that contains ``libmichidop.so`` and its manifest):

* Gate A private prefix root: ``<root>/lib/gstreamer-1.0/``
* Gate B installed wheel: ``<site-packages>/michi/native/gstreamer-1.0/``

Consumers must never concatenate ``lib/gstreamer-1.0`` themselves; that is
how the installed-wheel certification silently skipped in CI.
"""

from __future__ import annotations

import os
from pathlib import Path

_PLUGIN_FILENAME = "libmichidop.so"
_MANIFEST_FILENAME = "michidop.manifest.json"


def _plugin_dir(candidate: Path) -> Path | None:
    """Return ``candidate`` when it is a complete plugin directory."""
    if (candidate / _PLUGIN_FILENAME).is_file() and (
        candidate / _MANIFEST_FILENAME
    ).is_file():
        return candidate
    return None


def installed_dop_prefix() -> Path | None:
    """Return the app-owned installed plugin directory, if complete."""
    import michi

    root = Path(michi.__file__).resolve().parent / "native/gstreamer-1.0"
    return _plugin_dir(root)


def resolve_dop_prefix() -> Path:
    """Resolve the canonical plugin directory (never a laboratory root).

    ``MICHI_DOP_PLUGIN_PREFIX`` is the canonical override. The legacy
    ``MICHI_DOP_PREFIX`` name is accepted for Gate A installers. Both a
    private-prefix root and a direct plugin directory normalize to the
    directory holding the shared object and manifest.
    """
    explicit = (
        os.environ.get("MICHI_DOP_PLUGIN_PREFIX", "").strip()
        or os.environ.get("MICHI_DOP_PREFIX", "").strip()
    )
    if explicit:
        root = Path(explicit).resolve()
        for candidate in (root, root / "lib/gstreamer-1.0"):
            found = _plugin_dir(candidate)
            if found is not None:
                return found
        raise RuntimeError(
            "DOP_RUNTIME_UNAVAILABLE: explicit DoP prefix has no complete "
            f"plugin directory: {root}"
        )
    installed = installed_dop_prefix()
    if installed is None:
        raise RuntimeError("DOP_RUNTIME_UNAVAILABLE: installed michidop not found")
    return installed.resolve()


def resolve_dop_plugin_path() -> Path:
    """Return the canonical shared object for the resolved installation."""
    return resolve_dop_prefix() / _PLUGIN_FILENAME


def resolve_dop_manifest_path() -> Path:
    """Return the canonical manifest for the resolved installation."""
    return resolve_dop_prefix() / _MANIFEST_FILENAME
