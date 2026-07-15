<<<<<<< Updated upstream
"""Test transfer: select → plan → start → progress → cancel."""
=======
<<<<<<< HEAD
"""Test device transfer with cancel."""
from __future__ import annotations

=======
"""Test transfer: select → plan → start → progress → cancel."""
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
from pathlib import Path
from unittest.mock import MagicMock

import pytest

<<<<<<< Updated upstream
from core.device_sync_service import (
    DeviceSyncService,
    SyncDirection,
    TransferStatus,
)
from ui_qml_bridge.devices_bridge import DevicesBridge


=======
<<<<<<< HEAD
from core.device_sync_service import DeviceSyncService, SyncDirection, TransferStatus
from ui_qml_bridge.devices_bridge import DevicesBridge

=======
from core.device_sync_service import (
    DeviceSyncService,
    SyncDirection,
    TransferStatus,
)
from ui_qml_bridge.devices_bridge import DevicesBridge


>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
pytestmark = pytest.mark.isolation


@pytest.fixture
def temp_music(tmp_path):
    music = tmp_path / "Music"
    music.mkdir()
    (music / "track.flac").write_bytes(b"fLaC" + b"\x00" * 2000)
    (music / "track.mp3").write_bytes(b"\xff\xfb" + b"\x00" * 2000)
    (music / "track.ogg").write_bytes(b"OggS" + b"\x00" * 2000)
<<<<<<< Updated upstream
    (music / "track.wav").write_bytes(b"RIFF" + b"\x00" * 2000)
    (music / "video.mp4").write_bytes(b"\x00" * 200)
    sub = music / "sub"
    sub.mkdir()
    (sub / "deep.flac").write_bytes(b"fLaC" + b"\x00" * 2000)
=======
<<<<<<< HEAD
    (music / "video.mp4").write_bytes(b"\x00" * 200)
=======
    (music / "track.wav").write_bytes(b"RIFF" + b"\x00" * 2000)
    (music / "video.mp4").write_bytes(b"\x00" * 200)
    sub = music / "sub"
    sub.mkdir()
    (sub / "deep.flac").write_bytes(b"fLaC" + b"\x00" * 2000)
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
    return tmp_path


@pytest.fixture
<<<<<<< Updated upstream
def dev_svc():
=======
<<<<<<< HEAD
def svc():
=======
def dev_svc():
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
    return DeviceSyncService()


@pytest.fixture
<<<<<<< Updated upstream
def mock_sync_mgr():
=======
<<<<<<< HEAD
def bridge(svc):
>>>>>>> Stashed changes
    mgr = MagicMock()
    mgr.start.return_value = True
    mgr.stop.return_value = True
    mgr.get_all_peers.return_value = []
    mgr.get_paired_devices.return_value = []
    mgr.is_active = MagicMock(return_value=False)
    return mgr


@pytest.fixture
def bridge(dev_svc, mock_sync_mgr):
    return DevicesBridge(
        sync_manager=mock_sync_mgr,
        device_sync_service=dev_svc,
    )


class TestTransferFlow:
    """Test the complete transfer flow: select → plan → start → progress → cancel."""

    def test_create_transfer_job(self, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "planned.flac")
        job = dev_svc.create_transfer_job(src, dst, SyncDirection.TO_DEVICE)
        assert job.job_id.startswith("sync_")
        assert job.source_path == src
        assert job.total_bytes > 0
        assert job.status == TransferStatus.QUEUED

    def test_start_transfer_audio(self, bridge, temp_music):
        src = str(temp_music / "Music" / "track.flac")
<<<<<<< Updated upstream
        dst = str(temp_music / "dest.flac")
=======
        dst = str(temp_music / "out.flac")
=======
def mock_sync_mgr():
    mgr = MagicMock()
    mgr.start.return_value = True
    mgr.stop.return_value = True
    mgr.get_all_peers.return_value = []
    mgr.get_paired_devices.return_value = []
    mgr.is_active = MagicMock(return_value=False)
    return mgr


@pytest.fixture
def bridge(dev_svc, mock_sync_mgr):
    return DevicesBridge(
        sync_manager=mock_sync_mgr,
        device_sync_service=dev_svc,
    )


class TestTransferFlow:
    """Test the complete transfer flow: select → plan → start → progress → cancel."""

    def test_create_transfer_job(self, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "planned.flac")
        job = dev_svc.create_transfer_job(src, dst, SyncDirection.TO_DEVICE)
        assert job.job_id.startswith("sync_")
        assert job.source_path == src
        assert job.total_bytes > 0
        assert job.status == TransferStatus.QUEUED

    def test_start_transfer_audio(self, bridge, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "dest.flac")
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        result = bridge.startTransfer(src, dst)
        assert result["ok"] is True
        assert Path(dst).exists()

<<<<<<< Updated upstream
    def test_start_transfer_non_audio_rejected(self, bridge, temp_music):
        src = str(temp_music / "Music" / "video.mp4")
        dst = str(temp_music / "dest.mp4")
        result = bridge.startTransfer(src, dst)
        assert result["ok"] is False

    def test_transfer_progress_tracking(self, dev_svc, temp_music):
=======
<<<<<<< HEAD
    def test_transfer_updates_jobs(self, bridge, temp_music):
>>>>>>> Stashed changes
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "progress.flac")
        job = dev_svc.create_transfer_job(src, dst)
        progress_values = []

        def track(j):
            progress_values.append(j.transferred_bytes)

        dev_svc.set_on_progress(track)
        dev_svc.execute_job(job.job_id)
        assert len(progress_values) > 0
        assert progress_values[-1] == job.total_bytes

    def test_cancel_transfer(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "cancel.flac")
        job = dev_svc.create_transfer_job(src, dst, SyncDirection.TO_DEVICE)
        result = bridge.cancelTransfer(job.job_id)
        assert result["ok"] is True
<<<<<<< Updated upstream
        assert dev_svc.get_job(job.job_id).status == TransferStatus.CANCELLED
=======
        assert svc.get_job(job.job_id).status == TransferStatus.CANCELLED
=======
    def test_start_transfer_non_audio_rejected(self, bridge, temp_music):
        src = str(temp_music / "Music" / "video.mp4")
        dst = str(temp_music / "dest.mp4")
        result = bridge.startTransfer(src, dst)
        assert result["ok"] is False

    def test_transfer_progress_tracking(self, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "progress.flac")
        job = dev_svc.create_transfer_job(src, dst)
        progress_values = []

        def track(j):
            progress_values.append(j.transferred_bytes)

        dev_svc.set_on_progress(track)
        dev_svc.execute_job(job.job_id)
        assert len(progress_values) > 0
        assert progress_values[-1] == job.total_bytes

    def test_cancel_transfer(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "cancel.flac")
        job = dev_svc.create_transfer_job(src, dst, SyncDirection.TO_DEVICE)
        result = bridge.cancelTransfer(job.job_id)
        assert result["ok"] is True
        assert dev_svc.get_job(job.job_id).status == TransferStatus.CANCELLED
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes

    def test_cancel_nonexistent(self, bridge):
        result = bridge.cancelTransfer("nonexistent")
        assert result["ok"] is False

<<<<<<< Updated upstream
    def test_cancel_twice(self, dev_svc, temp_music):
=======
<<<<<<< HEAD
    def test_cancel_no_service(self):
        b = DevicesBridge()
        result = b.cancelTransfer("nonexistent")
        assert result["ok"] is False

    def test_cancel_twice(self, bridge, svc, temp_music):
>>>>>>> Stashed changes
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "cancel2.flac")
        job = dev_svc.create_transfer_job(src, dst)
        dev_svc.cancel_job(job.job_id)
        result = dev_svc.cancel_job(job.job_id)
        assert result["ok"] is False

    def test_retry_transfer(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "retry.flac")
        job = dev_svc.create_transfer_job(src, dst)
        dev_svc.execute_job(job.job_id)
        result = bridge.retryTransfer(job.job_id)
        assert isinstance(result, dict)

    def test_transfer_jobs_list(self, bridge, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "list.flac")
        bridge.startTransfer(src, dst)
        self._refresh_internal(bridge)

    def _refresh_internal(self, bridge):
        if bridge._dev_svc:
            jobs = bridge._dev_svc.list_jobs()
            assert len(jobs) >= 1

    def test_transfer_history(self, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "history.flac")
        job = dev_svc.create_transfer_job(src, dst)
        dev_svc.execute_job(job.job_id)
        history = dev_svc.get_history()
        assert len(history) >= 1
        assert history[0]["status"] == "completed"

    def test_clear_transfer_history(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "clear.flac")
        job = dev_svc.create_transfer_job(src, dst)
        dev_svc.execute_job(job.job_id)
        bridge.clearTransferHistory()
        assert bridge.transferHistory == []

    def test_transfer_audio_only(self, bridge, temp_music):
        src = str(temp_music / "Music" / "track.mp3")
        dst = str(temp_music / "audio_only.mp3")
        result = bridge.startTransfer(src, dst)
        assert result["ok"] is True
        assert Path(dst).exists()

    def test_transfer_verify_file(self, bridge, temp_music):
        src = str(temp_music / "Music" / "track.wav")
        dst = str(temp_music / "verify.wav")
        result = bridge.startTransfer(src, dst)
        assert result["ok"] is True
        assert Path(dst).exists()
        assert Path(dst).stat().st_size > 0

    def test_execute_job_not_found(self, dev_svc):
        result = dev_svc.execute_job("nonexistent")
        assert result["ok"] is False

    def test_start_transfer_no_service(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.startTransfer("/src/track.flac", "/dst/track.flac")
        assert result["ok"] is False
<<<<<<< Updated upstream
=======
        assert result["error"] == "VIDEO_NOT_SUPPORTED"
=======
    def test_cancel_twice(self, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "cancel2.flac")
        job = dev_svc.create_transfer_job(src, dst)
        dev_svc.cancel_job(job.job_id)
        result = dev_svc.cancel_job(job.job_id)
        assert result["ok"] is False

    def test_retry_transfer(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "retry.flac")
        job = dev_svc.create_transfer_job(src, dst)
        dev_svc.execute_job(job.job_id)
        result = bridge.retryTransfer(job.job_id)
        assert isinstance(result, dict)

    def test_transfer_jobs_list(self, bridge, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "list.flac")
        bridge.startTransfer(src, dst)
        self._refresh_internal(bridge)

    def _refresh_internal(self, bridge):
        if bridge._dev_svc:
            jobs = bridge._dev_svc.list_jobs()
            assert len(jobs) >= 1

    def test_transfer_history(self, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "history.flac")
        job = dev_svc.create_transfer_job(src, dst)
        dev_svc.execute_job(job.job_id)
        history = dev_svc.get_history()
        assert len(history) >= 1
        assert history[0]["status"] == "completed"

    def test_clear_transfer_history(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "clear.flac")
        job = dev_svc.create_transfer_job(src, dst)
        dev_svc.execute_job(job.job_id)
        bridge.clearTransferHistory()
        assert bridge.transferHistory == []

    def test_transfer_audio_only(self, bridge, temp_music):
        src = str(temp_music / "Music" / "track.mp3")
        dst = str(temp_music / "audio_only.mp3")
        result = bridge.startTransfer(src, dst)
        assert result["ok"] is True
        assert Path(dst).exists()

    def test_transfer_verify_file(self, bridge, temp_music):
        src = str(temp_music / "Music" / "track.wav")
        dst = str(temp_music / "verify.wav")
        result = bridge.startTransfer(src, dst)
        assert result["ok"] is True
        assert Path(dst).exists()
        assert Path(dst).stat().st_size > 0

    def test_execute_job_not_found(self, dev_svc):
        result = dev_svc.execute_job("nonexistent")
        assert result["ok"] is False

    def test_start_transfer_no_service(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.startTransfer("/src/track.flac", "/dst/track.flac")
        assert result["ok"] is False
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
