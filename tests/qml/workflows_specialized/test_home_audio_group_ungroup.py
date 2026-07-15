from __future__ import annotations
"""MW: Home Audio — group zones, ungroup zones."""

from unittest.mock import MagicMock

from .specialized_workflow_harness import SpecializedWorkflowBase


class TestHomeAudioGroupUngroup(SpecializedWorkflowBase):
    def test_initial_state(self, home_audio_fixtures):
        b = home_audio_fixtures
        assert b.homeAssistantState == "not_configured"

    def test_configure_home_assistant(self, home_audio_fixtures):
        b = home_audio_fixtures
        result = b.configureHomeAssistant()
        self.assert_ok(result)

    def test_group_zones(self, home_audio_fixtures):
        b = home_audio_fixtures
        result = b.groupZones(["zone1", "zone2"])
        self.assert_ok(result)

    def test_ungroup_zones(self, home_audio_fixtures):
        b = home_audio_fixtures
        result = b.ungroupZones("group_id")
        self.assert_ok(result)

    def test_full_workflow(self, home_audio_fixtures):
        b = home_audio_fixtures
        b.refresh()
        b.configureHomeAssistant()
        b.groupZones(["zone1", "zone2"])
        b.ungroupZones("group_id")
        assert b.refresh.called
        assert b.configureHomeAssistant.called
        assert b.groupZones.called
        assert b.ungroupZones.called

    def test_no_zones(self):
        b = MagicMock()
        b.zones = []
        assert len(b.zones) == 0

    def test_group_error(self, home_audio_fixtures):
        b = home_audio_fixtures
        b.groupZones = MagicMock(
            return_value={"ok": False, "error": "EMPTY_ZONES"}
        )
        result = b.groupZones([])
        self.assert_error(result, "EMPTY_ZONES")
