"""Tests for AudioBatchJobsPage — active, completed, failed jobs display and actions."""
from pathlib import Path

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

    def test_retry_job_button(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioBatchJobsPage.qml").read_text()
        assert "retryJob" in source or "Reintentar" in source

    def test_job_progress_bar(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioBatchJobsPage.qml").read_text()
        assert "MichiProgressBar" in source or "progress" in source.lower()

    def test_summary_metrics(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioBatchJobsPage.qml").read_text()
        assert "activeCount" in source
        assert "Activos" in source
        assert "Total" in source

    def test_empty_state_when_no_active_jobs(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioBatchJobsPage.qml").read_text()
        assert "EmptyState" in source

    def test_back_button(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioBatchJobsPage.qml").read_text()
        assert "Volver" in source

    def test_accessible_attributes(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioBatchJobsPage.qml").read_text()
        assert "Accessible.name" in source
        assert "Accessible.Panel" in source

    def test_focus_scope(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioBatchJobsPage.qml").read_text()
        assert "FocusScope" in source
        assert "activeFocusOnTab" in source

    def test_filtered_repeaters(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioBatchJobsPage.qml").read_text()
        assert ".filter(" in source or "filter" in source.lower()

    def test_job_id_object_names(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioBatchJobsPage.qml").read_text()
        assert "modelData.job_id" in source

    def test_michitheme_references(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioBatchJobsPage.qml").read_text()
        assert "MichiTheme" in source
