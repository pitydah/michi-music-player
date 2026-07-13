"""Test AppBridge lifecycle phases and shutdown with active tasks."""
from unittest.mock import MagicMock

from ui_qml_bridge.app_bridge import AppBridge


def _make_app_bridge(**kwargs) -> AppBridge:
    defaults = dict(
        worker_manager=MagicMock(),
        query_executor=MagicMock(),
        player_service=MagicMock(),
        queue_bridge=MagicMock(),
        sync_manager=MagicMock(),
        home_audio_controller=MagicMock(),
        radio_manager=MagicMock(),
        discovery=MagicMock(),
        db=MagicMock(),
    )
    defaults.update(kwargs)
    return AppBridge(**defaults)


def test_initial_phase():
    bridge = _make_app_bridge()
    assert bridge.phase == AppBridge.PHASE_INITIALIZING


def test_set_ready():
    bridge = _make_app_bridge()
    assert not bridge.ready
    bridge.setReady()
    assert bridge.ready
    assert bridge.phase == AppBridge.PHASE_READY


def test_set_phase():
    bridge = _make_app_bridge()
    bridge.setPhase(AppBridge.PHASE_LOADING_SERVICES)
    assert bridge.phase == AppBridge.PHASE_LOADING_SERVICES
    bridge.setPhase(AppBridge.PHASE_LOADING_QML)
    assert bridge.phase == AppBridge.PHASE_LOADING_QML


def test_set_ready_emits_status():
    bridge = _make_app_bridge()
    received = []
    bridge.statusChanged.connect(lambda s: received.append(s))
    bridge.setReady()
    assert "ready" in received


def test_quit_sets_accepting_new_false():
    bridge = _make_app_bridge()
    assert bridge._accepting_new
    bridge.quit()
    assert not bridge._accepting_new


def test_quit_emits_shutting_down():
    bridge = _make_app_bridge()
    received = []
    bridge.statusChanged.connect(lambda s: received.append(s))
    bridge.quit()
    assert "shutting_down" in received


def test_quit_shuts_down_query_executor():
    qe = MagicMock()
    bridge = _make_app_bridge(query_executor=qe)
    bridge.quit()
    qe.shutdown.assert_called_once()


def test_quit_cancels_worker_manager():
    wm = MagicMock()
    bridge = _make_app_bridge(worker_manager=wm)
    bridge.quit()
    assert wm.cancel_all.called
    assert wm.shutdown.called


def test_quit_stops_sync_manager():
    sm = MagicMock()
    bridge = _make_app_bridge(sync_manager=sm)
    bridge.quit()
    sm.stop.assert_called_once()


def test_quit_stops_home_audio():
    ha = MagicMock()
    bridge = _make_app_bridge(home_audio_controller=ha)
    bridge.quit()
    assert ha.stop.called or ha.shutdown.called


def test_quit_stops_radio():
    rm = MagicMock()
    bridge = _make_app_bridge(radio_manager=rm)
    bridge.quit()
    assert rm.stop.called or rm.shutdown.called


def test_quit_stops_player():
    ps = MagicMock()
    bridge = _make_app_bridge(player_service=ps)
    bridge.quit()
    ps.stop.assert_called_once()


def test_quit_saves_queue():
    qb = MagicMock()
    bridge = _make_app_bridge(queue_bridge=qb)
    bridge.quit()
    qb.saveState.assert_called_once()


def test_quit_closes_db():
    db = MagicMock()
    bridge = _make_app_bridge(db=db)
    bridge.quit()
    db.close.assert_called_once()


def test_shutdown_with_active_tasks():
    worker_manager = MagicMock()
    query_executor = MagicMock()
    bridge = _make_app_bridge(
        worker_manager=worker_manager,
        query_executor=query_executor,
    )
    bridge.setReady()
    bridge.quit()
    assert bridge._shutting_down
    assert bridge.phase == AppBridge.PHASE_SHUTTING_DOWN
    assert not bridge._accepting_new


def test_shutdown_tolerates_null_services():
    bridge = AppBridge()
    bridge.quit()
    assert bridge._shutting_down


def test_shutdown_does_not_raise():
    wm = MagicMock()
    wm.cancel_all.side_effect = RuntimeError("fail")
    wm.shutdown.side_effect = RuntimeError("fail")
    qe = MagicMock()
    qe.shutdown.side_effect = RuntimeError("fail")
    bridge = _make_app_bridge(worker_manager=wm, query_executor=qe)
    bridge.quit()
    assert bridge._shutting_down


def test_shutting_down_property():
    bridge = _make_app_bridge()
    assert not bridge.shuttingDown
    bridge.quit()
    assert bridge.shuttingDown
