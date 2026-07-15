<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""Test pairing flow: discover → pair → trust."""
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
"""Test device pairing flow."""
from __future__ import annotations

=======
"""Test pairing flow: discover → pair → trust."""
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
from unittest.mock import MagicMock

import pytest

<<<<<<< Updated upstream
<<<<<<< Updated upstream
from core.device_sync_service import (
    DeviceSyncService,
    DeviceIdentity,
    DeviceProtocol,
)
from ui_qml_bridge.devices_bridge import DevicesBridge


=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
from core.device_sync_service import DeviceSyncService, DeviceIdentity, DeviceProtocol
from ui_qml_bridge.devices_bridge import DevicesBridge

=======
from core.device_sync_service import (
    DeviceSyncService,
    DeviceIdentity,
    DeviceProtocol,
)
from ui_qml_bridge.devices_bridge import DevicesBridge


>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
pytestmark = pytest.mark.isolation


@pytest.fixture
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
def svc():
=======
>>>>>>> Stashed changes
=======
<<<<<<< HEAD
def svc():
=======
>>>>>>> Stashed changes
def temp_music(tmp_path):
    music = tmp_path / "Music"
    music.mkdir()
    (music / "track.flac").write_bytes(b"fLaC" + b"\x00" * 2000)
    (music / "track.mp3").write_bytes(b"\xff\xfb" + b"\x00" * 2000)
    return tmp_path


@pytest.fixture
def dev_svc():
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
    return DeviceSyncService()


@pytest.fixture
<<<<<<< Updated upstream
<<<<<<< Updated upstream
def mock_sync_mgr():
=======
=======
>>>>>>> Stashed changes
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


class TestPairingFlow:
    """Test the complete pairing flow: discover → pair → trust."""

    def test_discover_devices_populates(self, bridge, dev_svc, temp_music):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="Test", model="Player", serial="disc1",
            mount_point=str(temp_music),
        )
        dev_svc._discovered[f"{identity.protocol.value}:{identity.serial}"] = identity
        result = bridge.discoverDevices()
        assert result["ok"] is True

    def test_discover_empty(self, bridge):
        result = bridge.discoverDevices()
        assert result["ok"] is True

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

    def test_pair_device_duplicate(self, dev_svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="Test", model="Device", serial="dup",
            mount_point="/media/test",
        )
        dev_svc.pair(identity)
        result = dev_svc.pair(identity)
        assert result["ok"] is False
        assert result["error"] == "ALREADY_PAIRED"

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

    def test_untrust_device(self, bridge, dev_svc, temp_music):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.GENERIC_DEDICATED,
            vendor="HiBy", model="R6", serial="untrust1",
            mount_point=str(temp_music),
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        dev_svc.pair(identity)
        dev_svc.trust(key)
        result = bridge.untrustDevice(key)
        assert result["ok"] is True

    def test_trust_not_paired(self, bridge):
        result = bridge.trustDevice("nonexistent")
        assert result["ok"] is False

<<<<<<< Updated upstream
=======
    def test_connect_invalid_port(self, bridge):
        mgr = bridge._sync_mgr
        mgr.connect.return_value = {"ok": False, "error": "Connection refused"}
        result = bridge.connectToPeer("192.168.1.50", 0)
        assert result["ok"] is False
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


class TestPairingFlow:
    """Test the complete pairing flow: discover → pair → trust."""

    def test_discover_devices_populates(self, bridge, dev_svc, temp_music):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="Test", model="Player", serial="disc1",
            mount_point=str(temp_music),
        )
        dev_svc._discovered[f"{identity.protocol.value}:{identity.serial}"] = identity
        result = bridge.discoverDevices()
        assert result["ok"] is True

    def test_discover_empty(self, bridge):
        result = bridge.discoverDevices()
        assert result["ok"] is True

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

    def test_pair_device_duplicate(self, dev_svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="Test", model="Device", serial="dup",
            mount_point="/media/test",
        )
        dev_svc.pair(identity)
        result = dev_svc.pair(identity)
        assert result["ok"] is False
        assert result["error"] == "ALREADY_PAIRED"

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

    def test_untrust_device(self, bridge, dev_svc, temp_music):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.GENERIC_DEDICATED,
            vendor="HiBy", model="R6", serial="untrust1",
            mount_point=str(temp_music),
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        dev_svc.pair(identity)
        dev_svc.trust(key)
        result = bridge.untrustDevice(key)
        assert result["ok"] is True

    def test_trust_not_paired(self, bridge):
        result = bridge.trustDevice("nonexistent")
        assert result["ok"] is False

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    def test_authorize_device(self, bridge, dev_svc, temp_music):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.ANDROID_MTP,
            vendor="Android", model="Phone", serial="auth1",
            mount_point=str(temp_music),
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        dev_svc.pair(identity)
        result = bridge.authorizeDevice(key)
        assert result["ok"] is True

    def test_unauthorize_device(self, bridge, dev_svc, temp_music):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.ANDROID_MTP,
            vendor="Android", model="Phone", serial="unauth1",
            mount_point=str(temp_music),
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        dev_svc.pair(identity)
        dev_svc.authorize(key)
        result = bridge.unauthorizeDevice(key)
        assert result["ok"] is True

    def test_get_paired_after_pair(self, bridge, dev_svc, temp_music):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="Test", model="Device", serial="list_pair",
            mount_point=str(temp_music),
        )
        dev_svc.pair(identity)
        paired = dev_svc.get_paired()
        assert len(paired) >= 1
        assert any(p.get("vendor") == "Test" for p in paired)

    def test_pairing_round_trip(self, bridge, dev_svc, temp_music):
        """Full round-trip: discover → pair → trust → unauthorize → unpair."""
        identity = DeviceIdentity(
            protocol=DeviceProtocol.ANDROID_MTP,
            vendor="Google", model="Pixel", serial="roundtrip",
            mount_point=str(temp_music),
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        dev_svc._discovered[key] = identity
        pair_result = dev_svc.pair(identity)
        assert pair_result["ok"] is True

        trust_result = bridge.trustDevice(key)
        assert trust_result["ok"] is True

        unauth_result = bridge.unauthorizeDevice(key)
        assert unauth_result["ok"] is True

        unpair_result = bridge.unpairDevice(key)
        assert unpair_result["ok"] is True
        assert dev_svc.is_paired(key) is False
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
