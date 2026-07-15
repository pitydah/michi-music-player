from __future__ import annotations
"""MX: Negative — cancellation edge cases for specialized domains."""

from unittest.mock import MagicMock


def test_cancel_nonexistent_job():
    bridge = MagicMock()
    bridge.cancelTransfer = MagicMock(
        return_value={"ok": False, "error": "JOB_NOT_FOUND"}
    )
    result = bridge.cancelTransfer("nonexistent_job")
    assert result.get("ok") is False
    assert result.get("error") == "JOB_NOT_FOUND"


def test_cancel_already_completed():
    bridge = MagicMock()
    bridge.cancelTransfer = MagicMock(
        return_value={"ok": False, "error": "JOB_ALREADY_COMPLETED"}
    )
    result = bridge.cancelTransfer("completed_job")
    assert result.get("ok") is False
    assert result.get("error") == "JOB_ALREADY_COMPLETED"


def test_double_cancel():
    bridge = MagicMock()
    bridge.cancelTransfer = MagicMock()
    bridge.cancelTransfer.side_effect = [
        {"ok": True},
        {"ok": False, "error": "JOB_NOT_FOUND"},
    ]
    r1 = bridge.cancelTransfer("job_1")
    assert r1.get("ok") is True
    r2 = bridge.cancelTransfer("job_1")
    assert r2.get("ok") is False


def test_cancel_mix_generation_not_running():
    bridge = MagicMock()
    bridge.cancelGeneration = MagicMock(
        return_value={"ok": True, "message": "No active generation"}
    )
    result = bridge.cancelGeneration()
    assert result.get("ok") is True


def test_cancel_global_search_no_active():
    bridge = MagicMock()
    bridge.cancel = MagicMock(return_value={"ok": True})
    result = bridge.cancel()
    assert result.get("ok") is True


def test_cancel_radio_stream_not_playing():
    bridge = MagicMock()
    bridge.stopStream = MagicMock(
        return_value={"ok": True, "message": "No active stream"}
    )
    result = bridge.stopStream()
    assert result.get("ok") is True


def test_dismiss_no_current_notification():
    bridge = MagicMock()
    bridge.currentNotification = None
    bridge.dismiss = MagicMock(return_value=None)
    bridge.dismiss()
    assert bridge.dismiss.called
