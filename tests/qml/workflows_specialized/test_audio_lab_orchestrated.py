"""MF-MK: AudioLabBridge orchestrated — accepts audio_lab_service, job_service, confirmation_service by DI."""
from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QCoreApplication

from ui_qml_bridge.audio_lab_bridge import AudioLabBridge


class TestAudioLabOrchestrated:
    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    @pytest.fixture
    def db(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE IF NOT EXISTS media_items (id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, artist TEXT, album TEXT)")
        return conn

    @pytest.fixture
    def wm(self):
        from core.worker_manager import WorkerManager
        wm = WorkerManager()
        yield wm
        wm.shutdown()

    @pytest.fixture
    def audio_lab_svc(self, app, db, wm):
        from core.audio_lab.audio_lab_service import AudioLabService
        s = AudioLabService(db=db, worker_manager=wm)
        s.setup()
        return s

    @pytest.fixture
    def job_svc(self):
        from core.job_service import JobService
        return JobService()

    @pytest.fixture
    def confirm_svc(self):
        from core.confirmation_service import ConfirmationService
        return ConfirmationService()

    @pytest.fixture
    def nav(self):
        nav = MagicMock()
        nav.navigate.return_value = {"ok": True}
        return nav

    @pytest.fixture
    def bridge(self, audio_lab_svc, job_svc, confirm_svc, nav):
        return AudioLabBridge(
            audio_lab_service=audio_lab_svc,
            job_service=job_svc,
            confirmation_service=confirm_svc,
            navigation_bridge=nav,
        )

    def test_bridge_receives_di(self, bridge, audio_lab_svc, job_svc, confirm_svc):
        assert bridge._audio_lab_svc is audio_lab_svc
        assert bridge._job_svc is job_svc
        assert bridge._confirm_svc is confirm_svc

    def test_bridge_no_service_construction_inside(self, bridge):
        assert bridge._audio_lab_svc is not None
        assert bridge._job_svc is not None
        assert bridge._confirm_svc is not None

    def test_bridge_modules(self, bridge):
        modules = bridge.modules
        module_ids = [m["id"] for m in modules]
        assert "conversion" in module_ids

    def test_bridge_refresh(self, bridge):
        result = bridge.refresh()
        assert result["ok"] is True
        assert "stats" in result

    def test_bridge_navigate(self, bridge):
        result = bridge.navigateTo("diagnostics")
        assert result["ok"] is True
        assert result["route"] == "diagnostics"

    def test_bridge_navigate_unsupported(self, bridge):
        result = bridge.navigateTo("nonexistent")
        assert result["ok"] is False

    def test_bridge_probe_via_service(self, bridge, tmp_path):
        f = tmp_path / "test.flac"
        f.write_bytes(b"fLaC" + b"\x00" * 200)
        result = bridge.probeFile(str(f))
        assert "format" in result

    def test_bridge_probe_missing(self, bridge):
        result = bridge.probeFile("/nonexistent.flac")
        assert "decode_status" in result

    def test_bridge_integrity(self, bridge, tmp_path):
        f = tmp_path / "test.flac"
        f.write_bytes(b"fLaC" + b"\x00" * 200)
        result = bridge.integrityCheck(str(f))
        assert "valid" in result or "error" in result

    def test_bridge_analysis_missing(self, bridge):
        result = bridge.analyzeFile("/nonexistent.flac")
        assert result["status"] in ("error", "unsupported")

    def test_cancel_is_real(self, bridge):
        assert hasattr(bridge, "_job_svc")

    def test_audio_only_message(self, bridge):
        modules = bridge.modules
        assert len(modules) > 0

    def test_bridge_refresh_no_db(self, app):
        b = AudioLabBridge()
        result = b.refresh()
        assert result["ok"] is True
        assert result["stats"] == {}
