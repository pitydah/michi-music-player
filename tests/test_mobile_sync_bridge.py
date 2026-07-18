"""Tests for MobileSyncBridge — QR, pairing, verify, unpair."""
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def svc():
    from core.mobile_sync_service import MobileSyncService
    return MobileSyncService()


@pytest.fixture
def bridge(svc):
    from ui_qml_bridge.mobile_sync_bridge import MobileSyncBridge
    return MobileSyncBridge(mobile_sync_service=svc)


class TestMobileSyncBridge:
    def test_start_pairing(self, bridge):
        result = bridge.startPairing()
        assert result["ok"]
        assert bridge.pairingCode != ""
        assert bridge.pairingState == "waiting"

    def test_start_pairing_no_service(self):
        from ui_qml_bridge.mobile_sync_bridge import MobileSyncBridge
        b = MobileSyncBridge()
        result = b.startPairing()
        assert not result["ok"]

    def test_verify_pairing_correct(self, bridge):
        pair = bridge.startPairing()
        result = bridge.verifyPairing(pair["code"])
        assert result["ok"]
        assert bridge.pairingState == "verified"

    def test_verify_pairing_wrong_code(self, bridge):
        bridge.startPairing()
        result = bridge.verifyPairing("000000")
        assert not result["ok"]

    def test_verify_pairing_no_session(self, bridge):
        result = bridge.verifyPairing("123456")
        assert not result["ok"]

    def test_unpair_device(self, bridge):
        pair = bridge.startPairing()
        bridge.verifyPairing(pair["code"])
        device_id = bridge.pairedDevices[0]["id"]
        result = bridge.unpairDevice(device_id)
        assert result["ok"]
        assert len(bridge.pairedDevices) == 0

    def test_cancel_pairing(self, bridge):
        bridge.startPairing()
        bridge.cancelPairing()
        assert bridge.pairingState == "idle"
        assert bridge.pairingCode == ""

    def test_paired_devices_property(self, bridge):
        assert isinstance(bridge.pairedDevices, list)

    def test_paired_devices_after_pairing(self, bridge):
        pair = bridge.startPairing()
        bridge.verifyPairing(pair["code"])
        assert len(bridge.pairedDevices) == 1
