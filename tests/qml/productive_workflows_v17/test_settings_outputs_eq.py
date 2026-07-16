"""Workflow: Settings, Outputs, EQ functions."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_dimension("service_wiring"),
    pytest.mark.qml_dimension("primary_interaction"),
]


class TestSettingsFunctions:
    pytestmark = [pytest.mark.qml_module("settings")]

    def test_settings_open_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("settings.open")
        assert a is not None and a.handler is not None

    def test_settings_service_exists(self, bootstrap):
        svc = bootstrap.container.get("settings_service")
        assert svc is not None
        assert hasattr(svc, 'categories')
        assert hasattr(svc, 'get')
        assert hasattr(svc, 'set_')
        assert hasattr(svc, 'open')

    def test_settings_bridge_exists(self, bootstrap):
        bridge = bootstrap._bridges.get("settings")
        assert bridge is not None


class TestOutputFunctions:
    pytestmark = [pytest.mark.qml_module("outputs")]

    def test_output_profiles_bridge_exists(self, bootstrap):
        bridge = bootstrap._bridges.get("output_profiles")
        assert bridge is not None

    def test_output_profile_service_exists(self, bootstrap):
        svc = bootstrap.container.get("output_profile_service")
        assert svc is not None
        assert type(svc).__name__ != "object"
        assert hasattr(svc, 'list_profiles')


class TestEqFunctions:
    pytestmark = [pytest.mark.qml_module("equalizer")]

    def test_eq_service_exists(self, bootstrap):
        svc = bootstrap.container.get("equalizer_service")
        assert svc is not None
        assert type(svc).__name__ != "object"
        assert hasattr(svc, 'set_bands')
        assert hasattr(svc, 'set_preamp')
        assert hasattr(svc, 'set_enabled')
        assert hasattr(svc, 'save_preset')
        assert hasattr(svc, 'load_preset')

    def test_eq_bridge_exists(self, bootstrap):
        bridge = bootstrap._bridges.get("eq")
        assert bridge is not None
