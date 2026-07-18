"""Test RiskPolicy classifies actions correctly."""
from __future__ import annotations

from core.ai.risk_policy import RiskPolicy, RiskLevel


def test_safe_actions():
    rp = RiskPolicy()
    safe_actions = [
        "search_library", "get_playback_status", "list_albums",
        "get_diagnostics", "get_suggestions", "navigate",
    ]
    for action in safe_actions:
        risk = rp.assess(action)
        assert risk == RiskLevel.SAFE, f"{action} should be SAFE"
        assert rp.require_confirmation(risk) is False


def test_critical_actions():
    rp = RiskPolicy()
    critical_actions = [
        "delete_from_disk", "format_drive", "unpair_all", "factory_reset",
    ]
    for action in critical_actions:
        risk = rp.assess(action)
        assert risk == RiskLevel.CRITICAL, f"{action} should be CRITICAL"
        assert rp.require_confirmation(risk) is True


def test_moderate_actions():
    rp = RiskPolicy()
    moderate_actions = [
        "delete_from_library", "batch_metadata_edit", "convert_files",
        "unpair_device", "pair_device", "transfer_files",
    ]
    for action in moderate_actions:
        risk = rp.assess(action)
        assert risk == RiskLevel.MODERATE, f"{action} should be MODERATE"
        assert rp.require_confirmation(risk) is True


def test_low_actions():
    rp = RiskPolicy()
    low_actions = [
        "skip_track", "change_volume", "add_to_queue",
        "create_playlist", "toggle_favorite",
    ]
    for action in low_actions:
        risk = rp.assess(action)
        assert risk == RiskLevel.LOW, f"{action} should be LOW"


def test_unknown_action_defaults_to_moderate():
    rp = RiskPolicy()
    risk = rp.assess("nonexistent_action")
    assert risk == RiskLevel.MODERATE
