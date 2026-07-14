"""Test Disc Lab contractual: UNAVAILABLE without real drive, NO declared verified."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.disc_lab_bridge import DiscLabBridge


@pytest.fixture
def no_drive_bridge():
    return DiscLabBridge()


@pytest.fixture
def mock_detection_service():
    svc = MagicMock()
    svc.detect_drives.return_value = []
    svc.get_default_drive.return_value = ""
    return svc


def test_status_unavailable_without_service(no_drive_bridge):
    bridge = no_drive_bridge
    result = bridge.refresh()
    assert bridge.status == "unavailable"
    assert not result["ok"]
    assert result["error"] == "UNSUPPORTED"


def test_status_no_drive_with_service_no_drives(mock_detection_service):
    bridge = DiscLabBridge(disc_detection_service=mock_detection_service)
    result = bridge.refresh()
    assert result["ok"]
    assert bridge.status == "no_drive"
    assert len(bridge.drives) == 0


def test_scan_disc_fails_when_no_drive(mock_detection_service):
    bridge = DiscLabBridge(disc_detection_service=mock_detection_service)
    bridge.refresh()
    result = bridge.scanDisc()
    assert not result["ok"]
    assert result["error"] in ("NO_DISC", "NO_DRIVE")


def test_extraction_fails_when_not_scanned(no_drive_bridge):
    bridge = no_drive_bridge
    result = bridge.startExtraction()
    assert not result["ok"]
    assert result["error"] == "NOT_SCANNED"


def test_cancel_extraction(no_drive_bridge):
    bridge = no_drive_bridge
    bridge._status = "extracting"
    result = bridge.cancelExtraction()
    assert result["ok"]
    assert bridge.status == "cancelled"


def test_set_format_valid(mock_detection_service):
    bridge = DiscLabBridge(disc_detection_service=mock_detection_service)
    result = bridge.setFormat("flac")
    assert result["ok"]
    assert bridge.extractionFormat == "flac"


def test_set_format_invalid(mock_detection_service):
    bridge = DiscLabBridge(disc_detection_service=mock_detection_service)
    result = bridge.setFormat("aiff")
    assert not result["ok"]
    assert result["error"] == "INVALID_FORMAT"


def test_eject_clears_state(mock_detection_service):
    bridge = DiscLabBridge(disc_detection_service=mock_detection_service)
    bridge._status = "scanned"
    bridge._tracks = [{"track": 1, "title": "Track 1"}]
    bridge.eject()
    assert bridge.status == "no_disc"
    assert len(bridge.tracks) == 0
