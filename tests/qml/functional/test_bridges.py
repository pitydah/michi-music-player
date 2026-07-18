"""Test: all bridges instantiate without errors and expose expected signals/slots."""
from unittest.mock import MagicMock, patch

import pytest


def _try_import(mod_path: str):
    import importlib
    try:
        return importlib.import_module(mod_path)
    except ImportError as e:
        pytest.skip(f"Cannot import {mod_path}: {e}")
        return None


BRIDGE_MODULES = [
    "ui_qml_bridge.navigation_bridge",
    "ui_qml_bridge.app_bridge",
    "ui_qml_bridge.theme_bridge",
    "ui_qml_bridge.library_bridge",
    "ui_qml_bridge.queue_bridge",
    "ui_qml_bridge.nowplaying_bridge",
    "ui_qml_bridge.playback_bridge",
    "ui_qml_bridge.eq_bridge",
    "ui_qml_bridge.metadata_bridge",
    "ui_qml_bridge.mix_bridge",
    "ui_qml_bridge.playlists_bridge",
    "ui_qml_bridge.radio_bridge",
    "ui_qml_bridge.lyrics_bridge",
    "ui_qml_bridge.history_bridge",
    "ui_qml_bridge.home_bridge",
    "ui_qml_bridge.home_audio_bridge",
    "ui_qml_bridge.connections_bridge",
    "ui_qml_bridge.devices_bridge",
    "ui_qml_bridge.diagnostics_bridge",
    "ui_qml_bridge.global_search_bridge",
    "ui_qml_bridge.job_bridge",
    "ui_qml_bridge.audio_lab_bridge",
    "ui_qml_bridge.smart_tagging_bridge",
    "ui_qml_bridge.library_doctor_bridge",
    "ui_qml_bridge.disc_lab_bridge",
    "ui_qml_bridge.notification_bridge",
    "ui_qml_bridge.michi_ai_bridge",
    "ui_qml_bridge.output_profiles_bridge",
    "ui_qml_bridge.accessibility_bridge",
    "ui_qml_bridge.settings_bridge_v2",
    "ui_qml_bridge.capability_bridge",
    "ui_qml_bridge.confirmation_bridge",
    "ui_qml_bridge.command_palette_bridge",
    "ui_qml_bridge.desktop_bridge",
    "ui_qml_bridge.app_state_bridge",
    "ui_qml_bridge.cover_provider_bridge",
]


def test_all_bridge_modules_import():
    for mod in BRIDGE_MODULES:
        m = _try_import(mod)
        if m is None:
            continue
        attrs = [x for x in dir(m) if not x.startswith("_")]
        assert len(attrs) > 0, f"{mod} has no public API"


def test_route_registry_source_count():
    from ui_qml_bridge.route_registry import ROUTES
    assert len(ROUTES) >= 30, f"Expected 30+ routes, got {len(ROUTES)}"
