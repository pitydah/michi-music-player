"""AP2-F10 C6 — remaining family matrix directions at the transaction level.

T03 Managed→DSD→PCM, T04 DSD→PCM→Managed, T05 Native→DSD→PCM,
T06 DSD→PCM→Native, plus T01 Direct→DSD→PCM. These are transaction/receipt
proofs with controlled host receipts; they are NOT physical DAC certification.
T01 asserts the exact Direct release receipt the executor receives from the
hosted discard command.
"""

from __future__ import annotations

from dataclasses import replace
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
from michi.domain.dop import DopInterpretationState
from michi.domain.dsd_signal import (
    DsdBitOrder,
    DsdOrganization,
    DsdPacking,
    DsdSignalFormat,
)
from tests.dop.test_dop_planner import (
    _carrier,
    _interp,
)
from tests.dop.test_dop_planner import (
    _plan as _dop_plan,
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


def _dsd_plan(
    *,
    quality: str = "FAST",
    rates: tuple[int, ...] = (88_200,),
    stable_device_id: str = "dev:matrix",
    binding_locator: str = "hw:0,0",
    binding_generation: int = 1,
):
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
        quality_profile=quality,
        binding_generation=binding_generation,
        available_output_rates=rates,
        decoder_available=True,
        target_qualified=True,
        stable_device_id=stable_device_id,
        binding_locator=binding_locator,
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
    facts = SimpleNamespace(profile=SimpleNamespace(path=OutputPathPreference.MANAGED))
    return OutputRequest(facts, "dev:matrix", "profile:managed")


def _service(
    requests: dict[str, OutputRequest],
    tx: _Tx,
    executor: _Deferred,
    *,
    dsd_current=None,
):
    provider = lambda path: requests[path.name]  # noqa: E731
    dsd_checker = dsd_current or (lambda _plan: True)
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
        dsd_pcm_plan_still_current=dsd_checker,
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
        "target.dsf": OutputRequest.dsd_to_pcm(dsd, dsd.stable_device_id, "profile:dsd")
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
        "target.dsf": OutputRequest.dsd_to_pcm(dsd, dsd.stable_device_id, "profile:dsd")
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


class _DirectExecutor:
    """Minimal committed Direct execution for the T01 release proof."""

    def __init__(self) -> None:
        self.plan = None
        self.receipt = "exec:direct:matrix"
        self.release_reasons: list[str] = []

    def prepare(self, plan) -> str:
        self.plan = plan
        return self.receipt

    def commit(self, receipt: str) -> None:
        self.receipt = receipt

    def abort(self, receipt: str, reason: str):
        from michi.application.audio_output_ports import (
            OutputExecutorAbortDisposition,
        )

        return OutputExecutorAbortDisposition.CANDIDATE_DISCARDED

    def owns_committed_receipt(self, receipt: str) -> bool:
        return receipt == self.receipt

    def release(self, reason: str) -> dict[str, Any]:
        self.release_reasons.append(reason)
        assert self.plan is not None
        return {
            "released": True,
            "command_confirmed": True,
            "reason": reason,
            "operation": "release",
            "plan_id": self.plan.plan_id,
            "execution_id": self.receipt,
            "stable_device_id": self.plan.stable_device_id,
            "device": self.plan.binding.locator,
            "binding_generation": self.plan.binding.generation,
            "host_generation": 0,
            "terminal_state": "RELEASED",
            "provenance": "SUPERVISED_HOST",
        }


class _DirectDeferred:
    """Deterministic async boundary for the owner-safe Direct handover."""

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


def test_t01_direct_to_dsd_pcm_async_releases_before_target_prepare(
    tmp_path: Path,
) -> None:
    """T01: the async owner-safe path releases Direct before DSD→PCM prepare."""
    from tests.dac.test_v34_output_planner import DEVICE, _facts

    dsd = _dsd_plan()
    direct_facts = _facts()
    executor = _DirectExecutor()
    tx = _Tx()
    deferred = _DirectDeferred()
    requests = {
        "direct.flac": OutputRequest(direct_facts, DEVICE, "profile:direct"),
        "target.dsf": OutputRequest.dsd_to_pcm(
            dsd, dsd.stable_device_id, "profile:direct"
        ),
    }
    service = OutputSessionService(
        OutputPlanner(),
        facts_provider=lambda _path: direct_facts,
        request_provider=lambda path: requests[path.name],
        executors={"gstreamer": executor},
        plan_still_current=lambda _plan: True,
        async_submit=deferred.submit,
        dsd_pcm_prepare=tx.dsd_prepare,
        dsd_pcm_commit=lambda _p: None,
        dsd_pcm_abort=tx.dsd_abort,
        dsd_pcm_stop=tx.dsd_abort,
        dsd_pcm_plan_still_current=lambda _plan: True,
    )

    direct_token = service.prepare_for_media(Path("direct.flac"))
    service.commit_media(direct_token, Path("direct.flac"))
    direct_plan = executor.plan
    assert direct_plan is not None

    tokens: list[str] = []
    failures: list[Exception] = []
    service.prepare_for_media_async(Path("target.dsf"), tokens.append, failures.append)

    deferred.run_one()  # characterization: no physical command yet
    assert executor.release_reasons == []
    assert tx.dsd_prepare_calls == 0

    deferred.run_one()  # release resolves before the target prepares
    assert executor.release_reasons == ["handover_to_dsd_pcm"]
    assert tx.dsd_prepare_calls == 0

    deferred.run_one()  # target prepare + commit
    assert tx.dsd_prepare_calls == 1
    assert failures == []
    assert len(tokens) == 1
    assert service.mode == "dsd_pcm"
    assert service.dsd_pcm_active is True
    evidence = service.last_handover_release_evidence
    assert evidence is not None
    assert evidence["plan_id"] == direct_plan.plan_id
    assert evidence["execution_id"] == "exec:direct:matrix"
    assert evidence["command_confirmed"] is True
    assert evidence["terminal_state"] == "RELEASED"
    assert evidence["provenance"] == "SUPERVISED_HOST"
    assert evidence["target_family"] == "dsd_pcm"


def test_t01_direct_to_dsd_pcm_records_the_host_release(tmp_path: Path) -> None:
    """T01: a committed Direct execution releases with exact identity."""
    from tests.dac.test_v34_output_planner import DEVICE, _facts

    dsd = _dsd_plan()
    direct_facts = _facts()
    executor = _DirectExecutor()
    tx = _Tx()
    requests = {
        "direct.flac": OutputRequest(direct_facts, DEVICE, "profile:direct"),
        "target.dsf": OutputRequest.dsd_to_pcm(
            dsd, dsd.stable_device_id, "profile:direct"
        ),
    }
    service = OutputSessionService(
        OutputPlanner(),
        facts_provider=lambda _path: direct_facts,
        request_provider=lambda path: requests[path.name],
        executors={"gstreamer": executor},
        plan_still_current=lambda _plan: True,
        dsd_pcm_prepare=tx.dsd_prepare,
        dsd_pcm_commit=lambda _p: None,
        dsd_pcm_abort=tx.dsd_abort,
        dsd_pcm_stop=tx.dsd_abort,
        dsd_pcm_plan_still_current=lambda _plan: True,
    )

    direct_token = service.prepare_for_media(Path("direct.flac"))
    service.commit_media(direct_token, Path("direct.flac"))
    assert service.mode == "direct"
    direct_plan = executor.plan
    assert direct_plan is not None

    service.prepare_for_media(Path("target.dsf"))

    assert executor.release_reasons == ["switch_to_dsd_pcm"]
    evidence = service.last_release_evidence
    assert evidence is not None
    assert evidence["plan_id"] == direct_plan.plan_id
    assert evidence["execution_id"] == "exec:direct:matrix"
    assert evidence["stable_device_id"] == direct_plan.stable_device_id
    assert evidence["binding_generation"] == direct_plan.binding.generation
    assert evidence["terminal_state"] == "RELEASED"
    assert evidence["provenance"] == "SUPERVISED_HOST"
    assert service.mode == "dsd_pcm"
    assert service.dsd_pcm_active is True


def test_t11_dsd_pcm_quality_change_releases_before_prepare(tmp_path: Path) -> None:
    """T11: same-family quality A→B is a destructive host reconfiguration.

    The host refuses a second DSD→PCM prepare while the first execution is
    active, so the transaction must release the predecessor (exact identity)
    before preparing the new quality/rate plan.
    """
    plan_a = _dsd_plan(quality="FAST", rates=(88_200,))
    plan_b = _dsd_plan(quality="HIGH", rates=(88_200, 176_400))
    assert plan_a.plan_id != plan_b.plan_id
    requests = {
        "quality-a.dsf": OutputRequest.dsd_to_pcm(
            plan_a, plan_a.stable_device_id, "profile:dsd"
        ),
        "quality-b.dsf": OutputRequest.dsd_to_pcm(
            plan_b, plan_b.stable_device_id, "profile:dsd"
        ),
    }
    tx = _Tx()
    executor = _Deferred()
    session = _service(requests, tx, executor)

    session.prepare_for_media(tmp_path / "quality-a.dsf")
    prepared_a = session._dsd_pcm_prepared
    assert prepared_a is not None
    assert prepared_a.plan.plan_id == plan_a.plan_id
    snapshot_a = session.transition_snapshot()

    tokens: list[str] = []
    failures: list[Exception] = []
    session.prepare_for_media_async(
        tmp_path / "quality-b.dsf", tokens.append, failures.append
    )

    executor.run_one()
    assert tx.aborts == []
    assert tx.dsd_prepare_calls == 1
    assert session._dsd_pcm_prepared is prepared_a

    executor.drive()
    assert failures == []
    assert len(tokens) == 1
    assert tx.aborts == [f"dsd_pcm:{prepared_a.execution_id}"]
    assert tx.dsd_prepare_calls == 2
    assert session._dsd_pcm_prepared is not None
    assert session._dsd_pcm_prepared.plan.plan_id == plan_b.plan_id
    assert session._dsd_pcm_prepared.plan.quality_profile == "HIGH"
    assert session.state is OutputSessionState.READY
    assert session.mode == "dsd_pcm"
    assert session.handover_state is HandoverState.READY
    evidence = session.last_handover_release_evidence
    assert evidence is not None
    assert evidence["execution_id"] == prepared_a.execution_id
    assert evidence["device"] == prepared_a.binding_locator
    snapshot_b = session.transition_snapshot()
    prepared_b = session._dsd_pcm_prepared
    assert prepared_b is not None
    assert snapshot_b["generation"] > snapshot_a["generation"]
    assert snapshot_b["plan_id"] == plan_b.plan_id
    assert snapshot_b["execution_id"] == prepared_b.execution_id

    requests["quality-a2.dsf"] = OutputRequest.dsd_to_pcm(
        plan_a, plan_a.stable_device_id, "profile:dsd"
    )
    tokens_again: list[str] = []
    failures_again: list[Exception] = []
    session.prepare_for_media_async(
        tmp_path / "quality-a2.dsf", tokens_again.append, failures_again.append
    )
    executor.run_one()
    assert tx.aborts == [f"dsd_pcm:{prepared_a.execution_id}"]
    assert tx.dsd_prepare_calls == 2

    executor.drive()
    assert failures_again == []
    assert len(tokens_again) == 1
    assert tx.aborts == [
        f"dsd_pcm:{prepared_a.execution_id}",
        f"dsd_pcm:{prepared_b.execution_id}",
    ]
    assert tx.dsd_prepare_calls == 3
    assert session._dsd_pcm_prepared is not None
    assert session._dsd_pcm_prepared.plan.plan_id == plan_a.plan_id
    assert session._dsd_pcm_prepared.plan.quality_profile == "FAST"
    evidence = session.last_handover_release_evidence
    assert evidence is not None
    assert evidence["execution_id"] == prepared_b.execution_id
    snapshot_a2 = session.transition_snapshot()
    assert snapshot_a2["generation"] > snapshot_b["generation"]
    assert snapshot_a2["plan_id"] == plan_a.plan_id
    assert snapshot_a2["execution_id"] == session._dsd_pcm_prepared.execution_id


def test_t12_dop_dac_change_releases_before_prepare(tmp_path: Path) -> None:
    """T12: same-family DoP DAC A→B releases device A before binding device B."""
    plan_a = _dop_plan(execution_id="exec:dac-a")
    carrier_b = replace(
        _carrier(),
        stable_device_id="dev:dac-b",
        binding_locator="hw:1,0",
        binding_generation=4,
        environment_fingerprint="env:2",
    )
    interpretation_b = replace(
        _interp(DopInterpretationState.USER_CONFIRMED),
        stable_device_id="dev:dac-b",
        device_revision="rev:2",
    )
    plan_b = _dop_plan(
        execution_id="exec:dac-b",
        stable_device_id="dev:dac-b",
        binding_locator="hw:1,0",
        binding_generation=4,
        environment_fingerprint="env:2",
        current_device_revision="rev:2",
        carrier_qualifications=(carrier_b,),
        interpretation=(interpretation_b,),
    )
    assert plan_a.plan_id != plan_b.plan_id
    requests = {
        "dac-a.dsf": OutputRequest.dop(plan_a, "profile:dop"),
        "dac-b.dsf": OutputRequest.dop(plan_b, "profile:dop"),
    }
    tx = _Tx()
    executor = _Deferred()
    session = _service(requests, tx, executor)

    session.prepare_for_media(tmp_path / "dac-a.dsf")
    prepared_a = session._dop_prepared
    assert prepared_a is not None
    assert prepared_a.plan.stable_device_id == "usb:152a:85dd"

    tokens: list[str] = []
    failures: list[Exception] = []
    session.prepare_for_media_async(
        tmp_path / "dac-b.dsf", tokens.append, failures.append
    )

    executor.run_one()
    assert tx.aborts == []
    assert tx.dop_prepare_calls == 1
    assert session._dop_prepared is prepared_a

    executor.drive()
    assert failures == []
    assert len(tokens) == 1
    assert tx.aborts == [f"dop:{prepared_a.execution_id}"]
    assert tx.dop_prepare_calls == 2
    assert session._dop_prepared is not None
    assert session._dop_prepared.plan.stable_device_id == "dev:dac-b"
    assert session._dop_prepared.plan.binding_locator == "hw:1,0"
    assert session.state is OutputSessionState.READY
    assert session.mode == "dop"
    assert session.handover_state is HandoverState.READY
    evidence = session.last_handover_release_evidence
    assert evidence is not None
    assert evidence["execution_id"] == "exec:dac-a"
    assert evidence["device"] == "hw:3,0"
    assert evidence["stable_device_id"] == "usb:152a:85dd"


def test_t11_stale_binding_rejects_before_releasing_the_predecessor(
    tmp_path: Path,
) -> None:
    plan_a = _dsd_plan(quality="FAST", rates=(88_200,))
    plan_b = _dsd_plan(quality="HIGH", rates=(88_200, 176_400))
    requests = {
        "quality-a.dsf": OutputRequest.dsd_to_pcm(
            plan_a, plan_a.stable_device_id, "profile:dsd"
        ),
        "quality-b.dsf": OutputRequest.dsd_to_pcm(
            plan_b, plan_b.stable_device_id, "profile:dsd"
        ),
    }
    tx = _Tx()
    executor = _Deferred()
    current = {"ok": True}
    session = _service(requests, tx, executor, dsd_current=lambda _plan: current["ok"])

    session.prepare_for_media(tmp_path / "quality-a.dsf")
    prepared_a = session._dsd_pcm_prepared
    assert prepared_a is not None
    assert tx.dsd_prepare_calls == 1

    current["ok"] = False
    failures: list[Exception] = []
    session.prepare_for_media_async(
        tmp_path / "quality-b.dsf", lambda _token: None, failures.append
    )
    executor.drive()

    assert failures
    assert "DSD_PCM_BINDING_STALE" in str(failures[0])
    assert tx.aborts == []
    assert tx.dsd_prepare_calls == 1
    assert session._dsd_pcm_prepared is prepared_a
