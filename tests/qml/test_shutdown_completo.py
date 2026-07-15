"""Test AppBridge — 14-step ordered shutdown with result reporting."""
import time
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.app_bridge import AppBridge, ShutdownResult


# ── Fixtures ──


@pytest.fixture
def mock_bridge():
    sync_mgr = MagicMock(spec=[])
    sync_mgr.stop = MagicMock()
    ha_ctrl = MagicMock(spec=[])
    ha_ctrl.stop = MagicMock()
    radio_mgr = MagicMock(spec=[])
    radio_mgr.stop = MagicMock()
    mocks = dict(
        worker_manager=MagicMock(),
        query_executor=MagicMock(),
        player_service=MagicMock(),
        queue_bridge=MagicMock(),
        sync_manager=sync_mgr,
        home_audio_controller=ha_ctrl,
        radio_manager=radio_mgr,
        discovery=MagicMock(spec=[]),
        db=MagicMock(),
    )
    mocks["queue_bridge"].queue_service = MagicMock()
    return AppBridge(**mocks)


@pytest.fixture
def bare_bridge():
    return AppBridge()


# ── ShutdownResult ──


def test_shutdown_result_records_step():
    sr = ShutdownResult()
    sr.record("block_actions", True)
    assert len(sr.steps) == 1
    assert sr.steps[0]["step"] == "block_actions"
    assert sr.steps[0]["ok"] is True


def test_shutdown_result_success():
    sr = ShutdownResult()
    sr.record("step1", True)
    sr.record("step2", True)
    assert sr.success is True


def test_shutdown_result_failure():
    sr = ShutdownResult()
    sr.record("step1", True)
    sr.record("step2", False, "error detail")
    assert sr.success is False


def test_shutdown_result_to_dict():
    sr = ShutdownResult()
    sr.record("step1", True)
    d = sr.to_dict()
    assert "success" in d
    assert "steps" in d
    assert d["steps"][0]["step"] == "step1"


# ── quit() returns result dict ──


def test_quit_returns_dict(mock_bridge):
    result = mock_bridge.quit()
    assert isinstance(result, dict)
    assert "success" in result
    assert "steps" in result


def test_quit_returns_14_steps(mock_bridge):
    result = mock_bridge.quit()
    assert len(result["steps"]) == 14


# ── Step 1: block_actions ──


def test_step1_block_actions(mock_bridge):
    assert mock_bridge._accepting_new
    result = mock_bridge.quit()
    assert not mock_bridge._accepting_new
    assert result["steps"][0]["step"] == "block_actions"
    assert result["steps"][0]["ok"] is True


# ── Step 2: cancel_navigation ──


def test_step2_cancel_navigation():
    nav = MagicMock()
    bridge = AppBridge()
    bridge.set_navigation_bridge(nav)
    result = bridge.quit()
    nav.clearHistory.assert_called_once()
    step = result["steps"][1]
    assert step["step"] == "cancel_navigation"


def test_step2_tolerates_no_navigation_bridge(bare_bridge):
    result = bare_bridge.quit()
    step = result["steps"][1]
    assert step["ok"] is True


# ── Step 3: cancel_queries ──


def test_step3_cancel_queries(mock_bridge):
    result = mock_bridge.quit()
    mock_bridge._qe.shutdown.assert_called_once_with(2000)
    step = result["steps"][2]
    assert step["step"] == "cancel_queries"


def test_step3_tolerates_no_query_executor(bare_bridge):
    result = bare_bridge.quit()
    step = result["steps"][2]
    assert step["ok"] is True


# ── Step 4: cancel_jobs ──


def test_step4_cancel_jobs(mock_bridge):
    result = mock_bridge.quit()
    mock_bridge._wm.cancel_all.assert_called_once()
    step = result["steps"][3]
    assert step["step"] == "cancel_jobs"


# ── Step 5: terminate_subprocesses ──


def test_step5_terminate_subprocesses():
    proc = MagicMock()
    bridge = AppBridge()
    bridge.track_external_process(proc)
    bridge.quit()
    proc.terminate.assert_called_once()
    proc.wait.assert_called_once_with(timeout=2)


def test_step5_no_subprocesses(bare_bridge):
    step = bare_bridge.quit()["steps"][4]
    assert step["step"] == "terminate_subprocesses"


# ── Step 6: persist_queue ──


def test_step6_persist_queue_via_service(mock_bridge):
    step = mock_bridge.quit()["steps"][5]
    assert step["step"] == "persist_queue"


def test_step6_no_queue_service(bare_bridge):
    result = bare_bridge.quit()
    step = result["steps"][5]
    assert step["ok"] is True


# ── Step 7: persist_page_state ──


def test_step7_persist_page_state(mock_bridge):
    result = mock_bridge.quit()
    step = result["steps"][6]
    assert step["step"] == "persist_page_state"


# ── Step 8: stop_device_sync ──


def test_step8_stop_device_sync(mock_bridge):
    result = mock_bridge.quit()
    mock_bridge._sync_manager.stop.assert_called_once()
    step = result["steps"][7]
    assert step["step"] == "stop_device_sync"


def test_step8_tolerates_no_sync(bare_bridge):
    result = bare_bridge.quit()
    step = result["steps"][7]
    assert step["ok"] is True


# ── Step 9: stop_connections ──


def test_step9_stop_connections(mock_bridge):
    result = mock_bridge.quit()
    step = result["steps"][8]
    assert step["step"] == "stop_connections"


def test_step9_tolerates_no_discovery(bare_bridge):
    result = bare_bridge.quit()
    step = result["steps"][8]
    assert step["ok"] is True


# ── Step 10: stop_home_audio ──


def test_step10_stop_home_audio(mock_bridge):
    result = mock_bridge.quit()
    mock_bridge._home_audio_controller.stop.assert_called_once()
    step = result["steps"][9]
    assert step["step"] == "stop_home_audio"


def test_step10_tolerates_no_home_audio(bare_bridge):
    result = bare_bridge.quit()
    step = result["steps"][9]
    assert step["ok"] is True


# ── Step 11: stop_radio ──


def test_step11_stop_radio(mock_bridge):
    result = mock_bridge.quit()
    mock_bridge._radio_manager.stop.assert_called_once()
    step = result["steps"][10]
    assert step["step"] == "stop_radio"


def test_step11_tolerates_no_radio(bare_bridge):
    result = bare_bridge.quit()
    step = result["steps"][10]
    assert step["ok"] is True


# ── Step 12: stop_playback ──


def test_step12_stop_playback(mock_bridge):
    result = mock_bridge.quit()
    mock_bridge._player_service.stop.assert_called_once()
    step = result["steps"][11]
    assert step["step"] == "stop_playback"


def test_step12_tolerates_no_player(bare_bridge):
    result = bare_bridge.quit()
    step = result["steps"][11]
    assert step["ok"] is True


# ── Step 13: close_repositories ──


def test_step13_close_repositories(mock_bridge):
    result = mock_bridge.quit()
    step = result["steps"][12]
    assert step["step"] == "close_repositories"


def test_step13_tolerates_no_repositories(bare_bridge):
    result = bare_bridge.quit()
    step = result["steps"][12]
    assert step["ok"] is True


# ── Step 14: close_db ──


def test_step14_close_db(mock_bridge):
    result = mock_bridge.quit()
    mock_bridge._db.close.assert_called_once()
    step = result["steps"][13]
    assert step["step"] == "close_db"


def test_step14_tolerates_no_db(bare_bridge):
    result = bare_bridge.quit()
    step = result["steps"][13]
    assert step["ok"] is True


# ── Full sequence ──


def test_full_shutdown_sequence(mock_bridge):
    mock_bridge.setReady()
    assert mock_bridge.ready
    result =     mock_bridge.quit()
    assert mock_bridge._shutting_down
    assert not mock_bridge._accepting_new
    assert mock_bridge.phase == AppBridge.STOPPED
    assert result["success"] is True
    assert len(result["steps"]) == 14


def test_shutdown_completes_quickly(mock_bridge):
    start = time.time()
    mock_bridge.quit()
    elapsed = time.time() - start
    assert elapsed < 5.0


def test_double_quit_idempotent(mock_bridge):
    r2 = mock_bridge.quit()
    assert r2.get("success") is True
    mock_bridge._player_service.stop.assert_called_once()


def test_shutdown_phase_transitions(bare_bridge):
    assert bare_bridge.phase == AppBridge.BOOTSTRAP
    bare_bridge.setReady()
    assert bare_bridge.phase == AppBridge.READY
    bare_bridge.quit()
    assert bare_bridge.phase == AppBridge.STOPPED


def test_shutdown_handles_step_failures():
    wm = MagicMock()
    wm.cancel_all.side_effect = RuntimeError("wm cancel failed")
    bridge = AppBridge(worker_manager=wm)
    result = bridge.quit()
    assert len(result["steps"]) == 14


# ── ShutdownResult edge cases ──


def test_shutdown_result_empty():
    sr = ShutdownResult()
    assert sr.success is True
    assert sr.to_dict() == {"success": True, "steps": []}
