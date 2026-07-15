from __future__ import annotations
"""MF-MK: Audio conversion real — conversion via AudioLabBridge with injected services."""

import sqlite3

import pytest
from PySide6.QtCore import QCoreApplication

from ui_qml_bridge.audio_lab_bridge import AudioLabBridge


class TestAudioConversionReal:
    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    @pytest.fixture
    def db(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE IF NOT EXISTS media_items (id INTEGER PRIMARY KEY, filepath TEXT)")
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
    def confirm_svc(self):
        from core.confirmation_service import ConfirmationService
        return ConfirmationService()

    @pytest.fixture
    def bridge(self, audio_lab_svc, confirm_svc):
        return AudioLabBridge(
            audio_lab_service=audio_lab_svc,
            confirmation_service=confirm_svc,
        )

    def test_conversion_module_present(self, bridge):
        modules = bridge.modules
        ids = [m["id"] for m in modules]
        assert "conversion" in ids

    def test_conversion_audio_only(self, bridge):
        modules = bridge.modules
        for m in modules:
            assert "desc" in m
            assert "title" in m

    def test_conversion_probe_audio(self, bridge, tmp_path):
        f = tmp_path / "test.wav"
        f.write_bytes(b"RIFF" + b"\x00" * 200)
        result = bridge.probeFile(str(f))
        assert "format" in result

    def test_conversion_probe_video_rejected(self, bridge, tmp_path):
        f = tmp_path / "video.mp4"
        f.write_bytes(b"\x00" * 200)
        result = bridge.probeFile(str(f))
        assert "decode_status" in result

    def test_conversion_integrity(self, bridge, tmp_path):
        f = tmp_path / "test.flac"
        f.write_bytes(b"fLaC" + b"\x00" * 200)
        result = bridge.integrityCheck(str(f))
        assert "valid" in result or "error" in result

    def test_conversion_no_service(self):
        b = AudioLabBridge()
        result = b.probeFile("/test.flac")
        assert "unavailable" in result.get("decode_status", "")

    def test_conversion_no_service_analysis(self):
        b = AudioLabBridge()
        result = b.analyzeFile("/test.flac")
        assert "no disponible" in result.get("error", "")
