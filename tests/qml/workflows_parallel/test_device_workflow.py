"""Full device workflow: discover  select  inspect  profile  plan  start  cancel.

Tests the complete lifecycle through DevicesBridge and DeviceSyncService.
Audio-only: validates that video files are rejected.
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.device_sync_service import (
    DeviceSyncService,
    DeviceIdentity,
    DeviceProtocol,
    SyncDirection,
    TransferStatus,
)
from core.job_service import JobService
from ui_qml_bridge.devices_bridge import DevicesBridge


pytestmark = pytest.mark.isolation


@pytest.fixture
def temp_music(tmp_path):
    music = tmp_path / "Music"
    music.mkdir()
    (music / "track.flac").write_bytes(b"fLaC" + b"\x00" * 2000)
    (music / "track.mp3").write_bytes(b"\xff\xfb" + b"\x00" * 2000)
    (music / "track.ogg").write_bytes(b"OggS" + b"\x00" * 2000)
    (music / "track.wav").write_bytes(b"RIFF" + b"\x00" * 2000)
    (music / "track.m4a").write_bytes(b"\x00" * 2000)
    (music / "video.mp4").write_bytes(b"\x00" * 200)
    (music / "video.avi").write_bytes(b"\x00" * 200)
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
    mgr.get_all_peers.return_value = [
        {"alias": "Android Phone", "device": "android", "ip": "192.168.1.50", "port": 53318},
        {"alias": "Tablet", "device": "android", "ip": "192.168.1.51", "port": 53318},
    ]
    mgr.get_paired_devices.return_value = [
        {"alias": "My Phone", "device": "android"},
    ]
    mgr.is_active = MagicMock(return_value=True)
    return mgr


@pytest.fixture
def bridge(dev_svc, job_svc, mock_sync_mgr):
    return DevicesBridge(
        sync_manager=mock_sync_mgr,
        device_sync_service=dev_svc,
        job_service=job_svc,
    )


class TestDeviceWorkflow:
    """Full device workflow: discover  select  inspect  profile  plan  start  cancel."""

    def test_step1_discover(self, bridge, dev_svc, temp_music):
        """Discover devices from sync manager."""
        bridge.refresh()
        assert len(bridge.pairedDevices) >= 1
        assert len(bridge.peers) >= 2

    def test_step2_select_device(self, bridge, dev_svc, temp_music):
        """Select a paired device."""
        bridge.refresh()
        selected = bridge.pairedDevices[0] if bridge.pairedDevices else {}
        assert selected.get("alias") == "My Phone"

    def test_step3_inspect_device(self, bridge, dev_svc, temp_music):
        """Inspect device detail."""
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="SanDisk", model="Clip", serial="wf_inspect",
            mount_point=str(temp_music),
        )
        dev_svc._discovered[f"{identity.protocol.value}:{identity.serial}"] = identity
        result = bridge.deviceDetailStorage(str(temp_music))
        assert result["ok"] is True
        assert bridge.storageInfo

    def test_step4_profile_device(self, dev_svc):
        """Profile device capabilities."""
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="SanDisk", model="Clip", serial="wf_profile",
            mount_point="/media/sandisk",
        )
        caps = dev_svc.resolve_capabilities(identity)
        assert caps.supports_pairing is False
        assert caps.supports_playlists is False

    def test_step5_plan_transfer(self, dev_svc, temp_music):
        """Plan a transfer by creating a job."""
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "planned.flac")
        job = dev_svc.create_transfer_job(src, dst, SyncDirection.TO_DEVICE)
        assert job.job_id.startswith("sync_")
        assert job.total_bytes > 0
        assert job.status == TransferStatus.QUEUED

    def test_step6_start_transfer(self, bridge, temp_music):
        """Start transfer via bridge."""
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "started.flac")
        result = bridge.startTransfer(src, dst)
        assert result["ok"] is True
        assert Path(dst).exists()

    def test_step7_cancel_transfer(self, bridge, dev_svc, temp_music):
        """Cancel a transfer."""
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "cancelled.flac")
        job = dev_svc.create_transfer_job(src, dst)
        result = bridge.cancelTransfer(job.job_id)
        assert result["ok"] is True
        assert dev_svc.get_job(job.job_id).status == TransferStatus.CANCELLED

    def test_full_workflow_round_trip(self, bridge, dev_svc, temp_music):
        """Complete round-trip: discover  select  inspect  profile  plan  start  cancel."""
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="FiiO", model="M11", serial="wf_full",
            mount_point=str(temp_music),
        )
        key = f"{identity.protocol.value}:{identity.serial}"

        bridge.refresh()

        dev_svc._discovered[key] = identity

        caps = dev_svc.resolve_capabilities(identity)
        assert caps.supports_playlists is True

        pair_result = dev_svc.pair(identity)
        assert pair_result["ok"] is True

        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "full_wf.flac")
        job = dev_svc.create_transfer_job(src, dst)
        assert job.status == TransferStatus.QUEUED

        transfer_result = bridge.startTransfer(src, dst)
        assert transfer_result["ok"] is True
        assert Path(dst).exists()

        cancel_result = bridge.cancelTransfer(job.job_id)
        assert cancel_result["ok"] is True

    def test_audio_only_video_rejected(self, bridge, temp_music):
        """Verify video files are rejected in transfers."""
        result = bridge.validateAudioFile(str(temp_music / "Music" / "video.mp4"))
        assert result["ok"] is False
        assert result["error"] == "VIDEO_NOT_SUPPORTED"

    def test_audio_only_video_avi_rejected(self, bridge, temp_music):
        """Verify AVI files are rejected."""
        result = bridge.validateAudioFile(str(temp_music / "Music" / "video.avi"))
        assert result["ok"] is False
        assert result["error"] == "VIDEO_NOT_SUPPORTED"

    def test_audio_only_flac_accepted(self, bridge, temp_music):
        """Verify FLAC files are accepted."""
        result = bridge.validateAudioFile(str(temp_music / "Music" / "track.flac"))
        assert result["ok"] is True

    def test_audio_only_mp3_accepted(self, bridge, temp_music):
        """Verify MP3 files are accepted."""
        result = bridge.validateAudioFile(str(temp_music / "Music" / "track.mp3"))
        assert result["ok"] is True

    def test_audio_only_ogg_accepted(self, bridge, temp_music):
        """Verify OGG files are accepted."""
        result = bridge.validateAudioFile(str(temp_music / "Music" / "track.ogg"))
        assert result["ok"] is True

    def test_transfer_history_after_completion(self, bridge, dev_svc, temp_music):
        """Verify history is populated after completed transfer."""
        src = str(temp_music / "Music" / "track.wav")
        dst = str(temp_music / "historical.wav")
        job = dev_svc.create_transfer_job(src, dst)
        dev_svc.execute_job(job.job_id)
        history = dev_svc.get_history()
        assert len(history) >= 1
        assert history[0]["status"] == "completed"

    def test_server_start_stop_cycle(self, bridge):
        """Verify server start/stop cycle."""
        r1 = bridge.startServer()
        assert r1["ok"] is True
        assert bridge.serverActive is True

        r2 = bridge.stopServer()
        assert r2["ok"] is True
        assert bridge.serverActive is False

    def test_plan_transfer_with_empty_source(self, dev_svc, tmp_path):
        """Verify planning a transfer with nonexistent source fails."""
        src = str(tmp_path / "nonexistent.flac")
        dst = str(tmp_path / "out.flac")
        job = dev_svc.create_transfer_job(src, dst)
        result = dev_svc.execute_job(job.job_id)
        assert result["ok"] is False
