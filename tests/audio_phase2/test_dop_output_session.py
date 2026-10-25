"""AP2-F09 — DoP transaction lifecycle in the canonical output session."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from michi.application.audio_output_planner import OutputPlanner
from michi.application.output_session_service import (
    DopSessionPrepared,
    OutputRequest,
    OutputSessionError,
    OutputSessionService,
)
from michi.domain.audio_output import OutputSessionState
from tests.dop.test_dop_planner import _plan


class _Tx:
    def __init__(self, plan) -> None:
        self.plan = plan
        self.aborted: list[str] = []
        self.stopped: list[str] = []
        self.committed = 0
        self.fail_abort = False
        self.fail_stop = False

    def prepare(self, plan, path: Path, instance: str) -> DopSessionPrepared:
        return DopSessionPrepared(
            plan=plan,
            execution_id=plan.execution_id,
            stable_device_id=plan.stable_device_id,
            runtime_identity={"host_generation": plan.host_generation},
            evidence_refs=(),
        )

    def commit(self, prepared: DopSessionPrepared) -> None:
        self.committed += 1

    def abort(self, prepared: DopSessionPrepared, reason: str) -> dict[str, Any]:
        if self.fail_abort:
            raise RuntimeError("abort failed")
        self.aborted.append(reason)
        return {"aborted": True, "stale": False}

    def stop(self, prepared: DopSessionPrepared, reason: str) -> dict[str, Any]:
        if self.fail_stop:
            raise RuntimeError("stop failed")
        self.stopped.append(reason)
        return {"stopped": True, "stale": False}


def _session(plan, tx: _Tx) -> OutputSessionService:
    return OutputSessionService(
        OutputPlanner(),
        request_provider=lambda _path: OutputRequest.dop(plan, "profile:dop"),
        dop_prepare=tx.prepare,
        dop_commit=tx.commit,
        dop_abort=tx.abort,
        dop_stop=tx.stop,
        dop_plan_still_current=lambda _plan: True,
    )


def test_prepare_commit_playing_eos_stop(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    session = _session(plan, tx)
    token = session.prepare_for_media(tmp_path / "track.dsf")
    assert token.startswith("output-tx:dop:")
    assert session.state is OutputSessionState.READY
    assert session.mode == "dop"
    assert session.active_device_id == plan.stable_device_id
    assert session.active_execution_id == plan.execution_id
    session.commit_media(token, tmp_path / "track.dsf")
    assert session.state is OutputSessionState.RUNNING
    assert session.notify_dop_playing(plan.execution_id) is True
    assert session.notify_dop_playing(plan.execution_id) is False
    assert session.notify_dop_eos(plan.execution_id) is True
    assert session.notify_dop_eos(plan.execution_id) is False
    session.release_active("stop")
    assert tx.stopped == ["stop"]
    assert session.state is OutputSessionState.IDLE


def test_abort_failure_keeps_the_receipt(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    tx.fail_abort = True
    session = _session(plan, tx)
    token = session.prepare_for_media(tmp_path / "track.dsf")
    with pytest.raises(OutputSessionError) as info:
        session.abort_media(token, "load_failed")
    assert info.value.code == "DOP_ABORT_UNCONFIRMED"
    assert session._dop_prepared is not None


def test_new_prepare_aborts_the_previous_dop_session(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    session = _session(plan, tx)
    session.prepare_for_media(tmp_path / "one.dsf")
    session.prepare_for_media(tmp_path / "two.dsf")
    assert "superseded" in tx.aborted
    assert session.state is OutputSessionState.READY


def test_host_loss_marks_dop_terminal(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    session = _session(plan, tx)
    session.prepare_for_media(tmp_path / "track.dsf")
    session.notify_host_lost("host crashed")
    assert session._dop_terminal_execution == plan.execution_id
    assert session.notify_dop_eos(plan.execution_id) is False


def test_stop_failure_keeps_the_dop_receipt(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    session = _session(plan, tx)
    session.prepare_for_media(tmp_path / "track.dsf")
    tx.fail_stop = True
    with pytest.raises(OutputSessionError) as info:
        session.release_active("stop")
    assert info.value.code == "DOP_RELEASE_FAILED"
    assert session._dop_prepared is not None


def test_device_loss_invalidates_and_aborts_dop(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    session = _session(plan, tx)
    session.prepare_for_media(tmp_path / "track.dsf")
    session.device_lost(plan.stable_device_id, 99)
    assert "device_lost" in tx.aborted
    assert session._dop_prepared is None
