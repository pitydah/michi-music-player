"""AP2-F06 WU2 — Managed PCM through the canonical OutputSessionService.

The session recognizes OutputPathPreference.MANAGED, plans through the
Managed planner, executes in the worker phase (never the owner), commits the
session state only after the execution exists, and retires the execution on
abort/release/device-loss/stale completion.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from michi.application.audio_output_planner import PlannerFacts
from michi.application.managed_pcm_output_planner import (
    ManagedPcmOutputPlanner,
    ManagedPcmPlannerFacts,
)
from michi.application.output_session_service import (
    ManagedOutputPrepared,
    OutputRequest,
    OutputSessionError,
    OutputSessionService,
)
from michi.domain.audio_device import AudioDeviceBinding, BindingKind
from michi.domain.audio_evidence import (
    CapabilityEvidence,
    DecodedSourceSignal,
    EvidenceStrength,
    PcmTuple,
)
from michi.domain.audio_output import (
    AudioOutputProfile,
    FallbackKind,
    OutputPathPreference,
    RatePolicy,
    VolumePolicy,
)
from michi.domain.managed_pcm_output import ManagedPcmOutputPlan

PATH = Path("/media/managed.flac")


def _binding(available: bool = True, generation: int = 3) -> AudioDeviceBinding:
    return AudioDeviceBinding(
        kind=BindingKind.ALSA_PCM,
        locator="hw:2,0",
        generation=generation,
        currently_available=available,
    )


def _facts(*, available: bool = True, generation: int = 3) -> PlannerFacts:
    binding = _binding(available=available, generation=generation)
    profile = AudioOutputProfile(
        profile_id="profile:managed",
        stable_device_id="dev:dac",
        path=OutputPathPreference.MANAGED,
        rate_policy=RatePolicy.SOURCE_NATIVE,
        volume_policy=VolumePolicy.SOFTWARE,
        allow_resample=False,
        allow_remix=False,
        allow_processing=True,
        fallback=FallbackKind.STOP,
    )
    evidence = (
        CapabilityEvidence(
            stable_device_id="dev:dac",
            tuple=PcmTuple(44100, "S16LE", 2, 16),
            supported=True,
            strength=EvidenceStrength.OPENED,
            source="test",
            observed_at_ns=1,
            environment_fingerprint="fp",
            evidence_refs=("ref",),
        ),
    )
    return PlannerFacts(
        active_engine_id="gstreamer",
        profile=profile,
        selected_device_id="dev:dac",
        binding=binding,
        decoded_source=DecodedSourceSignal(
            encoding="PCM",
            rate_hz=44100,
            significant_bits=16,
            channels=2,
            channel_positions=("FL", "FR"),
        ),
        source_file_facts=None,
        evidence=evidence,
        expected_binding_generation=generation,
        device_available=available,
    )


def _plan(facts: PlannerFacts) -> ManagedPcmOutputPlan:
    result = ManagedPcmOutputPlanner().plan(
        ManagedPcmPlannerFacts(
            selected_device_id=facts.selected_device_id,
            binding=facts.binding,
            binding_device_id=facts.selected_device_id,
            source_pcm=PcmTuple(44100, "", 2, 16),
            compiled_plan=None,
            terminal_formats=frozenset({"S16LE"}),
            volume_policy=facts.profile.volume_policy.value,
            selection_revision=0,
            current_selection_revision=0,
        )
    )
    assert isinstance(result, ManagedPcmOutputPlan), result
    return result


class _Provider:
    def __init__(self) -> None:
        self.next_request: OutputRequest | None = None

    def __call__(self, _path: Path) -> OutputRequest:
        if self.next_request is not None:
            return self.next_request
        facts = _facts()
        return OutputRequest(facts, facts.selected_device_id, facts.profile.profile_id)


class _ManagedHook:
    def __init__(self) -> None:
        self.prepared: list[ManagedOutputPrepared] = []
        self.aborted: list[tuple[str, str]] = []
        self.fail_with: Exception | None = None
        self.binding_current = True
        self.abort_result = {"stopped": True, "stale": False}

    def prepare(
        self, _path: Path, facts: PlannerFacts, instance_id: str
    ) -> ManagedOutputPrepared:
        if self.fail_with is not None:
            raise self.fail_with
        plan = _plan(facts)
        prepared = ManagedOutputPrepared(
            plan=plan,
            execution_id=instance_id,
            runtime_identity={"managed": True, "loaded": True},
        )
        self.prepared.append(prepared)
        return prepared

    def abort(self, prepared: ManagedOutputPrepared, reason: str):
        self.aborted.append((prepared.execution_id, reason))
        return dict(self.abort_result)

    def still_current(self, _plan: ManagedPcmOutputPlan) -> bool:
        return self.binding_current


def _service(provider: _Provider, hook: _ManagedHook, **kwargs):
    return OutputSessionService(
        planner=None,
        request_provider=provider,
        managed_prepare=hook.prepare,
        managed_abort=hook.abort,
        managed_plan_still_current=hook.still_current,
        **kwargs,
    )


def test_managed_prepare_commit_and_release_through_the_session() -> None:
    provider = _Provider()
    hook = _ManagedHook()
    service = _service(provider, hook)

    token = service.prepare_for_media(PATH)
    assert token.startswith("output-tx:managed:")
    assert service.mode == "managed"
    assert service.state.value == "ready"
    selection = service.selection_state()
    assert selection.active_device_id == "dev:dac"
    assert selection.active_plan_id == hook.prepared[0].plan.plan_id
    assert service.active_device_id == "dev:dac"
    assert service.volume_policy is VolumePolicy.SOFTWARE
    assert service.allows_automatic_engine_fallback() is False
    assert service.requires_release_on_media_loss is True

    service.commit_media(token, PATH)
    assert service.state.value == "running"

    service.release_active("stop")
    assert service.state.value == "idle"
    assert service.mode == "shared"
    assert hook.aborted and hook.aborted[-1][1] == "stop"


def test_managed_abort_retires_the_execution() -> None:
    provider = _Provider()
    hook = _ManagedHook()
    service = _service(provider, hook)
    token = service.prepare_for_media(PATH)
    service.abort_media(token, "load_failed")
    assert service.state.value == "idle"
    assert hook.aborted and hook.aborted[-1][1] == "load_failed"


def test_managed_supersession_aborts_the_previous_execution() -> None:
    provider = _Provider()
    hook = _ManagedHook()
    service = _service(provider, hook)
    service.prepare_for_media(PATH)
    first = hook.prepared[0]
    service.prepare_for_media(PATH)
    assert hook.prepared[1] is not first
    assert (first.execution_id, "superseded") in hook.aborted
    assert service.state.value == "ready"


def test_stale_binding_refuses_and_aborts_the_execution() -> None:
    provider = _Provider()
    hook = _ManagedHook()
    hook.binding_current = False
    service = _service(provider, hook)
    with pytest.raises(OutputSessionError) as info:
        service.prepare_for_media(PATH)
    assert info.value.code == "OUTPUT_BINDING_STALE"
    assert hook.aborted and hook.aborted[-1][1] == "binding_stale_during_prepare"
    assert service.state.value == "idle"


def test_managed_device_loss_retires_execution_and_session() -> None:
    provider = _Provider()
    hook = _ManagedHook()
    service = _service(provider, hook)
    service.prepare_for_media(PATH)
    service.commit_media(service.active_token_for_test(), PATH) if False else None
    service.device_lost("dev:dac", 9)
    assert service.state.value == "lost"
    assert hook.aborted and hook.aborted[-1][1] == "device_lost"
    assert service.mode == "lost"
    assert service.selection_state().active_device_id is None


class _TypedExecutionError(RuntimeError):
    code = "MANAGED_PCM_LOAD_FAILED"


def test_prepare_failure_preserves_selected_intent() -> None:
    provider = _Provider()
    hook = _ManagedHook()
    hook.fail_with = _TypedExecutionError("no such device")
    service = _service(provider, hook)
    with pytest.raises(OutputSessionError) as info:
        service.prepare_for_media(PATH)
    assert info.value.code == "MANAGED_PCM_LOAD_FAILED"
    assert service.state.value == "idle"
    assert service.selection_state().selected_device_id == "dev:dac"


class _DeferredExecutor:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.completions: list[tuple] = []
        self.worker_idents: list[int] = []
        self.owner_ident = threading.get_ident()

    def submit(self, work, completed) -> None:
        def run() -> None:
            with self.lock:
                self.worker_idents.append(threading.get_ident())
            try:
                value = work()
            except Exception as exc:  # noqa: BLE001
                with self.lock:
                    self.completions.append((completed, None, exc))
            else:
                with self.lock:
                    self.completions.append((completed, value, None))

        threading.Thread(target=run, daemon=True).start()

    def deliver(self) -> int:
        delivered = 0
        while True:
            with self.lock:
                if not self.completions:
                    return delivered
                completed, value, error = self.completions.pop(0)
            completed(value, error)
            delivered += 1

    def wait(self, timeout: float = 5.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self.lock:
                if self.completions:
                    return
            time.sleep(0.005)
        raise AssertionError("no completion arrived")


def test_async_managed_preparation_runs_in_worker_and_commits_on_owner() -> None:
    provider = _Provider()
    hook = _ManagedHook()
    executor = _DeferredExecutor()
    service = _service(provider, hook, async_submit=executor.submit)
    tokens: list[str] = []
    failures: list[Exception] = []
    service.prepare_for_media_async(PATH, tokens.append, failures.append)
    assert tokens == []  # the owner returned before any work
    executor.wait()
    threads: list[int] = []

    def owner_turn() -> None:
        threads.append(threading.get_ident())
        executor.deliver()

    owner_turn()
    assert threads == [executor.owner_ident]
    assert tokens and not failures
    assert executor.worker_idents[0] != executor.owner_ident
    assert service.mode == "managed"
    assert service.state.value == "ready"


def test_stale_async_completion_aborts_the_prepared_execution() -> None:
    provider = _Provider()
    hook = _ManagedHook()
    executor = _DeferredExecutor()
    service = _service(provider, hook, async_submit=executor.submit)
    tokens: list[str] = []
    failures: list[Exception] = []
    service.prepare_for_media_async(PATH, tokens.append, failures.append)
    # Supersede BEFORE the owner delivers the first completion.
    service.prepare_for_media_async(PATH, tokens.append, failures.append)
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        with executor.lock:
            if len(executor.completions) >= 2:
                break
        time.sleep(0.005)
    executor.deliver()
    assert len(failures) == 1 and failures[0].code == "OUTPUT_PREPARATION_STALE"
    assert any(reason == "superseded_before_commit" for _, reason in hook.aborted)
    assert len(tokens) == 1, "the current preparation never committed"
    assert service.state.value == "ready"


def test_managed_session_publishes_output_family_events_on_one_recorder() -> None:
    from michi.domain.signal_truth import OutputFamilyState, SignalTruthRecorder

    recorder = SignalTruthRecorder()
    provider = _Provider()
    hook = _ManagedHook()
    service = _service(provider, hook, truth_recorder=recorder)
    token = service.prepare_for_media(PATH)
    assert recorder.output_family_events[-1].state is OutputFamilyState.READY
    service.commit_media(token, PATH)
    assert recorder.output_family_events[-1].state is OutputFamilyState.RUNNING
    service.device_lost("dev:dac", 5)
    assert recorder.output_family_events[-1].state is OutputFamilyState.UNAVAILABLE
    assert all(event.family == "managed" for event in recorder.output_family_events)
    assert all(event.bit_perfect is None for event in recorder.output_family_events)
    assert recorder.output_family_events[0].device_id == "dev:dac"
    assert recorder.output_family_events[0].execution_id
    # No DAC verdict was fabricated by the output-family stream.
    assert recorder.active_snapshot is None
    assert recorder.last_snapshot is None
    assert recorder.processing_events == ()


def test_stale_managed_abort_is_expected_not_a_cleanup_failure() -> None:
    provider = _Provider()
    hook = _ManagedHook()
    hook.abort_result = {"stopped": False, "stale": True}
    service = _service(provider, hook)
    token = service.prepare_for_media(PATH)
    service.abort_media(token, "superseded")
    assert service.state.value == "idle"
    assert service.last_cleanup_diagnostic is None


def test_failed_managed_abort_records_a_diagnostic() -> None:
    provider = _Provider()
    hook = _ManagedHook()
    hook.abort_result = {
        "stopped": False,
        "stale": False,
        "code": "MANAGED_STOP_FAILED",
        "reason": "host refused",
    }
    service = _service(provider, hook)
    token = service.prepare_for_media(PATH)
    service.abort_media(token, "load_failed")
    diagnostic = service.last_cleanup_diagnostic
    assert diagnostic is not None
    assert diagnostic.code == "MANAGED_STOP_FAILED"
    assert "host refused" in diagnostic.detail


def test_each_managed_preparation_gets_a_new_execution_instance() -> None:
    provider = _Provider()
    hook = _ManagedHook()
    service = _service(provider, hook)
    service.prepare_for_media(PATH)
    service.prepare_for_media(PATH)
    first, second = hook.prepared[-2], hook.prepared[-1]
    # Same plan identity, different execution instance.
    assert first.plan.plan_id == second.plan.plan_id
    assert first.execution_id != second.execution_id
    assert first.execution_id.startswith("exec-instance:")


def test_measurements_are_bound_to_the_execution_and_discarded_on_retire() -> None:
    from michi.domain.signal_truth import (
        ProcessingMeasurement,
        SignalTruthRecorder,
    )

    recorder = SignalTruthRecorder()
    provider = _Provider()
    hook = _ManagedHook()
    service = _service(provider, hook, truth_recorder=recorder)
    token = service.prepare_for_media(PATH)
    prepared = hook.prepared[-1]
    recorder.record_processing_measurement(
        ProcessingMeasurement(
            execution_id=prepared.execution_id,
            plan_id=prepared.plan.plan_id,
            sample_peak=0.9,
            estimated_true_peak=0.95,
            worst_channel=1,
            channels=2,
            sample_rate_hz=44100,
            window="0.8s",
            evidence_level="NATIVE_GSTREAMER",
            sequence=1,
        )
    )
    assert len(recorder.processing_measurements) == 1
    service.abort_media(token, "superseded")
    assert recorder.processing_measurements == ()


def test_measurement_requires_an_execution_identity() -> None:
    from michi.domain.signal_truth import (
        ProcessingMeasurement,
        SignalTruthRecorder,
    )

    recorder = SignalTruthRecorder()
    with pytest.raises(ValueError):
        recorder.record_processing_measurement(
            ProcessingMeasurement(
                execution_id="",
                plan_id="p",
                sample_peak=None,
                estimated_true_peak=None,
                worst_channel=None,
                channels=None,
                sample_rate_hz=None,
                window="w",
                evidence_level="UNIT",
                sequence=1,
            )
        )
