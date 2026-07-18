"""Tests for ToastService — unified toast notification API."""
from unittest.mock import MagicMock

from core.toast_service import ToastService


class TestToastService:
    def test_show_info(self):
        svc = ToastService()
        result = svc.show("test", "info")
        assert result["ok"]
        assert result["level"] == "info"

    def test_show_success(self):
        svc = ToastService()
        result = svc.show("ok", "success")
        assert result["ok"]

    def test_show_warning(self):
        svc = ToastService()
        result = svc.show("warn", "warning")
        assert result["ok"]

    def test_show_error(self):
        svc = ToastService()
        result = svc.show("err", "error")
        assert result["ok"]

    def test_info_method(self):
        svc = ToastService()
        result = svc.info("test")
        assert result["ok"]

    def test_success_method(self):
        svc = ToastService()
        result = svc.success("ok")
        assert result["ok"]

    def test_warning_method(self):
        svc = ToastService()
        result = svc.warning("warn")
        assert result["ok"]

    def test_error_method(self):
        svc = ToastService()
        result = svc.error("err")
        assert result["ok"]

    def test_with_bridge(self):
        bridge = MagicMock()
        bridge.showMessage.return_value = {"ok": True, "sent": True}
        svc = ToastService(notification_bridge=bridge)
        result = svc.show("test", "info")
        assert result["sent"]
        bridge.showMessage.assert_called_once_with("test", "info")

    def test_log_only_when_no_bridge(self):
        svc = ToastService()
        result = svc.show("test", "info")
        assert result["ok"]

    def test_set_notification_bridge(self):
        svc = ToastService()
        bridge = MagicMock()
        svc.set_notification_bridge(bridge)
        result = svc.show("test", "info")
        assert result["ok"]

    def test_shortcuts(self):
        svc = ToastService()
        assert svc.info("a")["ok"]
        assert svc.success("a")["ok"]
        assert svc.warning("a")["ok"]
        assert svc.error("a")["ok"]
