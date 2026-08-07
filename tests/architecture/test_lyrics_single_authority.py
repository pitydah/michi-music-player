"""Lyrics single-domain authority (Slice 5, ADR-002).

- Exactly one productive ``LyricsService``: ``core/lyrics/service.py``
  (resolver/registry/providers/cache/editor/timeline/undo/attribution). The
  legacy ``core/lyrics_service.py`` is marked ``# LEGACY`` and is not wired
  into the container.
- The bridge constructs no LrcLibClient and keeps no second cache.
- ``load_sidecar`` must READ (never call ``save_sidecar``).
"""
from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

LYRICS_DIR = PROJECT_ROOT / "core" / "lyrics"
BRIDGE_FILE = PROJECT_ROOT / "ui_qml_bridge" / "lyrics_bridge.py"


def _lyrics_sources() -> dict[str, str]:
    return {
        p.name: p.read_text(encoding="utf-8", errors="ignore")
        for p in LYRICS_DIR.glob("*.py")
    }


def test_exactly_one_productive_lyrics_service() -> None:
    sources = _lyrics_sources()
    defining = {
        name for name, src in sources.items()
        if re.search(r"^class\s+LyricsService\b", src, re.M)
    }
    assert "service.py" in defining, (
        f"canonical core/lyrics/service.py must define LyricsService (got {defining})"
    )
    assert "# LEGACY" not in sources.get("service.py", ""), (
        "canonical core/lyrics/service.py must not be marked LEGACY"
    )
    for name in defining - {"service.py"}:
        assert "# LEGACY" in sources[name], (
            f"{name} defines LyricsService without a LEGACY marker"
        )


def test_load_sidecar_reads_never_writes() -> None:
    source = (LYRICS_DIR / "service.py").read_text(encoding="utf-8")
    assert "def load_sidecar" in source
    # The bug was calling save_sidecar from load_sidecar, writing an empty doc.
    assert "self._storage.load_sidecar(directory, identity)" in source
    assert "self._storage.save_sidecar(directory, LyricsDocument(identity=identity))" not in source
    storage = (LYRICS_DIR / "storage.py").read_text(encoding="utf-8")
    assert "def load_sidecar" in storage
    assert "self._sidecar.read(directory, identity)" in storage


def test_bridge_has_no_own_http_client() -> None:
    source = BRIDGE_FILE.read_text(encoding="utf-8")
    assert "LrcLibClient" not in source, (
        "lyrics_bridge must not construct its own LrcLibClient"
    )
    assert "search_lyrics" not in source
    assert "urllib" not in source


def test_bridge_has_no_second_cache() -> None:
    source = BRIDGE_FILE.read_text(encoding="utf-8")
    assert "self._cache" not in source, (
        "lyrics_bridge must not keep a second cache (service owns the cache)"
    )
    assert "self._cache_order" not in source
    assert "_trim_cache" not in source


def test_bridge_delegates_to_service_methods() -> None:
    source = BRIDGE_FILE.read_text(encoding="utf-8")
    for method in ("resolve", "search_manual", "save_local", "invalidate_identity"):
        assert method in source, (
            f"lyrics_bridge must delegate through the canonical '{method}'"
        )


def test_legacy_service_not_wired_in_composition() -> None:
    source = (PROJECT_ROOT / "core" / "composition" / "ecosystem.py").read_text(
        encoding="utf-8", errors="ignore")
    assert "core.lyrics.service" in source
    assert "from core.lyrics_service import LyricsService" not in source
