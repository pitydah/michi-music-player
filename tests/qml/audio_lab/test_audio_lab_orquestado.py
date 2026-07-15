"""DT — AudioLab orquestado: AudioLabService + AudioLabState instancia ÚNICA en AudioLabBridge.

Canonical API: capabilities, inputs, profiles, selectedProfile, preview,
startAnalysis, startConversion, startReplayGain, startNormalization,
startIntegrity, startComparison, cancelJob, retryJob, clearInputs, results, errors.
"""
from __future__ import annotations

import sqlite3
import time
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QCoreApplication


def _process_events(duration=0.5):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.02)


class TestAudioLabOrquestado:
    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    @pytest.fixture
    def db(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE IF NOT EXISTS media_items (id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, artist TEXT, album TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS album_art (id INTEGER PRIMARY KEY, album_key TEXT, data BLOB)")
        return conn

    @pytest.fixture
    def wm(self):
        from core.worker_manager import WorkerManager
        wm = WorkerManager()
        yield wm
        wm.shutdown()

    @pytest.fixture
    def audio_lab_service(self, app, db, wm):
        from core.audio_lab.audio_lab_service import AudioLabService
        svc = AudioLabService(db=db, worker_manager=wm)
        svc.setup()
        return svc

    @pytest.fixture
    def audio_lab_state(self):
        from core.audio_lab.audio_lab_state import AudioLabState
        return AudioLabState()

    @pytest.fixture
    def mock_player(self):
        player = MagicMock()
        player.get_active_backend_id.return_value = "gstreamer"
        player.get_eq_state.return_value = {"bypass": False, "preamp": 0.0}
        player.get_output_device_id.return_value = "default"
        return player

    @pytest.fixture
    def bridge(self, app, db, audio_lab_service, audio_lab_state, mock_player):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
import pytest
pytestmark = [pytest.mark.qml_module("audio_lab")]

        return AudioLabBridge(
            db_conn=db,
            player_service=mock_player,
            audio_lab_service=audio_lab_service,
            audio_lab_state=audio_lab_state,
        )

    # ── Canonical API tests ──

    def test_capabilities_returns_map(self, bridge):
        caps = bridge.capabilities()
        assert isinstance(caps, dict)
        assert caps.get("probe") is True
        assert caps.get("profiles") is True
        assert caps.get("analysis") is True
        assert caps.get("conversion") is True
        assert caps.get("integrity") is True
        assert caps.get("comparison") is True

    def test_inputs_empty_initially(self, bridge):
        assert bridge.inputs() == []

    def test_profiles_list(self, bridge):
        profiles = bridge.profiles()
        assert isinstance(profiles, list)
        assert len(profiles) >= 1

    def test_selected_profile_default(self, bridge):
        assert bridge.selectedProfile == ""

    def test_selected_profile_setter(self, bridge):
        bridge.selectedProfile = "flac"
        assert bridge.selectedProfile == "flac"

    def test_preview_empty_initially(self, bridge):
        preview = bridge.preview()
        assert isinstance(preview, dict)

    def test_start_analysis_returns_job_id(self, bridge):
        result = bridge.startAnalysis("/nonexistent.flac")
        assert result["ok"]
        assert result["job_id"].startswith("analysis_")

    def test_start_integrity_returns_job_id(self, bridge):
        result = bridge.startIntegrity("/nonexistent.flac")
        assert result["ok"]
        assert result["job_id"].startswith("integrity_")

    def test_start_comparison_returns_job_id(self, bridge):
        result = bridge.startComparison("/a.flac", "/b.flac")
        assert result["ok"]
        assert result["job_id"].startswith("compare_")

    def test_start_replaygain_returns_job_id(self, bridge):
        result = bridge.startReplayGain("/nonexistent.flac")
        assert result["ok"]
        assert result["job_id"].startswith("rg_")

    def test_start_conversion_returns_job_id(self, bridge):
        result = bridge.startConversion("/nonexistent.flac")
        assert result["ok"]

    def test_cancel_job(self, bridge):
        result = bridge.startAnalysis("/nonexistent.flac")
        job_id = result["job_id"]
        cancel = bridge.cancelJob(job_id)
        assert cancel["ok"] is True

    def test_retry_nonexistent_job(self, bridge):
        result = bridge.retryJob("nonexistent")
        assert not result["ok"]
        assert result["error"] == "NOT_FAILED"

    def test_clear_inputs(self, bridge):
        result = bridge.clearInputs()
        assert result["ok"]

    def test_results_empty_initially(self, bridge):
        assert bridge.results() == []

    def test_errors_empty_initially(self, bridge):
        assert bridge.errors() == []

    def test_refresh_with_service(self, bridge):
        result = bridge.refresh()
        assert result["ok"]
        assert result["backend"]["backend"] == "gstreamer"
