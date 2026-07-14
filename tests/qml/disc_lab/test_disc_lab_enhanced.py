"""CM — Disc Lab: contractual, no físico. Device detection, disc state, tracks, extraction, cancel."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.isolation


class TestDiscLab:
    @pytest.fixture
    def mock_service(self):
        svc = MagicMock()
        svc.detect_drives.return_value = ["/dev/sr0"]
        svc.get_default_drive.return_value = "/dev/sr0"
        svc.detect_audio_cd.return_value = True
        svc.get_disc_toc.return_value = {"tracks": 5}
        svc.get_track_durations.return_value = [180.0, 200.0, 190.0, 210.0, 175.0]
        return svc

    @pytest.fixture
    def bridge(self, mock_service):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        return DiscLabBridge(disc_detection_service=mock_service)

    def test_initial_state(self, bridge):
        assert bridge.status == "unavailable"
        assert bridge.tracks == []
        assert bridge.drives == []
        assert bridge.extractionProgress == 0.0

    def test_refresh_detects_drives(self, bridge, mock_service):
        result = bridge.refresh()
        assert result["ok"] is True
        assert len(bridge.drives) >= 1

    def test_refresh_no_service(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        bridge = DiscLabBridge()
        result = bridge.refresh()
        assert result["ok"] is False

    def test_scan_disc(self, bridge, mock_service):
        bridge.refresh()
        result = bridge.scanDisc()
        assert result["ok"] is True
        assert result["tracks"] == 5

    def test_scan_disc_no_disc(self, bridge):
        bridge._status = "no_disc"
        result = bridge.scanDisc()
        assert result["ok"] is False

    def test_set_format_valid(self, bridge):
        result = bridge.setFormat("flac")
        assert result["ok"] is True
        assert bridge.extractionFormat == "flac"

    def test_set_format_invalid(self, bridge):
        result = bridge.setFormat("avi")
        assert result["ok"] is False

    def test_set_destination(self, bridge):
        result = bridge.setDestination("/music")
        assert result["ok"] is True

    def test_set_destination_empty(self, bridge):
        result = bridge.setDestination("")
        assert result["ok"] is False

    def test_start_extraction_not_scanned(self, bridge):
        result = bridge.startExtraction()
        assert result["ok"] is False

    def test_cancel_extraction(self, bridge):
        result = bridge.cancelExtraction()
        assert result["ok"] is True
        assert bridge.status == "cancelled"

    def test_eject(self, bridge):
        bridge._tracks = [{"track": 1, "title": "Track 1"}]
        bridge._status = "scanned"
        result = bridge.eject()
        assert result["ok"] is True
        assert bridge.status == "no_disc"
        assert bridge.tracks == []

    def test_dependencies_ok(self, bridge):
        assert isinstance(bridge.dependenciesOk, bool)

    def test_drive_info(self, bridge):
        bridge.refresh()
        assert bridge.driveInfo == "/dev/sr0" or bridge.driveInfo != ""

    def test_extraction_format_initial(self, bridge):
        assert bridge.extractionFormat == "flac"
