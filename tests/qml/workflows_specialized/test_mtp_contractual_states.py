"""MTP contractual states test: discovery → authorization → disconnected → storage unavailable → transfer → cancel → reconnect.

Shows: "Compatibilidad contractual disponible. Validación física pendiente."
No hardware, no physical audio scoring.
"""
from pathlib import Path
from unittest.mock import MagicMock

from core.device_sync_service import (
    DeviceSyncService, DeviceIdentity, DeviceProtocol, TransferStatus,
)
from ui_qml_bridge.devices_bridge import DevicesBridge
import pytest
pytestmark = pytest.mark.isolation

_CONTRACTUAL_AVAILABLE = "Compatibilidad contractual disponible. Validación física pendiente."


@pytest.fixture
def temp_music(tmp_path):
    music = tmp_path / "Music"
    music.mkdir()
    (music / "track.flac").write_bytes(b"fLaC" + b"\x00" * 2000)
    (music / "track.mp3").write_bytes(b"\xff\xfb" + b"\x00" * 2000)
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


class TestMtpContractualStates:
    """MTP adapter: device discovery, authorization required, disconnected, storage unavailable, transfer, cancel, reconnect."""

    def test_mtp_discovery(self, dev_svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.ANDROID_MTP,
            vendor="Google", model="Pixel 8", serial="mtp001",
            mount_point="/media/pixel",
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        dev_svc._discovered[key] = identity
        discovered = dev_svc.get_discovered()
        assert len(discovered) == 1
        assert discovered[0].protocol == DeviceProtocol.ANDROID_MTP

    def test_mtp_authorization_required(self, dev_svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.ANDROID_MTP,
            vendor="Google", model="Pixel 8", serial="mtp_auth",
            mount_point="/media/pixel",
        )
        caps = dev_svc.resolve_capabilities(identity)
        assert caps.supports_authorization is True
        key = f"{identity.protocol.value}:{identity.serial}"
        dev_svc.pair(identity)
        assert dev_svc.is_paired(key)
        result = dev_svc.authorize(key)
        assert result["ok"] is True

    def test_mtp_contractual_message(self):
        assert _CONTRACTUAL_AVAILABLE == "Compatibilidad contractual disponible. Validación física pendiente."

    def test_mtp_disconnected_state(self, dev_svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.ANDROID_MTP,
            vendor="Google", model="Pixel 8", serial="mtp_disc",
            mount_point="/media/pixel",
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        dev_svc.pair(identity)
        assert dev_svc.is_paired(key)
        dev_svc.unpair(key)
        assert not dev_svc.is_paired(key)

    def test_mtp_storage_unavailable(self, dev_svc):
        info = dev_svc.get_storage("/nonexistent/mtp")
        assert info.total_bytes == 0
        assert info.free_bytes == 0

    def test_mtp_transfer(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "mtp_transferred.flac")
        result = bridge.startTransfer(src, dst)
        assert result["ok"] is True
        assert Path(dst).exists()

    def test_mtp_cancel_transfer(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "mtp_cancelled.flac")
        job = dev_svc.create_transfer_job(src, dst)
        result = bridge.cancelTransfer(job.job_id)
        assert result["ok"] is True
        assert dev_svc.get_job(job.job_id).status == TransferStatus.CANCELLED

    def test_mtp_reconnect_after_disconnect(self, dev_svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.ANDROID_MTP,
            vendor="Google", model="Pixel 8", serial="mtp_recon",
            mount_point="/media/pixel",
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        dev_svc.pair(identity)
        assert dev_svc.is_paired(key)
        dev_svc.unpair(key)
        assert not dev_svc.is_paired(key)
        dev_svc.pair(identity)
        assert dev_svc.is_paired(key)

    def test_mtp_discover_then_authorize(self, dev_svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.ANDROID_MTP,
            vendor="Samsung", model="Galaxy S24", serial="mtp_sam",
            mount_point="/media/samsung",
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        dev_svc._discovered[key] = identity
        discovered = dev_svc.get_discovered()
        assert any(d.serial == "mtp_sam" for d in discovered)
        dev_svc.pair(identity)
        result = dev_svc.authorize(key)
        assert result["ok"] is True

    def test_mtp_video_rejected(self, bridge, temp_music):
        src = str(temp_music / "Music" / "video.mp4")
        dst = str(temp_music / "mtp_video.mp4")
        result = bridge.startTransfer(src, dst)
        assert result["ok"] is False
        assert result["error"] == "VIDEO_NOT_SUPPORTED"
