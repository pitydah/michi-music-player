"""AP2-F10 C5 — adversarial owner-safe handover and Qt responsiveness."""

from __future__ import annotations

import importlib.util
import threading
import time
from pathlib import Path
from typing import Any

import pytest

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

_HAS_QT = importlib.util.find_spec("PySide6") is not None


class _StepExecutor:
    """Split work and completion so the test can interleave owner phases."""

    def __init__(self) -> None:
        self.pending: list[tuple[Any, Any]] = []
        self.deliveries: list[tuple[Any, Any, Any]] = []

    def submit(self, work, completed) -> None:
        self.pending.append((work, completed))

    def run_work(self):
        work, completed = self.pending.pop(0)
        try:
            value = work()
        except Exception as exc:  # noqa: BLE001 - test boundary
            self.deliveries.append((completed, None, exc))
        else:
            self.deliveries.append((completed, value, None))

    def deliver(self) -> None:
        completed, value, error = self.deliveries.pop(0)
        completed(value, error)

    def run_one(self) -> None:
        self.run_work()
        self.deliver()

    def drive(self, limit: int = 12) -> None:
        while (self.pending or self.deliveries) and limit > 0:
            self.run_one()
            limit -= 1


class _Tx:
    def __init__(self) -> None:
        self.aborted: list[tuple[str, str, str]] = []
        self.dop_prepare_calls = 0
        self.dsd_pcm_prepare_calls = 0
        self.dsd_pcm_prepare_error: Exception | None = None
        self.abort_result_override: dict | None = None

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

    def dop_prepare(self, plan, path, instance) -> DopSessionPrepared:
        self.dop_prepare_calls += 1
        return DopSessionPrepared(
            plan=plan,
            execution_id=plan.execution_id,
            stable_device_id=plan.stable_device_id,
            runtime_identity={"host_generation": plan.host_generation},
            evidence_refs=(),
        )

    def dop_commit(self, _prepared) -> None:
        return

    def dop_abort(self, prepared, reason) -> dict[str, Any]:
        self.aborted.append(("dop", prepared.execution_id, reason))
        if self.abort_result_override is not None:
            return dict(self.abort_result_override)
        return {
            "aborted": True,
            "stale": False,
            "execution_id": prepared.execution_id,
            "release": self._dop_receipt(prepared, "abort"),
        }

    def dop_stop(self, prepared, reason) -> dict[str, Any]:
        return {
            "stopped": True,
            "stale": False,
            "execution_id": prepared.execution_id,
            "release": self._dop_receipt(prepared, "stop"),
        }

    def dsd_pcm_prepare(self, plan, path, instance) -> DsdPcmSessionPrepared:
        self.dsd_pcm_prepare_calls += 1
        if self.dsd_pcm_prepare_error is not None:
            raise self.dsd_pcm_prepare_error
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

    def dsd_pcm_commit(self, _prepared) -> None:
        return

    def dsd_pcm_abort(self, prepared, reason) -> dict[str, Any]:
        self.aborted.append(("dsd_pcm", prepared.execution_id, reason))
        return {
            "aborted": True,
            "stale": False,
            "execution_id": prepared.execution_id,
            "release": self._dsd_receipt(prepared, "abort"),
        }

    def dsd_pcm_stop(self, prepared, reason) -> dict[str, Any]:
        return {
            "stopped": True,
            "stale": False,
            "execution_id": prepared.execution_id,
            "release": self._dsd_receipt(prepared, "stop"),
        }


def _dsd_pcm_plan():
    return DsdToPcmPlanner().plan(
        source_identity="track:adversarial",
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
        stable_device_id="dev:adv",
        binding_locator="hw:0,0",
        host_generation=1,
    )


class _Provider:
    def __init__(self, requests: dict[str, OutputRequest]) -> None:
        self.requests = requests
        self.intent = {"revision": 1}

    def __call__(self, path: Path) -> OutputRequest:
        return self.requests[path.name]

    def snapshot_output_intent(self):
        return dict(self.intent)


def _rig(
    requests: dict[str, OutputRequest],
    tx: _Tx,
    executor: _StepExecutor,
) -> tuple[OutputSessionService, _Provider]:
    provider = _Provider(requests)
    session = OutputSessionService(
        OutputPlanner(),
        request_provider=provider,
        async_submit=executor.submit,
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
    return session, provider


def _requests():
    dop_one = _dop_plan(execution_id="exec:1")
    dop_two = _dop_plan(execution_id="exec:2")
    dsd = _dsd_pcm_plan()
    return {
        "predecessor.dsf": OutputRequest.dop(dop_one, "profile:dop"),
        "target.dsf": OutputRequest.dsd_to_pcm(
            dsd, dsd.stable_device_id, "profile:dsd"
        ),
        "second.dsf": OutputRequest.dop(dop_two, "profile:dop"),
    }, dop_one, dop_two, dsd


def _start_handover(tmp_path: Path):
    requests, dop_one, _, _ = _requests()
    tx = _Tx()
    executor = _StepExecutor()
    session, _provider = _rig(requests, tx, executor)
    session.prepare_for_media(tmp_path / "predecessor.dsf")
    tokens: list[str] = []
    failures: list[Exception] = []
    session.prepare_for_media_async(
        tmp_path / "target.dsf", tokens.append, failures.append
    )
    executor.run_one()  # characterization only
    assert tx.aborted == []
    assert session.handover_state is HandoverState.RELEASE
    return session, tx, executor, tokens, failures


def test_release_rejected_never_prepares_the_target(tmp_path: Path) -> None:
    session, tx, executor, tokens, failures = _start_handover(tmp_path)
    tx.abort_result_override = {"aborted": False, "stale": False}
    executor.drive()

    assert tokens == []
    assert tx.dsd_pcm_prepare_calls == 0
    assert session.handover_state is HandoverState.OWNERSHIP_UNCONFIRMED
    assert session._dop_prepared is not None
    assert session.mode == "dop"
    assert [getattr(error, "code", None) for error in failures] == [
        "OUTPUT_OWNERSHIP_UNCONFIRMED"
    ]


def test_foreign_release_receipt_never_prepares_the_target(tmp_path: Path) -> None:
    session, tx, executor, tokens, failures = _start_handover(tmp_path)
    predecessor = session._dop_prepared
    assert predecessor is not None
    receipt = _Tx._dop_receipt(predecessor, "abort")
    receipt["execution_id"] = "exec:foreign"
    tx.abort_result_override = {
        "aborted": True,
        "stale": False,
        "execution_id": predecessor.execution_id,
        "release": receipt,
    }
    executor.drive()

    assert tokens == []
    assert tx.dsd_pcm_prepare_calls == 0
    assert session.handover_state is HandoverState.OWNERSHIP_UNCONFIRMED
    assert [getattr(error, "code", None) for error in failures] == [
        "OUTPUT_OWNERSHIP_UNCONFIRMED"
    ]


def test_host_restart_receipt_mismatch_rejects_the_release(tmp_path: Path) -> None:
    session, tx, executor, tokens, failures = _start_handover(tmp_path)
    predecessor = session._dop_prepared
    assert predecessor is not None
    receipt = _Tx._dop_receipt(predecessor, "abort")
    receipt["host_generation"] = predecessor.plan.host_generation + 1
    tx.abort_result_override = {
        "aborted": True,
        "stale": False,
        "execution_id": predecessor.execution_id,
        "release": receipt,
    }
    executor.drive()

    assert tokens == []
    assert tx.dsd_pcm_prepare_calls == 0
    assert session.handover_state is HandoverState.OWNERSHIP_UNCONFIRMED


def test_stop_during_release_never_prepares_the_target(tmp_path: Path) -> None:
    session, tx, executor, tokens, failures = _start_handover(tmp_path)
    session.cancel_pending_prepare()
    executor.drive()

    assert tokens == []
    assert tx.dsd_pcm_prepare_calls == 0
    assert session.handover_state is HandoverState.SUPERSEDED
    assert [getattr(error, "code", None) for error in failures] == [
        "OUTPUT_PREPARATION_STALE"
    ]


def test_device_selection_aba_during_prepare_aborts_the_target(
    tmp_path: Path,
) -> None:
    session, tx, executor, tokens, failures = _start_handover(tmp_path)
    executor.run_work()  # release work executes
    executor.deliver()  # owner reconciles and submits PREPARE
    assert session.handover_state is HandoverState.PREPARE
    executor.run_work()  # target prepared off-owner, not yet committed

    # ABA: the selection changes after the release and before the commit.
    provider = session._request_provider
    provider.intent = {"revision": 2}
    executor.deliver()

    assert tokens == []
    assert session.mode != "dsd_pcm"
    assert session.handover_state is HandoverState.SUPERSEDED
    assert [getattr(error, "code", None) for error in failures] == [
        "OUTPUT_PREPARATION_STALE"
    ]
    assert any(family == "dsd_pcm" for family, _exec, _reason in tx.aborted)


def test_prepare_failure_after_release_is_terminal(tmp_path: Path) -> None:
    session, tx, executor, tokens, failures = _start_handover(tmp_path)
    tx.dsd_pcm_prepare_error = RuntimeError("target prepare failed")
    executor.drive()

    assert tokens == []
    assert session.handover_state is HandoverState.FAILED
    assert session._dop_prepared is None
    assert session.dop_active is False
    assert getattr(failures[-1], "code", None) == "DSD_PCM_OUTPUT_PREPARE_FAILED"
    assert session.state is not OutputSessionState.READY


def test_a_to_b_to_c_keeps_each_handover_independent(tmp_path: Path) -> None:
    requests, _, _, _ = _requests()
    tx = _Tx()
    executor = _StepExecutor()
    session, _provider = _rig(requests, tx, executor)

    session.prepare_for_media(tmp_path / "predecessor.dsf")
    tokens: list[str] = []
    failures: list[Exception] = []
    session.prepare_for_media_async(
        tmp_path / "target.dsf", tokens.append, failures.append
    )
    executor.drive()
    assert failures == []
    assert session.mode == "dsd_pcm"
    first = session._dsd_pcm_prepared
    assert first is not None

    session.prepare_for_media_async(
        tmp_path / "second.dsf", tokens.append, failures.append
    )
    executor.drive()
    assert failures == []
    assert session.mode == "dop"
    assert len(tokens) == 2
    evidence = session.last_handover_release_evidence
    assert evidence is not None
    assert evidence["execution_id"] == first.execution_id
    assert evidence["target_family"] == "dop"
    assert ("dsd_pcm", first.execution_id, "handover_to_dop") in tx.aborted


@pytest.mark.skipif(not _HAS_QT, reason="PySide6 unavailable")
def test_qt_loop_stays_free_during_release_and_prepare(qapp, tmp_path: Path) -> None:
    from michi.infrastructure.qt_async_call import QtAsyncCallExecutor

    requests, _, _, _ = _requests()
    tx = _Tx()
    executor = QtAsyncCallExecutor()
    provider = _Provider(requests)
    abort_entered = threading.Event()
    abort_release = threading.Event()
    prepare_entered = threading.Event()
    prepare_release = threading.Event()
    real_abort = tx.dop_abort
    real_prepare = tx.dsd_pcm_prepare

    def blocking_abort(prepared, reason):
        abort_entered.set()
        assert abort_release.wait(timeout=8.0)
        return real_abort(prepared, reason)

    def blocking_prepare(plan, path, instance):
        prepare_entered.set()
        assert prepare_release.wait(timeout=8.0)
        return real_prepare(plan, path, instance)

    session = OutputSessionService(
        OutputPlanner(),
        request_provider=provider,
        async_submit=executor.submit,
        dop_prepare=tx.dop_prepare,
        dop_commit=tx.dop_commit,
        dop_abort=blocking_abort,
        dop_stop=tx.dop_stop,
        dop_plan_still_current=lambda _plan: True,
        dsd_pcm_prepare=blocking_prepare,
        dsd_pcm_commit=tx.dsd_pcm_commit,
        dsd_pcm_abort=tx.dsd_pcm_abort,
        dsd_pcm_stop=tx.dsd_pcm_stop,
        dsd_pcm_plan_still_current=lambda _plan: True,
    )
    session.prepare_for_media(tmp_path / "predecessor.dsf")
    owner_thread = threading.get_ident()
    tokens: list[str] = []
    failures: list[Exception] = []
    callback_threads: list[int] = []
    ticks: list[float] = []
    from PySide6.QtCore import QTimer

    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(lambda: ticks.append(time.monotonic()))
    timer.start()

    def pump_until(predicate, timeout_s: float = 8.0) -> bool:
        deadline = time.monotonic() + timeout_s
        while not predicate() and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.005)
        qapp.processEvents()
        return predicate()

    try:
        session.prepare_for_media_async(
            tmp_path / "target.dsf",
            lambda token: (
                callback_threads.append(threading.get_ident()),
                tokens.append(token),
            ),
            failures.append,
        )
        assert pump_until(abort_entered.is_set)
        assert session.handover_state is HandoverState.RELEASE
        before = len(ticks)
        assert pump_until(lambda: len(ticks) >= before + 3)

        abort_release.set()
        assert pump_until(prepare_entered.is_set)
        assert session.handover_state is HandoverState.PREPARE
        before = len(ticks)
        assert pump_until(lambda: len(ticks) >= before + 3)

        prepare_release.set()
        assert pump_until(lambda: bool(tokens))
        assert failures == []
        assert tokens and session.state is OutputSessionState.READY
        assert callback_threads == [owner_thread]
        assert tx.dsd_pcm_prepare_calls == 1
        # Late duplicates never produce another READY token.
        qapp.processEvents()
        assert len(tokens) == 1
    finally:
        timer.stop()
        abort_release.set()
        prepare_release.set()


def test_stop_during_prepare_aborts_the_prepared_candidate(
    tmp_path: Path,
) -> None:
    session, tx, executor, tokens, failures = _start_handover(tmp_path)
    executor.run_work()  # release
    executor.deliver()  # reconcile + submit PREPARE
    executor.run_work()  # target prepared off-owner, held
    assert session.handover_state is HandoverState.PREPARE

    session.cancel_pending_prepare()
    executor.deliver()

    assert tokens == []
    assert session.mode != "dsd_pcm"
    assert session.state is not OutputSessionState.READY
    assert session.handover_state is HandoverState.SUPERSEDED
    assert [getattr(error, "code", None) for error in failures] == [
        "OUTPUT_PREPARATION_STALE"
    ]
    assert any(
        family == "dsd_pcm" and reason == "superseded_before_commit"
        for family, _exec, reason in tx.aborted
    )
