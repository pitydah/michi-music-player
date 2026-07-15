"""Disc Lab completo: disc discovery, track list, metadata, cover, rip plan, format, quality, destination, job, progress, cancel, retry, result."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.disc_lab_bridge import DiscLabBridge


@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.detect_drives.return_value = ["/dev/sr0"]
    svc.get_default_drive.return_value = "/dev/sr0"
    svc.detect_audio_cd.return_value = True
    svc.get_disc_toc.return_value = {"tracks": 5}
    svc.get_track_durations.return_value = [180.0, 200.0, 190.0, 210.0, 175.0]
    return svc


@pytest.fixture
def mock_wm():
    wm = MagicMock()
    wm.run_task.return_value = None
    wm.cancel_task.return_value = None
    return wm


@pytest.fixture
def bridge(mock_service, mock_wm):
    return DiscLabBridge(
        disc_detection_service=mock_service,
        worker_manager=mock_wm,
    )


@pytest.fixture
def no_svc_bridge():
    return DiscLabBridge()


def test_initial_state(no_svc_bridge):
    assert no_svc_bridge.status == "unavailable"
    assert no_svc_bridge.tracks == []
    assert no_svc_bridge.drives == []
    assert no_svc_bridge.extractionProgress == 0.0
    assert no_svc_bridge.extractionFormat == "flac"
    assert no_svc_bridge.driveInfo == ""


def test_disc_discovery_with_drive(bridge, mock_service):
    result = bridge.refresh()
    assert result["ok"] is True
    assert result["drives"] >= 1
    assert bridge.status == "ready"
    assert bridge.driveInfo == "/dev/sr0"
    assert len(bridge.drives) == 1
    assert bridge.drives[0]["device"] == "/dev/sr0"


def test_disc_discovery_no_drive(mock_service):
    mock_service.detect_drives.return_value = []
    b = DiscLabBridge(disc_detection_service=mock_service)
    result = b.refresh()
    assert result["ok"] is True
    assert b.status == "no_drive"
    assert len(b.drives) == 0


def test_disc_discovery_unavailable(no_svc_bridge):
    result = no_svc_bridge.refresh()
    assert result["ok"] is False
    assert result["error"] == "UNSUPPORTED"
    assert no_svc_bridge.status == "unavailable"


def test_track_list_after_scan(bridge, mock_service):
    bridge.refresh()
    result = bridge.scanDisc()
    assert result["ok"] is True
    assert result["tracks"] == 5
    assert bridge.status == "scanned"
    assert len(bridge.tracks) == 5
    for i, t in enumerate(bridge.tracks):
        assert t["track"] == i + 1
        assert t["duration"] > 0
        assert t["selected"] is True


def test_scan_disc_no_disc(bridge):
    bridge._status = "no_disc"
    result = bridge.scanDisc()
    assert result["ok"] is False
    assert result["error"] == "NO_DISC"


def test_scan_disc_no_drive(no_svc_bridge):
    result = no_svc_bridge.scanDisc()
    assert result["ok"] is False


def test_extraction_format_valid(bridge):
    for fmt in ("flac", "wav", "mp3", "ogg"):
        result = bridge.setFormat(fmt)
        assert result["ok"] is True
        assert bridge.extractionFormat == fmt


def test_extraction_format_invalid(bridge):
    result = bridge.setFormat("aiff")
    assert result["ok"] is False
    assert result["error"] == "INVALID_FORMAT"
    assert bridge.extractionFormat == "flac"


def test_extraction_destination(bridge):
    result = bridge.setDestination("/music/rips")
    assert result["ok"] is True


def test_extraction_destination_empty(bridge):
    result = bridge.setDestination("")
    assert result["ok"] is False
    assert result["error"] == "EMPTY_PATH"


def test_start_extraction_requires_scanned(bridge):
    result = bridge.startExtraction()
    assert result["ok"] is False
    assert result["error"] == "NOT_SCANNED"


def test_start_extraction_requires_destination(bridge, mock_service):
    bridge.refresh()
    bridge.scanDisc()
    result = bridge.startExtraction()
    assert result["ok"] is False
    assert result["error"] == "NO_DESTINATION"


def test_start_extraction_async_ok(bridge, mock_service, mock_wm):
    bridge.refresh()
    bridge.scanDisc()
    bridge.setDestination("/music/rips")
    result = bridge.startExtraction()
    assert result["ok"] is True
    assert result["async"] is True
    assert bridge.status == "extracting"
    mock_wm.run_task.assert_called_once()


def test_extraction_progress_tracking(bridge, mock_service, mock_wm):
    bridge.refresh()
    bridge.scanDisc()
    bridge.setDestination("/music/rips")
    bridge.startExtraction()
    assert bridge.extractionProgress == 0.0
    call_kwargs = mock_wm.run_task.call_args[1]
    on_progress = call_kwargs.get("on_progress")
    if on_progress:
        on_progress(0.5, "Mitad")
    assert bridge.extractionProgress == 0.5


def test_cancel_extraction(bridge, mock_wm):
    bridge._status = "extracting"
    result = bridge.cancelExtraction()
    assert result["ok"] is True
    assert bridge.status == "cancelled"
    assert bridge.extractionProgress == 0.0
    mock_wm.cancel_task.assert_called_once_with("disc_lab_extract")


def test_cancel_extraction_no_wm(no_svc_bridge):
    no_svc_bridge._status = "extracting"
    result = no_svc_bridge.cancelExtraction()
    assert result["ok"] is True


def test_eject_clears_tracks_and_state(bridge):
    bridge._status = "scanned"
    bridge._tracks = [{"track": 1, "title": "Track 1"}]
    bridge._extraction_progress = 0.5
    result = bridge.eject()
    assert result["ok"] is True
    assert bridge.status == "no_disc"
    assert bridge.tracks == []
    assert bridge.extractionProgress == 0.0


def test_dependencies_check(bridge):
    assert isinstance(bridge.dependenciesOk, bool)


def test_retry_after_error(bridge, mock_service, mock_wm):
    bridge.refresh()
    bridge.scanDisc()
    bridge.setDestination("/music/rips")
    bridge.startExtraction()
    bridge._extraction_gen += 1
    bridge._status = "scanned"
    result = bridge.startExtraction()
    assert result["ok"] is True


def test_extraction_cancelled_during_run(bridge, mock_service, mock_wm):
    bridge.refresh()
    bridge.scanDisc()
    bridge.setDestination("/music/rips")
    bridge.startExtraction()
    call_kwargs = mock_wm.run_task.call_args[1]
    on_cancelled = call_kwargs.get("on_cancelled")
    if on_cancelled:
        on_cancelled()
    assert bridge.status == "cancelled"


def test_extraction_error_during_run(bridge, mock_service, mock_wm):
    bridge.refresh()
    bridge.scanDisc()
    bridge.setDestination("/music/rips")
    bridge.startExtraction()
    call_kwargs = mock_wm.run_task.call_args[1]
    on_error = call_kwargs.get("on_error")
    if on_error:
        on_error("EXTRACT_FAILED", "Disk read error")
    assert bridge.status == "error"


def test_extraction_done_callback(bridge, mock_service, mock_wm):
    bridge.refresh()
    bridge.scanDisc()
    bridge.setDestination("/music/rips")
    bridge.startExtraction()
    call_kwargs = mock_wm.run_task.call_args[1]
    on_done = call_kwargs.get("on_done")
    if on_done:
        on_done({"tracks": [{"track": 1, "ok": True, "path": "/out/track01.flac"}]})
    assert bridge.status == "done"
    assert bridge.extractionProgress == 1.0


def test_generation_guard_prevents_stale_callbacks(bridge, mock_service, mock_wm):
    bridge.refresh()
    bridge.scanDisc()
    bridge.setDestination("/music/rips")
    bridge.startExtraction()
    gen = bridge._extraction_gen
    call_kwargs = mock_wm.run_task.call_args[1]
    on_done = call_kwargs.get("on_done")
    bridge._extraction_gen += 1
    if on_done:
        on_done({"tracks": []})
    assert bridge.status == "extracting"
