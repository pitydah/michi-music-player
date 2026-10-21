"""AP2-F06 — the complete authorized DSP chain on the real host.

Preamp -> Graphic EQ -> Parametric EQ -> FIR -> explicit Resample ->
Terminal Dither, with native readback before EFFECTIVE.
"""

from __future__ import annotations

import importlib.util
import time

import pytest

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
    ConvolutionNode,
    DitherMode,
    DitherNode,
    GraphicEqLayout,
    GraphicEqNode,
    ImpulseResponseMetadata,
    ParametricEqNode,
    PeqBand,
    PreampNode,
    ProcessingGraph,
    ProcessingStrategy,
    ResampleNode,
    ResampleQuality,
)
from michi.domain.audio_signal import ChannelLayout, PcmSignalFormat
from michi.infrastructure.audio_processing.native_mapping import (
    NativeProcessingMapping,
)

_HAS_GI = importlib.util.find_spec("gi") is not None


def _signal(rate: int = 44100):
    return PcmSignalFormat(
        rate_hz=rate,
        transport_format="S16LE",
        significant_bits=16,
        layout=ChannelLayout(positions=("FL", "FR")),
    )


class _IRStore:
    def __init__(self, kernel, rate_hz=44100):
        import hashlib
        import struct

        self.kernel = tuple(kernel)
        self.rate_hz = rate_hz
        raw = struct.pack(f"<{len(self.kernel)}f", *self.kernel)
        self.sha = hashlib.sha256(raw).hexdigest()
        self.asset_id = f"ir:sha256:{self.sha}"

    def load_float32_mono(self, ir_id):
        return self.kernel

    def metadata(self, ir_id):
        return {
            "sha256": self.sha,
            "rate_hz": self.rate_hz,
            "channels": 1,
        }


def _full_graph(store: _IRStore, *, revision: int = 1):
    gains = [0.0] * 10
    gains[4] = 2.0
    return ProcessingGraph(
        graph_id="graph:full-dsp",
        revision=revision,
        nodes=(
            PreampNode(node_id="pre", gain_db=-1.0),
            GraphicEqNode(
                "geq", layout_id=GraphicEqLayout.MICHI_10_V1, gains_db=tuple(gains)
            ),
            ParametricEqNode(
                "peq",
                bands=(PeqBand("b1", BiquadType.PEAK, 1000.0, 1.4, 3.0, True),),
            ),
            ConvolutionNode(
                node_id="fir",
                asset_id=store.asset_id,
                asset_sha256=store.sha,
            ),
            ResampleNode(
                node_id="rs", target_rate_hz=48000, quality=ResampleQuality.HIGH
            ),
            DitherNode(node_id="dither", mode=DitherMode.TPDF, target_bits=16),
        ),
    )


def _asset(store: _IRStore):
    return ImpulseResponseMetadata(
        asset_id=store.asset_id,
        sha256=store.sha,
        rate_hz=store.rate_hz,
        channels=1,
    )


def test_full_chain_compiles_in_canonical_order() -> None:
    store = _IRStore((0.25, 0.5, 0.25))
    effective = EffectiveProcessingGraphResolver().resolve(
        _full_graph(store), input_signal=_signal(), assets=(_asset(store),)
    )
    plan = ProcessingGraphCompiler().compile(
        effective,
        backend=ProcessingBackendCapabilities(
            backend_id="test", strategies=frozenset(ProcessingStrategy)
        ),
        assets=(_asset(store),),
        ir_kernels={store.asset_id: store.kernel},
        sample_policy=ProcessingSamplePolicy(terminal_format_verified=True),
    )
    assert [node.strategy for node in plan.nodes] == [
        ProcessingStrategy.GAIN,
        ProcessingStrategy.GRAPHIC_EQ_NBANDS,
        ProcessingStrategy.BIQUAD_CASCADE,
        ProcessingStrategy.CONVOLUTION_FIR,
        ProcessingStrategy.RESAMPLE,
        ProcessingStrategy.DITHER_TERMINAL,
    ]
    assert plan.sample_contract.output_rate_hz == 48000
    assert plan.sample_contract.output_format == "S16LE"
    assert plan.quantization_boundary is True


@pytest.mark.skipif(not _HAS_GI, reason="PyGObject/GStreamer unavailable")
def test_full_chain_executes_on_the_real_host(tmp_path, monkeypatch) -> None:
    from michi.application.audio_processing_service import AudioProcessingService
    from tests.audio_phase2.test_processing_graphic_eq import (
        _real_port,
        _write_multitone,
    )

    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    fixture = tmp_path / "full-chain.wav"
    _write_multitone(fixture, rate=44100)
    store = _IRStore((0.25, 0.5, 0.25))
    asset = _asset(store)
    supervisor, port = _real_port()
    try:
        port.activate()
        port.set_volume(0)
        port.load(fixture)
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline:
            port.dispatch_pending()
            try:
                duration = port.query_duration()
            except Exception:
                duration = None
            if isinstance(duration, int) and duration > 0:
                break
            time.sleep(0.02)
        service = AudioProcessingService(
            capability_query=port.query_processing_capabilities,
            native_mapping=NativeProcessingMapping(),
            transport=port,
        )
        service.refresh_capabilities()
        effective = EffectiveProcessingGraphResolver().resolve(
            _full_graph(store), input_signal=_signal(), assets=(asset,)
        )
        plan = ProcessingGraphCompiler().compile(
            effective,
            backend=service.capabilities,
            assets=(asset,),
            ir_kernels={store.asset_id: store.kernel},
            sample_policy=ProcessingSamplePolicy(terminal_format_verified=True),
        )
        candidate = service.begin_candidate(
            plan, host_generation=supervisor.host_generation, transport=port
        )
        receipt = service.commit_candidate(candidate, transport=port)
        service.publish_effective(receipt)
        truth = service.processing_truth()
        assert truth["effective_state"] == "effective"
        assert truth["readback_proven"] is True

        port.seek(0)
        metrics = port.capture_processing_output(1.0, probe_hz=[1000.0, 8000.0])
        assert metrics["rate_hz"] == 48000
        assert metrics["format"] == "S16LE"
        tones = {tone["hz"]: tone["magnitude"] for tone in metrics["tones"]}
        assert tones[1000.0] > 0.0
        assert metrics["frames"] > 0
    finally:
        port.close()
        supervisor.close()
