"""Tests for Audio Lab v12 — Bridge depende solo de: audio_lab_service, job_service, process_controller, confirmation_service.
NO db_conn, NO player_service como orquestador."""
from unittest.mock import MagicMock, patch

import pytest


class TestAudioLabBridgeCreation:
    def test_creation(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge(
            audio_lab_service=MagicMock(),
            job_service=MagicMock(),
            process_controller=MagicMock(),
        )
        assert alb is not None

    def test_service_available_default(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge(audio_lab_service=MagicMock())
        assert alb.serviceAvailable is True

    def test_service_unavailable(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge()
        assert alb.serviceAvailable is False

    def test_no_db_conn(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge(audio_lab_service=MagicMock(),
                              job_service=MagicMock(), process_controller=MagicMock())
        assert alb._db_conn is None

    def test_no_player_service_orquestador(self):
        from ui_qml_bridge import audio_lab_bridge
        content = open(audio_lab_bridge.__file__).read()
        assert "player_service=None" in content

    def test_capability_map(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        svc = MagicMock()
        svc.capability_map.return_value = {"analysis": True}
        alb = AudioLabBridge(audio_lab_service=svc)
        cap = alb.capabilityMap()
        assert isinstance(cap, dict)


class TestAudioLabOperations:
    def test_refresh(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge(audio_lab_service=MagicMock())
        result = alb.refresh()
        assert result.get("ok")

    def test_cancel_job(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge(audio_lab_service=MagicMock())
        result = alb.cancelJob("nonexistent")
        assert isinstance(result, dict)

    def test_cleanup_completed(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge(audio_lab_service=MagicMock())
        result = alb.cleanupCompleted()
        assert result.get("ok")

    def test_active_jobs(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge(audio_lab_service=MagicMock())
        jobs = alb.activeJobs()
        assert isinstance(jobs, dict)

    def test_navigate(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        nav = MagicMock()
        nav.navigate = MagicMock(return_value={"ok": True})
        alb = AudioLabBridge(audio_lab_service=MagicMock(), navigation_bridge=nav)
        result = alb.navigateTo("audio_lab")
        assert result.get("ok")

    def test_require_confirmation(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        confirm = MagicMock()
        confirm.request = MagicMock(return_value={"ok": True})
        alb = AudioLabBridge(audio_lab_service=MagicMock(), confirmation_service=confirm)
        result = alb.requireConfirmation("analyze")
        assert isinstance(result, dict)

    def test_partial_failure_report(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge(audio_lab_service=MagicMock())
        report = alb.partialFailureReport()
        assert isinstance(report, dict)

    def test_retry_job(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge(audio_lab_service=MagicMock())
        result = alb.retryJob("nonexistent")
        assert not result.get("ok")

    def test_preview_analysis_no_service(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge()
        result = alb.previewAnalysis("/test/file.flac")
        assert not result.get("ok")

    def test_validate_analysis_no_service(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge()
        result = alb.validateAnalysis("/test/file.flac")
        assert not result.get("ok")
