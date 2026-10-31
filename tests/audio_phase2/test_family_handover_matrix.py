"""AP2-F10 C6 — remaining family matrix directions at the transaction level.

T03 Managed→DSD→PCM, T04 DSD→PCM→Managed, T05 Native→DSD→PCM,
T06 DSD→PCM→Native. These are transaction/receipt proofs with controlled host
receipts; they are NOT physical DAC certification. PCM Direct (T01/T07) still
lacks a supervised release receipt adapter and is not claimed here.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from michi.application.audio_family_transition import (
    AudioFamily,
    AudioFamilyTransitionService,
    FamilyTransitionRequest,
    PlaybackStatus,
    TransitionError,
)
from michi.application.audio_output_planner import OutputPlanner
from michi.application.dsd_to_pcm_plan import DsdToPcmPlanner
from michi.application.output_session_service import (
    DopSessionPrepared,
    DsdPcmSessionPrepared,
    HandoverState,
    ManagedOutputPrepared,
    NativeDsdSessionPrepared,
    OutputRequest,
    OutputSessionService,
)
from michi.domain.audio_output import (
    OutputPathPreference,
    OutputSessionState,
)
from michi.domain.dsd_signal import (
    DsdBitOrder,
    DsdOrganization,
    DsdPacking,
    DsdSignalFormat,
)


class _Deferred:
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

    def drive(self, limit: int = 12) -> None:
        while self.pending and limit > 0:
            self.run_one()
            limit -= 1


class _Tx:
    def __init__(self) -> None:
        self.aborts: list[str] = []
        self.dop_prepare_calls = 0
        self.dsd_prepare_calls = 0
        self.native_prepare_calls = 0
        self.managed_prepare_calls = 0

    @staticmethod
    def _receipt(
        prepared,
        *,
        plan_id: str,
        execution_id: str,
        stable_device_id: str,
        device: str,
        binding_generation: int,
        host_generation: int,
        operation: str,
    ) -> dict[str, Any]:
        return {
            "confirmed": True,
            "operation": operation,
            "plan_id": plan_id,
            "execution_id": execution_id,
            "stable_device_id": stable_device_id,
            "device": device,
            "binding_generation": binding_generation,
            "host_generation": host_generation,
            "terminal_state": "RELEASED",
            "provenance": "SUPERVISED_HOST",
        }

    def dop_abort(self, prepared: DopSessionPrepared, reason: str) -> dict:
        self.aborts.append(f"dop:{prepared.execution_id}")
        plan = prepared.plan
        return {
            "aborted": True,
            "stale": False,
            "execution_id": prepared.execution_id,
            "release": self._receipt(
                prepared,
                plan_id=plan.plan_id,
                execution_id=prepared.execution_id,
                stable_device_id=plan.stable_device_id,
                device=plan.binding_locator,
                binding_generation=plan.binding_generation,
                host_generation=plan.host_generation,
                operation="abort",
            ),
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

    def dsd_abort(self, prepared: DsdPcmSessionPrepared, reason: str) -> dict:
        self.aborts.append(f"dsd_pcm:{prepared.execution_id}")
        return {
            "aborted": True,
            "stale": False,
            "execution_id": prepared.execution_id,
            "release": self._receipt(
                prepared,
                plan_id=prepared.plan.plan_id,
                execution_id=prepared.execution_id,
                stable_device_id=prepared.stable_device_id,
                device=prepared.binding_locator,
                binding_generation=prepared.plan.binding_generation,
                host_generation=prepared.host_generation,
                operation="abort",
            ),
        }

    def dsd_prepare(self, plan, path, instance) -> DsdPcmSessionPrepared:
        self.dsd_prepare_calls += 1
        return DsdPcmSessionPrepared(
            plan=plan,
            execution_id=instance,
            stable_device_id=plan.stable_device_id,
            binding_locator=plan.binding_locator,
            host_generation=plan.host_generation,
            runtime_identity={"plan_id": plan.plan_id},
            evidence_refs=(),
        )

    def native_abort(self, prepared: NativeDsdSessionPrepared, reason: str) -> dict:
        self.aborts.append(f"native_dsd:{prepared.execution_id}")
        plan = prepared.plan
        return {
            "aborted": True,
            "stale": False,
            "release": self._receipt(
                prepared,
                plan_id=plan.plan_id,
                execution_id=prepared.execution_id,
                stable_device_id=prepared.stable_device_id,
                device=plan.binding_locator,
                binding_generation=plan.binding_generation,
                host_generation=prepared.runtime_identity.get("host_generation", 1),
                operation="abort",
            ),
        }

    def native_prepare(self, plan, path, instance) -> NativeDsdSessionPrepared:
        self.native_prepare_calls += 1
        return NativeDsdSessionPrepared(
            plan=plan,
            execution_id=plan.execution_id,
            stable_device_id=plan.stable_device_id,
            runtime_identity={"host_generation": 1},
            evidence_refs=(),
        )

    def managed_abort(self, prepared: ManagedOutputPrepared, reason: str) -> dict:
        self.aborts.append(f"managed:{prepared.execution_id}")
        plan = prepared.plan
        return {
            "stopped": True,
            "stale": False,
            "release": self._receipt(
                prepared,
                plan_id=plan.plan_id,
                execution_id=prepared.execution_id,
                stable_device_id=plan.stable_device_id,
                device=plan.device_locator,
                binding_generation=plan.binding_generation,
                host_generation=prepared.runtime_identity.get("host_generation", 1),
                operation="stop",
            ),
        }

    def managed_prepare(self, path, facts, instance) -> ManagedOutputPrepared:
        self.managed_prepare_calls += 1
        return ManagedOutputPrepared(
            plan=_managed_plan(),
            execution_id=instance,
            runtime_identity={"host_generation": 1},
        )


def _dsd_plan():
    return DsdToPcmPlanner().plan(
        source_identity="track:matrix",
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
        stable_device_id="dev:matrix",
        binding_locator="hw:0,0",
        host_generation=1,
    )


def _native_plan():
    return SimpleNamespace(
        plan_id="native:plan:matrix",
        execution_id="exec:native:matrix",
        stable_device_id="dev:matrix",
        binding_locator="hw:1,0",
        binding_generation=4,
    )


def _managed_plan():
    return SimpleNamespace(
        plan_id="managed:plan:matrix",
        stable_device_id="dev:matrix",
        device_locator="hw:2,0",
        binding_generation=5,
        processing_plan_id=None,
        processing_graph_revision=0,
        processing_revision=0,
        transform_policy=(),
        selection_revision=0,
        execution_id="exec:managed:matrix",
    )


def _managed_request():
    facts = SimpleNamespace(
        profile=SimpleNamespace(path=OutputPathPreference.MANAGED)
    )
    return OutputRequest(facts, "dev:matrix", "profile:managed")


def _service(requests: dict[str, OutputRequest], tx: _Tx, executor: _Deferred):
    provider = lambda path: requests[path.name]  # noqa: E731
    return OutputSessionService(
        OutputPlanner(),
        request_provider=provider,
        async_submit=executor.submit,
        dop_prepare=tx.dop_prepare,
        dop_commit=lambda _p: None,
        dop_abort=tx.dop_abort,
        dop_stop=tx.dop_abort,
        dop_plan_still_current=lambda _plan: True,
        dsd_pcm_prepare=tx.dsd_prepare,
        dsd_pcm_commit=lambda _p: None,
        dsd_pcm_abort=tx.dsd_abort,
        dsd_pcm_stop=tx.dsd_abort,
        dsd_pcm_plan_still_current=lambda _plan: True,
        native_dsd_prepare=tx.native_prepare,
        native_dsd_commit=lambda _p: None,
        native_dsd_abort=tx.native_abort,
        native_dsd_stop=tx.native_abort,
        native_dsd_plan_still_current=lambda _plan: True,
        managed_prepare=tx.managed_prepare,
        managed_abort=tx.managed_abort,
        managed_plan_still_current=lambda _plan: True,
    )


def test_t03_managed_to_dsd_pcm_releases_before_prepare(tmp_path: Path) -> None:
    dsd = _dsd_plan()
    requests = {
        "target.dsf": OutputRequest.dsd_to_pcm(
            dsd, dsd.stable_device_id, "profile:dsd"
        )
    }
    tx = _Tx()
    executor = _Deferred()
    session = _service(requests, tx, executor)
    managed = ManagedOutputPrepared(
        plan=_managed_plan(),
        execution_id="exec:managed:matrix",
        runtime_identity={"host_generation": 1},
    )
    session._managed_prepared = managed
    session._managed_plan = managed.plan
    session._mode = "managed"

    tokens: list[str] = []
    failures: list[Exception] = []
    session.prepare_for_media_async(
        tmp_path / "target.dsf", tokens.append, failures.append
    )
    executor.drive()

    assert failures == []
    assert tokens
    assert tx.aborts == ["managed:exec:managed:matrix"]
    assert session._managed_prepared is None
    assert session.mode == "dsd_pcm"
    assert session.state is OutputSessionState.READY


def test_t04_dsd_pcm_to_managed_releases_before_prepare(tmp_path: Path) -> None:
    dsd = _dsd_plan()
    requests = {
        "predecessor.dsf": OutputRequest.dsd_to_pcm(
            dsd, dsd.stable_device_id, "profile:dsd"
        ),
        "target.dsf": _managed_request(),
    }
    tx = _Tx()
    executor = _Deferred()
    session = _service(requests, tx, executor)
    session.prepare_for_media(tmp_path / "predecessor.dsf")
    predecessor = session._dsd_pcm_prepared
    assert predecessor is not None

    tokens: list[str] = []
    failures: list[Exception] = []
    session.prepare_for_media_async(
        tmp_path / "target.dsf", tokens.append, failures.append
    )
    executor.drive()

    assert failures == []
    assert tokens
    assert tx.aborts == [f"dsd_pcm:{predecessor.execution_id}"]
    assert tx.managed_prepare_calls == 1
    assert session.mode == "managed"
    assert session.state is OutputSessionState.READY


def test_t05_native_to_dsd_pcm_releases_before_prepare(tmp_path: Path) -> None:
    dsd = _dsd_plan()
    requests = {
        "target.dsf": OutputRequest.dsd_to_pcm(
            dsd, dsd.stable_device_id, "profile:dsd"
        )
    }
    tx = _Tx()
    executor = _Deferred()
    session = _service(requests, tx, executor)
    plan = _native_plan()
    prepared = NativeDsdSessionPrepared(
        plan=plan,
        execution_id=plan.execution_id,
        stable_device_id=plan.stable_device_id,
        runtime_identity={"host_generation": 1},
        evidence_refs=(),
    )
    session._native_dsd_prepared = prepared
    session._native_dsd_plan = plan
    session._mode = "native_dsd"

    tokens: list[str] = []
    failures: list[Exception] = []
    session.prepare_for_media_async(
        tmp_path / "target.dsf", tokens.append, failures.append
    )
    executor.drive()

    assert failures == []
    assert tokens
    assert tx.aborts == ["native_dsd:exec:native:matrix"]
    assert session._native_dsd_prepared is None
    assert session.mode == "dsd_pcm"


def test_t06_dsd_pcm_to_native_releases_before_prepare(tmp_path: Path) -> None:
    dsd = _dsd_plan()
    native = _native_plan()
    requests = {
        "predecessor.dsf": OutputRequest.dsd_to_pcm(
            dsd, dsd.stable_device_id, "profile:dsd"
        ),
        "target.dsf": OutputRequest.native_dsd(native, "dev:matrix", "profile:native"),
    }
    tx = _Tx()
    executor = _Deferred()
    session = _service(requests, tx, executor)
    session.prepare_for_media(tmp_path / "predecessor.dsf")
    predecessor = session._dsd_pcm_prepared
    assert predecessor is not None

    tokens: list[str] = []
    failures: list[Exception] = []
    session.prepare_for_media_async(
        tmp_path / "target.dsf", tokens.append, failures.append
    )
    executor.drive()

    assert failures == []
    assert tokens
    assert tx.aborts == [f"dsd_pcm:{predecessor.execution_id}"]
    assert tx.native_prepare_calls == 1
    assert session.mode == "native_dsd"
    assert session.handover_state is HandoverState.READY


def test_same_family_reconfigurations_are_not_family_transitions() -> None:
    service = AudioFamilyTransitionService()
    for family in (
        AudioFamily.DSD_TO_PCM,
        AudioFamily.PCM_MANAGED,
        AudioFamily.NATIVE_DSD,
    ):
        request = FamilyTransitionRequest(
            media_identity="/tmp/same.dsf",
            source_family=family,
            target_family=family,
            predecessor_status=PlaybackStatus.PLAYING,
            request_epoch=2,
            current_epoch=1,
            output_generation=3,
            processing_generation=1,
            binding_generation=1,
            destructive_boundary=False,
        )
        with pytest.raises(TransitionError) as info:
            service.plan(request)
        assert info.value.code == "TRANSITION_SAME_FAMILY"
