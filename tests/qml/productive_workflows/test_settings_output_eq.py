"""Workflow: Settings → Change → Output Profile → EQ."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("settings"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestSettingsOutputEq:
    def test_settings_open_action(self, bootstrap, bridges):
        ar = bridges.get("action_registry")
        a = ar.get("settings.open")
        assert a is not None, "settings.open action exists"

    def test_output_profiles_service(self, bootstrap):
        svc = bootstrap.container.get("output_profile_service")
        assert svc is not None
        assert hasattr(svc, 'list_profiles')

    def test_eq_service_methods(self, bootstrap):
        svc = bootstrap.container.get("equalizer_service")
        assert svc is not None
        assert hasattr(svc, 'set_bands')
        assert hasattr(svc, 'set_enabled')
        assert hasattr(svc, 'save_preset')
        assert hasattr(svc, 'load_preset')
