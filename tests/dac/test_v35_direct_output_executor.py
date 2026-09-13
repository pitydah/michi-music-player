"""DAC-V35-050C1 — Direct executor generation core gates (C1-01..C1-10)."""

from __future__ import annotations

import dataclasses

import pytest

from michi.infrastructure.audio_output.direct_output_executor import (
    DirectExecutionState,
    DirectExecutorError,
    GStreamerDirectOutputExecutor,
)
from michi.infrastructure.audio_output.runtime_inspector import (
    DirectRuntimeSnapshot,
)


def _plan(plan_id: str = "plan:test", rate: int = 96000):
    from michi.domain.audio_device import AudioDeviceBinding, BindingKind
    from michi.domain.audio_evidence import PcmTuple
    from michi.domain.audio_output import (
        FallbackKind,
        GstSinkSpec,
        OutputPlan,
        PathSemantics,
        VolumePolicy,
    )

    binding = AudioDeviceBinding(
        kind=BindingKind.ALSA_PCM,
        locator="hw:CARD=DX5,DEV=0",
        generation=1,
        currently_available=True,
        card_index=1,
        pcm_device=0,
    )
    return OutputPlan(
        plan_id=plan_id,
        stable_device_id="usb:test",
        binding=binding,
        path_semantics=PathSemantics.HARDWARE_RAW,
        requested_pcm=PcmTuple(rate, "S32_LE", 2, 24),
        engine_id="gstreamer",
        volume_policy=VolumePolicy.FIXED,
        allow_resample=False,
        allow_remix=False,
        allow_processing=False,
        fallback=FallbackKind.STOP,
        sink=GstSinkSpec(factory="alsasink", device="hw:CARD=DX5,DEV=0"),
        resync_delay_ms=0,
        preconditions=("engine_gstreamer_direct",),
        evidence_refs=("probe:1",),
        decision_codes=("ENGINE_GSTREAMER_DIRECT",),
    )


def _snapshot(
    execution_generation: int = 1,
    plan_id: str = "plan:test",
    **overrides,
) -> DirectRuntimeSnapshot:
    base: dict = dict(
        execution_generation=execution_generation,
        port_generation=7,
        plan_id=plan_id,
        sink_factory="alsasink",
        sink_device="hw:CARD=DX5,DEV=0",
        negotiated_format="S32LE",
        negotiated_rate_hz=96000,
        negotiated_channels=2,
        graph_factories=("capsfilter", "alsasink"),
    )
    base.update(overrides)
    return DirectRuntimeSnapshot(**base)


def test_c1_01_stage_increments_generation_and_stages() -> None:
    executor = GStreamerDirectOutputExecutor()
    handle = executor.stage(_plan())
    assert handle.generation == 1
    assert handle.plan_id == "plan:test"
    assert executor.state is DirectExecutionState.STAGED
    assert executor.handle == handle


def test_c1_02_stage_replaces_previous_execution() -> None:
    executor = GStreamerDirectOutputExecutor()
    handle_a = executor.stage(_plan("plan:A"))
    handle_b = executor.stage(_plan("plan:B"))
    assert handle_b.generation == handle_a.generation + 1
    assert executor.handle == handle_b
    with pytest.raises(DirectExecutorError) as exc_info:
        executor.recipe_for_load(handle_a)
    assert exc_info.value.code == "DIRECT_STALE_EXECUTION"


def test_c1_03_same_plan_new_generation_makes_old_snapshot_stale() -> None:
    """plan_id NO es autoridad suficiente: la generación manda."""
    executor = GStreamerDirectOutputExecutor()
    handle_1 = executor.stage(_plan("plan:P"))
    executor.stage(_plan("plan:P"))  # mismo plan, nueva ejecución
    stale_snapshot = _snapshot(execution_generation=handle_1.generation)

    with pytest.raises(DirectExecutorError) as exc_info:
        executor.verify_preroll(handle_1, stale_snapshot)
    assert exc_info.value.code == "DIRECT_STALE_EXECUTION"


def test_c1_04_exact_snapshot_yields_evidence_and_verified_state() -> None:
    executor = GStreamerDirectOutputExecutor()
    handle = executor.stage(_plan())
    evidence = executor.verify_preroll(handle, _snapshot(execution_generation=1))

    assert evidence.plan_id == "plan:test"
    assert evidence.execution_generation == handle.generation
    assert evidence.port_generation == 7, "port_generation se preserva intacta"
    assert evidence.negotiated_format == "S32LE"
    assert evidence.negotiated_rate_hz == 96000
    assert evidence.negotiated_channels == 2
    assert executor.state is DirectExecutionState.PREROLL_VERIFIED
    assert executor.evidence_for(handle) == evidence


def test_c1_05_wrong_generation_never_reaches_validate_runtime(monkeypatch) -> None:
    from michi.infrastructure.audio_output import direct_output_executor as mod

    calls: list[tuple] = []

    def _spy(recipe, snapshot):
        calls.append((recipe, snapshot))
        raise AssertionError("validate_runtime no debe ejecutarse")

    monkeypatch.setattr(mod, "validate_runtime", _spy)

    executor = GStreamerDirectOutputExecutor()
    handle = executor.stage(_plan())
    with pytest.raises(DirectExecutorError) as exc_info:
        executor.verify_preroll(handle, _snapshot(execution_generation=99))
    assert exc_info.value.code == "DIRECT_STALE_EXECUTION"
    assert calls == []


def test_c1_06_runtime_mismatch_leaves_staged_without_evidence() -> None:
    from michi.infrastructure.audio_output.runtime_inspector import (
        DirectRuntimeValidationError,
    )

    executor = GStreamerDirectOutputExecutor()
    handle = executor.stage(_plan())
    with pytest.raises(DirectRuntimeValidationError) as exc_info:
        executor.verify_preroll(
            handle, _snapshot(execution_generation=1, negotiated_rate_hz=48000)
        )
    assert exc_info.value.code == "DIRECT_RATE_MISMATCH"
    assert executor.state is DirectExecutionState.STAGED
    assert executor.evidence_for(handle) is None
    assert executor.is_preroll_verified(handle) is False


def test_c1_07_is_preroll_verified_only_for_current() -> None:
    executor = GStreamerDirectOutputExecutor()
    handle_a = executor.stage(_plan("plan:A"))
    executor.verify_preroll(
        handle_a, _snapshot(execution_generation=1, plan_id="plan:A")
    )
    handle_b = executor.stage(_plan("plan:B"))

    assert executor.is_preroll_verified(handle_a) is False, "stale -> False"
    assert executor.is_preroll_verified(handle_b) is False, "staged sin verify"


def test_c1_08_abort_current_returns_idle() -> None:
    executor = GStreamerDirectOutputExecutor()
    handle = executor.stage(_plan())
    executor.abort(handle, "media_rejected")

    assert executor.state is DirectExecutionState.IDLE
    assert executor.handle is None
    with pytest.raises(DirectExecutorError) as exc_info:
        executor.recipe_for_load(handle)
    assert exc_info.value.code == "DIRECT_STALE_EXECUTION"


def test_c1_09_stale_abort_does_not_affect_current_execution() -> None:
    executor = GStreamerDirectOutputExecutor()
    handle_a = executor.stage(_plan("plan:A"))
    handle_b = executor.stage(_plan("plan:B"))

    executor.abort(handle_a, "superseded")  # stale

    assert executor.state is DirectExecutionState.STAGED
    assert executor.handle == handle_b
    assert executor.recipe_for_load(handle_b) is not None


def test_c1_10_release_is_idempotent() -> None:
    executor = GStreamerDirectOutputExecutor()
    executor.stage(_plan())
    executor.release("stop")
    executor.release("stop")

    assert executor.state is DirectExecutionState.IDLE
    assert executor.handle is None
    assert executor.generation == 1, "release no incrementa generation"


def test_c1_11_handle_is_immutable() -> None:
    executor = GStreamerDirectOutputExecutor()
    handle = executor.stage(_plan())
    with pytest.raises(dataclasses.FrozenInstanceError):
        handle.generation = 99  # type: ignore[misc]
