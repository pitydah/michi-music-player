"""Radio single-domain authority (Slice 5, ADR-002).

- Exactly one productive ``RadioService``: ``core/radio/service.py`` (advanced:
  sessions, stream probe, reconnect, sqlite persistence). The legacy facade in
  ``core/radio/radio_service.py`` is marked ``# LEGACY`` and delegates to it.
- The bridge holds no parallel history list and constructs no station store.
- ``removeStation`` must reference the injected service, never an unassigned
  ``_radio_svc``.
"""
from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

RADIO_DIR = PROJECT_ROOT / "core" / "radio"
BRIDGE_FILE = PROJECT_ROOT / "ui_qml_bridge" / "radio_bridge.py"


def _radio_sources() -> dict[str, str]:
    return {
        p.name: p.read_text(encoding="utf-8", errors="ignore")
        for p in RADIO_DIR.glob("*.py")
    }


def test_exactly_one_productive_radio_service() -> None:
    sources = _radio_sources()
    defining = {
        name for name, src in sources.items()
        if re.search(r"^class\s+RadioService\b", src, re.M)
    }
    assert "service.py" in defining, (
        f"canonical core/radio/service.py must define RadioService (got {defining})"
    )
    # The canonical file must NOT be marked LEGACY.
    assert "# LEGACY" not in sources.get("service.py", ""), (
        "canonical core/radio/service.py must not be marked LEGACY"
    )
    # Every other defining file must be explicitly marked LEGACY.
    for name in defining - {"service.py"}:
        assert "# LEGACY" in sources[name], (
            f"{name} defines RadioService without a LEGACY marker"
        )


def test_bridge_has_no_parallel_history() -> None:
    source = BRIDGE_FILE.read_text(encoding="utf-8")
    assert "self._history = [" not in source, (
        "radio_bridge must not keep a parallel in-memory history list"
    )
    assert "_add_to_history" not in source, (
        "radio_bridge must not append to its own history"
    )
    # History reads must come from the service.
    assert "get_history" in source


def test_bridge_crud_reaches_service_api() -> None:
    source = BRIDGE_FILE.read_text(encoding="utf-8")
    for method in ("get_stations", "add_station", "edit_station",
                   "delete_station", "favorite_station", "search_stations",
                   "clear_history", "play_station"):
        assert method in source, (
            f"radio_bridge must delegate through '{method}'"
        )
    # Playback delegation goes through the service; the bridge never records
    # plays itself (the canonical service owns history on PLAYING).
    assert "mark_played" not in source, (
        "radio_bridge must not record plays — the canonical service does"
    )


def test_remove_station_uses_injected_service() -> None:
    source = BRIDGE_FILE.read_text(encoding="utf-8")
    assert "_radio_svc" not in source, (
        "removeStation must not reference the unassigned '_radio_svc'"
    )
    assert "self._radio_mgr" in source


def test_bridge_does_not_construct_station_repository() -> None:
    source = BRIDGE_FILE.read_text(encoding="utf-8")
    assert "SqliteStationRepository" not in source
    assert "RadioRepository(" not in source
    assert "RadioManager(" not in source
    assert "import sqlite3" not in source


def test_no_parallel_instantiation_in_composition() -> None:
    """ecosystem.py must construct a single radio service object."""
    source = (PROJECT_ROOT / "core" / "composition" / "ecosystem.py").read_text(
        encoding="utf-8", errors="ignore")
    # One productive registration + one None degradation on failure (same
    # convention as every ecosystem block); never a second construction.
    assert source.count('register("radio_service"') == 2
    assert source.count("CanonicalRadioService(") == 1
