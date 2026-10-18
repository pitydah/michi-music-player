"""AP2-F06 — Managed PCM productive route through the supervised host.

Lab-sink tests are HEADLESS proofs of the managed route (selected binding
identity + real DSP install). A physical DAC run is available only through an
explicit opt-in operator gate: the physical campaign remains PARKED.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

_HAS_GI = importlib.util.find_spec("gi") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_GI, reason="PyGObject/GStreamer not available on this host"
)

FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "evidence/dac-v35-110/2026-09-25-smsl-152a85dd-operator-run"
    / "fixtures/pcm16_44100.wav"
)
SLOW = {
    "start_timeout_s": 45.0,
    "command_timeout_s": 30.0,
    "terminate_grace_s": 5.0,
    "term_grace_s": 3.0,
    "kill_grace_s": 3.0,
}


def _real_port():
    from michi.infrastructure.audio_engines.gstreamer_host_client import (
        GStreamerHostSupervisor,
    )
    from michi.infrastructure.audio_engines.gstreamer_host_port import (
        GStreamerHostedAudioPort,
    )

    supervisor = GStreamerHostSupervisor(**SLOW)
    port = GStreamerHostedAudioPort(
        supervisor, command_deadline_s=30.0, load_deadline_s=30.0
    )
    return supervisor, port


def _planner_inputs(binding_locator: str = "hw:2,0"):
    from michi.application.managed_pcm_output_planner import (
        ManagedPcmPlannerFacts,
    )
    from michi.domain.audio_device import AudioDeviceBinding, BindingKind
    from michi.domain.audio_evidence import PcmTuple

    binding = AudioDeviceBinding(
        kind=BindingKind.ALSA_PCM,
        locator=binding_locator,
        generation=1,
        currently_available=True,
    )
    return ManagedPcmPlannerFacts(
        selected_device_id="dev:smsl-managed",
        binding=binding,
        binding_device_id="dev:smsl-managed",
        source_pcm=PcmTuple(
            rate_hz=44100, transport_format="S16LE", channels=2, significant_bits=16
        ),
        compiled_plan=None,
        terminal_formats=frozenset({"S16LE", "S32LE"}),
        volume_policy="software",
        selection_revision=1,
        current_selection_revision=1,
    )


def _compile_preamp(service, signal):
    from michi.application.effective_processing_graph import (
        EffectiveProcessingGraphResolver,
    )
    from michi.application.processing_graph_compiler import ProcessingGraphCompiler
    from michi.domain.audio_processing import PreampNode, ProcessingGraph

    graph = ProcessingGraph(
        graph_id="graph:managed",
        revision=1,
        nodes=(PreampNode(node_id="pre", gain_db=-6.0),),
    )
    effective = EffectiveProcessingGraphResolver().resolve(
        graph, input_signal=signal, assets=()
    )
    return ProcessingGraphCompiler().compile(
        effective, backend=service.capabilities, assets=()
    )


def test_managed_route_selects_the_binding_and_processes_real_media(
    monkeypatch,
) -> None:
    if not FIXTURE.is_file():
        pytest.skip("PCM fixture unavailable")
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    from dataclasses import replace as dc_replace

    from michi.application.audio_processing_service import AudioProcessingService
    from michi.application.managed_pcm_output_planner import (
        ManagedPcmOutputPlanner,
    )
    from michi.domain.audio_signal import ChannelLayout, PcmSignalFormat
    from michi.infrastructure.audio_output.managed_pcm_executor import (
        ManagedPcmExecutor,
    )
    from michi.infrastructure.audio_processing.native_mapping import (
        NativeProcessingMapping,
    )

    supervisor, port = _real_port()
    try:
        port.activate()
        service = AudioProcessingService(
            capability_query=port.query_processing_capabilities,
            native_mapping=NativeProcessingMapping(),
            transport=port,
        )
        service.refresh_capabilities()
        signal = PcmSignalFormat(
            rate_hz=44100,
            transport_format="S16LE",
            significant_bits=16,
            layout=ChannelLayout(positions=("FL", "FR")),
        )
        compiled = _compile_preamp(service, signal)
        facts = dc_replace(_planner_inputs("hw:2,0"), compiled_plan=compiled)
        plan = ManagedPcmOutputPlanner().plan(facts)
        assert type(plan).__name__ == "ManagedPcmOutputPlan", plan

        def installer(_plan):
            candidate = service.begin_candidate(
                compiled,
                host_generation=supervisor.host_generation,
                transport=port,
            )
            receipt = service.commit_candidate(candidate, transport=port)
            service.publish_effective(receipt)
            return {"revision": candidate.processing_generation}

        executor = ManagedPcmExecutor(lambda: port, install_processing=installer)
        receipt = executor.execute(plan, FIXTURE)
        assert receipt.path == "managed_pcm"
        assert receipt.device_locator == "hw:2,0"
        # Headless: the lab sink replaces the physical DAC; the identity says
        # so explicitly (no physical claim is fabricated).
        assert receipt.lab_sink is True
        assert receipt.runtime_identity["managed"] is True
        assert receipt.runtime_identity["device"] == "hw:2,0"
        # D1/D2: runtime evidence, not the requested recipe content.
        assert receipt.runtime_identity["evidence_level"] == "gstreamer_negotiated"
        negotiated = receipt.runtime_identity["negotiated"]
        assert negotiated["rate_hz"] == 44100
        assert negotiated["channels"] == 2
        # Lab route: fakesink accepts the DSP working format (F64LE) instead
        # of the strict sink caps; lab_sink=True records that explicitly.
        assert negotiated["format"] in {"S16LE", "F64LE"}
        assert "host_generation" in receipt.runtime_identity
        assert service.effective_state.value == "effective"
        assert receipt.processing_revision >= 1

        port.set_volume(0)
        # The diagnostic capture owns its bounded PLAYING window; a separate
        # play() would run the short fixture to EOS before measurement.
        metrics = port.capture_processing_output(0.5)
        assert metrics["frames"] > 0 and metrics["rms"] > 0.0
    finally:
        port.close()
        supervisor.close()


def test_managed_route_never_falls_back_to_the_default_output(monkeypatch) -> None:
    monkeypatch.delenv("MICHI_GST_LAB_SINK", raising=False)
    from michi.application.managed_pcm_output_planner import (
        ManagedPcmOutputPlanner,
    )
    from michi.infrastructure.audio_output.managed_pcm_executor import (
        ManagedPcmExecutionError,
        ManagedPcmExecutor,
    )

    supervisor, port = _real_port()
    try:
        port.activate()
        facts = _planner_inputs("hw:99,0")
        plan = ManagedPcmOutputPlanner().plan(facts)
        assert type(plan).__name__ == "ManagedPcmOutputPlan", plan
        executor = ManagedPcmExecutor(lambda: port)
        with pytest.raises(ManagedPcmExecutionError) as info:
            executor.execute(plan, FIXTURE)
        # The requested DAC does not exist: fail closed, never the default.
        assert info.value.code in (
            "MANAGED_PCM_LOAD_FAILED",
            "MANAGED_PCM_IDENTITY_UNAVAILABLE",
        )
        identity = port.query_managed_identity()
        assert identity.get("managed") is False or identity.get("loaded") is False
        assert port.backend_state() in (None, "STOPPED")
    finally:
        port.close()
        supervisor.close()


@pytest.mark.skipif(
    os.environ.get("MICHI_MANAGED_PHYSICAL_TEST") != "1",
    reason="physical DAC run requires the explicit operator gate (PARKED)",
)
def test_managed_route_to_a_physical_dac_operator_gate() -> None:
    """Opt-in only. Never part of automated CI; volume 0 (silent)."""
    device = os.environ.get("MICHI_MANAGED_PHYSICAL_DEVICE", "")
    if not device:
        pytest.skip("MICHI_MANAGED_PHYSICAL_DEVICE is not set")
    from michi.application.managed_pcm_output_planner import (
        ManagedPcmOutputPlanner,
    )
    from michi.infrastructure.audio_output.managed_pcm_executor import (
        ManagedPcmExecutor,
    )

    supervisor, port = _real_port()
    try:
        port.activate()
        plan = ManagedPcmOutputPlanner().plan(_planner_inputs(device))
        assert type(plan).__name__ == "ManagedPcmOutputPlan", plan
        receipt = ManagedPcmExecutor(lambda: port).execute(plan, FIXTURE)
        assert receipt.lab_sink is False
        assert receipt.runtime_identity["loaded"] is True
        assert receipt.runtime_identity["device"] == device
    finally:
        port.close()
        supervisor.close()


def test_output_session_managed_end_to_end_with_dsp(monkeypatch) -> None:
    """The USER-level session path: MANAGED profile -> planner -> executor ->
    DSP transaction -> selected binding -> RUNNING, all through the canonical
    OutputSessionService (no direct executor invocation from the test)."""
    if not FIXTURE.is_file():
        pytest.skip("PCM fixture unavailable")
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")

    from michi.application.audio_output_planner import PlannerFacts
    from michi.application.audio_processing_service import AudioProcessingService
    from michi.application.managed_pcm_output_planner import (
        ManagedPcmOutputPlanner,
        ManagedPcmPlannerFacts,
    )
    from michi.application.output_session_service import (
        ManagedOutputPrepared,
        OutputRequest,
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
    from michi.domain.audio_signal import ChannelLayout, PcmSignalFormat
    from michi.domain.managed_pcm_output import ManagedPcmOutputPlan
    from michi.infrastructure.audio_output.managed_pcm_executor import (
        ManagedPcmExecutor,
    )
    from michi.infrastructure.audio_processing.native_mapping import (
        NativeProcessingMapping,
    )

    supervisor, port = _real_port()
    try:
        port.activate()
        service = AudioProcessingService(
            capability_query=port.query_processing_capabilities,
            native_mapping=NativeProcessingMapping(),
            transport=port,
        )
        service.refresh_capabilities()
        signal = PcmSignalFormat(
            rate_hz=44100,
            transport_format="S16LE",
            significant_bits=16,
            layout=ChannelLayout(positions=("FL", "FR")),
        )
        compiled = _compile_preamp(service, signal)

        binding = AudioDeviceBinding(
            kind=BindingKind.ALSA_PCM,
            locator="hw:2,0",
            generation=1,
            currently_available=True,
        )
        profile = AudioOutputProfile(
            profile_id="profile:managed",
            stable_device_id="dev:managed",
            path=OutputPathPreference.MANAGED,
            rate_policy=RatePolicy.SOURCE_NATIVE,
            volume_policy=VolumePolicy.SOFTWARE,
            allow_resample=False,
            allow_remix=False,
            allow_processing=True,
            fallback=FallbackKind.STOP,
        )
        facts = PlannerFacts(
            active_engine_id="gstreamer",
            profile=profile,
            selected_device_id="dev:managed",
            binding=binding,
            decoded_source=DecodedSourceSignal(
                encoding="PCM",
                rate_hz=44100,
                significant_bits=16,
                channels=2,
                channel_positions=("FL", "FR"),
            ),
            evidence=(
                CapabilityEvidence(
                    stable_device_id="dev:managed",
                    tuple=PcmTuple(44100, "S16LE", 2, 16),
                    supported=True,
                    strength=EvidenceStrength.OPENED,
                    source="test",
                    observed_at_ns=1,
                    environment_fingerprint="fp",
                    evidence_refs=("ref",),
                ),
            ),
            expected_binding_generation=1,
            device_available=True,
        )
        request = OutputRequest(facts, "dev:managed", "profile:managed")
        planner = ManagedPcmOutputPlanner()
        executor = ManagedPcmExecutor(lambda: port)

        def managed_prepare(path, resolved_facts, instance_id):
            planner_facts = ManagedPcmPlannerFacts(
                selected_device_id=resolved_facts.selected_device_id,
                binding=resolved_facts.binding,
                binding_device_id=resolved_facts.selected_device_id,
                source_pcm=PcmTuple(44100, "", 2, 16),
                compiled_plan=compiled,
                terminal_formats=frozenset({"S16LE", "S32LE"}),
                volume_policy="software",
                selection_revision=0,
                current_selection_revision=0,
            )
            plan = planner.plan(planner_facts)
            assert isinstance(plan, ManagedPcmOutputPlan), plan

            def installer(_managed):
                candidate = service.begin_candidate(
                    compiled,
                    host_generation=supervisor.host_generation,
                    transport=port,
                )
                receipt = service.commit_candidate(candidate, transport=port)
                service.publish_effective(receipt)
                return {"revision": candidate.processing_generation}

            receipt = executor.execute(plan, path, install_processing=installer)
            return ManagedOutputPrepared(
                plan=plan,
                execution_id=receipt.execution_id,
                runtime_identity=dict(receipt.runtime_identity),
            )

        session = OutputSessionService(
            None,
            request_provider=lambda _path: request,
            managed_prepare=managed_prepare,
            managed_abort=lambda _prepared, _reason: port.stop(),
            managed_plan_still_current=lambda plan: True,
        )
        token = session.prepare_for_media(FIXTURE)
        assert session.mode == "managed"
        assert session.state.value == "ready"
        session.commit_media(token, FIXTURE)
        assert session.state.value == "running"
        assert session.active_device_id == "dev:managed"
        assert service.effective_state.value == "effective"

        identity = port.query_managed_identity()
        assert identity["managed"] is True
        assert identity["loaded"] is True
        assert identity["device"] == "hw:2,0"
        assert identity["evidence_level"] == "gstreamer_negotiated"
        assert identity["negotiated"]["rate_hz"] == 44100
        assert identity["negotiated"]["channels"] == 2
        assert identity["negotiated"]["format"] in {"S16LE", "F64LE"}

        metrics = port.capture_processing_output(0.5)
        assert metrics["frames"] > 0 and metrics["rms"] > 0.0

        session.release_active("stop")
        assert session.state.value == "idle"
        assert session.mode == "shared"
    finally:
        port.close()
        supervisor.close()
