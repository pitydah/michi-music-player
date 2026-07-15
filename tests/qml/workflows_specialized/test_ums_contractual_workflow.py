"""Contractual UMS workflow test: discover  select  inspect  profile  plan  transfer  progress  cancel  verify cleanup  retry  verify copied audio.

No hardware, no physical audio scoring. Audio-only respected.
"""
from pathlib import Path
from unittest.mock import MagicMock

from core.device_sync_service import (
    DeviceSyncService, DeviceIdentity, DeviceProtocol, TransferStatus,
)
from ui_qml_bridge.devices_bridge import DevicesBridge
import pytest
pytestmark = pytest.mark.isolation


@pytest.fixture
def temp_music(tmp_path):
    music = tmp_path / "Music"
    music.mkdir()
    (music / "track.flac").write_bytes(b"fLaC" + b"\x00" * 2000)
    (music / "track.mp3").write_bytes(b"\xff\xfb" + b"\x00" * 2000)
    (music / "track.ogg").write_bytes(b"OggS" + b"\x00" * 2000)
    (music / "track.wav").write_bytes(b"RIFF" + b"\x00" * 2000)
    (music / "video.mp4").write_bytes(b"\x00" * 200)
    sub = music / "sub"
    sub.mkdir()
    (sub / "deep.flac").write_bytes(b"fLaC" + b"\x00" * 2000)
    return tmp_path


@pytest.fixture
def dev_svc():
    return DeviceSyncService()


@pytest.fixture
def mock_sync_mgr():
    mgr = MagicMock()
    mgr.start.return_value = True
    mgr.stop.return_value = True
    mgr.get_all_peers.return_value = []
    mgr.is_active = MagicMock(return_value=False)
    return mgr


@pytest.fixture
def bridge(dev_svc, mock_sync_mgr):
    return DevicesBridge(
        sync_manager=mock_sync_mgr,
        device_sync_service=dev_svc,
    )


class TestUmsContractualWorkflow:
    """Discover  select  inspect  profile  plan  transfer  progress  cancel  verify cleanup  retry  verify copied audio."""

    def test_workflow_discover(self, dev_svc, tmp_path):
        music = tmp_path / "Music"
        music.mkdir()
        (music / "song.flac").write_bytes(b"fLaC" + b"\x00" * 100)
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="SanDisk", model="Clip", serial="ums001",
            mount_point=str(tmp_path),
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        dev_svc._discovered[key] = identity
        discovered = dev_svc.get_discovered()
        assert len(discovered) >= 1
        assert discovered[0].vendor == "SanDisk"

    def test_workflow_select_device(self, dev_svc, tmp_path):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="SanDisk", model="Clip", serial="ums002",
            mount_point=str(tmp_path),
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        dev_svc._discovered[key] = identity
        result = dev_svc.pair(identity)
        assert result["ok"] is True
        assert dev_svc.is_paired(key)

    def test_workflow_inspect_storage(self, dev_svc, temp_music):
        info = dev_svc.get_storage(str(temp_music))
        assert info.total_bytes > 0
        assert info.free_bytes > 0

    def test_workflow_profile_device(self, dev_svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="SanDisk", model="Clip", serial="ums003",
            mount_point="/media/sandisk",
        )
        caps = dev_svc.resolve_capabilities(identity)
        assert caps.supports_pairing is False
        assert caps.supports_playlists is False
        assert ".flac" in caps.supported_formats

    def test_workflow_plan_transfer(self, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "planned.flac")
        job = dev_svc.create_transfer_job(src, dst)
        assert job.job_id.startswith("sync_")
        assert job.total_bytes > 0
        assert job.status == TransferStatus.QUEUED

    def test_workflow_transfer(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "transferred.flac")
        result = bridge.startTransfer(src, dst)
        assert result["ok"] is True
        assert Path(dst).exists()
        assert Path(dst).stat().st_size > 0

    def test_workflow_transfer_progress(self, dev_svc, temp_music):
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

    def test_workflow_cancel_transfer(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "cancelled.flac")
        job = dev_svc.create_transfer_job(src, dst)
        result = bridge.cancelTransfer(job.job_id)
        assert result["ok"] is True
        assert dev_svc.get_job(job.job_id).status == TransferStatus.CANCELLED

    def test_workflow_cleanup_after_cancel(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "cleanup.flac")
        job = dev_svc.create_transfer_job(src, dst)
        dev_svc.execute_job(job.job_id)
        bridge.clearTransferHistory()
        assert bridge.transferHistory == []
        job_status = dev_svc.get_job(job.job_id)
        assert job_status is not None

    def test_workflow_retry_after_cancel(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "retry.flac")
        job = dev_svc.create_transfer_job(src, dst)
        dev_svc.cancel_job(job.job_id)
        result = bridge.retryTransfer(job.job_id)
        assert result["ok"] is True
        assert Path(dst).exists()

    def test_workflow_verify_copied_audio(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.wav")
        dst = str(temp_music / "verified.wav")
        result = bridge.startTransfer(src, dst)
        assert result["ok"] is True
        assert Path(dst).exists()
        assert Path(dst).stat().st_size > 0
        original_size = Path(src).stat().st_size
        copied_size = Path(dst).stat().st_size
        assert copied_size == original_size

    def test_workflow_video_rejected(self, bridge, temp_music):
        src = str(temp_music / "Music" / "video.mp4")
        dst = str(temp_music / "video_out.mp4")
        result = bridge.startTransfer(src, dst)
        assert result["ok"] is False
        assert result["error"] == "VIDEO_NOT_SUPPORTED"
        assert not Path(dst).exists()

    def test_workflow_history_after_transfer(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.ogg")
        dst = str(temp_music / "history.ogg")
        bridge.startTransfer(src, dst)
        history = dev_svc.get_history()
        assert len(history) >= 1

    def test_workflow_clear_history(self, bridge, dev_svc):
        bridge.clearTransferHistory()
        assert dev_svc.get_history() == []
        assert bridge.transferHistory == []
