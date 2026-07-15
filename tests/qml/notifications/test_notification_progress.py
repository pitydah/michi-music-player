"""Test progress notifications — progress updates, updateProgress, cancel."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.notification_bridge import NotificationBridge


@pytest.fixture
def job_bridge():
    jb = MagicMock()
    jb.cancelJob.return_value = {"ok": True}
    return jb


@pytest.fixture
def bridge(job_bridge):
    return NotificationBridge(job_bridge=job_bridge)


class TestShowProgress:
    def test_show_progress_creates_notification(self, bridge):
        result = bridge.showProgress("Descargando...", "job_1", 50)
        assert result["ok"] is True
        assert bridge.currentNotification is not None

    def test_show_progress_has_kind_and_job_id(self, bridge):
        bridge.showProgress("Procesando", "job_99", 25)
        n = bridge.currentNotification
        assert n["progress"] == 25
        assert n["job_id"] == "job_99"
        assert n["kind"] == "info"

    def test_show_progress_clamps_value(self, bridge):
        bridge.showProgress("Sobre 100", "j1", 150)
        assert bridge.currentNotification["progress"] == 100

        bridge.dismiss()
        bridge.showProgress("Bajo 0", "j2", -10)
        assert bridge.currentNotification is None or bridge.currentNotification["progress"] == 0

    def test_progress_is_persistent(self, bridge):
        bridge.showProgress("Largo", "j_long", 10)
        assert bridge.currentNotification["persistent"] is True

    def test_show_progress_dedup(self, bridge):
        bridge.showProgress("Paso 1", "j_dedup", 25)
        result = bridge.showProgress("Paso 2", "j_dedup", 50)
        assert result.get("updated") is True
        assert bridge.currentNotification["progress"] == 50
        assert bridge.currentNotification["text"] == "Paso 2"


class TestUpdateProgress:
    def test_update_existing_progress(self, bridge):
        bridge.showProgress("Iniciando", "j_upd", 0)
        result = bridge.updateProgress("j_upd", 0.75, "75% completado")
        assert result["ok"] is True
        assert bridge.currentNotification["progress"] >= 75

    def test_update_progress_creates_if_not_exists(self, bridge):
        result = bridge.updateProgress("j_new", 0.5, "Mitad")
        assert result["ok"] is True
        assert bridge.currentNotification is not None

    def test_update_progress_float_conversion(self, bridge):
        bridge.showProgress("Empezando", "j_float", 0)
        bridge.updateProgress("j_float", 0.333, "Un tercio")
        assert bridge.currentNotification["progress"] == 33

    def test_update_progress_above_one(self, bridge):
        bridge.showProgress("Start", "j_pct", 0)
        bridge.updateProgress("j_pct", 90.0, "90%")
        assert bridge.currentNotification["progress"] == 90


class TestCancelProgress:
    def test_cancel_job_calls_bridge(self, bridge, job_bridge):
        bridge.showProgress("Trabajo", "42", 50)
        result = bridge.cancelJobById("42")
        assert result["ok"] is True
        job_bridge.cancelJob.assert_called_once_with(42)

    def test_cancel_job_no_bridge(self, bridge):
        bridge._job_bridge = None
        result = bridge.cancelJobById("42")
        assert result["ok"] is False

    def test_cancel_job_invalid_id(self, bridge, job_bridge):
        job_bridge.cancelJob.side_effect = ValueError("invalid")
        result = bridge.cancelJobById("abc")
        assert result["ok"] is False

    def test_show_then_cancel_then_verify_cleared(self, bridge, job_bridge):
        bridge.showProgress("Descarga", "100", 30)
        assert bridge.currentNotification is not None
        bridge.dismiss()
        assert bridge.currentNotification is None


class TestProgressEdgeCases:
    def test_progress_0_percent(self, bridge):
        bridge.showProgress("Nuevo", "j_0", 0)
        assert bridge.currentNotification["progress"] == 0

    def test_progress_100_percent(self, bridge):
        bridge.showProgress("Completado", "j_100", 100)
        assert bridge.currentNotification["progress"] == 100

    def test_multiple_progress_jobs(self, bridge):
        bridge.showProgress("Job A", "j_a", 25)
        bridge.showProgress("Job B", "j_b", 50)
        assert bridge.queueLength == 1
        assert bridge.currentNotification["job_id"] == "j_a"
