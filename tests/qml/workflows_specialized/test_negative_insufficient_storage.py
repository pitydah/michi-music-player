"""MX: Negative — insufficient storage scenarios."""
from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock


def test_device_storage_unavailable():
    bridge = MagicMock()
    bridge.storageInfo = []
    assert len(bridge.storageInfo) == 0


def test_device_storage_full():
    bridge = MagicMock()
    type(bridge).storageInfo = PropertyMock(
        return_value=[{"device": "/dev/sda1", "available": 0, "total": 16000000000}]
    )
    info = bridge.storageInfo[0]
    assert info["available"] == 0
    assert info["total"] > 0


def test_transfer_fails_no_space():
    bridge = MagicMock()
    bridge.startTransfer = MagicMock(
        return_value={"ok": False, "error": "INSUFFICIENT_STORAGE"}
    )
    result = bridge.startTransfer("/src/big.flac", "/dst/big.flac")
    assert result.get("ok") is False
    assert result.get("error") == "INSUFFICIENT_STORAGE"


def test_conversion_fails_no_space():
    bridge = MagicMock()
    bridge.convertFile = MagicMock(
        return_value={"ok": False, "error": "INSUFFICIENT_STORAGE"}
    )
    result = bridge.convertFile("/src/big.flac", "MP3")
    assert result.get("ok") is False
    assert result.get("error") == "INSUFFICIENT_STORAGE"
