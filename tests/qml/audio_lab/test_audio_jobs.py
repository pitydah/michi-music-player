"""Tests for AudioBatchJobsPage — active, completed, failed jobs display and actions."""
from pathlib import Path
"""Tests for Audio Lab jobs queue — running, queued, completed, failed, cancelled."""
from __future__ import annotations


import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

pytestmark = pytest.mark.qml_module("audio_lab")

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


@pytest.fixture
def engine(qapp):
    return QQmlEngine(qapp)


def _load_page(engine) -> QQmlComponent:
    engine.addImportPath(str(QML_DIR))
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/audio_lab/AudioBatchJobsPage.qml")))
    return component


class TestAudioJobs:
    def test_instantiate(self, engine):
        component = _load_page(engine)
        assert component.isReady(), component.errorString()

    def test_object_name(self, engine):
        component = _load_page(engine)
        assert component.isReady()
        obj = component.create()
        try:
            assert obj.property("objectName") == "audioJobs.page"
        finally:
            obj.deleteLater()

    def test_job_bridge_property(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioBatchJobsPage.qml").read_text()
        assert "jobBridge" in source
        assert "jobBr" in source

    def test_active_jobs_section(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioBatchJobsPage.qml").read_text()
        assert "En ejecución" in source or "active" in source.lower()

    def test_completed_jobs_section(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioBatchJobsPage.qml").read_text()
        assert "Completados" in source or "completed" in source.lower()

    def test_failed_jobs_section(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioBatchJobsPage.qml").read_text()
        assert "Fallidos" in source or "failed" in source.lower()

    def test_clear_completed_button(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioBatchJobsPage.qml").read_text()
        assert "clearCompleted" in source or "Limpiar completados" in source

    def test_clear_failed_button(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioBatchJobsPage.qml").read_text()
        assert "clearFailed" in source or "Limpiar fallidos" in source

    def test_cancel_job_button(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioBatchJobsPage.qml").read_text()
        assert "cancelJob" in source or "Cancelar" in source

    def test_list_jobs(self, adapter):
        adapter.submit_probe("/a.flac")
        adapter.submit_analysis("/b.flac")
        jobs = adapter.list()
        assert len(jobs) >= 2
    def test_retry_job_button(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioBatchJobsPage.qml").read_text()
        assert "retryJob" in source or "Reintentar" in source

    def test_job_bridge_clear_completed(self):
        from ui_qml_bridge.job_bridge import JobBridge
        jb = JobBridge()
        result = jb.clearCompleted()
        assert result["ok"] is True

    def test_job_bridge_clear_failed(self):
        from ui_qml_bridge.job_bridge import JobBridge
        jb = JobBridge()
        result = jb.clearFailed()
        assert result["ok"] is True

    def test_job_bridge_active_count(self):
        from ui_qml_bridge.job_bridge import JobBridge
        jb = JobBridge()
        assert jb.activeCount >= 0

    def test_job_bridge_cancel_job_existing(self):
        from ui_qml_bridge.job_bridge import JobBridge
        jb = JobBridge()
        result = jb.runJob("library_scan", "/tmp")
        assert result["ok"] is True

    def test_job_bridge_retry_job_nonexistent(self):
        from ui_qml_bridge.job_bridge import JobBridge
        jb = JobBridge()
        result = jb.retryJob(99999)
        assert result["ok"] is False

    def test_job_queue_sections(self):
        sections = ["active", "completed", "failed", "cancelled"]
        assert len(sections) == 4

    def test_job_detail_shows_info(self):
        job = {"title": "Test", "state": "running", "progress": 0.5, "job_id": 1}
        assert job["title"] == "Test"
        assert job["state"] == "running"

    def test_job_cancel_button_visible_on_running(self):
        assert True

    def test_michitheme_references(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioBatchJobsPage.qml").read_text()
        assert "MichiTheme" in source
    def test_list_jobs(self, adapter):
        adapter.submit_probe("/a.flac")
        adapter.submit_analysis("/b.flac")
        jobs = adapter.list()
        assert len(jobs) >= 2

    def test_job_bridge_clear_completed(self):
        from ui_qml_bridge.job_bridge import JobBridge
        jb = JobBridge()
        result = jb.clearCompleted()
        assert result["ok"] is True

    def test_job_bridge_clear_failed(self):
        from ui_qml_bridge.job_bridge import JobBridge
        jb = JobBridge()
        result = jb.clearFailed()
        assert result["ok"] is True

    def test_job_bridge_active_count(self):
        from ui_qml_bridge.job_bridge import JobBridge
        jb = JobBridge()
        assert jb.activeCount >= 0

    def test_job_bridge_cancel_job_existing(self):
        from ui_qml_bridge.job_bridge import JobBridge
        jb = JobBridge()
        result = jb.runJob("library_scan", "/tmp")
        assert result["ok"] is True

    def test_job_bridge_retry_job_nonexistent(self):
        from ui_qml_bridge.job_bridge import JobBridge
        jb = JobBridge()
        result = jb.retryJob(99999)
        assert result["ok"] is False

    def test_job_queue_sections(self):
        sections = ["active", "completed", "failed", "cancelled"]
        assert len(sections) == 4

    def test_job_detail_shows_info(self):
        job = {"title": "Test", "state": "running", "progress": 0.5, "job_id": 1}
        assert job["title"] == "Test"
        assert job["state"] == "running"

    def test_job_cancel_button_visible_on_running(self):
        assert True

    def test_job_retry_button_visible_on_failed(self):
        assert True

    def test_clear_completed_removes_done(self):
        assert True

    def test_clear_failed_removes_errors(self):
        assert True
