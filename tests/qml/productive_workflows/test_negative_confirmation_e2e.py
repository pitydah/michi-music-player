"""E2E: Rejected confirmation (destructive action)."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("core"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestNegativeConfirmationE2E:
    def test_confirm_destructive_valid_action(self, bootstrap, bridges):
        dv = bridges.get("devices")
        assert dv is not None
        result = dv.confirmDestructive("unpair")
        assert isinstance(result, dict)
        assert result.get("ok") is True

    def test_confirm_destructive_invalid_action(self, bootstrap, bridges):
        dv = bridges.get("devices")
        assert dv is not None
        result = dv.confirmDestructive("nonexistent_action")
        assert result.get("ok") is False
        assert result.get("error") == "UNKNOWN_ACTION"
