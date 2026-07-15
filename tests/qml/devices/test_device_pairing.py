"""Test device pairing flow."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.device_sync_service import DeviceSyncService, DeviceIdentity, DeviceProtocol
from ui_qml_bridge.devices_bridge import DevicesBridge

pytestmark = pytest.mark.isolation


@pytest.fixture
def svc():
    return DeviceSyncService()


@pytest.fixture
def bridge(svc):
    mgr = MagicMock()
    mgr.start.return_value = True
    mgr.stop.return_value = True
    mgr.is_active = True
    mgr.get_all_peers.return_value = [
        {"alias": "Android Phone", "device": "android", "ip": "192.168.1.50", "port": 53318},
        {"alias": "HiBy R6", "device": "dedicated", "ip": "192.168.1.51", "port": 53318},
    ]
    mgr.get_paired_devices.return_value = []
    return DevicesBridge(sync_manager=mgr, device_sync_service=svc)


class TestPairingDiscovery:
    def test_peers_available(self, bridge):
        bridge.refresh()
        assert len(bridge.peers) == 2

    def test_discover_empty(self, bridge, svc):
        result = bridge.discoverDevices()
        assert result["ok"] is True

    def test_discover_with_devices(self, bridge, svc, tmp_path):
        music = tmp_path / "Music"
        music.mkdir()
        (music / "track.flac").write_bytes(b"fLaC" + b"\x00" * 100)
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="SanDisk", model="Clip", serial="disc1",
            mount_point=str(tmp_path),
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        svc._discovered[key] = identity
        result = bridge.discoverDevices()
        assert result["ok"] is True
        assert result["count"] >= 1

    def test_identify_device(self, svc, tmp_path):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="FiiO", model="M11", serial="id1",
            mount_point=str(tmp_path),
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        svc._discovered[key] = identity
        result = svc.identify(str(tmp_path))
        assert result is not None
        assert result.vendor == "FiiO"

    def test_identify_unknown(self, svc):
        assert svc.identify("/nonexistent") is None


class TestPairingAction:
    def test_pair_device(self, bridge, svc, tmp_path):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="Test", model="Player", serial="pair1",
            mount_point=str(tmp_path),
        )
        svc._discovered[f"{identity.protocol.value}:{identity.serial}"] = identity
        result = bridge.pairDevice(str(tmp_path))
        assert result["ok"] is True

    def test_pair_not_found(self, bridge):
        result = bridge.pairDevice("/nonexistent")
        assert result["ok"] is False

    def test_pair_no_service(self):
        b = DevicesBridge()
        result = b.pairDevice("/media/test")
        assert result["ok"] is False

    def test_pair_duplicate(self, svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="Test", model="Player", serial="dup",
            mount_point="/media/dup",
        )
        svc.pair(identity)
        result = svc.pair(identity)
        assert result["ok"] is False
        assert result["error"] == "ALREADY_PAIRED"

    def test_unpair_paired_device(self, bridge, svc, tmp_path):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="Test", model="Player", serial="unpair1",
            mount_point=str(tmp_path),
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        svc.pair(identity)
        result = bridge.unpairDevice(key)
        assert result["ok"] is True


class TestQRCode:
    def test_generate_qr(self, bridge):
        qr = bridge.generateQRCode()
        assert qr.startswith("michi://pair/")
        assert len(qr) > len("michi://pair/")

    def test_qr_data_property(self, bridge):
        qr = bridge.generateQRCode()
        assert bridge.qrCodeData == qr

    def test_qr_generates_unique(self, bridge):
        qr1 = bridge.generateQRCode()
        qr2 = bridge.generateQRCode()
        assert qr1 != qr2

    def test_qr_initial_empty(self):
        b = DevicesBridge()
        assert b.qrCodeData == ""


class TestManualConnection:
    def test_connect_to_peer_ip(self, bridge):
        mgr = bridge._sync_mgr
        mgr.connect.return_value = {"ok": True}
        result = bridge.connectToPeer("192.168.1.50", 53318)
        assert result["ok"] is True
        mgr.connect.assert_called_once_with("192.168.1.50", 53318)

    def test_connect_no_manager(self):
        b = DevicesBridge()
        result = b.connectToPeer("192.168.1.50", 53318)
        assert result["ok"] is False

    def test_connect_invalid_port(self, bridge):
        mgr = bridge._sync_mgr
        mgr.connect.return_value = {"ok": False, "error": "Connection refused"}
        result = bridge.connectToPeer("192.168.1.50", 0)
        assert result["ok"] is False
