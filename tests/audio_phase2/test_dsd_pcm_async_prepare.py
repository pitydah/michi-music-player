"""AP2-F10 — DSD→PCM preparation stays off the owner until completion."""

from __future__ import annotations

from pathlib import Path

from michi.application.audio_output_planner import OutputPlanner
from michi.application.dsd_to_pcm_plan import DsdToPcmPlanner
from michi.application.output_session_service import (
    DsdPcmSessionPrepared,
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


class _Deferred:
    def __init__(self) -> None:
        self.pending: list[tuple] = []

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


def _plan():
    return DsdToPcmPlanner().plan(
        source_identity="track:async",
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
        stable_device_id="dev:async",
        binding_locator="hw:0,0",
        host_generation=1,
    )


def test_dsd_pcm_async_prepare_returns_before_worker_and_commits_on_owner():
    plan = _plan()
    executor = _Deferred()
    prepared_calls: list[str] = []

    def prepare(_plan, _path, execution_id):
        prepared_calls.append(execution_id)
        return DsdPcmSessionPrepared(
            plan=plan,
            execution_id=execution_id,
            stable_device_id=plan.stable_device_id,
            binding_locator=plan.binding_locator,
            host_generation=plan.host_generation,
            runtime_identity={"plan_id": plan.plan_id, "execution_id": execution_id},
            evidence_refs=(),
            handle={"execution_id": execution_id},
        )

    service = OutputSessionService(
        OutputPlanner(),
        request_provider=lambda _path: OutputRequest.dsd_to_pcm(
            plan, plan.stable_device_id, "profile:async"
        ),
        async_submit=executor.submit,
        dsd_pcm_prepare=prepare,
        dsd_pcm_commit=lambda _prepared: None,
        dsd_pcm_abort=lambda _prepared, _reason: {"aborted": True},
        dsd_pcm_stop=lambda _prepared, _reason: {"stopped": True},
        dsd_pcm_plan_still_current=lambda _plan: True,
    )
    tokens: list[str] = []
    failures: list[Exception] = []
    source = Path("/tmp/async.dsf")
    service.prepare_for_media_async(source, tokens.append, failures.append)
    assert tokens == []
    assert failures == []
    assert len(executor.pending) == 1
    executor.run_one()
    assert failures == []
    assert tokens
    assert service.state is OutputSessionState.READY
    assert service.dsd_pcm_active is True
    assert prepared_calls
