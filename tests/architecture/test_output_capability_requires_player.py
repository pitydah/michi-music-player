"""OutputProfileService availability depends on player presence + readback.

``available``/``health()`` are never always-True: they require the player
facade and the readback surface (profile, backend, output device).
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_SOURCE = (PROJECT_ROOT / "core" / "output_profile_service.py").read_text(
    encoding="utf-8")


def test_available_is_not_always_true() -> None:
    assert '"player_missing"' in OUTPUT_SOURCE, (
        "available must report player_missing as a reason")
    assert 'reasons.append("player_missing")' in OUTPUT_SOURCE


def test_health_reflects_player_check() -> None:
    assert "def _reasons" in OUTPUT_SOURCE
    assert 'reasons.append("player_missing")' in OUTPUT_SOURCE
    assert '"reasons"' in OUTPUT_SOURCE
    assert "def health" in OUTPUT_SOURCE


def test_apply_checks_availability_first() -> None:
    assert "if not self.available" in OUTPUT_SOURCE, (
        "set_profile must refuse when the player is missing")
    assert "CAPABILITY_UNAVAILABLE" in OUTPUT_SOURCE


def test_apply_readback_verifies_intent() -> None:
    assert "READBACK_MISMATCH" in OUTPUT_SOURCE, (
        "apply must detect when the readback does not match the intent")
    assert "PARTIAL_SUCCESS" in OUTPUT_SOURCE
    assert "def _readback_matches" in OUTPUT_SOURCE


def test_bitperfect_conflicts_are_honest() -> None:
    assert "BITPERFECT_CONFLICT" in OUTPUT_SOURCE, (
        "bit-perfect incompatibilities must be reported, not ignored")
    assert "def check_compatibility" in OUTPUT_SOURCE
    assert '"conflicts"' in OUTPUT_SOURCE
