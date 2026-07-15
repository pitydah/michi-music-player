"""Test Devices UMS workflow through DevicesBridge and DeviceSyncService.

Contractual UMS workflow: discover  identify  profile  calculate storage 
plan  transfer  cancel  cleanup  retry  verify files.
Audio-only: validate extensions and MIME. No video.
Strategy for unsupported codec: skip, warn, transcode audio optional.
"""
from pathlib import Path
from unittest.mock import MagicMock

from core.device_sync_service import (
    DeviceSyncService, DeviceIdentity, DeviceProtocol, TransferStatus,
)
from core.job_service import JobService
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
    (music / "video.avi").write_bytes(b"\x00" * 200)
    (music / "document.txt").write_text("not audio")
    sub = music / "sub"
    sub.mkdir()
    (sub / "deep.flac").write_bytes(b"fLaC" + b"\x00" * 2000)
    return tmp_path


@pytest.fixture
def dev_svc():
    return DeviceSyncService()


@pytest.fixture
def job_svc():
    return JobService()


@pytest.fixture
def mock_sync_mgr():
    mgr = MagicMock()
    mgr.start.return_value = True
    mgr.stop.return_value = True
    mgr.get_all_peers.return_value = []
    mgr.is_active = MagicMock(return_value=False)
    return mgr


@pytest.fixture
def bridge(dev_svc, job_svc, mock_sync_mgr):
    return DevicesBridge(
        sync_manager=mock_sync_mgr,
        device_sync_service=dev_svc,
        job_service=job_svc,
    )


class TestUmsWorkflow:
    """Complete UMS workflow: discover  identify  profile  storage  plan  transfer  cancel  cleanup  retry  verify."""

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

    def test_workflow_identify(self, dev_svc, tmp_path):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="SanDisk", model="Clip", serial="ums002",
            mount_point=str(tmp_path),
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        dev_svc._discovered[key] = identity
        result = dev_svc.identify(str(tmp_path))
        assert result is not None
        assert result.vendor == "SanDisk"

    def test_workflow_profile(self, dev_svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="SanDisk", model="Clip", serial="ums003",
            mount_point="/media/sandisk",
        )
        caps = dev_svc.resolve_capabilities(identity)
        assert caps.supports_pairing is False
        assert caps.supports_playlists is False

    def test_workflow_calculate_storage(self, dev_svc, temp_music):
        info = dev_svc.get_storage(str(temp_music))
        assert info.total_bytes > 0
        assert info.free_bytes > 0

    def test_workflow_plan_transfer(self, bridge, dev_svc, temp_music):
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

    def test_workflow_cancel(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "cancelled.flac")
        job = dev_svc.create_transfer_job(src, dst)
        result = bridge.cancelTransfer(job.job_id)
        assert result["ok"] is True
        assert dev_svc.get_job(job.job_id).status == TransferStatus.CANCELLED

    def test_workflow_cleanup(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "cleanup.flac")
        job = dev_svc.create_transfer_job(src, dst)
        dev_svc.execute_job(job.job_id)
        bridge.clearTransferHistory()
        assert bridge.transferHistory == []

    def test_workflow_retry(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "retried.flac")
        job = dev_svc.create_transfer_job(src, dst)
        dev_svc.execute_job(job.job_id)
        result = bridge.retryTransfer(job.job_id)
        assert result["ok"] is True

    def test_workflow_verify_files(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.wav")
        dst = str(temp_music / "verified.wav")
        result = bridge.startTransfer(src, dst)
        assert result["ok"] is True
        assert Path(dst).exists()
        assert Path(dst).stat().st_size > 0

    def test_workflow_history(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.ogg")
        dst = str(temp_music / "history.ogg")
        dev_svc.create_transfer_job(src, dst)
        dev_svc.execute_job("nonexistent")
        history = dev_svc.get_history()
        assert isinstance(history, list)


class TestAudioOnlyValidation:
    def test_valid_audio_accepted(self, bridge, temp_music):
        for ext in [".flac", ".mp3", ".ogg", ".wav"]:
            path = str(temp_music / "Music" / f"track{ext}")
            result = bridge.validateAudioFile(path)
            assert result["ok"] is True, f"{ext} should be accepted"

    def test_video_rejected(self, bridge, temp_music):
        for ext in [".mp4", ".avi", ".mkv", ".mov", ".webm", ".m4v"]:
            path = str(temp_music / f"video{ext}")
            result = bridge.validateAudioFile(path)
            assert result["ok"] is False, f"{ext} should be rejected"
            assert result["error"] == "VIDEO_NOT_SUPPORTED"

    def test_unknown_format_warned(self, bridge, temp_music):
        path = str(temp_music / "unknown.xyz")
        result = bridge.validateAudioFile(path)
        assert result["ok"] is False
        assert "UNSUPPORTED_FORMAT" in result.get("error", "")

    def test_transcode_policy_returned(self, bridge, temp_music):
        path = str(temp_music / "Music/track.flac")
        result = bridge.validateAudioFile(path)
        assert result["ok"] is True
        assert "transcode_policy" in result
        assert result["transcode_policy"] == "copy"


class TestUnsupportedCodecStrategy:
    def test_skip_unsupported(self, bridge, dev_svc, temp_music):
        path = str(temp_music / "document.txt")
        result = bridge.validateAudioFile(path)
        assert result["ok"] is False

    def test_warn_unsupported(self, bridge, dev_svc, temp_music):
        result = bridge.validateAudioFile("/nonexistent.xyz")
        assert result["ok"] is False
        assert "message" in result
