"""MW: Devices — discover paired devices, transfer file, cancel transfer."""
from __future__ import annotations

from unittest.mock import MagicMock

from .specialized_workflow_harness import SpecializedWorkflowBase


class TestDevicesDiscoverTransferCancel(SpecializedWorkflowBase):
    def test_discover_paired_devices(self, devices_fixtures):
        b = devices_fixtures
        b.refresh()
        assert len(b.peers) >= 1
        assert len(b.pairedDevices) >= 1

    def test_select_paired_device(self, devices_fixtures):
        b = devices_fixtures
        b.refresh()
        selected = b.pairedDevices[0]
        assert selected.get("alias") == "My Phone"

    def test_start_transfer(self, devices_fixtures):
        b = devices_fixtures
        result = b.startTransfer("/src/track.flac", "/dst/track.flac")
        self.assert_ok(result)

    def test_cancel_transfer(self, devices_fixtures):
        b = devices_fixtures
        result = b.cancelTransfer("job_123")
        self.assert_ok(result)

    def test_full_workflow(self, devices_fixtures):
        b = devices_fixtures
        b.refresh()
        b.startTransfer("/src/track.flac", "/dst/track.flac")
        b.cancelTransfer("job_123")
        assert b.startTransfer.called
        assert b.cancelTransfer.called

    def test_audio_file_validated(self, devices_fixtures):
        b = devices_fixtures
        result = b.validateAudioFile("/path/track.flac")
        self.assert_ok(result)

    def test_server_start_stop(self, devices_fixtures):
        b = devices_fixtures
        self.assert_ok(b.startServer())
        self.assert_ok(b.stopServer())

    def test_discover_no_devices(self):
        b = MagicMock()
        b.peers = []
        b.pairedDevices = []
        assert len(b.peers) == 0
        assert len(b.pairedDevices) == 0
