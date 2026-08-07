"""FASE 5 P0 — radio never reports success without effective playback.

Source-level gates:

- No ``if playback_backend is None: return True`` / ``return True`` fallback in
  ``core/radio/`` or ``ui_qml_bridge/radio_bridge.py``: an absent playback
  mechanism is an explicit failure.
- The bridge holds no optimistic ``_is_playing = True`` assignment: playback
  flags only change through service state events or player readback.
- Composition registers the canonical stack directly: SqliteStationRepository,
  SqliteRadioHistoryRepository, RadioPlaybackAdapter and the canonical
  RadioService — the legacy facade never constructs the canonical service in
  productive composition.
"""
from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

RADIO_DIR = PROJECT_ROOT / "core" / "radio"
BRIDGE_FILE = PROJECT_ROOT / "ui_qml_bridge" / "radio_bridge.py"
COMPOSITION_FILE = PROJECT_ROOT / "core" / "composition" / "ecosystem.py"

_FALLBACK_PATTERNS = (
    r"if\s+playback_backend\s+is\s+None\s*:\s*return\s+True",
    r"if\s+self\._playback_backend\s+is\s+None\s*:\s*return\s+True",
    r"if\s+self\._playback_adapter\s+is\s+None\s*:\s*return\s+True",
    r"if\s+backend\s+is\s+None\s*:\s*return\s+True",
    r"if\s+self\._player\s+is\s+None\s*:\s*return\s+True",
    r"if\s+player\s+is\s+None\s*:\s*return\s+True",
)


def _radio_sources() -> list[str]:
    return [
        p.read_text(encoding="utf-8", errors="ignore")
        for p in RADIO_DIR.glob("*.py")
        if p.suffix == ".py"
    ]


def test_no_success_fallback_when_backend_missing() -> None:
    sources = _radio_sources() + [BRIDGE_FILE.read_text(encoding="utf-8")]
    for pattern in _FALLBACK_PATTERNS:
        for src in sources:
            assert not re.search(pattern, src), (
                f"prohibited fallback '{pattern}' found in radio chain"
            )


def test_playback_adapter_is_used_by_canonical_service() -> None:
    service = (RADIO_DIR / "service.py").read_text(encoding="utf-8")
    adapter = (RADIO_DIR / "playback_adapter.py").read_text(encoding="utf-8")
    assert "playback_adapter" in service
    assert "load_stream" in adapter and "get_state" in adapter
    assert "BACKEND_UNAVAILABLE" in service


def test_bridge_has_no_optimistic_is_playing() -> None:
    source = BRIDGE_FILE.read_text(encoding="utf-8")
    # The only place playback flags flip to True is _apply_state (readback
    # driven). A second occurrence anywhere is an optimistic assignment.
    assert source.count("self._is_playing = True") == 1, (
        "bridge must set _is_playing=True only inside _apply_state (readback)"
    )
    apply_state = source.split("def _apply_state", 1)[1].split("def _sync_readback", 1)[0]
    assert "self._is_playing = True" in apply_state
    # Playback flags only change through the state-reflection methods.
    assert "_apply_state" in source
    assert "play_station" in source


def test_bridge_delegates_play_and_stop() -> None:
    source = BRIDGE_FILE.read_text(encoding="utf-8")
    assert "play_station(url, name)" in source
    assert 'getattr(self._radio_mgr, "stop", None)' in source


def test_bridge_does_not_talk_to_player_directly() -> None:
    source = BRIDGE_FILE.read_text(encoding="utf-8")
    # The bridge may subscribe to the player readback signal, but it must
    # never start/stop playback itself.
    assert "self._player.play_url" not in source
    assert "self._player.play(" not in source
    assert "self._player.stop()" not in source


def test_composition_registers_canonical_stack_directly() -> None:
    source = COMPOSITION_FILE.read_text(encoding="utf-8")
    for component in (
        "SqliteStationRepository",
        "SqliteRadioHistoryRepository",
        "RadioPlaybackAdapter",
        "CanonicalRadioService",
    ):
        assert component in source, (
            f"composition must register {component} directly"
        )
    # The legacy facade is NOT imported by productive composition.
    assert "from core.radio.radio_service" not in source
    assert 'register("radio_station_repository"' in source
    assert 'register("radio_history_repository"' in source
    assert 'register("radio_playback_adapter"' in source
    assert 'register("radio_service"' in source
    # radio_service is registered twice at most: once productive, once as a
    # None degradation on failure (same convention as every ecosystem block).
    assert source.count('register("radio_service"') == 2


def test_canonical_service_registers_attempt_before_play() -> None:
    service = (RADIO_DIR / "service.py").read_text(encoding="utf-8")
    # Play history is recorded on PLAYING, never at connection start.
    assert "record_event(" in service
    assert '"play"' in service
    assert '"attempt"' in service
    # start_station must not bump play counters at start.
    assert "mark_played" in service
    assert "self.mark_played(station_id)" not in service
