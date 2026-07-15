"""MV: Specialized workflow harness.

Same pattern as domain harness but for specialized domains.
Provides fixtures and helper methods for workflow tests.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QCoreApplication


@pytest.fixture
def qapp():
    return QCoreApplication.instance() or QCoreApplication()


@pytest.fixture
def mock_bridge():
    bridge = MagicMock()
    bridge.capabilities = {}
    bridge.has = MagicMock(return_value=True)
    return bridge


@pytest.fixture
def mock_notification_bridge():
    notif = MagicMock()
    notif.showMessage = MagicMock(return_value=None)
    notif.dismiss = MagicMock(return_value=None)
    notif.clear = MagicMock(return_value=None)
    return notif


@pytest.fixture
def mock_navigation_bridge():
    nav = MagicMock()
    nav.navigate = MagicMock(return_value=None)
    nav.navigateWithParams = MagicMock(return_value=None)
    return nav


class SpecializedWorkflowBase:
    """Base class for specialized workflow tests.

    Provides common assertion helpers.
    """

    def assert_ok(self, result: dict, msg: str = "Expected ok=True") -> None:
        assert isinstance(result, dict), msg
        assert result.get("ok") is True, f"{msg}: {result}"

    def assert_error(self, result: dict, code: str | None = None,
                     msg: str = "Expected error") -> None:
        assert isinstance(result, dict), msg
        assert result.get("ok") is False, f"{msg}: {result}"
        if code:
            assert result.get("error") == code, f"Expected error {code}: {result}"

    def assert_state_transition(self, old_state: str, new_state: str,
                                valid_transitions: dict) -> None:
        assert new_state in valid_transitions.get(old_state, []), (
            f"Invalid transition: {old_state} -> {new_state}"
        )

    def simulate_progress(self, bridge, current: int, total: int) -> None:
        if hasattr(bridge, "generationProgress"):
            bridge.generationProgress.emit(current, total)

    def simulate_cancellation(self, bridge) -> None:
        if hasattr(bridge, "cancelTransfer"):
            bridge.cancelTransfer.return_value = {"ok": True}
        elif hasattr(bridge, "cancelGeneration"):
            bridge.cancelGeneration.return_value = {"ok": True}
        elif hasattr(bridge, "cancel"):
            bridge.cancel.return_value = {"ok": True}


class SpecializedDomainFixtures:
    """Fixtures for each specialized domain."""

    @staticmethod
    @pytest.fixture
    def devices_fixtures():
        bridge = MagicMock()
        bridge.serverActive = True
        bridge.serverPort = 53318
        bridge.peers = [
            {"alias": "Phone", "device": "android", "ip": "192.168.1.50"},
        ]
        bridge.pairedDevices = [
            {"alias": "My Phone", "device": "android"},
        ]
        bridge.refresh = MagicMock(return_value={"ok": True})
        bridge.startServer = MagicMock(return_value={"ok": True})
        bridge.stopServer = MagicMock(return_value={"ok": True})
        bridge.startTransfer = MagicMock(return_value={"ok": True})
        bridge.cancelTransfer = MagicMock(return_value={"ok": True})
        bridge.validateAudioFile = MagicMock(return_value={"ok": True})
        return bridge

    @staticmethod
    @pytest.fixture
    def audio_lab_fixtures():
        bridge = MagicMock()
        bridge.modules = [
            {"id": "diagnostics", "title": "Diagnóstico", "status": "available"},
        ]
        bridge.refresh = MagicMock(return_value={"ok": True})
        bridge.backendInfo = {"available": True, "backend": "gstreamer"}
        return bridge

    @staticmethod
    @pytest.fixture
    def mix_fixtures():
        bridge = MagicMock()
        bridge.categories = [
            {"id": "favorites", "title": "Favoritos", "desc": "Tus canciones favoritas"},
        ]
        bridge.currentSongs = []
        bridge.currentMixTitle = ""
        bridge.loadMix = MagicMock(return_value={"ok": True})
        bridge.cancelGeneration = MagicMock(return_value={"ok": True})
        return bridge

    @staticmethod
    @pytest.fixture
    def connections_fixtures():
        bridge = MagicMock()
        bridge.microServerState = "not_configured"
        bridge.discoveredServers = []
        bridge.externalServers = []
        bridge.refresh = MagicMock(return_value={"ok": True})
        bridge.scanForServers = MagicMock(return_value={"ok": True})
        bridge.requestPair = MagicMock(return_value={"ok": True})
        bridge.forgetServer = MagicMock(return_value={"ok": True})
        return bridge

    @staticmethod
    @pytest.fixture
    def home_audio_fixtures():
        bridge = MagicMock()
        bridge.homeAssistantState = "not_configured"
        bridge.snapcastState = "unavailable"
        bridge.zones = []
        bridge.devices = []
        bridge.groups = []
        bridge.refresh = MagicMock(return_value={"ok": True})
        bridge.configureHomeAssistant = MagicMock(return_value={"ok": True})
        bridge.groupZones = MagicMock(return_value={"ok": True})
        bridge.ungroupZones = MagicMock(return_value={"ok": True})
        return bridge

    @staticmethod
    @pytest.fixture
    def notifications_fixtures():
        bridge = MagicMock()
        bridge.currentNotification = None
        bridge.queueLength = 0
        bridge.persistentNotifications = []
        bridge.showMessage = MagicMock(return_value=None)
        bridge.dismiss = MagicMock(return_value=None)
        bridge.clear = MagicMock(return_value=None)
        return bridge

    @staticmethod
    @pytest.fixture
    def radio_fixtures():
        bridge = MagicMock()
        bridge.stations = []
        bridge.favorites = []
        bridge.history = []
        bridge.refresh = MagicMock(return_value={"ok": True})
        bridge.playStation = MagicMock(return_value={"ok": True})
        bridge.stopStream = MagicMock(return_value={"ok": True})
        bridge.addStation = MagicMock(return_value={"ok": True})
        bridge.deleteStation = MagicMock(return_value={"ok": True})
        return bridge

    @staticmethod
    @pytest.fixture
    def global_search_fixtures():
        bridge = MagicMock()
        bridge.query = ""
        bridge.results = []
        bridge.isSearching = False
        bridge.errorCode = ""
        bridge.errorMessage = ""
        bridge.search = MagicMock(return_value={"ok": True, "count": 0})
        bridge.cancel = MagicMock(return_value={"ok": True})
        return bridge
