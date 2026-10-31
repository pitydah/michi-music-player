"""AP2-F10 — owner-safe async handover.

C1 classification: an async preparation whose target family differs from the
committed one may CHARACTERIZE the request off-owner, but it must never read
live ``OutputSessionService`` ownership to release the predecessor, and it must
never physically prepare the target from that worker phase. The historical fast
path (no incompatible predecessor) keeps one worker and one completion.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from michi.application.audio_output_planner import OutputPlanner
from michi.application.dsd_to_pcm_plan import DsdToPcmPlanner
from michi.application.output_session_service import (
    DopSessionPrepared,
    DsdPcmSessionPrepared,
    HandoverState,
    OutputRequest,
    OutputSessionService,
)
from michi.domain.audio_output import OutputSessionState
from michi.domain.dsd_signal import (
    DsdBitOrder,
    DsdOrganization,
    DsdPacking,
    DsdSignalFormat,
)
from tests.dop.test_dop_planner import _plan as _dop_plan


class _Deferred:
    """Deterministic async boundary: nothing runs until the test drives it."""

    def __init__(self) -> None:
        self.pending: list[tuple[Any, Any]] = []

    def submit(self, work, completed) -> None:
        self.pending.append((work, completed))

    def run_one(self) -> None:
        work, completed = self.pending.pop(0)
        try:
            value = work()
        except Exception as exc:  # noqa: BLE001 - test boundary
            completed(None, exc)
        else:
            completed(value, None)

    def drive(self, limit: int = 8) -> None:
        while self.pending and limit > 0:
            self.run_one()
            limit -= 1


class _Tx:
    """Fake host transaction recording exact physical commands."""

    def __init__(self) -> None:
        self.aborted: list[tuple[str, str, str]] = []
        self.stopped: list[tuple[str, str, str]] = []
        self.dop_prepare_calls = 0
        self.dsd_pcm_prepare_calls = 0

    @staticmethod
    def _dop_receipt(prepared: DopSessionPrepared, operation: str) -> dict[str, Any]:
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

    @staticmethod
    def _dsd_receipt(
        prepared: DsdPcmSessionPrepared, operation: str
    ) -> dict[str, Any]:
        plan = prepared.plan
        return {
            "confirmed": True,
            "operation": operation,
            "plan_id": plan.plan_id,
            "execution_id": prepared.execution_id,
            "stable_device_id": prepared.stable_device_id,
            "device": prepared.binding_locator,
            "binding_generation": plan.binding_generation,
            "host_generation": prepared.host_generation,
            "terminal_state": "RELEASED",
            "provenance": "SUPERVISED_HOST",
        }

    def dop_prepare(self, plan, path: Path, instance: str) -> DopSessionPrepared:
        self.dop_prepare_calls += 1
        return DopSessionPrepared(
            plan=plan,
            execution_id=plan.execution_id,
            stable_device_id=plan.stable_device_id,
            runtime_identity={"host_generation": plan.host_generation},
            evidence_refs=(),
        )

    def dop_commit(self, _prepared: DopSessionPrepared) -> None:
        return

    def dop_abort(self, prepared: DopSessionPrepared, reason: str) -> dict[str, Any]:
        self.aborted.append(("dop", prepared.execution_id, reason))
        return {
            "aborted": True,
            "stale": False,
            "execution_id": prepared.execution_id,
            "release": self._dop_receipt(prepared, "abort"),
        }

    def dop_stop(self, prepared: DopSessionPrepared, reason: str) -> dict[str, Any]:
        self.stopped.append(("dop", prepared.execution_id, reason))
        return {
            "stopped": True,
            "stale": False,
            "execution_id": prepared.execution_id,
            "release": self._dop_receipt(prepared, "stop"),
        }

    def dsd_pcm_prepare(self, plan, path: Path, instance: str) -> DsdPcmSessionPrepared:
        self.dsd_pcm_prepare_calls += 1
        return DsdPcmSessionPrepared(
            plan=plan,
            execution_id=instance,
            stable_device_id=plan.stable_device_id,
            binding_locator=plan.binding_locator,
            host_generation=plan.host_generation,
            runtime_identity={"plan_id": plan.plan_id, "execution_id": instance},
            evidence_refs=(),
            handle={"execution_id": instance},
        )

    def dsd_pcm_commit(self, _prepared: DsdPcmSessionPrepared) -> None:
        return

    def dsd_pcm_abort(
        self, prepared: DsdPcmSessionPrepared, reason: str
    ) -> dict[str, Any]:
        self.aborted.append(("dsd_pcm", prepared.execution_id, reason))
        return {
            "aborted": True,
            "stale": False,
            "execution_id": prepared.execution_id,
            "release": self._dsd_receipt(prepared, "abort"),
        }

    def dsd_pcm_stop(
        self, prepared: DsdPcmSessionPrepared, reason: str
    ) -> dict[str, Any]:
        self.stopped.append(("dsd_pcm", prepared.execution_id, reason))
        return {
            "stopped": True,
            "stale": False,
            "execution_id": prepared.execution_id,
            "release": self._dsd_receipt(prepared, "stop"),
        }


def _dsd_pcm_plan():
    return DsdToPcmPlanner().plan(
        source_identity="track:handover",
        source_format=DsdSignalFormat(
            bit_rate_hz=2_822_400,
            channels=2,
            packing=DsdPacking.DSD_U8,
            bit_order=DsdBitOrder.LSBF,
            organization=DsdOrganization.PLANAR,
            layout=("FL", "FR"),
        ),
        quality_profile="FAST",
        binding_generation=1,
        available_output_rates=(88_200,),
        decoder_available=True,
        target_qualified=True,
        stable_device_id="dev:handover",
        binding_locator="hw:0,0",
        host_generation=1,
    )


def _session(requests: dict[str, OutputRequest], tx: _Tx, deferred: _Deferred):
    def request_for(path: Path) -> OutputRequest:
        return requests[path.name]

    return OutputSessionService(
        OutputPlanner(),
        request_provider=request_for,
        async_submit=deferred.submit,
        dop_prepare=tx.dop_prepare,
        dop_commit=tx.dop_commit,
        dop_abort=tx.dop_abort,
        dop_stop=tx.dop_stop,
        dop_plan_still_current=lambda _plan: True,
        dsd_pcm_prepare=tx.dsd_pcm_prepare,
        dsd_pcm_commit=tx.dsd_pcm_commit,
        dsd_pcm_abort=tx.dsd_pcm_abort,
        dsd_pcm_stop=tx.dsd_pcm_stop,
        dsd_pcm_plan_still_current=lambda _plan: True,
    )


def test_obsolete_async_request_never_releases_the_current_execution(
    tmp_path: Path,
) -> None:
    """A stale worker must never release the execution a newer request owns."""
    dop_one = _dop_plan(execution_id="exec:1")
    dop_two = _dop_plan(execution_id="exec:2")
    dsd_plan = _dsd_pcm_plan()
    requests = {
        "predecessor.dsf": OutputRequest.dop(dop_one, "profile:dop"),
        "stale.dsf": OutputRequest.dsd_to_pcm(
            dsd_plan, dsd_plan.stable_device_id, "profile:dsd"
        ),
        "current.dsf": OutputRequest.dop(dop_two, "profile:dop"),
    }
    tx = _Tx()
    deferred = _Deferred()
    session = _session(requests, tx, deferred)

    # A: the device is owned by DoP execution 1.
    session.prepare_for_media(tmp_path / "predecessor.dsf")
    assert session.mode == "dop"

    # A stale async request for a different family is submitted and held.
    tokens: list[str] = []
    failures: list[Exception] = []
    session.prepare_for_media_async(
        tmp_path / "stale.dsf", tokens.append, failures.append
    )

    # B: a newer request replaces the intent and commits DoP execution 2.
    session.prepare_for_media(tmp_path / "current.dsf")
    current = session._dop_prepared
    assert current is not None
    assert current.execution_id == "exec:2"

    # The obsolete worker finally runs: it must not touch B.
    deferred.run_one()

    assert ("dop", "exec:2", "handover_to_dsd_pcm") not in tx.aborted
    assert session._dop_prepared is current
    assert tx.dsd_pcm_prepare_calls == 0
    assert [getattr(error, "code", None) for error in failures] == [
        "OUTPUT_PREPARATION_STALE"
    ]
    assert tokens == []


def test_handover_releases_predecessor_before_target_prepare(
    tmp_path: Path,
) -> None:
    """Phase one only characterizes; the owner drives RELEASE before PREPARE."""
    dop_one = _dop_plan(execution_id="exec:1")
    dsd_plan = _dsd_pcm_plan()
    requests = {
        "predecessor.dsf": OutputRequest.dop(dop_one, "profile:dop"),
        "target.dsf": OutputRequest.dsd_to_pcm(
            dsd_plan, dsd_plan.stable_device_id, "profile:dsd"
        ),
    }
    tx = _Tx()
    deferred = _Deferred()
    session = _session(requests, tx, deferred)

    session.prepare_for_media(tmp_path / "predecessor.dsf")
    assert session._dop_prepared is not None

    tokens: list[str] = []
    failures: list[Exception] = []
    session.prepare_for_media_async(
        tmp_path / "target.dsf", tokens.append, failures.append
    )

    # Phase one: characterization only, nothing destructive.
    deferred.run_one()
    assert tx.aborted == []
    assert tx.dsd_pcm_prepare_calls == 0
    assert session._dop_prepared is not None
    assert session.mode == "dop"
    assert tokens == []
    assert failures == []

    # Owner transaction: RELEASE → RECONCILE → PREPARE → READY.
    deferred.drive()
    assert tx.aborted == [("dop", "exec:1", "handover_to_dsd_pcm")]
    assert tx.dsd_pcm_prepare_calls == 1
    assert failures == []
    assert len(tokens) == 1
    assert session.state is OutputSessionState.READY
    assert session.mode == "dsd_pcm"
    assert session.dop_active is False
    assert session.handover_state is HandoverState.READY
    assert session.handover_target_family == "dsd_pcm"
    evidence = session.last_handover_release_evidence
    assert evidence is not None
    assert evidence["confirmed"] is True
    assert evidence["execution_id"] == "exec:1"
    assert evidence["attempt_id"] == session.handover_attempt_id
    assert evidence["target_family"] == "dsd_pcm"


def test_fast_path_keeps_one_worker_one_completion_and_no_release(
    tmp_path: Path,
) -> None:
    """No incompatible predecessor: the historical fast path is untouched."""
    dsd_plan = _dsd_pcm_plan()
    requests = {
        "target.dsf": OutputRequest.dsd_to_pcm(
            dsd_plan, dsd_plan.stable_device_id, "profile:dsd"
        ),
    }
    tx = _Tx()
    deferred = _Deferred()
    session = _session(requests, tx, deferred)

    tokens: list[str] = []
    failures: list[Exception] = []
    session.prepare_for_media_async(
        tmp_path / "target.dsf", tokens.append, failures.append
    )

    assert len(deferred.pending) == 1
    assert tokens == []
    deferred.run_one()

    assert failures == []
    assert len(tokens) == 1
    assert tx.aborted == []
    assert tx.dsd_pcm_prepare_calls == 1
    assert session.state is OutputSessionState.READY
    assert session.mode == "dsd_pcm"
    assert session.handover_state is None


def test_same_family_async_replacement_releases_the_active_execution(
    tmp_path: Path,
) -> None:
    """A new quality/device plan must release the active same-family execution.

    The host refuses a second prepare while an execution is active
    (``DSD_PCM_HOST_SUPERSESSION_UNAUTHORIZED``), so a same-family replacement
    is a destructive handover too, not a fast-path prepare.
    """
    dop_one = _dop_plan(execution_id="exec:1")
    dop_two = _dop_plan(execution_id="exec:2")
    requests = {
        "one.dsf": OutputRequest.dop(dop_one, "profile:dop"),
        "two.dsf": OutputRequest.dop(dop_two, "profile:dop"),
    }
    tx = _Tx()
    deferred = _Deferred()
    session = _session(requests, tx, deferred)

    session.prepare_for_media(tmp_path / "one.dsf")
    tokens: list[str] = []
    failures: list[Exception] = []
    session.prepare_for_media_async(
        tmp_path / "two.dsf", tokens.append, failures.append
    )

    # Phase one only characterizes: the active execution stays untouched.
    deferred.run_one()
    assert tx.aborted == []
    assert tx.dop_prepare_calls == 1
    assert tokens == []
    assert failures == []

    # The owner releases execution 1 before preparing execution 2.
    deferred.drive()
    assert tx.aborted == [("dop", "exec:1", "handover_to_dop")]
    assert tx.dop_prepare_calls == 2
    assert failures == []
    assert len(tokens) == 1
    assert session._dop_prepared is not None
    assert session._dop_prepared.execution_id == "exec:2"
    assert session.state is OutputSessionState.READY
    assert session.mode == "dop"
    assert session.handover_state is HandoverState.READY
    assert session.handover_target_family == "dop"


def test_reverse_handover_from_dsd_pcm_to_dop(tmp_path: Path) -> None:
    """E2E-B direction at the transaction boundary: DSD→PCM → DoP."""
    dop_target = _dop_plan(execution_id="exec:dop")
    dsd_plan = _dsd_pcm_plan()
    requests = {
        "predecessor.dsf": OutputRequest.dsd_to_pcm(
            dsd_plan, dsd_plan.stable_device_id, "profile:dsd"
        ),
        "target.dsf": OutputRequest.dop(dop_target, "profile:dop"),
    }
    tx = _Tx()
    deferred = _Deferred()
    session = _session(requests, tx, deferred)

    session.prepare_for_media(tmp_path / "predecessor.dsf")
    predecessor = session._dsd_pcm_prepared
    assert predecessor is not None
    assert session.mode == "dsd_pcm"

    tokens: list[str] = []
    failures: list[Exception] = []
    session.prepare_for_media_async(
        tmp_path / "target.dsf", tokens.append, failures.append
    )
    deferred.run_one()
    assert tx.aborted == []
    assert tx.dop_prepare_calls == 0
    assert session._dsd_pcm_prepared is predecessor

    deferred.drive()
    assert tx.aborted == [
        ("dsd_pcm", predecessor.execution_id, "handover_to_dop")
    ]
    assert tx.dop_prepare_calls == 1
    assert failures == []
    assert len(tokens) == 1
    assert session.state is OutputSessionState.READY
    assert session.mode == "dop"
    assert session.dsd_pcm_active is False
    assert session.handover_state is HandoverState.READY


def test_preflight_failure_never_releases_the_predecessor(
    tmp_path: Path,
) -> None:
    """Missing target backend rejects BEFORE the destructive boundary."""
    dop_one = _dop_plan(execution_id="exec:1")
    dsd_plan = _dsd_pcm_plan()
    requests = {
        "predecessor.dsf": OutputRequest.dop(dop_one, "profile:dop"),
        "target.dsf": OutputRequest.dsd_to_pcm(
            dsd_plan, dsd_plan.stable_device_id, "profile:dsd"
        ),
    }
    tx = _Tx()
    deferred = _Deferred()

    def request_for(path: Path) -> OutputRequest:
        return requests[path.name]

    session = OutputSessionService(
        OutputPlanner(),
        request_provider=request_for,
        async_submit=deferred.submit,
        dop_prepare=tx.dop_prepare,
        dop_commit=tx.dop_commit,
        dop_abort=tx.dop_abort,
        dop_stop=tx.dop_stop,
        dop_plan_still_current=lambda _plan: True,
        # No DSD→PCM preparation authority is composed.
        dsd_pcm_plan_still_current=lambda _plan: True,
    )
    session.prepare_for_media(tmp_path / "predecessor.dsf")
    assert session._dop_prepared is not None

    tokens: list[str] = []
    failures: list[Exception] = []
    session.prepare_for_media_async(
        tmp_path / "target.dsf", tokens.append, failures.append
    )
    deferred.drive()

    assert tx.aborted == []
    assert session._dop_prepared is not None
    assert session.mode == "dop"
    assert tokens == []
    assert [getattr(error, "code", None) for error in failures] == [
        "DSD_PCM_OUTPUT_UNAVAILABLE"
    ]
    assert session.handover_state is HandoverState.FAILED
