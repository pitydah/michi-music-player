"""DAC-V35-080 Direct transition classification and freshness gates."""

from __future__ import annotations

from pathlib import Path

import pytest

from michi.application.audio_output_planner import OutputPlanner
from michi.application.audio_output_ports import OutputExecutorAbortDisposition
from michi.application.output_session_service import (
    DirectTransitionKind,
    OutputSessionError,
    OutputSessionService,
)
from michi.domain.audio_output import FallbackKind, OutputSessionState, VolumePolicy
from tests.dac.test_v34_output_planner import _binding, _evidence, _facts, _source


class _Executor:
    engine_id = "gstreamer"

    def __init__(self) -> None:
        self.receipt = ""
        self.releases: list[str] = []
        self.aborts: list[str] = []

    def prepare(self, plan) -> str:
        self.receipt = f"receipt:{plan.plan_id}"
        return self.receipt

    def commit(self, receipt: str) -> None:
        assert receipt == self.receipt

    def abort(self, receipt: str, reason: str) -> OutputExecutorAbortDisposition:
        self.aborts.append(reason)
        return (
            OutputExecutorAbortDisposition.CANDIDATE_DISCARDED
            if receipt == self.receipt
            else OutputExecutorAbortDisposition.STALE
        )

    def release(self, reason: str) -> None:
        self.releases.append(reason)


def _service(facts_for_path) -> OutputSessionService:
    return OutputSessionService(
        OutputPlanner(),
        facts_provider=facts_for_path,
        executors={"gstreamer": _Executor()},
    )


def _commit(service: OutputSessionService, path: str) -> None:
    media = Path(path)
    token = service.prepare_for_media(media)
    service.commit_media(token, media)


def test_r80_20_same_tuple_transition_remains_strict_and_not_gapless_claim() -> None:
    service = _service(lambda _path: _facts())
    _commit(service, "a.flac")
    first_plan = service.plan

    token = service.prepare_for_media(Path("b.flac"))

    assert service.state is OutputSessionState.READY
    assert service.last_transition_kind is DirectTransitionKind.SAME_TUPLE
    assert service.plan is not first_plan
    assert service.plan.requested_pcm == first_plan.requested_pcm
    assert service.plan.volume_policy is VolumePolicy.FIXED
    assert service.plan.fallback is FallbackKind.STOP
    assert service.plan.allow_resample is False
    assert service.plan.allow_remix is False
    assert token


def test_r80_21_cross_rate_is_explicit_reconfigure_without_resample() -> None:
    def facts(path: Path):
        if path.stem == "rate44":
            return _facts(
                source=_source(rate=44_100),
                evidence=(_evidence(rate=44_100),),
            )
        return _facts()

    service = _service(facts)
    _commit(service, "rate96.flac")
    first_plan_id = service.plan.plan_id

    service.prepare_for_media(Path("rate44.flac"))

    assert service.last_transition_kind is DirectTransitionKind.RECONFIGURE
    assert service.plan.plan_id != first_plan_id
    assert service.plan.requested_pcm.rate_hz == 44_100
    assert service.plan.requested_pcm.transport_format == "S32_LE"
    assert service.plan.allow_resample is False
    assert service.plan.sink.factory == "alsasink"


def test_r80_22_new_binding_generation_is_reacquire_not_plan_reuse() -> None:
    def facts(path: Path):
        generation = 2 if path.stem == "generation2" else 1
        return _facts(binding=_binding(generation=generation))

    service = _service(facts)
    _commit(service, "generation1.flac")
    first_plan_id = service.plan.plan_id

    service.prepare_for_media(Path("generation2.flac"))

    assert service.last_transition_kind is DirectTransitionKind.REACQUIRE
    assert service.plan.plan_id != first_plan_id
    assert service.plan.binding.generation == 2


def test_r80_29_30_reconnect_ack_rejects_stale_and_never_restores_old_plan() -> None:
    service = _service(lambda _path: _facts())
    _commit(service, "a.flac")
    old_plan = service.plan
    service.topology_lost(old_plan.stable_device_id, 2)

    assert service.state is OutputSessionState.LOST
    assert service.rebind_after_topology_change(old_plan.stable_device_id, 1) is False
    assert service.state is OutputSessionState.LOST
    assert service.plan is None
    assert service.rebind_after_topology_change("usb:other", 3) is False
    assert service.rebind_after_topology_change(old_plan.stable_device_id, 3) is True
    assert service.state is OutputSessionState.IDLE
    assert service.plan is None


def test_unrelated_topology_loss_cannot_release_active_direct_device() -> None:
    service = _service(lambda _path: _facts())
    _commit(service, "a.flac")

    service.topology_lost("usb:unrelated", 2)

    assert service.state is OutputSessionState.RUNNING
    assert service.active_plan is not None


def test_duplicate_topology_loss_releases_executor_exactly_once() -> None:
    executor = _Executor()
    service = OutputSessionService(
        OutputPlanner(),
        facts_provider=lambda _path: _facts(),
        executors={"gstreamer": executor},
    )
    _commit(service, "a.flac")
    stable_id = service.active_device_id

    service.topology_lost(stable_id, 2)
    service.topology_lost(stable_id, 2)

    assert executor.releases == ["device_lost"]
    assert service.state is OutputSessionState.LOST


def test_rebind_requires_generation_newer_than_lost_binding() -> None:
    service = _service(lambda _path: _facts())
    _commit(service, "a.flac")
    stable_id = service.active_device_id
    service.topology_lost(stable_id, 2)

    assert service.rebind_after_topology_change(stable_id, 1) is False
    assert service.state is OutputSessionState.LOST


def test_plan_freshness_guard_aborts_candidate_before_session_activation() -> None:
    executor = _Executor()
    service = OutputSessionService(
        OutputPlanner(),
        facts_provider=lambda _path: _facts(),
        executors={"gstreamer": executor},
        plan_still_current=lambda _plan: False,
    )

    with pytest.raises(OutputSessionError, match="OUTPUT_BINDING_STALE"):
        service.prepare_for_media(Path("stale.flac"))

    assert executor.receipt == ""
    assert executor.aborts == []
    assert service.state is OutputSessionState.IDLE
    assert service.active_plan is None


def test_initial_direct_prepare_has_no_replacement_classification() -> None:
    service = _service(lambda _path: _facts())

    service.prepare_for_media(Path("first.flac"))

    assert service.state is OutputSessionState.READY
    assert service.last_transition_kind is None
