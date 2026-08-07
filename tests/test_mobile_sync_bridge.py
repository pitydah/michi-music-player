"""Tests for MobileSyncBridge — QR, pairing, verify, unpair (Phase 7).

Bridge slot names and dict shapes stay stable; the secure default rejects
code-only pairing (SIGNATURE_REQUIRED), and the legacy code mode is tested
explicitly with the insecure flag surfaced through health.
"""

import pytest


@pytest.fixture
def svc():
    from core.mobile_sync_service import MobileSyncService
    return MobileSyncService()


@pytest.fixture
def legacy_svc():
    from core.mobile_sync_service import MobileSyncService
    return MobileSyncService(legacy_code_pairing_enabled=True)


@pytest.fixture
def bridge(svc):
    from ui_qml_bridge.mobile_sync_bridge import MobileSyncBridge
    return MobileSyncBridge(mobile_sync_service=svc)


@pytest.fixture
def legacy_bridge(legacy_svc):
    from ui_qml_bridge.mobile_sync_bridge import MobileSyncBridge
    return MobileSyncBridge(mobile_sync_service=legacy_svc)


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

    def test_verify_pairing_code_only_rejected_by_default(self, bridge):
        pair = bridge.startPairing()
        result = bridge.verifyPairing(pair["code"])
        assert not result["ok"]
        assert result["error"] == "SIGNATURE_REQUIRED"

    def test_verify_pairing_correct_legacy_mode(self, legacy_bridge):
        pair = legacy_bridge.startPairing()
        result = legacy_bridge.verifyPairing(pair["code"])
        assert result["ok"]
        assert legacy_bridge.pairingState == "verified"
        # Legacy pairing never auto-trusts; health flags it as insecure.
        device_id = result["device_id"]
        assert not legacy_bridge._svc.is_trusted(device_id)
        assert legacy_bridge.health["insecure_legacy_enabled"] is True

    def test_verify_pairing_wrong_code(self, bridge):
        bridge.startPairing()
        result = bridge.verifyPairing("000000")
        assert not result["ok"]

    def test_verify_pairing_no_session(self, bridge):
        result = bridge.verifyPairing("123456")
        assert not result["ok"]

    def test_unpair_device(self, legacy_bridge):
        pair = legacy_bridge.startPairing()
        legacy_bridge.verifyPairing(pair["code"])
        device_id = legacy_bridge.pairedDevices[0]["id"]
        result = legacy_bridge.unpairDevice(device_id)
        assert result["ok"]
        assert len(legacy_bridge.pairedDevices) == 0

    def test_cancel_pairing(self, bridge):
        bridge.startPairing()
        bridge.cancelPairing()
        assert bridge.pairingState == "idle"
        assert bridge.pairingCode == ""

    def test_paired_devices_property(self, bridge):
        assert isinstance(bridge.pairedDevices, list)

    def test_paired_devices_after_pairing(self, legacy_bridge):
        pair = legacy_bridge.startPairing()
        legacy_bridge.verifyPairing(pair["code"])
        assert len(legacy_bridge.pairedDevices) == 1

    def test_approve_device_slot(self, legacy_bridge):
        pair = legacy_bridge.startPairing()
        result = legacy_bridge.verifyPairing(pair["code"])
        device_id = result["device_id"]
        assert not legacy_bridge._svc.is_trusted(device_id)
        approved = legacy_bridge.approveDevice(device_id)
        assert approved["ok"]
        assert legacy_bridge._svc.is_trusted(device_id)

    def test_approve_device_no_service(self):
        from ui_qml_bridge.mobile_sync_bridge import MobileSyncBridge
        b = MobileSyncBridge()
        result = b.approveDevice("x")
        assert not result["ok"]

    def test_health_reports_secure_pairing(self, bridge):
        assert bridge.health["secure_pairing_available"] is True
        assert bridge.health["signature_pairing_enabled"] is True
