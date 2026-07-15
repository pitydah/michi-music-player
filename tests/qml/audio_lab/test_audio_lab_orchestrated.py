from __future__ import annotations
"""Tests for AU — AudioLabService orquestado."""

import sqlite3
import time

import pytest
from PySide6.QtCore import QCoreApplication

pytestmark = [pytest.mark.qml_module("audio_lab")]


def _process_events(duration=1.0):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.02)


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
    def svc(self, app, db, wm):
        from core.audio_lab.audio_lab_service import AudioLabService

        s = AudioLabService(db=db, worker_manager=wm)
        s.setup()
        return s

    def test_orchestrated_setup_all_services(self, svc):
        caps = svc.capability_map()
        assert caps["profiles"] is True
        assert caps["probe"] is True
        assert caps["analysis"] is True
        assert caps["conversion"] is True
        assert caps["normalization"] is True
        assert caps["replaygain"] is True
        assert caps["integrity"] is True
        assert caps["comparison"] is True
        assert caps["batch"] is True

    def test_orchestrated_properties(self, svc):
        assert svc.profiles is not None
        assert svc.probe is not None
        assert svc.analysis is not None
        assert svc.conversion is not None
        assert svc.normalization is not None
        assert svc.replaygain is not None
        assert svc.integrity is not None
        assert svc.comparison is not None
        assert svc.batch is not None
        assert svc.jobs is not None

    def test_orchestrated_topological_order(self, svc):
        assert svc.profiles is not None
        assert svc.probe is not None
        assert svc.conversion._profile_service is not None

    def test_orchestrated_status(self, svc):
        status = svc.status()
        assert status["available"] is True
        assert "capabilities" in status

    def test_orchestrated_profiles_list(self, svc):
        profiles = svc.profiles.list_profiles()
        assert len(profiles) >= 8

    def test_orchestrated_probe_missing_file(self, svc):
        result = svc.probe.probe("/nonexistent.flac")
        assert result.decode_status == "not_found"

    def test_orchestrated_analysis_missing(self, svc):
        result = svc.analysis.analyze_file("/nonexistent.flac")
        assert result["status"] == "error"

    def test_orchestrated_job_adapter_creates_probe(self, svc):
        job_id = svc.jobs.submit_probe("/nonexistent.flac")
        assert job_id.startswith("probe_")

    def test_orchestrated_job_adapter_creates_analysis(self, svc):
        job_id = svc.jobs.submit_analysis("/nonexistent.flac")
        assert job_id.startswith("analysis_")

    def test_orchestrated_job_adapter_creates_replaygain(self, svc):
        job_id = svc.jobs.submit_replaygain("/nonexistent.flac")
        assert job_id.startswith("rg_")

    def test_orchestrated_job_adapter_creates_integrity(self, svc):
        job_id = svc.jobs.submit_integrity("/nonexistent.flac")
        assert job_id.startswith("integrity_")

    def test_orchestrated_job_adapter_creates_comparison(self, svc):
        job_id = svc.jobs.submit_comparison("/a.flac", "/b.flac")
        assert job_id.startswith("compare_")

    def test_orchestrated_signal_connectivity(self, svc):
        signals = []
        svc.stateChanged.connect(lambda s, d: signals.append((s, d)))
        svc.stateChanged.emit("test", {"ok": True})
        _process_events(0.2)
        assert len(signals) >= 1

    def test_orchestrated_batch_creates(self, svc):
        batch_id = svc.batch.create_batch(["/a.flac", "/b.flac"])
        assert batch_id.startswith("batch_")
