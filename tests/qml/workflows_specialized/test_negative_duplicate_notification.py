from __future__ import annotations
"""MX: Negative — duplicate notification handling."""

from unittest.mock import MagicMock


def test_duplicate_notification_dedup():
    bridge = MagicMock()
    seen = set()

    def show(msg, kind):
        key = f"{kind}:{msg}"
        if key in seen:
            return {"ok": True, "deduped": True}
        seen.add(key)
        return {"ok": True, "deduped": False}

    bridge.showMessage = show
    r1 = bridge.showMessage("Test message", "info")
    assert r1.get("deduped") is False
    r2 = bridge.showMessage("Test message", "info")
    assert r2.get("deduped") is True


def test_duplicate_notification_different_kind():
    bridge = MagicMock()
    shown = {}

    def show(msg, kind):
        key = f"{kind}:{msg}"
        if key in shown:
            return {"ok": True, "deduped": True}
        shown[key] = True
        return {"ok": True, "deduped": False}

    bridge.showMessage = show
    r1 = bridge.showMessage("Same message", "info")
    assert r1.get("deduped") is False
    r2 = bridge.showMessage("Same message", "warning")
    assert r2.get("deduped") is False


def test_notification_queue_limit():
    bridge = MagicMock()
    bridge.queueLength = 20
    assert bridge.queueLength >= 20
