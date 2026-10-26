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
from michi.domain.signal_truth import OutputFamilyState
from tests.dop.test_dop_planner import _plan


class _Tx:
    def __init__(self, plan) -> None:
        self.plan = plan
        self.aborted: list[str] = []
        self.stopped: list[str] = []
        self.committed = 0
        self.fail_abort = False
        self.fail_stop = False
        self.abort_result: dict[str, Any] | None = None

    @staticmethod
    def _receipt(prepared: DopSessionPrepared, operation: str) -> dict[str, Any]:
        plan = prepared.plan
        return {
            "confirmed": True,
            "operation": operation,
            "plan_id": plan.plan_id,
            "execution_id": plan.execution_id,
            "stable_device_id": plan.stable_device_id,
            "device": plan.binding_locator,
            "binding_generation": plan.binding_generation,
            "host_generation": plan.host_generation,
            "terminal_state": "RELEASED",
            "provenance": "SUPERVISED_HOST",
        }

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
        if self.abort_result is not None:
            return dict(self.abort_result)
        return {
            "aborted": True,
            "stale": False,
            "execution_id": prepared.execution_id,
            "release": self._receipt(prepared, "abort"),
        }

    def stop(self, prepared: DopSessionPrepared, reason: str) -> dict[str, Any]:
        if self.fail_stop:
            raise RuntimeError("stop failed")
        self.stopped.append(reason)
        return {
            "stopped": True,
            "stale": False,
            "execution_id": prepared.execution_id,
            "release": self._receipt(prepared, "stop"),
        }


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


class _Recorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, OutputFamilyState]] = []

    def activate_execution(self, *_args, **_kwargs) -> None:
        return

    def record_output_family_event(self, event) -> None:
        self.events.append((event.family, event.state))


def test_dop_active_is_readable_and_truth_waits_for_playing(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    recorder = _Recorder()
    session = OutputSessionService(
        OutputPlanner(),
        request_provider=lambda _path: OutputRequest.dop(plan, "profile:dop"),
        dop_prepare=tx.prepare,
        dop_commit=tx.commit,
        dop_abort=tx.abort,
        dop_stop=tx.stop,
        dop_plan_still_current=lambda _plan: True,
        truth_recorder=recorder,
    )
    assert session.dop_active is False
    token = session.prepare_for_media(tmp_path / "track.dsf")
    assert session.dop_active is True
    assert ("dop", OutputFamilyState.READY) in recorder.events
    session.commit_media(token, tmp_path / "track.dsf")
    assert ("dop", OutputFamilyState.RUNNING) not in recorder.events
    assert session.notify_dop_playing(plan.execution_id) is True
    assert recorder.events.count(("dop", OutputFamilyState.RUNNING)) == 1
    session.release_active("stop")
    assert session.dop_active is False


def test_release_without_stop_authority_is_not_released(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    session = OutputSessionService(
        OutputPlanner(),
        request_provider=lambda _path: OutputRequest.dop(plan, "profile:dop"),
        dop_prepare=tx.prepare,
        dop_commit=tx.commit,
        dop_abort=tx.abort,
        dop_plan_still_current=lambda _plan: True,
    )
    session.prepare_for_media(tmp_path / "track.dsf")
    with pytest.raises(OutputSessionError) as info:
        session.release_active("stop")
    assert info.value.code == "DOP_RELEASE_UNAVAILABLE"
    assert session._dop_prepared is not None


def test_supersession_abort_failure_keeps_current_session(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    tx.fail_abort = True
    session = _session(plan, tx)
    session.prepare_for_media(tmp_path / "one.dsf")
    with pytest.raises(OutputSessionError) as info:
        session.prepare_for_media(tmp_path / "two.dsf")
    assert info.value.code == "DOP_SUPERSESSION_UNCONFIRMED"
    assert session._dop_prepared is not None


def _native_prepared():
    from types import SimpleNamespace

    return SimpleNamespace(
        plan=SimpleNamespace(plan_id="native:plan", stable_device_id="dev:dac"),
        execution_id="exec:native",
        stable_device_id="dev:dac",
        runtime_identity={},
        handle=None,
    )


def _managed_prepared():
    from types import SimpleNamespace

    return SimpleNamespace(
        plan=SimpleNamespace(
            plan_id="managed:plan",
            stable_device_id="dev:dac",
            processing_plan_id=None,
            transform_policy=(),
        ),
        execution_id="exec:managed",
        runtime_identity={},
    )


def test_dop_to_native_requires_confirmed_cleanup(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    tx.fail_abort = True
    session = _session(plan, tx)
    session.prepare_for_media(tmp_path / "track.dsf")
    native_aborts: list[str] = []
    session._native_dsd_prepared = _native_prepared()
    session._native_dsd_plan = session._native_dsd_prepared.plan
    session._native_dsd_abort = lambda _prepared, reason: (
        native_aborts.append(reason) or {"aborted": True}
    )
    with pytest.raises(OutputSessionError) as info:
        session._begin_native_dsd_session(
            tmp_path / "track.dsf",
            OutputRequest.dop(plan, "profile:dop"),
            _native_prepared(),
            previous_direct=None,
        )
    assert info.value.code == "OUTPUT_OWNERSHIP_UNCONFIRMED"
    assert session._dop_prepared is not None
    assert session.mode == "dop"
    assert native_aborts == []


def test_dop_to_native_aborts_then_switches(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    session = _session(plan, tx)
    session.prepare_for_media(tmp_path / "track.dsf")
    native = _native_prepared()
    session._native_dsd_prepared = native
    session._native_dsd_plan = native.plan
    session._native_dsd_abort = lambda _prepared, reason: {"aborted": True}
    session._begin_native_dsd_session(
        tmp_path / "track.dsf",
        OutputRequest.dop(plan, "profile:dop"),
        native,
        previous_direct=None,
    )
    assert "superseded_by_native_dsd" in tx.aborted
    assert session._dop_prepared is None
    assert session.mode == "native_dsd"


def test_dop_to_managed_requires_confirmed_cleanup(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    tx.fail_abort = True
    session = _session(plan, tx)
    session.prepare_for_media(tmp_path / "track.dsf")
    managed = _managed_prepared()
    session._managed_prepared = managed
    session._managed_plan = managed.plan
    session._managed_abort = lambda _prepared, _reason: {"stopped": True}
    with pytest.raises(OutputSessionError) as info:
        session._begin_managed_session(
            tmp_path / "track.dsf",
            OutputRequest.dop(plan, "profile:dop"),
            managed,
            previous_direct=None,
        )
    assert info.value.code == "OUTPUT_OWNERSHIP_UNCONFIRMED"
    assert session._dop_prepared is not None
    assert session.mode == "dop"


def test_direct_to_dop_requires_confirmed_release(tmp_path: Path) -> None:
    from types import SimpleNamespace

    class _Executor:
        def release(self, _reason: str) -> None:
            raise RuntimeError("direct release failed")

    plan = _plan()
    tx = _Tx(plan)
    session = _session(plan, tx)
    previous = SimpleNamespace(
        plan=SimpleNamespace(stable_device_id="dev:dac"),
        executor=_Executor(),
        receipt="direct:receipt",
        state=OutputSessionState.RUNNING,
        path=tmp_path / "old.wav",
        selected_device_id="dev:dac",
        selected_profile_id="profile:direct",
    )
    prepared = tx.prepare(plan, tmp_path / "track.dsf", "instance")
    with pytest.raises(OutputSessionError) as info:
        session._begin_dop_session(
            tmp_path / "track.dsf",
            OutputRequest.dop(plan, "profile:dop"),
            prepared,
            previous_direct=previous,
        )
    assert info.value.code == "OUTPUT_OWNERSHIP_UNCONFIRMED"
    assert session._dop_prepared is None
    assert session.last_cleanup_diagnostic is not None


def test_native_to_dop_requires_confirmed_cleanup(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    session = _session(plan, tx)
    native = _native_prepared()
    session._native_dsd_prepared = native
    session._native_dsd_plan = native.plan
    session._native_dsd_abort = lambda _prepared, _reason: {
        "aborted": False,
        "stale": False,
    }
    prepared = tx.prepare(plan, tmp_path / "track.dsf", "instance")
    with pytest.raises(OutputSessionError) as info:
        session._begin_dop_session(
            tmp_path / "track.dsf",
            OutputRequest.dop(plan, "profile:dop"),
            prepared,
            previous_direct=None,
        )
    assert info.value.code == "OUTPUT_OWNERSHIP_UNCONFIRMED"
    assert session._native_dsd_prepared is native
    assert session._dop_prepared is None


def test_managed_to_dop_requires_confirmed_cleanup(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    session = _session(plan, tx)
    managed = _managed_prepared()
    session._managed_prepared = managed
    session._managed_plan = managed.plan
    session._managed_abort = lambda _prepared, _reason: {
        "stopped": False,
        "stale": False,
    }
    prepared = tx.prepare(plan, tmp_path / "track.dsf", "instance")
    with pytest.raises(OutputSessionError) as info:
        session._begin_dop_session(
            tmp_path / "track.dsf",
            OutputRequest.dop(plan, "profile:dop"),
            prepared,
            previous_direct=None,
        )
    assert info.value.code == "OUTPUT_OWNERSHIP_UNCONFIRMED"
    assert session._managed_prepared is managed
    assert session._dop_prepared is None


def test_abort_retry_after_failure_can_confirm(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    tx.fail_abort = True
    session = _session(plan, tx)
    token = session.prepare_for_media(tmp_path / "track.dsf")
    with pytest.raises(OutputSessionError):
        session.abort_media(token, "load_failed")
    assert session._dop_prepared is not None
    tx.fail_abort = False
    session.abort_media(token, "retry")
    assert session._dop_prepared is None
    assert "retry" in tx.aborted


def test_quiet_cleanup_retains_unconfirmed_receipt(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    tx.fail_abort = True
    session = _session(plan, tx)
    session.prepare_for_media(tmp_path / "track.dsf")
    prepared = session._dop_prepared
    session._dop_abort_quietly(prepared, "superseded_before_commit")
    assert session._unconfirmed_cleanup == ("dop", prepared)
    assert session.last_cleanup_diagnostic is not None


def test_unconfirmed_cleanup_blocks_new_acquisition_until_retry(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    tx.fail_abort = True
    session = _session(plan, tx)
    session.prepare_for_media(tmp_path / "track.dsf")
    prepared = session._dop_prepared
    session._dop_abort_quietly(prepared, "superseded_before_commit")
    assert session.pending_cleanup == ("dop", prepared)
    with pytest.raises(OutputSessionError) as info:
        session.prepare_for_media(tmp_path / "blocked.dsf")
    assert info.value.code == "OUTPUT_OWNERSHIP_UNCONFIRMED"

    tx.fail_abort = False
    assert session.retry_pending_cleanup() is True
    assert session.pending_cleanup is None
    token = session.prepare_for_media(tmp_path / "allowed.dsf")
    assert token.startswith("output-tx:dop:")
    assert session.pending_cleanup is None


def test_async_prepare_fails_closed_on_unconfirmed_cleanup(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    tx.fail_abort = True
    session = _session(plan, tx)
    session.prepare_for_media(tmp_path / "track.dsf")
    prepared = session._dop_prepared
    session._dop_abort_quietly(prepared, "superseded_before_commit")

    events: list[tuple[str, object]] = []
    session.prepare_for_media_async(
        tmp_path / "blocked-async.dsf",
        lambda token: events.append(("prepared", token)),
        lambda exc: events.append(("failed", exc)),
    )

    assert events and events[0][0] == "failed"
    error = events[0][1]
    assert isinstance(error, OutputSessionError)
    assert error.code == "OUTPUT_OWNERSHIP_UNCONFIRMED"
    assert session.pending_cleanup == ("dop", prepared)


def test_async_prepare_fails_closed_on_pending_cleanup(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    tx.fail_abort = True
    session = _session(plan, tx)
    session.prepare_for_media(tmp_path / "track.dsf")
    prepared = session._dop_prepared
    session._dop_abort_quietly(prepared, "superseded_before_commit")
    errors: list[Exception] = []

    session.prepare_for_media_async(
        tmp_path / "blocked.dsf", lambda _token: None, errors.append
    )

    assert session.pending_cleanup == ("dop", prepared)
    assert len(errors) == 1
    assert getattr(errors[0], "code", None) == "OUTPUT_OWNERSHIP_UNCONFIRMED"


def test_device_loss_is_lost_even_when_abort_is_unconfirmed(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    tx.fail_abort = True
    recorder = _Recorder()
    session = OutputSessionService(
        OutputPlanner(),
        request_provider=lambda _path: OutputRequest.dop(plan, "profile:dop"),
        dop_prepare=tx.prepare,
        dop_commit=tx.commit,
        dop_abort=tx.abort,
        dop_stop=tx.stop,
        dop_plan_still_current=lambda _plan: True,
        truth_recorder=recorder,
    )
    session.prepare_for_media(tmp_path / "track.dsf")
    token = session._token_value
    session.commit_media(token, tmp_path / "track.dsf")
    prepared = session._dop_prepared

    session.device_lost(plan.stable_device_id, 7)

    assert session.state is OutputSessionState.LOST
    assert session.mode == "lost"
    assert session._error_code == "device_lost"
    assert session._dop_prepared is None
    assert session._dop_plan is None
    assert session._dop_playing_execution is None
    assert session._dop_terminal_execution == plan.execution_id
    assert session.pending_cleanup == ("dop", prepared)
    assert session.last_cleanup_diagnostic is not None
    assert not any(
        event == ("dop", OutputFamilyState.RELEASED) for event in recorder.events
    )
    assert session.notify_dop_eos(plan.execution_id) is False


def test_retry_reconciles_the_logical_dop_session(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    tx.fail_abort = True
    session = _session(plan, tx)
    token = session.prepare_for_media(tmp_path / "track.dsf")
    session.commit_media(token, tmp_path / "track.dsf")
    session.notify_dop_playing(plan.execution_id)
    prepared = session._dop_prepared
    session._dop_abort_quietly(prepared, "superseded_before_commit")
    assert session.pending_cleanup == ("dop", prepared)
    assert session._dop_playing_execution == plan.execution_id

    tx.fail_abort = False
    assert session.retry_pending_cleanup() is True

    assert session.pending_cleanup is None
    assert session._dop_prepared is None
    assert session._dop_plan is None
    assert session._dop_playing_execution is None
    assert session._token_value is None
    assert session.state is OutputSessionState.IDLE
    assert session.notify_dop_playing(plan.execution_id) is False
    assert session.prepare_for_media(tmp_path / "next.dsf").startswith("output-tx:dop:")


def test_device_loss_retry_keeps_lost_until_newer_binding(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    tx.fail_abort = True
    session = _session(plan, tx)
    token = session.prepare_for_media(tmp_path / "track.dsf")
    session.commit_media(token, tmp_path / "track.dsf")
    session.device_lost(plan.stable_device_id, 7)
    assert session.state is OutputSessionState.LOST
    assert session.pending_cleanup is not None
    assert session.rebind_after_topology_change(plan.stable_device_id, 8) is False

    tx.fail_abort = False
    assert session.retry_pending_cleanup() is True

    assert session.state is OutputSessionState.LOST
    assert session.mode == "lost"
    assert session.pending_cleanup is None
    assert session._dop_terminal_execution is None
    assert session.rebind_after_topology_change(plan.stable_device_id, 7) is False
    assert session.rebind_after_topology_change(plan.stable_device_id, 8) is True
    assert session.state is OutputSessionState.IDLE


def test_second_cleanup_failure_does_not_replace_the_first_receipt(
    tmp_path: Path,
) -> None:
    plan = _plan()
    tx = _Tx(plan)
    tx.fail_abort = True
    session = _session(plan, tx)
    session.prepare_for_media(tmp_path / "track.dsf")
    first = session._dop_prepared
    session._dop_abort_quietly(first, "first")

    newer = tx.prepare(plan, tmp_path / "newer.dsf", "instance")
    session._retain_pending_cleanup("dop", newer)

    assert session.pending_cleanup == ("dop", first)
    assert session.last_cleanup_diagnostic is not None


def test_stale_abort_evidence_is_not_treated_as_release(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    tx.abort_result = {"aborted": True, "stale": True}
    session = _session(plan, tx)
    session.prepare_for_media(tmp_path / "track.dsf")
    prepared = session._dop_prepared

    assert session._dop_abort_quietly(prepared, "cleanup_retry") is False

    assert session.pending_cleanup == ("dop", prepared)
    assert session._dop_prepared is prepared


def test_generic_already_without_execution_identity_is_not_release(
    tmp_path: Path,
) -> None:
    plan = _plan()
    tx = _Tx(plan)
    tx.abort_result = {"aborted": True, "already": True, "stale": False}
    session = _session(plan, tx)
    session.prepare_for_media(tmp_path / "track.dsf")
    prepared = session._dop_prepared

    assert session._dop_abort_quietly(prepared, "cleanup_retry") is False

    assert session.pending_cleanup == ("dop", prepared)
    assert session._dop_prepared is prepared


def test_stop_identity_is_required_for_release(tmp_path: Path) -> None:
    plan = _plan()
    tx = _Tx(plan)
    session = _session(plan, tx)
    path = tmp_path / "track.dsf"
    token = session.prepare_for_media(path)
    prepared = session._dop_prepared
    assert prepared is not None
    session.commit_media(token, path)

    def unproven_stop(_prepared, _reason):
        return {"stopped": True, "stale": False}

    session._dop_stop = unproven_stop
    with pytest.raises(OutputSessionError, match="DOP_RELEASE_UNCONFIRMED"):
        session.release_active("stop")
    assert session._dop_prepared is prepared
