"""E2E: Settings rollback workflow."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("settings"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestSettingsRollbackE2E:
    def test_settings_get_value(self, bootstrap, bridges):
        ss = bridges.get("settings_v2")
        assert ss is not None
        result = ss.getValue("audio/volume")
        assert result is None or isinstance(result, (str, int))

    def test_settings_validate_key(self, bootstrap, bridges):
        ss = bridges.get("settings_v2")
        assert ss is not None
        result = ss.validate("audio/volume")
        assert isinstance(result, dict)
