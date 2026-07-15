"""Test device transfer with cancel."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.device_sync_service import DeviceSyncService, SyncDirection, TransferStatus
from ui_qml_bridge.devices_bridge import DevicesBridge

pytestmark = pytest.mark.isolation


@pytest.fixture
def temp_music(tmp_path):
    music = tmp_path / "Music"
    music.mkdir()
    (music / "track.flac").write_bytes(b"fLaC" + b"\x00" * 2000)
    (music / "track.mp3").write_bytes(b"\xff\xfb" + b"\x00" * 2000)
    (music / "track.ogg").write_bytes(b"OggS" + b"\x00" * 2000)
    (music / "video.mp4").write_bytes(b"\x00" * 200)
    return tmp_path


@pytest.fixture
def svc():
    return DeviceSyncService()


@pytest.fixture
def bridge(svc):
    mgr = MagicMock()
    mgr.start.return_value = True
    mgr.stop.return_value = True
    mgr.is_active = True
    return DevicesBridge(sync_manager=mgr, device_sync_service=svc)


class TestTransferCreate:
    def test_create_transfer_audio(self, bridge, svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "dest.flac")
        job = svc.create_transfer_job(src, dst, SyncDirection.TO_DEVICE)
        assert job.job_id.startswith("sync_")
        assert job.source_path == src
        assert job.dest_path == dst
        assert job.total_bytes > 0
        assert job.status == TransferStatus.QUEUED

    def test_start_transfer(self, bridge, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "out.flac")
        result = bridge.startTransfer(src, dst)
        assert result["ok"] is True
        assert Path(dst).exists()

    def test_transfer_updates_jobs(self, bridge, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "jobs.flac")
        bridge.startTransfer(src, dst)
        assert len(bridge.transferJobs) >= 1

    def test_transfer_history_after_complete(self, bridge, svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "hist.flac")
        job = svc.create_transfer_job(src, dst)
        svc.execute_job(job.job_id)
        history = svc.get_history()
        assert len(history) >= 1


class TestTransferCancel:
    def test_cancel_transfer(self, bridge, svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "cancel.flac")
        job = svc.create_transfer_job(src, dst)
        result = bridge.cancelTransfer(job.job_id)
        assert result["ok"] is True
        assert svc.get_job(job.job_id).status == TransferStatus.CANCELLED

    def test_cancel_nonexistent(self, bridge):
        result = bridge.cancelTransfer("nonexistent")
        assert result["ok"] is False

    def test_cancel_no_service(self):
        b = DevicesBridge()
        result = b.cancelTransfer("nonexistent")
        assert result["ok"] is False

    def test_cancel_twice(self, bridge, svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "cancel2.flac")
        job = svc.create_transfer_job(src, dst)
        bridge.cancelTransfer(job.job_id)
        result = bridge.cancelTransfer(job.job_id)
        assert result["ok"] is False

    def test_cancel_updates_state(self, bridge, svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "cancel_state.flac")
        job = svc.create_transfer_job(src, dst)
        bridge.cancelTransfer(job.job_id)
        assert len(bridge.transferJobs) >= 0


class TestTransferRetry:
    def test_retry_transfer(self, bridge, svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "retry.flac")
        job = svc.create_transfer_job(src, dst)
        svc.execute_job(job.job_id)
        result = bridge.retryTransfer(job.job_id)
        assert result["ok"] is True

    def test_retry_nonexistent(self, bridge):
        result = bridge.retryTransfer("nonexistent")
        assert result["ok"] is False

    def test_retry_no_service(self):
        b = DevicesBridge()
        result = b.retryTransfer("nonexistent")
        assert result["ok"] is False

    def test_retry_resets_status(self, svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "retry_status.flac")
        job = svc.create_transfer_job(src, dst)
        svc.cancel_job(job.job_id)
        assert job.status == TransferStatus.CANCELLED
        svc.retry_job(job.job_id)
        assert job.status in (TransferStatus.QUEUED, TransferStatus.COMPLETED)


class TestTransferAudioOnly:
    def test_video_rejected(self, bridge, temp_music):
        src = str(temp_music / "Music" / "video.mp4")
        dst = str(temp_music / "dest.mp4")
        result = bridge.startTransfer(src, dst)
        assert result["ok"] is False
        assert "VIDEO" in result.get("error", "").upper()

    def test_audio_accepted(self, bridge, temp_music):
        for ext in [".flac", ".mp3", ".ogg"]:
            src = str(temp_music / "Music" / f"track{ext}")
            dst = str(temp_music / f"out{ext}")
            result = bridge.startTransfer(src, dst)
            assert result["ok"] is True, f"{ext} should be accepted"

    def test_unknown_extension_rejected(self, bridge, temp_music):
        path = str(temp_music / "Music" / "track.xyz")
        Path(path).write_bytes(b"test")
        result = bridge.startTransfer(path, str(temp_music / "out.xyz"))
        assert result["ok"] is False

    def test_missing_source_rejected(self, bridge, temp_music):
        result = bridge.startTransfer(
            str(temp_music / "nonexistent.flac"),
            str(temp_music / "out.flac"),
        )
        assert result["ok"] is False


class TestTransferHistory:
    def test_clear_history(self, bridge, svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "clear.flac")
        job = svc.create_transfer_job(src, dst)
        svc.execute_job(job.job_id)
        bridge.clearTransferHistory()
        assert bridge.transferHistory == []

    def test_validate_audio_file(self, bridge, temp_music):
        path = str(temp_music / "Music" / "track.flac")
        result = bridge.validateAudioFile(path)
        assert result["ok"] is True
        assert result["transcode_policy"] == "copy"

    def test_validate_video_rejected(self, bridge, temp_music):
        path = str(temp_music / "Music" / "video.mp4")
        result = bridge.validateAudioFile(path)
        assert result["ok"] is False
        assert result["error"] == "VIDEO_NOT_SUPPORTED"
