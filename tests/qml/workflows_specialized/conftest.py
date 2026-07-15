from __future__ import annotations
"""conftest for specialized workflow tests — provides domain fixtures."""

from unittest.mock import MagicMock

import pytest


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


@pytest.fixture
def audio_lab_fixtures():
    bridge = MagicMock()
    bridge.modules = [
        {"id": "diagnostics", "title": "Diagnóstico", "status": "available"},
    ]
    bridge.refresh = MagicMock(return_value={"ok": True})
    bridge.backendInfo = {"available": True, "backend": "gstreamer"}
    return bridge


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
