"""AP2-F10 — F06 processing authority installs into the DSD→PCM host route."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from michi.application.dsd_to_pcm_plan import DsdToPcmPlanner
from michi.domain.dsd_signal import (
    DsdBitOrder,
    DsdOrganization,
    DsdPacking,
    DsdSignalFormat,
)
from tests.audio_phase2.test_dsd_source_truth import build_dsf

_HAS_GI = importlib.util.find_spec("gi") is not None


def _has_dsd_decoder() -> bool:
    inspector = shutil.which("gst-inspect-1.0")
    if inspector is None:
        return False
    return (
        subprocess.run(
            [inspector, "avdec_dsd_msbf"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


pytestmark = pytest.mark.skipif(
    not _HAS_GI or not _has_dsd_decoder(),
    reason="gst-libav DSD decoder unavailable on this host",
)


def _format() -> DsdSignalFormat:
    return DsdSignalFormat(
        bit_rate_hz=2_822_400,
        channels=2,
        packing=DsdPacking.DSD_U8,
        bit_order=DsdBitOrder.LSBF,
        organization=DsdOrganization.PLANAR,
        layout=("FL", "FR"),
    )


def _compiled_plan():
    from michi.application.effective_processing_graph import (
        EffectiveProcessingGraphResolver,
    )
    from michi.application.processing_graph_compiler import (
        ProcessingBackendCapabilities,
        ProcessingGraphCompiler,
        ProcessingSamplePolicy,
    )
    from michi.domain.audio_processing import (
        BiquadType,
        ParametricEqNode,
        PeqBand,
        ProcessingGraph,
        ProcessingStrategy,
    )
    from michi.domain.audio_signal import ChannelLayout, PcmSignalFormat

    graph = ProcessingGraph(
        graph_id="graph:dsd-host-peq",
        revision=1,
        nodes=(
            ParametricEqNode(
                node_id="peq",
                bands=(PeqBand("b1", BiquadType.PEAK, 1000.0, 1.4, 12.0, True),),
            ),
        ),
    )
    signal = PcmSignalFormat(
        rate_hz=88_200,
        transport_format="F32LE",
        significant_bits=32,
        layout=ChannelLayout(positions=("FL", "FR")),
    )
    effective = EffectiveProcessingGraphResolver().resolve(
        graph, input_signal=signal, assets=()
    )
    return ProcessingGraphCompiler().compile(
        effective,
        backend=ProcessingBackendCapabilities(
            backend_id="test", strategies=frozenset(ProcessingStrategy)
        ),
        assets=(),
        sample_policy=ProcessingSamplePolicy(terminal_format_verified=True),
    )


def _payload(plan, source: Path) -> dict:
    return {
        "path": str(source),
        "plan_id": plan.plan_id,
        "execution_id": "exec:dsd-processing:1",
        "host_generation": 1,
        "binding_generation": plan.binding_generation,
        "stable_device_id": "dev:lab",
        "locator": "lab",
        "source_family": "dsf",
        "source_rate_hz": plan.source_format.bit_rate_hz,
        "source_bits": plan.source_format.bit_rate_hz,
        "bit_order": plan.source_format.bit_order.value,
        "channels": plan.channels,
        "decoder_factory": plan.decoder_factory,
        "target_rate_hz": plan.target_rate_hz,
        "output_format": plan.output_format,
        "quality_profile": plan.quality_profile,
        "resampler_policy": [list(item) for item in plan.resampler_policy],
        "sink_factory": "fakesink",
    }


def test_audio_processing_service_installs_f06_on_dsd_pcm_host(tmp_path):
    from michi.application.audio_processing_service import (
        AudioProcessingService,
        ProcessingEffectiveState,
    )
    from michi.infrastructure.audio_engines.gstreamer_host_client import (
        GStreamerHostSupervisor,
    )
    from michi.infrastructure.audio_engines.gstreamer_host_port import (
        GStreamerHostedAudioPort,
    )
    from michi.infrastructure.audio_processing.native_mapping import (
        NativeProcessingMapping,
    )

    source = tmp_path / "host-processing.dsf"
    source.write_bytes(build_dsf(sample_count=8_192, payload=bytes([0x69]) * 16_384))
    plan = DsdToPcmPlanner().plan(
        source_identity="track:host-processing",
        source_format=_format(),
        quality_profile="FAST",
        binding_generation=1,
        available_output_rates=(88_200,),
        decoder_available=True,
        target_qualified=True,
        backend_version="gst-libav",
    )
    compiled = _compiled_plan()
    supervisor = GStreamerHostSupervisor(
        start_timeout_s=45.0,
        command_timeout_s=30.0,
        terminate_grace_s=8.0,
        term_grace_s=5.0,
        kill_grace_s=5.0,
    )
    port = GStreamerHostedAudioPort(
        supervisor, command_deadline_s=30.0, load_deadline_s=30.0
    )
    try:
        port.activate()
        identity = port.prepare_dsd_pcm(_payload(plan, source))
        expected = {
            "plan_id": identity["plan_id"],
            "execution_id": identity["execution_id"],
            "stable_device_id": identity["stable_device_id"],
            "device": identity["device"],
            "binding_generation": identity["binding_generation"],
            "host_generation": identity["host_generation"],
        }
        processing = AudioProcessingService(
            capability_query=port.query_processing_capabilities,
            native_mapping=NativeProcessingMapping(),
            transport=port,
        )
        processing.refresh_capabilities()
        candidate = processing.begin_candidate(
            compiled,
            host_generation=int(identity["host_generation"]),
            transport=port,
        )
        receipt = processing.commit_candidate(
            candidate,
            transport=port,
            allow_configured_caps=True,
        )
        assert receipt.installed is True
        assert receipt.observed_plan_id == compiled.plan_id
        assert receipt.observed_graph_revision == compiled.graph_revision
        assert processing.effective_state is not ProcessingEffectiveState.EFFECTIVE

        port.commit_dsd_pcm(expected)
        start = port.start_dsd_pcm(expected)
        assert start["confirmed"] is True
        deadline = time.monotonic() + 2.0
        observed = port.query_dsd_pcm_identity()
        while time.monotonic() < deadline:
            observed = port.query_dsd_pcm_identity()
            processing_info = observed.get("processing") or {}
            if processing_info.get("caps_source") == "negotiated":
                break
            time.sleep(0.01)
        assert observed["processing"]["graph_revision"] == compiled.graph_revision
        assert observed["processing"]["caps_source"] == "negotiated"
        assert processing.publish_effective(receipt) >= candidate.processing_generation
        assert processing.effective_state is ProcessingEffectiveState.EFFECTIVE
        bypass = port.bypass_processing()
        assert bypass["bypassed"] is True
        assert bypass["route_restored"] is True
        port.stop_dsd_pcm(expected)
        processing.shutdown()
    finally:
        supervisor.close()
