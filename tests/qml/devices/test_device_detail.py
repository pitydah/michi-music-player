from __future__ import annotations
"""Test DeviceDetailPage, storage, transfer plan."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.device_sync_service import DeviceSyncService, DeviceIdentity, DeviceProtocol
from ui_qml_bridge.devices_bridge import DevicesBridge

pytestmark = pytest.mark.isolation


@pytest.fixture
def temp_device(tmp_path):
    music = tmp_path / "Music"
    music.mkdir()
    (music / "track.flac").write_bytes(b"fLaC" + b"\x00" * 2000)
    (music / "track.mp3").write_bytes(b"\xff\xfb" + b"\x00" * 2000)
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


class TestDeviceDetailStorage:
    def test_storage_info(self, bridge, temp_device):
        result = bridge.deviceDetailStorage(str(temp_device))
        assert result["ok"] is True
        assert bridge.storageInfo
        info = bridge.storageInfo[0]
        assert info["mount_point"] == str(temp_device)
        assert info["total_bytes"] > 0

    def test_storage_info_no_service(self):
        b = DevicesBridge()
        result = b.deviceDetailStorage("/media/test")
        assert result["ok"] is False

    def test_storage_normalised_values(self, bridge, temp_device):
        bridge.deviceDetailStorage(str(temp_device))
        info = bridge.storageInfo[0]
        assert info["total_gb"] > 0
        assert info["free_bytes"] >= 0
        assert info["used_bytes"] >= 0

    def test_storage_no_mount_point(self, bridge):
        result = bridge.deviceDetailStorage("/nonexistent")
        assert result["ok"] is True  # get_storage returns empty StorageInfo, not an error


class TestDeviceDetailCompatibility:
    def test_compatibility_info(self, bridge, svc, temp_device):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="Test", model="Player", serial="comp1",
            mount_point=str(temp_device),
        )
        svc._discovered[f"{identity.protocol.value}:{identity.serial}"] = identity
        result = bridge.deviceDetailCompatibility(str(temp_device))
        assert result["ok"] is True
        assert bridge.compatibilityInfo
        compat = bridge.compatibilityInfo[0]
        assert "flac" in str(compat["supported_formats"]).lower()

    def test_compatibility_no_service(self):
        b = DevicesBridge()
        result = b.deviceDetailCompatibility("/media/test")
        assert result["ok"] is False

    def test_compatibility_unknown_device(self, bridge):
        result = bridge.deviceDetailCompatibility("/nonexistent")
        assert result["ok"] is False

    def test_compatibility_hiby_caps(self, svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="HiBy", model="R6", serial="hiby1",
            mount_point="/media/hiby",
        )
        caps = svc.resolve_capabilities(identity)
        assert caps.supports_pairing is True
        assert caps.supports_playlists is True


class TestDeviceDetailActions:
    def test_unpair_device(self, bridge, svc, temp_device):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="Test", model="DAP", serial="unpair1",
            mount_point=str(temp_device),
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        svc.pair(identity)
        assert svc.is_paired(key) is True
        result = bridge.unpairDevice(key)
        assert result["ok"] is True

    def test_trust_device(self, bridge, svc, temp_device):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.GENERIC_DEDICATED,
            vendor="HiBy", model="R6", serial="trust1",
            mount_point=str(temp_device),
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        svc.pair(identity)
        result = bridge.trustDevice(key)
        assert result["ok"] is True

    def test_authorize_device(self, bridge, svc, temp_device):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.ANDROID_MTP,
            vendor="Google", model="Pixel", serial="auth1",
            mount_point=str(temp_device),
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        svc.pair(identity)
        result = svc.authorize(key)
        assert result["ok"] is True

    def test_eject_device(self, bridge, svc, temp_device):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="Test", model="USB", serial="eject1",
            mount_point=str(temp_device),
        )
        svc.pair(identity)
        result = bridge.ejectDevice(str(temp_device))
        assert result["ok"] is True

    def test_eject_no_service(self):
        b = DevicesBridge()
        result = b.ejectDevice("/media/test")
        assert result["ok"] is False

    def test_browse_files(self, bridge, temp_device):
        result = bridge.browseFiles(str(temp_device), "Music")
        assert result["ok"] is True
        assert len(result["files"]) >= 2


class TestDeviceTransferPlan:
    def test_create_transfer_job(self, bridge, svc, temp_device):
        src = str(temp_device / "Music" / "track.flac")
        dst = str(temp_device / "dest.flac")
        job = svc.create_transfer_job(src, dst)
        assert job.job_id.startswith("sync_")
        assert job.total_bytes > 0

    def test_transfer_job_execution(self, bridge, temp_device):
        src = str(temp_device / "Music" / "track.flac")
        dst = str(temp_device / "exec.flac")
        result = bridge.startTransfer(src, dst)
        assert result["ok"] is True
        assert Path(dst).exists()

    def test_transfer_list(self, bridge, temp_device):
        src = str(temp_device / "Music" / "track.flac")
        dst = str(temp_device / "list.flac")
        bridge.startTransfer(src, dst)
        assert len(bridge.transferJobs) >= 1
