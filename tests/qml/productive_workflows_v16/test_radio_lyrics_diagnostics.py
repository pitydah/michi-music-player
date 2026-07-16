"""Workflow: Radio, Lyrics, Diagnostics functions."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_dimension("service_wiring"),
]


class TestRadioFunctions:
    pytestmark = [pytest.mark.qml_module("radio")]

    def test_radio_play_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("radio.play")
        assert a is not None and a.handler is not None

    def test_radio_stop_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("radio.stop")
        assert a is not None and a.handler is not None

    def test_radio_service_exists(self, bootstrap):
        svc = bootstrap.container.get("radio_service")
        assert svc is not None
        assert hasattr(svc, 'play_station')
        assert hasattr(svc, 'stop')

    def test_radio_bridge_exists(self, bootstrap):
        bridge = bootstrap._bridges.get("radio")
        assert bridge is not None


class TestLyricsFunctions:
    pytestmark = [pytest.mark.qml_module("lyrics")]

    def test_lyrics_service_exists(self, bootstrap):
        svc = bootstrap.container.get("lyrics_service")
        assert svc is not None
        assert type(svc).__name__ != "object"
        assert hasattr(svc, 'get_lyrics')
        assert hasattr(svc, 'save_lyrics')

    def test_lyrics_bridge_exists(self, bootstrap):
        bridge = bootstrap._bridges.get("lyrics")
        assert bridge is not None


class TestDiagnosticsFunctions:
    pytestmark = [pytest.mark.qml_module("diagnostics")]

    def test_diagnostics_open_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("diagnostics.open")
        assert a is not None and a.handler is not None

    def test_diagnostics_service_exists(self, bootstrap):
        svc = bootstrap.container.get("diagnostics_service")
        assert svc is not None
        assert type(svc).__name__ != "object"
        assert hasattr(svc, 'check_all')
        assert hasattr(svc, 'check_database')
        assert hasattr(svc, 'check_library')

    def test_diagnostics_bridge_exists(self, bootstrap):
        bridge = bootstrap._bridges.get("diagnostics")
        assert bridge is not None
