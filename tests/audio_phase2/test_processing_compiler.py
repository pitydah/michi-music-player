"""AP2-F04 — effective graph resolver and deterministic compiler.

Contract anchors: R11-F04 (resolver is the only runtime adaptation seam;
compiler is pure with semantic strategies and typed refusals), R11-G04
(ProcessingSampleContract, representation/quantization boundaries), R11-G07
(no I/O, no threads, no callbacks, no backend names in the compiler).
"""

from __future__ import annotations

import ast
import dataclasses
import sys
from pathlib import Path

import pytest

from michi.application.effective_processing_graph import (
    EffectiveProcessingGraphResolver,
)
from michi.application.processing_graph_compiler import (
    ProcessingBackendCapabilities,
    ProcessingCompilationError,
    ProcessingGraphCompiler,
    ProcessingSamplePolicy,
)
from michi.domain.audio_processing import (
    BiquadType,
    ChannelDelayNode,
    ChannelMapNode,
    ConvolutionNode,
    DitherMode,
    DitherNode,
    GraphicEqLayout,
    GraphicEqNode,
    ImpulseResponseMetadata,
    ParametricEqNode,
    PeqBand,
    PreampNode,
    ProcessingAdaptationReason,
    ProcessingGraph,
    ProcessingNodeKind,
    ProcessingStrategy,
    ResampleNode,
    ResampleQuality,
)
from michi.domain.audio_signal import ChannelLayout, PcmSignalFormat

EFFECTIVE_MODULE = Path(
    sys.modules["michi.application.effective_processing_graph"].__file__
)
COMPILER_MODULE = Path(
    sys.modules["michi.application.processing_graph_compiler"].__file__
)

_ASSET_SHA = "ab" * 32
_ASSET_ID = f"ir:sha256:{_ASSET_SHA}"

_ALL_STRATEGIES = frozenset(ProcessingStrategy)


def _signal(*, rate: int = 96000, fmt: str = "F32LE", channels: int = 2, bits=None):
    return PcmSignalFormat(
        rate_hz=rate,
        transport_format=fmt,
        significant_bits=bits,
        layout=ChannelLayout(
            positions=tuple(f"CH{index}" for index in range(channels))
        ),
    )


def _backend(**kwargs) -> ProcessingBackendCapabilities:
    return ProcessingBackendCapabilities(
        backend_id=kwargs.get("backend_id", "test-backend"),
        strategies=kwargs.get("strategies", _ALL_STRATEGIES),
    )


def _resolve(graph, *, signal=None, assets=()):
    return EffectiveProcessingGraphResolver().resolve(
        graph, input_signal=signal or _signal(), assets=assets
    )


def _compile(graph, *, signal=None, assets=(), backend=None, policy=None):
    effective = _resolve(graph, signal=signal, assets=assets)
    return ProcessingGraphCompiler().compile(
        effective,
        backend=backend or _backend(),
        assets=assets,
        sample_policy=policy,
    )


def _preamp(gain_db: float, node_id: str = "pre") -> PreampNode:
    return PreampNode(node_id=node_id, gain_db=gain_db)


def _peq(*bands: PeqBand) -> ParametricEqNode:
    return ParametricEqNode(node_id="peq", bands=bands)


def _peak(band_id: str, frequency: float, gain: float, **kwargs) -> PeqBand:
    return PeqBand(
        band_id=band_id,
        filter_type=BiquadType.PEAK,
        frequency_hz=frequency,
        q=0.707,
        gain_db=gain,
        **kwargs,
    )


def _graph(*nodes, revision: int = 1, bypassed: bool = False) -> ProcessingGraph:
    return ProcessingGraph(
        graph_id="graph:test", revision=revision, nodes=tuple(nodes), bypassed=bypassed
    )


def _imported_modules(source_path: Path) -> list[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.append("." * node.level + (node.module or ""))
    return modules


# --------------------------------------------------------------------------- #
# effective resolver
# --------------------------------------------------------------------------- #


def test_bypassed_graph_marks_every_node_with_a_reason() -> None:
    effective = _resolve(_graph(_preamp(-3.0), bypassed=True))
    assert effective.bypassed is True
    assert all(not entry.executable for entry in effective.nodes)
    assert all(
        entry.reason is ProcessingAdaptationReason.GRAPH_BYPASSED
        for entry in effective.nodes
    )


def test_disabled_node_keeps_saved_intent_with_reason() -> None:
    node = ConvolutionNode(
        node_id="ir", asset_id=_ASSET_ID, asset_sha256=_ASSET_SHA, enabled=False
    )
    effective = _resolve(_graph(node), assets=(_ir_meta(),))
    entry = effective.nodes[0]
    assert entry.node is node
    assert entry.executable is False
    assert entry.reason is ProcessingAdaptationReason.NODE_DISABLED


def test_above_nyquist_peq_band_is_adapted_without_rewriting_intent() -> None:
    graph = _graph(_peq(_peak("ok", 1000.0, 3.0), _peak("high", 20000.0, 3.0)))
    effective = _resolve(graph, signal=_signal(rate=32000))
    entry = effective.nodes[0]
    assert entry.executable is True
    assert entry.reason is ProcessingAdaptationReason.INACTIVE_ABOVE_NYQUIST
    assert entry.inactive_band_ids == ("high",)
    assert graph.nodes[0].bands[1].frequency_hz == 20000.0  # saved intent untouched

    plan = ProcessingGraphCompiler().compile(
        effective,
        backend=_backend(),
        assets=(),
        sample_policy=None,
    )
    assert plan.adaptation_reasons == ("inactive_above_nyquist",)
    compiled_bands = dict(plan.nodes[0].properties)["bands"]
    assert [band[0] for band in compiled_bands] == ["ok"]


def test_above_nyquist_band_becomes_executable_again_at_high_rate() -> None:
    graph = _graph(_peq(_peak("high", 20000.0, 3.0)))
    effective = _resolve(graph, signal=_signal(rate=96000))
    entry = effective.nodes[0]
    assert entry.executable is True
    assert entry.reason is None
    assert entry.inactive_band_ids == ()


def test_all_bands_above_nyquist_make_the_node_non_executable() -> None:
    graph = _graph(_peq(_peak("high", 20000.0, 3.0)))
    effective = _resolve(graph, signal=_signal(rate=32000))
    entry = effective.nodes[0]
    assert entry.executable is False
    assert entry.reason is ProcessingAdaptationReason.INACTIVE_ABOVE_NYQUIST


def test_missing_asset_is_adapted_and_refused() -> None:
    graph = _graph(
        ConvolutionNode(node_id="ir", asset_id=_ASSET_ID, asset_sha256=_ASSET_SHA)
    )
    effective = _resolve(graph)
    entry = effective.nodes[0]
    assert entry.executable is False
    assert entry.reason is ProcessingAdaptationReason.ASSET_UNAVAILABLE
    with pytest.raises(ProcessingCompilationError) as error:
        _compile(graph)
    assert error.value.code == "DSP_ASSET_UNAVAILABLE"


def test_asset_hash_mismatch_is_refused() -> None:
    graph = _graph(
        ConvolutionNode(node_id="ir", asset_id=_ASSET_ID, asset_sha256=_ASSET_SHA)
    )
    other = ImpulseResponseMetadata(
        asset_id=_ASSET_ID, sha256="cd" * 32, rate_hz=96000, channels=2
    )
    effective = _resolve(graph, assets=(other,))
    assert effective.nodes[0].reason is ProcessingAdaptationReason.ASSET_HASH_MISMATCH
    with pytest.raises(ProcessingCompilationError) as error:
        _compile(graph, assets=(other,))
    assert error.value.code == "DSP_ASSET_HASH_MISMATCH"


def test_asset_rate_or_channel_mismatch_is_unsupported_signal() -> None:
    graph = _graph(
        ConvolutionNode(node_id="ir", asset_id=_ASSET_ID, asset_sha256=_ASSET_SHA)
    )
    for meta in (
        dataclasses.replace(_ir_meta(), rate_hz=44100),
        dataclasses.replace(_ir_meta(), channels=6),
    ):
        effective = _resolve(graph, assets=(meta,))
        assert (
            effective.nodes[0].reason
            is ProcessingAdaptationReason.UNSUPPORTED_CURRENT_SIGNAL
        )
        with pytest.raises(ProcessingCompilationError):
            _compile(graph, assets=(meta,))


def test_channel_map_beyond_current_channels_is_refused() -> None:
    graph = _graph(ChannelMapNode(node_id="map", output_to_input=(0, 4)))
    effective = _resolve(graph, signal=_signal(channels=2))
    assert (
        effective.nodes[0].reason
        is ProcessingAdaptationReason.CHANNEL_LAYOUT_UNAVAILABLE
    )
    with pytest.raises(ProcessingCompilationError) as error:
        _compile(graph, signal=_signal(channels=2))
    assert error.value.code == "DSP_CHANNEL_MAP_INVALID"


def _ir_meta(**kwargs) -> ImpulseResponseMetadata:
    sha256 = kwargs.get("sha256", _ASSET_SHA)
    return ImpulseResponseMetadata(
        asset_id=kwargs.get("asset_id", f"ir:sha256:{sha256}"),
        sha256=sha256,
        rate_hz=kwargs.get("rate_hz", 96000),
        channels=kwargs.get("channels", 2),
    )


# --------------------------------------------------------------------------- #
# compiler semantics
# --------------------------------------------------------------------------- #


def test_bypass_compiles_to_zero_nodes_and_records_the_reason() -> None:
    plan = _compile(_graph(_preamp(-3.0), bypassed=True))
    assert plan.nodes == ()
    assert plan.changes_sample_values is False
    assert plan.changes_representation is False
    assert plan.adaptation_reasons == ("graph_bypassed",)
    assert plan.evidence_refs == ("graph:graph:test:1",)


def test_identity_transform_reports_no_mutation() -> None:
    graph = _graph(
        _preamp(0.0),
        GraphicEqNode(
            node_id="geq",
            layout_id=GraphicEqLayout.MICHI_10_V1,
            gains_db=(0.0,) * 10,
        ),
        _peq(_peak("b", 1000.0, 0.0)),
        ChannelDelayNode(node_id="delay", delays_us=(0, 0)),
    )
    plan = _compile(graph, signal=_signal(fmt="F32LE"))
    assert plan.changes_sample_values is False
    assert plan.changes_rate is False
    assert plan.changes_channels is False
    assert plan.changes_timing is False
    assert plan.changes_channel_assignment is False
    assert plan.changes_representation is False
    assert plan.quantization_boundary is False
    assert plan.sample_contract.input_rate_hz == 96000
    assert plan.sample_contract.output_rate_hz == 96000
    assert plan.sample_contract.channels_out == 2


def test_preamp_gain_is_signal_mutation_with_semantic_strategy() -> None:
    plan = _compile(_graph(_preamp(-3.0)))
    node = plan.nodes[0]
    assert node.kind is ProcessingNodeKind.PREAMP
    assert node.strategy is ProcessingStrategy.GAIN
    assert node.properties == (("gain_db", -3.0),)
    assert plan.changes_sample_values is True


def test_graphic_eq_compiles_with_layout_and_gains() -> None:
    gains = (1.0,) * 31
    plan = _compile(
        _graph(
            GraphicEqNode(
                node_id="geq", layout_id=GraphicEqLayout.ISO_31_V1, gains_db=gains
            )
        )
    )
    node = plan.nodes[0]
    assert node.strategy is ProcessingStrategy.GRAPHIC_EQ_NBANDS
    properties = dict(node.properties)
    assert properties["layout_id"] == "iso_31_v1"
    assert properties["gains_db"] == gains
    assert plan.changes_sample_values is True


def test_parametric_eq_compiles_typed_bands_at_current_rate() -> None:
    plan = _compile(_graph(_peq(_peak("b1", 1000.0, -4.0))))
    node = plan.nodes[0]
    assert node.strategy is ProcessingStrategy.BIQUAD_CASCADE
    properties = dict(node.properties)
    assert properties["rate_hz"] == 96000
    assert properties["bands"][0][0] == "b1"
    assert properties["bands"][0][1] == "peak"
    assert plan.changes_sample_values is True


def test_disabled_bands_do_not_change_sample_values() -> None:
    plan = _compile(_graph(_peq(_peak("b1", 1000.0, -4.0, enabled=False))))
    assert plan.changes_sample_values is False


def test_resampling_is_explicit_only() -> None:
    without = _compile(_graph(_preamp(-1.0)))
    assert without.changes_rate is False
    assert without.sample_contract.output_rate_hz == 96000

    with_resample = _compile(
        _graph(
            ResampleNode(
                node_id="rs", target_rate_hz=48000, quality=ResampleQuality.HIGH
            )
        )
    )
    assert with_resample.changes_rate is True
    assert with_resample.changes_sample_values is True
    assert with_resample.sample_contract.output_rate_hz == 48000


def test_channel_map_explicit_changes() -> None:
    identity = _compile(_graph(ChannelMapNode(node_id="map", output_to_input=(0, 1))))
    assert identity.changes_channels is False
    assert identity.changes_channel_assignment is False

    swapped = _compile(_graph(ChannelMapNode(node_id="map", output_to_input=(1, 0))))
    assert swapped.changes_channels is False
    assert swapped.changes_channel_assignment is True

    widened = _compile(
        _graph(ChannelMapNode(node_id="map", output_to_input=(0, 0, None)))
    )
    assert widened.changes_channels is True
    assert widened.changes_channel_assignment is True
    assert widened.sample_contract.channels_out == 3


def test_dither_is_terminal_and_quantizes() -> None:
    plan = _compile(
        _graph(
            _preamp(-1.0), DitherNode(node_id="d", mode=DitherMode.TPDF, target_bits=16)
        )
    )
    assert plan.nodes[-1].strategy is ProcessingStrategy.DITHER_TERMINAL
    assert plan.quantization_boundary is True
    assert plan.sample_contract.output_format == "S16LE"
    assert plan.sample_contract.dither_mode == "tpdf"


def test_dither_not_terminal_is_refused() -> None:
    with pytest.raises(ProcessingCompilationError) as error:
        _compile(
            _graph(
                DitherNode(node_id="d", mode=DitherMode.TPDF, target_bits=16),
                _preamp(-1.0),
            )
        )
    assert error.value.code == "DSP_DITHER_NOT_TERMINAL"


def test_convolution_compiles_with_immutable_asset_identity() -> None:
    graph = _graph(
        ConvolutionNode(
            node_id="ir", asset_id=_ASSET_ID, asset_sha256=_ASSET_SHA, gain_db=-2.0
        )
    )
    plan = _compile(graph, assets=(_ir_meta(),))
    node = plan.nodes[0]
    assert node.strategy is ProcessingStrategy.CONVOLUTION_FIR
    assert node.asset_sha256 == _ASSET_SHA
    properties = dict(node.properties)
    assert properties["asset_id"] == _ASSET_ID
    assert properties["gain_db"] == -2.0
    assert plan.asset_hashes == (_ASSET_SHA,)
    assert plan.changes_sample_values is True


def test_integer_input_reports_representation_conversion_and_quantization() -> None:
    plan = _compile(
        _graph(
            ResampleNode(
                node_id="rs", target_rate_hz=48000, quality=ResampleQuality.FAST
            )
        ),
        signal=_signal(fmt="S32LE", bits=32),
    )
    contract = plan.sample_contract
    assert contract.input_conversion is True
    assert contract.output_quantization is True
    assert plan.changes_representation is True
    assert plan.quantization_boundary is True
    assert contract.working_format == "F64LE"


def test_explicit_f32_working_policy_is_honored() -> None:
    plan = _compile(
        _graph(_preamp(-1.0)),
        policy=ProcessingSamplePolicy(working_format="F32LE"),
    )
    assert plan.sample_contract.working_format == "F32LE"
    with pytest.raises(ValueError):
        ProcessingSamplePolicy(working_format="S32LE")


def test_unknown_strategy_is_a_typed_refusal_never_a_fallback() -> None:
    backend = ProcessingBackendCapabilities(
        backend_id="limited", strategies=frozenset({ProcessingStrategy.GAIN})
    )
    with pytest.raises(ProcessingCompilationError) as error:
        _compile(_graph(_peq(_peak("b", 1000.0, 3.0))), backend=backend)
    assert error.value.code == "DSP_STRATEGY_UNAVAILABLE"


# --------------------------------------------------------------------------- #
# deterministic plan hash
# --------------------------------------------------------------------------- #


def test_plan_id_is_deterministic_for_identical_facts() -> None:
    graph = _graph(_preamp(-3.0), _peq(_peak("b", 1000.0, 2.0)), revision=2)
    first = _compile(graph)
    second = _compile(graph)
    assert first.plan_id == second.plan_id
    assert first == second


def test_plan_id_changes_when_semantics_change() -> None:
    baseline = _compile(_graph(_preamp(-3.0)))
    assert _compile(_graph(_preamp(-2.0))).plan_id != baseline.plan_id
    assert _compile(_graph(_preamp(-3.0), revision=2)).plan_id != baseline.plan_id
    assert (
        _compile(_graph(_preamp(-3.0)), backend=_backend(backend_id="other")).plan_id
        != baseline.plan_id
    )
    assert (
        _compile(_graph(_preamp(-3.0)), signal=_signal(rate=44100)).plan_id
        != baseline.plan_id
    )
    assert (
        _compile(
            _graph(_preamp(-3.0)),
            policy=ProcessingSamplePolicy(working_format="F32LE"),
        ).plan_id
        != baseline.plan_id
    )


def test_plan_id_ignores_incidental_inputs() -> None:
    graph = _graph(_preamp(-3.0))
    first = _compile(graph)
    second = _compile(dataclasses.replace(graph))
    assert first.plan_id == second.plan_id


def test_compiler_and_effective_modules_are_pure_and_factory_free() -> None:
    for module in (EFFECTIVE_MODULE, COMPILER_MODULE):
        imports = _imported_modules(module)
        for name in imports:
            assert not any(
                name == prefix or name.startswith(prefix + ".")
                for prefix in (
                    "PySide6",
                    "gi",
                    "Gst",
                    "sqlite3",
                    "ctypes",
                    "numpy",
                    "os",
                    "pathlib",
                    "socket",
                    "urllib",
                    "threading",
                    "asyncio",
                    "michi.presentation",
                    "michi.infrastructure",
                    "michi.bootstrap",
                )
            ), (module.name, name)
        source = module.read_text(encoding="utf-8")
        for forbidden in (
            "equalizer-nbands",
            "audioiirfilter",
            "audiofirfilter",
            "audioconvert",
            "audioresample",
        ):
            assert forbidden not in source, (module.name, forbidden)
