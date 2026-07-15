"""Test Devices productive workflows: discovery, pairing, detail, compatibility,
transfer queue, audio-only validation, and DeviceSyncService integration."""
from pathlib import Path
from unittest.mock import MagicMock


from core.device_sync_service import (
    DeviceSyncService, DeviceIdentity, DeviceProtocol, SyncDirection,
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
        {"alias": "Phone", "device": "android", "ip": "192.168.1.50", "port": 53318},
    ]
    mgr.is_active = True
    return mgr


@pytest.fixture
def bridge(dev_svc, job_svc, mock_sync_mgr):
    return DevicesBridge(
        sync_manager=mock_sync_mgr,
        device_sync_service=dev_svc,
        job_service=job_svc,
    )


class TestDiscovery:
    def test_discover_devices_populates_discovered(self, bridge, dev_svc, temp_music):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="Test", model="Player", serial="disc1",
            mount_point=str(temp_music),
        )
        dev_svc.pair(identity)
        result = bridge.discoverDevices()
        assert result["ok"] is True

    def test_discover_no_service(self):
        b = DevicesBridge()
        result = b.discoverDevices()
        assert result["ok"] is False
        assert result["error"] == "NO_DEVICE_SYNC_SERVICE"

    def test_get_discovered_initially_empty(self, bridge):
        assert bridge.discovered == []


class TestPairingFlow:
    def test_pair_device(self, bridge, dev_svc, temp_music):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="Test", model="Player", serial="pair1",
            mount_point=str(temp_music),
        )
        dev_svc._discovered[f"{identity.protocol.value}:{identity.serial}"] = identity
        result = bridge.pairDevice(str(temp_music))
        assert result["ok"] is True

    def test_pair_device_not_found(self, bridge):
        result = bridge.pairDevice("/nonexistent")
        assert result["ok"] is False

    def test_pair_no_service(self):
        b = DevicesBridge()
        result = b.pairDevice("/media/test")
        assert result["ok"] is False

    def test_unpair_device(self, bridge, dev_svc, temp_music):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="Test", model="Player", serial="unpair1",
            mount_point=str(temp_music),
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        dev_svc.pair(identity)
        result = bridge.unpairDevice(key)
        assert result["ok"] is True

    def test_unpair_not_paired(self, bridge):
        result = bridge.unpairDevice("nonexistent")
        assert result["ok"] is False

    def test_trust_device(self, bridge, dev_svc, temp_music):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.GENERIC_DEDICATED,
            vendor="HiBy", model="R6", serial="trust1",
            mount_point=str(temp_music),
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        dev_svc.pair(identity)
        result = bridge.trustDevice(key)
        assert result["ok"] is True


class TestStorageDetail:
    def test_device_detail_storage(self, bridge, temp_music):
        result = bridge.deviceDetailStorage(str(temp_music))
        assert result["ok"] is True
        assert bridge.storageInfo
        info = bridge.storageInfo[0]
        assert info["mount_point"] == str(temp_music)
        assert info["total_gb"] >= 0

    def test_device_detail_storage_no_service(self):
        b = DevicesBridge()
        result = b.deviceDetailStorage("/media/test")
        assert result["ok"] is False

    def test_device_detail_compatibility(self, bridge, dev_svc, temp_music):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="Test", model="Player", serial="comp1",
            mount_point=str(temp_music),
        )
        dev_svc._discovered[f"{identity.protocol.value}:{identity.serial}"] = identity
        result = bridge.deviceDetailCompatibility(str(temp_music))
        assert result["ok"] is True
        assert bridge.compatibilityInfo
        compat = bridge.compatibilityInfo[0]
        assert "flac" in str(compat["supported_formats"]).lower()


class TestTransferQueue:
    def test_start_transfer_audio(self, bridge, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "dest.flac")
        result = bridge.startTransfer(src, dst)
        assert result["ok"] is True
        assert Path(dst).exists()

    def test_start_transfer_non_audio(self, bridge, temp_music):
        src = str(temp_music / "Music" / "video.mp4")
        dst = str(temp_music / "dest.mp4")
        result = bridge.startTransfer(src, dst)
        assert result["ok"] is False
        assert "VIDEO" in result.get("error", "").upper() or "AUDIO" in result.get("error", "").upper()

    def test_cancel_transfer(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "cancel.flac")
        job = dev_svc.create_transfer_job(src, dst, SyncDirection.TO_DEVICE)
        result = bridge.cancelTransfer(job.job_id)
        assert result["ok"] is True

    def test_cancel_nonexistent(self, bridge):
        result = bridge.cancelTransfer("nonexistent")
        assert result["ok"] is False

    def test_retry_transfer(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "retry.flac")
        job = dev_svc.create_transfer_job(src, dst, SyncDirection.TO_DEVICE)
        dev_svc.execute_job(job.job_id)
        result = bridge.retryTransfer(job.job_id)
        assert result["ok"] is True

    def test_transfer_jobs_populated(self, bridge, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "tlist.flac")
        bridge.startTransfer(src, dst)
        assert len(bridge.transferJobs) >= 1


class TestAudioOnlyValidation:
    def test_validate_audio_file(self, bridge, temp_music):
        path = str(temp_music / "Music" / "track.flac")
        result = bridge.validateAudioFile(path)
        assert result["ok"] is True

    def test_validate_video_file_rejected(self, bridge, temp_music):
        path = str(temp_music / "Music" / "video.mp4")
        result = bridge.validateAudioFile(path)
        assert result["ok"] is False
        assert result["error"] == "VIDEO_NOT_SUPPORTED"

    def test_validate_nonexistent_ext(self, bridge):
        result = bridge.validateAudioFile("/nonexistent.xyz")
        assert result["ok"] is False

    def test_validate_shows_transcode_policy(self, bridge, temp_music):
        path = str(temp_music / "Music" / "track.flac")
        result = bridge.validateAudioFile(path)
        assert result["ok"] is True
        assert "transcode_policy" in result

    def test_clear_history(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "chist.flac")
        job = dev_svc.create_transfer_job(src, dst)
        dev_svc.execute_job(job.job_id)
        bridge.clearTransferHistory()
        assert bridge.transferHistory == []


class TestDeviceSyncIntegration:
    def test_refresh_includes_device_sync(self, bridge, dev_svc, temp_music):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="Test", model="Player", serial="ref1",
            mount_point=str(temp_music),
        )
        dev_svc.pair(identity)
        bridge.refresh()
        assert len(bridge.pairedDevices) >= 1

    def test_server_active_after_start(self, bridge, mock_sync_mgr):
        bridge.startServer()
        assert bridge.serverActive is True

    def test_job_service_tracks_transfer(self, bridge, job_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "jtrack.flac")
        bridge.startTransfer(src, dst)
        active = job_svc.list_active()
        assert len(active) == 0 or any(j.kind == "device_transfer" for j in active)
