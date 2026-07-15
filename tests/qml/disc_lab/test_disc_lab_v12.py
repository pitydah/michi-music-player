"""Tests for Disc Lab v12 — real disc detection, no sync operations prolonged in UI thread."""
from unittest.mock import MagicMock

import pytest


class TestDiscLabBridgeCreation:
    def test_requires_worker_manager(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        with pytest.raises(Exception):
            DiscLabBridge()

    def test_creation(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        dl = DiscLabBridge(worker_manager=MagicMock())
        assert dl is not None

    def test_status_default(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        dl = DiscLabBridge(worker_manager=MagicMock())
        assert dl.status == "unavailable"

    def test_tracks_default(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        dl = DiscLabBridge(worker_manager=MagicMock())
        assert len(dl.tracks) == 0

    def test_drives_default(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        dl = DiscLabBridge(worker_manager=MagicMock())
        assert len(dl.drives) == 0

    def test_extraction_progress_default(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        dl = DiscLabBridge(worker_manager=MagicMock())
        assert dl.extractionProgress == 0.0

    def test_dependencies_ok_default(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        dl = DiscLabBridge(worker_manager=MagicMock())
        assert isinstance(dl.dependenciesOk, bool)

    def test_drive_info_default(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        dl = DiscLabBridge(worker_manager=MagicMock())
        assert dl.driveInfo == ""

    def test_extraction_format_default(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        dl = DiscLabBridge(worker_manager=MagicMock())
        assert dl.extractionFormat == "flac"


class TestDiscLabOperations:
    def test_refresh(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        dl = DiscLabBridge(worker_manager=MagicMock())
        result = dl.refresh()
        assert isinstance(result, dict)

    def test_set_format(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        dl = DiscLabBridge(worker_manager=MagicMock())
        result = dl.setFormat("wav")
        assert result.get("ok")

    def test_set_format_invalid(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        dl = DiscLabBridge(worker_manager=MagicMock())
        result = dl.setFormat("aiff")
        assert not result.get("ok")

    def test_set_destination(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        dl = DiscLabBridge(worker_manager=MagicMock())
        result = dl.setDestination("/tmp/extract")
        assert result.get("ok")

    def test_set_destination_empty(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        dl = DiscLabBridge(worker_manager=MagicMock())
        result = dl.setDestination("")
        assert not result.get("ok")

    def test_eject(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        dl = DiscLabBridge(worker_manager=MagicMock())
        result = dl.eject()
        assert result.get("ok")

    def test_cancel_extraction(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        dl = DiscLabBridge(worker_manager=MagicMock())
        result = dl.cancelExtraction()
        assert result.get("ok")

    def test_scan_no_disc(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        dl = DiscLabBridge(worker_manager=MagicMock())
        result = dl.scanDisc()
        assert not result.get("ok")
