"""DAC-V35-040 — OutputSessionService gates (§0H.2/§21/§22/§403).

prepare/commit/abort/release, state machine, generation guard (callbacks
viejos descartados), selected vs active (§22) y Shared no-op.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from michi.application.audio_output_planner import OutputPlanner
from michi.application.output_session_service import (
    OutputSessionError,
    OutputSessionService,
    SharedOutputTransaction,
)
from michi.domain.audio_output import OutputPlan, OutputSessionState
from tests.dac.test_v34_output_planner import _facts


def _plan() -> OutputPlan:
    result = OutputPlanner().plan(_facts())
    assert isinstance(result, OutputPlan)
    return result


def _service() -> OutputSessionService:
    return OutputSessionService(OutputPlanner())


def test_prepare_commit_runs_session(tmp_path: Path) -> None:
    service = _service()
    token = service.prepare_for_media(_plan(), tmp_path / "a.flac")
    assert service.state is OutputSessionState.READY
    service.commit_media(token, tmp_path / "a.flac")
    assert service.state is OutputSessionState.RUNNING
    selection = service.selection_state()
    assert selection.active_plan_id == _plan().plan_id
    assert selection.active_device_id is not None


def test_abort_returns_to_idle_with_reason(tmp_path: Path) -> None:
    service = _service()
    token = service.prepare_for_media(_plan(), tmp_path / "a.flac")
    service.abort_media(token, "media_rejected")
    assert service.state is OutputSessionState.IDLE
    assert service.plan is None
    assert service.selection_state().error_code == "media_rejected"


def test_release_active_returns_to_idle(tmp_path: Path) -> None:
    service = _service()
    token = service.prepare_for_media(_plan(), tmp_path / "a.flac")
    service.commit_media(token, tmp_path / "a.flac")
    service.release_active("stop")
    assert service.state is OutputSessionState.IDLE
    assert service.plan is None


def test_stale_generation_callbacks_are_discarded(tmp_path: Path) -> None:
    service = _service()
    stale = service.prepare_for_media(_plan(), tmp_path / "a.flac")
    service.release_active("stop")
    fresh = service.prepare_for_media(_plan(), tmp_path / "b.flac")
    assert fresh != stale
    # El commit del token viejo NO debe mutar la sesión nueva.
    service.commit_media(stale, tmp_path / "a.flac")
    assert service.state is OutputSessionState.READY, (
        "callbacks de generations viejas se descartan"
    )
    service.commit_media(fresh, tmp_path / "b.flac")
    assert service.state is OutputSessionState.RUNNING


def test_device_lost_preserves_selected_and_clears_active(tmp_path: Path) -> None:
    service = _service()
    service.select(device_id="usb:2622:0105:DX5ABC123", profile_id="p1")
    token = service.prepare_for_media(_plan(), tmp_path / "a.flac")
    service.commit_media(token, tmp_path / "a.flac")
    service.device_lost()
    selection = service.selection_state()
    assert service.state is OutputSessionState.LOST
    assert selection.selected_device_id == "usb:2622:0105:DX5ABC123", (
        "el selected sobrevive a la desaparición (§22)"
    )
    assert selection.active_device_id is None
    assert selection.active_plan_id is None


def test_illegal_transition_raises() -> None:
    service = _service()
    with pytest.raises(OutputSessionError) as exc_info:
        service.commit_media("output-tx:None:0", Path("x.flac"))
    assert exc_info.value.code == "illegal_transition"


def test_reprepare_from_ready_reconfigures(tmp_path: Path) -> None:
    service = _service()
    first = service.prepare_for_media(_plan(), tmp_path / "a.flac")
    second = service.prepare_for_media(_plan(), tmp_path / "b.flac")
    assert second != first
    assert service.state is OutputSessionState.READY


def test_fail_records_error_code() -> None:
    service = _service()
    service.fail("device_removed")
    assert service.state is OutputSessionState.FAILED
    assert service.selection_state().error_code == "device_removed"


def test_shared_transaction_is_noop_with_truthful_mode(tmp_path: Path) -> None:
    shared = SharedOutputTransaction()
    assert shared.mode == "shared"
    token = shared.prepare_for_media(tmp_path / "a.flac")
    shared.commit_media(token, tmp_path / "a.flac")
    shared.abort_media(token, "x")
    shared.release_active("y")
    assert token == "shared:noop"
