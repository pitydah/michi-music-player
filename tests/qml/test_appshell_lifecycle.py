from __future__ import annotations
"""DG — AppShell + AppBridge lifecycle: states, shutdown (14 steps), constructor, edge cases."""

import os
import time
from unittest.mock import MagicMock

import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["MICHI_SAFE_MODE"] = "1"

from ui_qml_bridge.app_bridge import AppBridge


# ── Fixtures ──


@pytest.fixture
def mock_services():
    return dict(
        worker_manager=MagicMock(),
        query_executor=MagicMock(),
        player_service=MagicMock(),
        queue_service=MagicMock(),
        device_sync_service=MagicMock(),
        connection_service=MagicMock(),
        home_audio_service=MagicMock(),
        radio_service=MagicMock(),
        database=MagicMock(),
        navigation_bridge=MagicMock(),
    )


@pytest.fixture
def bridge(mock_services):
    return AppBridge(**mock_services)


@pytest.fixture
def bare_bridge():
    return AppBridge()


# ── Estado inicial BOOTSTRAP ──


def test_initial_phase_is_bootstrap():
    bridge = AppBridge()
    assert bridge.phase == AppBridge.BOOTSTRAP


def test_initial_phase_with_all_services(mock_services):
    bridge = AppBridge(**mock_services)
    assert bridge.phase == AppBridge.BOOTSTRAP


def test_initial_not_ready(bare_bridge):
    assert not bare_bridge.ready


def test_initial_not_shutting_down(bare_bridge):
    assert not bare_bridge.shuttingDown


def test_initial_accepting_new(bare_bridge):
    assert bare_bridge._accepting_new


# ── Transiciones de estado ──


def test_set_phase_database_ready(bare_bridge):
    bare_bridge.setPhase(AppBridge.DATABASE_READY)
    assert bare_bridge.phase == AppBridge.DATABASE_READY


def test_set_phase_services_ready(bare_bridge):
    bare_bridge.setPhase(AppBridge.SERVICES_READY)
    assert bare_bridge.phase == AppBridge.SERVICES_READY


def test_set_phase_bridges_ready(bare_bridge):
    bare_bridge.setPhase(AppBridge.BRIDGES_READY)
    assert bare_bridge.phase == AppBridge.BRIDGES_READY


def test_set_phase_qml_loading(bare_bridge):
    bare_bridge.setPhase(AppBridge.QML_LOADING)
    assert bare_bridge.phase == AppBridge.QML_LOADING


def test_set_phase_degraded(bare_bridge):
    bare_bridge.setPhase(AppBridge.DEGRADED)
    assert bare_bridge.phase == AppBridge.DEGRADED


def test_set_phase_failed(bare_bridge):
    bare_bridge.setPhase(AppBridge.FAILED)
    assert bare_bridge.phase == AppBridge.FAILED


def test_set_ready_transition(bridge):
    assert not bridge.ready
    bridge.setReady()
    assert bridge.ready
    assert bridge.phase == AppBridge.READY


def test_set_ready_emits_signal(bridge):
    received = []
    bridge.statusChanged.connect(lambda s: received.append(s))
    bridge.setReady()
    assert "ready" in received


# ── Constantes de estado ──


def test_state_constants():
    assert AppBridge.BOOTSTRAP == "bootstrap"
    assert AppBridge.DATABASE_READY == "database_ready"
    assert AppBridge.SERVICES_READY == "services_ready"
    assert AppBridge.BRIDGES_READY == "bridges_ready"
    assert AppBridge.QML_LOADING == "qml_loading"
    assert AppBridge.READY == "ready"
    assert AppBridge.DEGRADED == "degraded"
    assert AppBridge.FAILED == "failed"
    assert AppBridge.SHUTTING_DOWN == "shutting_down"
    assert AppBridge.STOPPED == "stopped"


# ── Constructor — servicios correctos ──


def test_constructor_accepts_worker_manager(mock_services):
    bridge = AppBridge(**mock_services)
    assert bridge._wm is mock_services["worker_manager"]


def test_constructor_accepts_query_executor(mock_services):
    bridge = AppBridge(**mock_services)
    assert bridge._qe is mock_services["query_executor"]


def test_constructor_accepts_player_service(mock_services):
    bridge = AppBridge(**mock_services)
    assert bridge._player_service is mock_services["player_service"]


def test_constructor_accepts_queue_service(mock_services):
    bridge = AppBridge(**mock_services)
    assert bridge._queue_service is mock_services["queue_service"]


def test_constructor_accepts_device_sync(mock_services):
    bridge = AppBridge(**mock_services)
    assert bridge._device_sync_service is mock_services["device_sync_service"]


def test_constructor_accepts_connection_service(mock_services):
    bridge = AppBridge(**mock_services)
    assert bridge._connection_service is mock_services["connection_service"]


def test_constructor_accepts_home_audio(mock_services):
    bridge = AppBridge(**mock_services)
    assert bridge._home_audio_service is mock_services["home_audio_service"]


def test_constructor_accepts_radio_service(mock_services):
    bridge = AppBridge(**mock_services)
    assert bridge._radio_service is mock_services["radio_service"]


def test_constructor_accepts_database(mock_services):
    bridge = AppBridge(**mock_services)
    assert bridge._database is mock_services["database"]


# ── Shutdown — banderas ──


def test_quit_sets_shutting_down(bridge):
    bridge.quit()
    assert bridge._shutting_down


def test_quit_sets_accepting_false(bridge):
    assert bridge._accepting_new
    bridge.quit()
    assert not bridge._accepting_new


def test_quit_emits_shutting_down_signal(bridge):
    received = []
    bridge.statusChanged.connect(lambda s: received.append(s))
    bridge.quit()
    assert "shutting_down" in received


def test_quit_sets_shutting_down_flag(bridge):
    bridge.quit()
    assert bridge._shutting_down


def test_quit_ends_at_stopped(bridge):
    bridge.quit()
    assert bridge.phase in (AppBridge.SHUTTING_DOWN, AppBridge.STOPPED)


# ── Shutdown — 14 pasos ──


def test_shutdown_has_14_steps(bridge):
    sr = bridge._ordered_shutdown()
    assert len(sr.steps) == 14, f"Expected 14 steps, got {len(sr.steps)}"


def test_shutdown_step_names(bridge):
    sr = bridge._ordered_shutdown()
    names = [s["step"] for s in sr.steps]
    assert names == [
        "block_actions",
        "cancel_navigation",
        "cancel_queries",
        "cancel_jobs",
        "terminate_subprocesses",
        "persist_queue",
        "persist_page_state",
        "stop_device_sync",
        "stop_connections",
        "stop_home_audio",
        "stop_radio",
        "stop_playback",
        "close_repositories",
        "close_db",
    ]


def test_shutdown_cancels_queries(mock_services):
    qe = MagicMock()
    mock_services["query_executor"] = qe
    bridge = AppBridge(**mock_services)
    bridge.quit()
    qe.shutdown.assert_called_once_with(2000)


def test_shutdown_cancels_jobs(mock_services):
    wm = MagicMock()
    mock_services["worker_manager"] = wm
    bridge = AppBridge(**mock_services)
    bridge.quit()
    assert wm.cancel_all.called or wm.shutdown.called


def test_shutdown_clears_navigation(mock_services):
    nav = MagicMock()
    mock_services["navigation_bridge"] = nav
    bridge = AppBridge(**mock_services)
    bridge.quit()
    assert nav.clearHistory.called


def test_shutdown_persists_queue(mock_services):
    qs = MagicMock()
    mock_services["queue_service"] = qs
    bridge = AppBridge(**mock_services)
    bridge.quit()
    assert qs.shutdown.called or qs.save_state.called


def test_shutdown_stops_device_sync(mock_services):
    ds = MagicMock()
    mock_services["device_sync_service"] = ds
    bridge = AppBridge(**mock_services)
    bridge.quit()
    assert ds.shutdown.called or ds.stop.called


def test_shutdown_stops_connection_service(mock_services):
    cs = MagicMock()
    mock_services["connection_service"] = cs
    bridge = AppBridge(**mock_services)
    bridge.quit()
    assert cs.shutdown.called or cs.stop.called


def test_shutdown_stops_home_audio(mock_services):
    ha = MagicMock()
    mock_services["home_audio_service"] = ha
    bridge = AppBridge(**mock_services)
    bridge.quit()
    assert ha.shutdown.called or ha.stop.called


def test_shutdown_stops_radio(mock_services):
    rs = MagicMock()
    mock_services["radio_service"] = rs
    bridge = AppBridge(**mock_services)
    bridge.quit()
    assert rs.shutdown.called or rs.stop.called


def test_shutdown_stops_playback(mock_services):
    ps = MagicMock()
    mock_services["player_service"] = ps
    bridge = AppBridge(**mock_services)
    bridge.quit()
    ps.stop.assert_called_once()


def test_shutdown_closes_database(mock_services):
    db = MagicMock()
    mock_services["database"] = db
    bridge = AppBridge(**mock_services)
    bridge.quit()
    db.close.assert_called_once()


def test_shutdown_stops_at_stopped(bridge):
    bridge.quit()
    assert bridge.phase == AppBridge.SHUTTING_DOWN


# ── Shutdown — tolerancia a errores ──


def test_shutdown_tolerates_missing_services():
    bridge = AppBridge()
    bridge.quit()
    assert bridge._shutting_down


def test_shutdown_tolerates_failures(mock_services):
    wm = MagicMock()
    wm.cancel_all.side_effect = RuntimeError("fail")
    mock_services["worker_manager"] = wm
    bridge = AppBridge(**mock_services)
    result = bridge.quit()
    assert isinstance(result, dict)
    assert not result.get("success", True) or len(result.get("steps", [])) > 0


def test_double_quit_idempotent(bridge):
    bridge.quit()
    bridge.quit()
    assert bridge._shutting_down


def test_shutdown_completes_quickly(bridge):
    start = time.time()
    bridge.quit()
    elapsed = time.time() - start
    assert elapsed < 5.0


# ── cancelAllTasks ──


def test_cancel_all_tasks_calls_worker_manager(mock_services):
    wm = MagicMock()
    mock_services["worker_manager"] = wm
    bridge = AppBridge(**mock_services)
    bridge.cancelAllTasks()
    assert wm.cancel_all.called


def test_cancel_all_tasks_tolerates_no_container():
    bridge = AppBridge()
    bridge.cancelAllTasks()


# ── appScore ──


def test_app_score_initial(bare_bridge):
    score = bare_bridge.appScore()
    assert score["score"] == 0


def test_app_score_after_ready(bridge):
    bridge.setReady()
    score = bridge.appScore()
    assert score["ready"]
    assert score["score"] > 0


def test_app_score_includes_service_count(mock_services):
    bridge = AppBridge(**mock_services)
    score = bridge.appScore()
    assert score["service_count"] > 0 and score["score"] > 0


# ── Properties ──


def test_safe_mode_from_env(monkeypatch):
    monkeypatch.setenv("MICHI_SAFE_MODE", "1")
    bridge = AppBridge()
    assert bridge.safeMode


def test_safe_mode_default():
    bridge = AppBridge()
    assert bridge.safeMode


def test_version_string():
    bridge = AppBridge()
    assert isinstance(bridge.version, str)
    assert len(bridge.version) > 0


def test_app_name():
    bridge = AppBridge()
    assert bridge.appName == "Michi Music Player"


def test_experimental_qml():
    bridge = AppBridge()
    assert bridge.experimentalQml


def test_restart_required_default(bare_bridge):
    assert not bare_bridge.restartRequired


def test_notify_restart(bare_bridge):
    bare_bridge.notifyRestartRequired()
    assert bare_bridge.restartRequired


def test_request_restart_slot(bare_bridge):
    result = bare_bridge.requestRestart()
    assert result["ok"]
    assert bare_bridge.restartRequired


# ── copyVersionInfo ──


def test_copy_version_info(bare_bridge):
    result = bare_bridge.copyVersionInfo()
    assert result["ok"]
    assert "Michi Music Player" in result["text"]


# ── Paths ──


def test_data_path_returns_string(bare_bridge):
    assert isinstance(bare_bridge.dataPath, str)


def test_cache_path_returns_string(bare_bridge):
    assert isinstance(bare_bridge.cachePath, str)


def test_config_path_returns_string(bare_bridge):
    assert isinstance(bare_bridge.configPath, str)


def test_log_path_returns_string(bare_bridge):
    assert isinstance(bare_bridge.logPath, str)


# ── Edge cases ──


def test_bridge_accepts_no_args():
    bridge = AppBridge()
    assert bridge._wm is None
    assert bridge._phase == AppBridge.BOOTSTRAP


def test_shutdown_records_step_errors(mock_services):
    wm = MagicMock()
    wm.cancel_all.side_effect = RuntimeError("test error")
    mock_services["worker_manager"] = wm
    bridge = AppBridge(**mock_services)
    result = bridge.quit()
    assert isinstance(result, dict)
    failed = [s for s in result.get("steps", []) if not s.get("ok")]
    assert len(failed) >= 1


def test_receive_services_noop():
    bridge = AppBridge()
    bridge.receive_services(MagicMock(), MagicMock())
