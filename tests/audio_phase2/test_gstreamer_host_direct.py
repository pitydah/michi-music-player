"""Direct transport tests: wire DTOs and real executor callbacks over IPC.

The child only reports facts; the real GStreamerDirectOutputExecutor stays in
the parent and executes verify_preroll / begin_runtime / observe_runtime /
mark_previous_source_released / abort / release through bounded reverse
callbacks.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from michi.application.audio_output_ports import OutputExecutorAbortDisposition
from michi.domain.audio_device import AudioDeviceBinding, BindingKind
from michi.domain.audio_evidence import PcmTuple, RuntimeTransformEvidence
from michi.domain.audio_output import (
    FallbackKind,
    GstSinkSpec,
    OutputPlan,
    PathSemantics,
    VolumePolicy,
)
from michi.infrastructure.audio_engines.gstreamer_host_client import (
    GStreamerHostSupervisor,
)
from michi.infrastructure.audio_engines.gstreamer_host_direct import (
    handle_from_wire,
    handle_to_wire,
    preparation_from_wire,
    preparation_to_wire,
    recipe_from_wire,
    recipe_to_wire,
    snapshot_from_wire,
    snapshot_to_wire,
)
from michi.infrastructure.audio_engines.gstreamer_host_port import (
    GStreamerHostedAudioPort,
)
from michi.infrastructure.audio_output.direct_output_executor import (
    DirectExecutionHandle,
    DirectExecutionState,
    DirectExecutorError,
    DirectLoadPreparation,
    GStreamerDirectOutputExecutor,
)
from michi.infrastructure.audio_output.runtime_inspector import (
    DirectRuntimeSnapshot,
)
from michi.infrastructure.audio_output.strict_sink import recipe_from_plan

FAKE_HOST = Path(__file__).parent / "gst_host_engine_fake.py"
FAST = {
    "start_timeout_s": 1.5,
    "command_timeout_s": 2.0,
    "terminate_grace_s": 0.5,
    "term_grace_s": 0.3,
    "kill_grace_s": 0.5,
}


def _plan(plan_id: str = "plan:direct", rate: int = 96000) -> OutputPlan:
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


def _snapshot(execution_generation: int = 1) -> DirectRuntimeSnapshot:
    return DirectRuntimeSnapshot(
        execution_generation=execution_generation,
        port_generation=7,
        plan_id="plan:direct",
        sink_factory="alsasink",
        sink_device="hw:CARD=DX5,DEV=0",
        negotiated_format="S32LE",
        negotiated_rate_hz=96000,
        negotiated_channels=2,
        graph_factories=("capsfilter", "alsasink"),
        transform_evidence=RuntimeTransformEvidence(
            converter_present=True,
            converter_transforming=None,
            resampler_present=False,
            resampler_transforming=None,
            remix_transforming=None,
            converter_dithering_disabled=True,
            converter_noise_shaping_disabled=None,
        ),
        decoded_format="S24LE",
        decoded_rate_hz=96000,
        decoded_channels=2,
        decoded_significant_bits=24,
        effective_significant_bits=24,
        software_gain=1.0,
        muted=False,
    )


def _port(behavior: str, *, with_executor: bool = False):
    def factory(fd: int) -> list[str]:
        return [
            sys.executable,
            str(FAKE_HOST),
            "--fd",
            str(fd),
            "--engine-behavior",
            behavior,
        ]

    supervisor = GStreamerHostSupervisor(command_factory=factory, **FAST)
    executor = GStreamerDirectOutputExecutor() if with_executor else None
    port = GStreamerHostedAudioPort(
        supervisor,
        command_deadline_s=FAST["command_timeout_s"],
        load_deadline_s=FAST["command_timeout_s"],
        direct_executor=executor,
    )
    if executor is not None:
        executor.bind_port_provider(lambda: port)
    return supervisor, port, executor


# ── wire codecs ───────────────────────────────────────────────────────
def test_wire_roundtrip_handle_recipe_preparation_snapshot() -> None:
    handle = DirectExecutionHandle(generation=3, plan_id="plan:direct")
    assert handle_from_wire(handle_to_wire(handle)) == handle

    recipe = recipe_from_plan(_plan())
    assert recipe_from_wire(recipe_to_wire(recipe)) == recipe

    preparation = DirectLoadPreparation(handle, recipe, candidate_volume=1.0)
    assert preparation_from_wire(preparation_to_wire(preparation)) == preparation

    snapshot = _snapshot(execution_generation=3)
    assert snapshot_from_wire(snapshot_to_wire(snapshot)) == snapshot


def test_wire_validation_rejects_malformed_payloads() -> None:
    from michi.infrastructure.audio_engines.gstreamer_host_protocol import (
        HostProtocolError,
    )

    bad_handle = {"generation": -1, "plan_id": "p"}
    with pytest.raises(HostProtocolError):
        handle_from_wire(bad_handle)
    with pytest.raises(HostProtocolError):
        handle_from_wire({"generation": 1})
    with pytest.raises(HostProtocolError):
        recipe_from_wire({"plan_id": "p"})
    with pytest.raises(HostProtocolError):
        preparation_from_wire({"handle": {}, "recipe": {}, "candidate_volume": "x"})
    with pytest.raises(HostProtocolError):
        snapshot_from_wire({"execution_generation": 1})
    with pytest.raises(HostProtocolError):
        snapshot_from_wire(
            {
                "execution_generation": 1,
                "port_generation": 1,
                "plan_id": "p",
                "sink_factory": "alsasink",
                "sink_device": "d",
                "graph_factories": ["alsasink", 5],
            }
        )


# ── flujo real con el executor en el parent ───────────────────────────
def test_direct_stage_and_verify_preroll_run_through_ipc() -> None:
    supervisor, port, executor = _port("normal", with_executor=True)
    try:
        port.activate()
        receipt = executor.prepare(_plan())
        handle = executor.handle
        assert handle is not None
        assert executor.state is DirectExecutionState.STAGED
        port.play()  # the child triggers the real Direct reversals in order
        assert executor.is_preroll_verified(handle)
        assert executor.state is DirectExecutionState.PREROLL_VERIFIED
        evidence = executor.evidence_for(handle)
        assert evidence is not None
        assert evidence.port_generation == 7
        assert evidence.negotiated_rate_hz == 96000
        executor.commit(receipt)
        assert executor.state is DirectExecutionState.COMMITTED
    finally:
        port.close()
    # close() -> child port release -> parent executor.release
    assert executor.state is DirectExecutionState.IDLE
    assert not supervisor.pid_alive()


def test_stale_direct_snapshot_is_rejected_by_the_parent_executor() -> None:
    from michi.application.ports import AudioTransportCommandError

    supervisor, port, executor = _port("direct_stale", with_executor=True)
    try:
        port.activate()
        executor.prepare(_plan())
        handle = executor.handle
        assert handle is not None
        with pytest.raises(AudioTransportCommandError):
            port.play()
        # Fail-closed: the candidate is NOT verified and no evidence exists.
        assert not executor.is_preroll_verified(handle)
        assert executor.state is DirectExecutionState.STAGED
        assert executor.evidence_for(handle) is None
    finally:
        port.close()
    assert executor.state is DirectExecutionState.IDLE


def test_abort_discards_the_child_mirror() -> None:
    supervisor, port, executor = _port("normal", with_executor=True)
    try:
        port.activate()
        receipt = executor.prepare(_plan())
        disposition = executor.abort(receipt, "test_abort")
        assert disposition is OutputExecutorAbortDisposition.CANDIDATE_DISCARDED
        assert executor.state is DirectExecutionState.IDLE
        # The child no longer stages anything: play publishes no Direct work.
        port.play()
        assert executor.state is DirectExecutionState.IDLE
    finally:
        port.close()


def test_stage_with_foreign_executor_identity_is_rejected() -> None:
    supervisor, port, executor = _port("normal", with_executor=True)
    try:
        port.activate()
        recipe = recipe_from_plan(_plan())
        preparation = DirectLoadPreparation(
            DirectExecutionHandle(generation=1, plan_id="plan:direct"),
            recipe,
            candidate_volume=1.0,
        )
        with pytest.raises(DirectExecutorError) as info:
            port.stage_direct_load(preparation, executor=object())
        assert info.value.code == "DIRECT_EXECUTOR_IDENTITY_MISMATCH"
    finally:
        port.close()


def test_stage_without_bound_executor_is_rejected() -> None:
    supervisor, port, _ = _port("normal", with_executor=False)
    try:
        port.activate()
        recipe = recipe_from_plan(_plan())
        preparation = DirectLoadPreparation(
            DirectExecutionHandle(generation=1, plan_id="plan:direct"),
            recipe,
            candidate_volume=1.0,
        )
        with pytest.raises(DirectExecutorError) as info:
            port.stage_direct_load(preparation, executor=None)
        assert info.value.code == "DIRECT_EXECUTOR_IDENTITY_MISMATCH"
    finally:
        port.close()
