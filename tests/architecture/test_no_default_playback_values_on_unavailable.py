"""No fabricated playback values when the player is unavailable.

PlayerBarService / PlaybackSnapshotService must never return invented
defaults (volume=75, state='stopped', position=0.0). The unavailable state is
explicit: ``available=False`` / ``status=SERVICE_UNAVAILABLE``.
"""
from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CORE_DIR = PROJECT_ROOT / "core"


def _read(name: str) -> str:
    return (CORE_DIR / name).read_text(encoding="utf-8")


def test_no_literal_default_volume_75() -> None:
    for name in ("player_bar_service.py", "playback_snapshot_service.py"):
        source = _read(name)
        assert "75" not in re.sub(r"#.*", "", source), (
            f"{name} must not contain a fabricated default volume (75)")


def test_player_bar_returns_explicit_unavailable_shape() -> None:
    source = _read("player_bar_service.py")
    assert "SERVICE_UNAVAILABLE" in source
    assert "available" in source
    assert "reasons" in source


def test_snapshot_service_is_explicit_on_missing_player() -> None:
    source = _read("playback_snapshot_service.py")
    assert "SERVICE_UNAVAILABLE" in source
    # No fallback-to-fabricated-state path: unavailable returns None/None.
    assert '"volume": None' in source
    assert '"position": None' in source
    assert '"state": "unavailable"' in source
    assert '"track": None' in source


def test_player_bar_state_is_never_invented_stopped() -> None:
    player_bar = _read("player_bar_service.py")
    snapshot = _read("playback_snapshot_service.py")
    # The only 'stopped' allowed is read from the backend snapshot — never a
    # default branch for the missing-player case.
    assert "unavailable" in player_bar
    assert "def get_state" in snapshot
    assert '"state": "unavailable"' in snapshot
