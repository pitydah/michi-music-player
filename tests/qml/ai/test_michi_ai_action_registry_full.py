from __future__ import annotations

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge

pytestmark = [pytest.mark.qml_module("michi_ai")]


def test_play_fails_without_engine():
    bridge = MichiAIBridge()
    bridge.sendMessage("reproduce canción 42")
    assert bridge.status == "FAILED"


def test_queue_fails_without_engine():
    bridge = MichiAIBridge()
    bridge.sendMessage("encolar canción 7")
    assert bridge.status == "FAILED"


def test_playlist_fails_without_engine():
    bridge = MichiAIBridge()
    bridge.sendMessage("crear playlist llamada Favoritos")
    assert bridge.status == "FAILED"


def test_search_fails_without_engine():
    bridge = MichiAIBridge()
    bridge.sendMessage("buscar rock progresivo")
    assert bridge.status == "FAILED"


def test_navigate_fails_without_engine():
    bridge = MichiAIBridge()
    bridge.sendMessage("ir a biblioteca")
    assert bridge.status == "FAILED"


def test_settings_fails_without_engine():
    bridge = MichiAIBridge()
    bridge.sendMessage("abrir ajustes")
    assert bridge.status == "FAILED"


def test_metadata_fails_without_engine():
    bridge = MichiAIBridge()
    bridge.sendMessage("reproduce canción 1")
    assert bridge.status == "FAILED"


def test_doctor_fails_without_engine():
    bridge = MichiAIBridge()
    bridge.sendMessage("diagnosticar biblioteca")
    assert bridge.status == "FAILED"


def test_devices_fails_without_engine():
    bridge = MichiAIBridge()
    bridge.sendMessage("ir a conexiones")
    assert bridge.status == "FAILED"


def test_action_unavailable_on_no_service():
    bridge = MichiAIBridge()
    bridge.sendMessage("reproduce canción 42")
    assert bridge.status == "FAILED"
