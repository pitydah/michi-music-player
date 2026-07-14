"""Test AppBridge — full lifecycle: constructor, phases, shutdown order, persistence."""
import time
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.app_bridge import AppBridge


# ── Fixtures ──


@pytest.fixture
def mock_services():
    return dict(
        worker_manager=MagicMock(),
        query_executor=MagicMock(),
        queue_service=MagicMock(),
        player_service=MagicMock(),
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


# ── Phase lifecycle ──


def test_initial_phase_is_bootstrap():
    bridge = AppBridge()
    assert bridge.phase == AppBridge.BOOTSTRAP


def test_initial_phase_with_services(mock_services):
    bridge = AppBridge(**mock_services)
    assert bridge.phase == AppBridge.BOOTSTRAP


def test_set_ready_transitions_to_ready(bridge):
    assert not bridge.ready
    bridge.setReady()
    assert bridge.ready
    assert bridge.phase == AppBridge.READY


def test_set_ready_emits_signal(bridge):
    received = []
    bridge.statusChanged.connect(lambda s: received.append(s))
    bridge.setReady()
    assert "ready" in received


def test_set_phase(bridge):
    bridge.setPhase(AppBridge.SERVICES_READY)
    assert bridge.phase == AppBridge.SERVICES_READY
    bridge.setPhase(AppBridge.QML_LOADING)
    assert bridge.phase == AppBridge.QML_LOADING


def test_phase_not_polluted_by_shorthand():
    assert AppBridge.BOOTSTRAP == "bootstrap"
    assert AppBridge.READY == "ready"
    assert AppBridge.FAILED == "failed"
    assert AppBridge.SHUTTING_DOWN == "shutting_down"


# ── Shutdown: stop accepting commands ──


def test_quit_sets_accepting_false(bridge):
    assert bridge._accepting
    bridge.quit()
    assert not bridge._accepting


def test_quit_emits_shutting_down(bridge):
    received = []
    bridge.statusChanged.connect(lambda s: received.append(s))
    bridge.quit()
    assert "shutting_down" in received


def test_quit_sets_phase_shutting_down(bridge):
    bridge.quit()
    assert bridge.phase == AppBridge.SHUTTING_DOWN


# ── Shutdown: navigation cancel ──


def test_shutdown_cancels_navigation(mock_services):
    nav = MagicMock()
    mock_services["navigation_bridge"] = nav
    bridge = AppBridge(**mock_services)
    bridge.quit()
    nav.clearHistory.assert_called_once()


def test_shutdown_tolerates_no_navigation_bridge():
    bridge = AppBridge(worker_manager=MagicMock(), query_executor=MagicMock())
    bridge.quit()


# ── Shutdown: query executor ──


def test_shutdown_cancels_searches(mock_services):
    qe = MagicMock()
    mock_services["query_executor"] = qe
    bridge = AppBridge(**mock_services)
    bridge.quit()
    qe.shutdown.assert_called_once_with(2000)


def test_shutdown_tolerates_no_query_executor():
    bridge = AppBridge(worker_manager=MagicMock())
    bridge.quit()


# ── Shutdown: worker manager ──


def test_shutdown_cancels_worker_manager(mock_services):
    wm = MagicMock()
    mock_services["worker_manager"] = wm
    bridge = AppBridge(**mock_services)
    bridge.quit()
    wm.cancel_all.assert_called_once()
    wm.shutdown.assert_called_once_with(3000)


def test_shutdown_tolerates_no_worker_manager():
    bridge = AppBridge()
    bridge.quit()


# ── Shutdown: external processes ──


def test_shutdown_terminates_external_processes():
    proc = MagicMock()
    bridge = AppBridge()
    bridge.track_external_process(proc)
    bridge.quit()
    proc.terminate.assert_called_once()
    proc.wait.assert_called_once_with(timeout=2)


def test_shutdown_clears_external_processes_list():
    proc = MagicMock()
    bridge = AppBridge()
    bridge.track_external_process(proc)
    bridge.quit()
    assert len(bridge._external_processes) == 0


# ── Shutdown: queue_service ──


def test_shutdown_persists_queue_service(mock_services):
    qs = MagicMock()
    mock_services["queue_service"] = qs
    bridge = AppBridge(**mock_services)
    bridge.quit()
    qs.shutdown.assert_called_once()


def test_shutdown_tolerates_no_queue_service():
    bridge = AppBridge()
    bridge.quit()


# ── Shutdown: device sync ──


def test_shutdown_stops_device_sync(mock_services):
    ds = MagicMock()
    mock_services["device_sync_service"] = ds
    bridge = AppBridge(**mock_services)
    bridge.quit()
    ds.shutdown.assert_called_once()


def test_shutdown_stops_device_sync_via_stop(mock_services):
    ds = MagicMock()
    ds.shutdown = None
    del ds.shutdown
    mock_services["device_sync_service"] = ds
    bridge = AppBridge(**mock_services)
    bridge.quit()
    ds.stop.assert_called_once()


# ── Shutdown: connection service ──


def test_shutdown_stops_connection_service(mock_services):
    cs = MagicMock()
    mock_services["connection_service"] = cs
    bridge = AppBridge(**mock_services)
    bridge.quit()
    cs.shutdown.assert_called_once()


# ── Shutdown: home audio ──


def test_shutdown_stops_home_audio(mock_services):
    ha = MagicMock()
    mock_services["home_audio_service"] = ha
    bridge = AppBridge(**mock_services)
    bridge.quit()
    ha.shutdown.assert_called_once()


def test_shutdown_stops_home_audio_via_stop():
    ha = MagicMock()
    ha.shutdown = None
    del ha.shutdown
    bridge = AppBridge(home_audio_service=ha)
    bridge.quit()
    ha.stop.assert_called_once()


# ── Shutdown: radio ──


def test_shutdown_stops_radio(mock_services):
    rs = MagicMock()
    mock_services["radio_service"] = rs
    bridge = AppBridge(**mock_services)
    bridge.quit()
    rs.shutdown.assert_called_once()


def test_shutdown_stops_radio_via_stop():
    rs = MagicMock()
    rs.shutdown = None
    del rs.shutdown
    bridge = AppBridge(radio_service=rs)
    bridge.quit()
    rs.stop.assert_called_once()


# ── Shutdown: player_service ──


def test_shutdown_stops_player_service(mock_services):
    ps = MagicMock()
    mock_services["player_service"] = ps
    bridge = AppBridge(**mock_services)
    bridge.quit()
    ps.stop.assert_called_once()


# ── Shutdown: database ──


def test_shutdown_closes_database(mock_services):
    db = MagicMock()
    mock_services["database"] = db
    bridge = AppBridge(**mock_services)
    bridge.quit()
    db.close.assert_called_once()


def test_shutdown_tolerates_no_database():
    bridge = AppBridge()
    bridge.quit()


# ── Shutdown: full sequence ──


def test_full_shutdown_sequence(mock_services):
    bridge = AppBridge(**mock_services)
    bridge.setReady()
    assert bridge.ready
    bridge.quit()
    assert bridge._shutting_down
    assert not bridge._accepting
    assert bridge.phase == AppBridge.SHUTTING_DOWN


def test_shutdown_completes_within_timeout(mock_services):
    wm = MagicMock()
    wm.shutdown.side_effect = lambda ms: time.sleep(0.01)
    mock_services["worker_manager"] = wm
    bridge = AppBridge(**mock_services)
    start = time.time()
    bridge.quit()
    elapsed = time.time() - start
    assert elapsed < 5.0


def test_shutdown_records_failures_as_warnings(mock_services, caplog):
    import logging
    caplog.set_level(logging.WARNING)
    wm = MagicMock()
    wm.cancel_all.side_effect = RuntimeError("worker fail")
    mock_services["worker_manager"] = wm
    bridge = AppBridge(**mock_services)
    bridge.quit()
    assert any("worker" in r.message for r in caplog.records)
    assert any("Shutdown completed" in r.message for r in caplog.records)


# ── Persistence ──


def test_persist_page_state_called(mock_services):
    bridge = AppBridge(**mock_services)
    called = False
    def tracking():
        nonlocal called
        called = True
    bridge._persist_page_state = tracking
    bridge.quit()
    assert called


def test_close_repositories_called(mock_services):
    bridge = AppBridge(**mock_services)
    called = False
    def tracking():
        nonlocal called
        called = True
    bridge._close_repositories = tracking
    bridge.quit()
    assert called


# ── Constructor signature ──


def test_constructor_accepts_only_services_no_queue_bridge():
    bridge = AppBridge(
        worker_manager=MagicMock(),
        query_executor=MagicMock(),
        queue_service=MagicMock(),
        player_service=MagicMock(),
        device_sync_service=MagicMock(),
        connection_service=MagicMock(),
        home_audio_service=MagicMock(),
        radio_service=MagicMock(),
        database=MagicMock(),
        navigation_bridge=MagicMock(),
    )
    assert bridge._wm is not None
    assert bridge._qe is not None
    assert bridge._queue_service is not None


def test_constructor_no_queue_bridge_param(mock_services):
    bridge = AppBridge(**mock_services)
    assert not hasattr(bridge, '_queue_bridge')


# ── Edge cases ──


def test_shutdown_with_null_all_services():
    bridge = AppBridge()
    bridge.quit()
    assert bridge._shutting_down


def test_double_quit_idempotent(mock_services):
    bridge = AppBridge(**mock_services)
    bridge.quit()
    bridge.quit()
    ps = mock_services["player_service"]
    ps.stop.assert_called_once()


def test_version_string():
    bridge = AppBridge()
    assert isinstance(bridge.version, str)
    assert len(bridge.version) > 0


def test_safe_mode_from_env(monkeypatch):
    monkeypatch.setenv("MICHI_SAFE_MODE", "1")
    bridge = AppBridge()
    assert bridge.safeMode


def test_experimental_qml_default():
    bridge = AppBridge()
    assert bridge.experimentalQml


def test_app_score_after_ready(mock_services):
    bridge = AppBridge(**mock_services)
    score = bridge.appScore()
    assert score["has_worker_manager"]
    assert not score["ready"]
    bridge.setReady()
    score = bridge.appScore()
    assert score["ready"]
    assert score["score"] >= 50


def test_notify_restart_required(mock_services):
    bridge = AppBridge(**mock_services)
    assert not bridge.restartRequired
    bridge.notifyRestartRequired()
    assert bridge.restartRequired


def test_cancel_all_tasks(mock_services):
    wm = MagicMock()
    mock_services["worker_manager"] = wm
    bridge = AppBridge(**mock_services)
    bridge.cancelAllTasks()
    wm.cancel_all.assert_called_once()


def test_shutting_down_property(mock_services):
    bridge = AppBridge(**mock_services)
    assert not bridge.shuttingDown
    bridge.quit()
    assert bridge.shuttingDown
