"""Tests for MobileSyncService — pairing, verification, trust."""
import time
from unittest.mock import patch

import pytest


@pytest.fixture
def svc():
    from core.mobile_sync_service import MobileSyncService
    return MobileSyncService()


class TestMobileSync:
    def test_initial_state(self, svc):
        assert len(svc.paired_devices) == 0

    def test_start_pairing(self, svc):
        result = svc.start_pairing()
        assert result["ok"]
        assert len(result["code"]) == 6
        assert "session_id" in result
        assert "qr_data" in result

    def test_qr_code_generated(self, svc):
        result = svc.start_pairing()
        assert "qr_svg" in result
        # SVG should be base64 data URL or empty if qrcode not installed
        if result["qr_svg"]:
            assert result["qr_svg"].startswith("data:image/")

    def test_get_qr_code(self, svc):
        pair = svc.start_pairing()
        qr = svc.get_qr_code(pair["session_id"])
        assert qr["ok"]
        assert "qr_data" in qr

    def test_verify_pairing_valid(self, svc):
        pair = svc.start_pairing()
        result = svc.verify_pairing(pair["session_id"], pair["code"],
                                    device_name="Test Phone", device_id="phone-001")
        assert result["ok"]
        assert result["device_id"] == "phone-001"
        assert svc.is_paired("phone-001")
        assert svc.is_trusted("phone-001")

    def test_verify_pairing_wrong_code(self, svc):
        pair = svc.start_pairing()
        result = svc.verify_pairing(pair["session_id"], "000000")
        assert not result["ok"]
        assert "INVALID_CODE" in result.get("error", "")

    def test_verify_pairing_expired(self, svc):
        with patch("time.time", return_value=1000):
            pair = svc.start_pairing()
        with patch("time.time", return_value=2000):  # expired
            result = svc.verify_pairing(pair["session_id"], pair["code"])
            assert not result["ok"]
            assert "EXPIRED" in result.get("error", "")

    def test_unpair(self, svc):
        pair = svc.start_pairing()
        svc.verify_pairing(pair["session_id"], pair["code"],
                           device_id="phone-001")
        result = svc.unpair("phone-001")
        assert result["ok"]
        assert not svc.is_paired("phone-001")

    def test_unpair_nonexistent(self, svc):
        result = svc.unpair("nonexistent")
        assert not result["ok"]

    def test_trust_cycle(self, svc):
        pair = svc.start_pairing()
        svc.verify_pairing(pair["session_id"], pair["code"],
                           device_id="phone-001")
        svc.revoke_trust("phone-001")
        assert not svc.is_trusted("phone-001")
        svc.trust_device("phone-001")
        assert svc.is_trusted("phone-001")

    def test_get_pairing_info(self, svc):
        pair = svc.start_pairing()
        svc.verify_pairing(pair["session_id"], pair["code"],
                           device_id="phone-001", device_name="My Phone")
        info = svc.get_pairing_info("phone-001")
        assert info is not None
        assert info["name"] == "My Phone"
        assert info["trusted"]

    def test_get_pairing_info_nonexistent(self, svc):
        assert svc.get_pairing_info("nonexistent") is None

    def test_pending_sessions(self, svc):
        svc.start_pairing()
        sessions = svc.get_pending_sessions()
        assert len(sessions) >= 1

    def test_port_setting(self, svc):
        assert svc.get_port() == 28700
        svc.set_port(30000)
        assert svc.get_port() == 30000
        svc.set_port(80)  # too low, clamped
        assert svc.get_port() >= 1024

    def test_health(self, svc):
        health = svc.health()
        assert health["paired"] == 0
        assert health["active_sessions"] >= 0

    def test_multiple_devices(self, svc):
        for i in range(3):
            pair = svc.start_pairing()
            svc.verify_pairing(pair["session_id"], pair["code"],
                               device_id=f"device-{i}", device_name=f"Device {i}")
        assert len(svc.paired_devices) == 3
