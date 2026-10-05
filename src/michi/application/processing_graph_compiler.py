"""Deterministic processing graph compiler (AP2-F04, R11-F04 / §130).

Pure application module: effective graph + backend capabilities + asset
metadata + sample policy -> immutable CompiledProcessingPlan. It selects
SEMANTIC strategies only; concrete factories are bound by F05 after probing.
No GStreamer import, no filesystem, no threads, no callbacks, no fallback:
an unsupported strategy or an unprovable fact is a typed refusal.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from michi.application.effective_processing_graph import (
    EffectiveProcessingGraph,
    EffectiveProcessingNode,
)
from michi.domain.audio_processing import (
    GAINLESS_BIQUAD_TYPES,
    GRAPHIC_EQ_CENTER_HZ,
    ChannelDelayNode,
    ChannelMapNode,
    CompiledProcessingNode,
    CompiledProcessingPlan,
    ConvolutionNode,
    DitherMode,
    DitherNode,
    GraphicEqNode,
    ImpulseResponseMetadata,
    ParametricEqNode,
    PreampNode,
    ProcessingAdaptationReason,
    ProcessingNode,
    ProcessingSampleContract,
    ProcessingStrategy,
    ResampleNode,
)

#: Non-executable nodes whose absence is benign and recorded in the plan.
_SKIPPED_ADAPTATIONS: dict[ProcessingAdaptationReason, str] = {
    ProcessingAdaptationReason.GRAPH_BYPASSED: "graph_bypassed",
    ProcessingAdaptationReason.NODE_DISABLED: "node_disabled",
    ProcessingAdaptationReason.INACTIVE_ABOVE_NYQUIST: "inactive_above_nyquist",
}

#: Non-executable nodes that must fail the compilation, never silently drop.
_REFUSED_ADAPTATIONS: dict[ProcessingAdaptationReason, str] = {
    ProcessingAdaptationReason.UNSUPPORTED_CURRENT_SIGNAL: (
        "DSP_ASSET_UNSUPPORTED_SIGNAL"
    ),
    ProcessingAdaptationReason.ASSET_UNAVAILABLE: "DSP_ASSET_UNAVAILABLE",
    ProcessingAdaptationReason.ASSET_HASH_MISMATCH: "DSP_ASSET_HASH_MISMATCH",
    ProcessingAdaptationReason.CHANNEL_LAYOUT_UNAVAILABLE: "DSP_CHANNEL_MAP_INVALID",
}


class ProcessingCompilationError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class ProcessingBackendCapabilities:
    """Probe result supplied by infrastructure; never guessed by the compiler."""

    backend_id: str
    strategies: frozenset[ProcessingStrategy]
    factories: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class ProcessingSamplePolicy:
    """Explicit representation policy. F64LE is the deterministic default."""

    working_format: str = "F64LE"
    dither_mode: DitherMode = DitherMode.NONE
    noise_shaping_mode: str = "none"

    def __post_init__(self) -> None:
        if self.working_format not in {"F32LE", "F64LE"}:
            raise ValueError("working format must be F32LE or F64LE")
        if not isinstance(self.dither_mode, DitherMode):
            raise TypeError("dither policy must be a DitherMode")
        if not self.noise_shaping_mode.strip():
            raise ValueError("noise shaping mode must be explicit")


def _is_float_format(transport_format: str) -> bool:
    normalized = transport_format.strip().replace("_", "").upper()
    return normalized.startswith("F")


def _canonical(value: object) -> object:
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    return value


class ProcessingGraphCompiler:
    """Pure compiler: no I/O, no threads, deterministic plan identity."""

    def compile(
        self,
        graph: EffectiveProcessingGraph,
        *,
        backend: ProcessingBackendCapabilities,
        assets: tuple[ImpulseResponseMetadata, ...] = (),
        sample_policy: ProcessingSamplePolicy | None = None,
    ) -> CompiledProcessingPlan:
        policy = (
            sample_policy if sample_policy is not None else ProcessingSamplePolicy()
        )
        self._refuse_non_executable(graph)
        executable = graph.executable_nodes
        self._require_terminal_dither(executable)

        signal = graph.input_signal
        input_format = signal.transport_format
        input_is_float = _is_float_format(input_format)
        current_rate = signal.rate_hz
        current_channels = signal.layout.channels
        assets_by_id = {asset.asset_id: asset for asset in assets}

        compiled: list[CompiledProcessingNode] = []
        latency = 0
        changes_values = False
        changes_rate = False
        changes_channels = False
        changes_timing = False
        changes_channel_assignment = False
        asset_hashes: list[str] = []

        for entry in executable:
            node = entry.node
            self._validate_node_for_signal(
                entry, rate_hz=current_rate, channels=current_channels
            )
            strategy, properties, node_latency, node_asset_hash = (
                self._compile_semantics(
                    entry,
                    rate_hz=current_rate,
                    assets=assets_by_id,
                )
            )
            if strategy not in backend.strategies:
                raise ProcessingCompilationError(
                    "DSP_STRATEGY_UNAVAILABLE",
                    f"{backend.backend_id!r} does not implement {strategy.value!r}",
                )
            compiled.append(
                CompiledProcessingNode(
                    node_id=node.node_id,
                    kind=node.kind,
                    strategy=strategy,
                    properties=properties,
                    expected_latency_samples=node_latency,
                    asset_sha256=node_asset_hash,
                )
            )
            latency += node_latency
            if node_asset_hash is not None and node_asset_hash not in asset_hashes:
                asset_hashes.append(node_asset_hash)

            changes_values |= self._changes_sample_values(
                node, entry=entry, rate_hz=current_rate
            )
            if isinstance(node, ChannelDelayNode) and any(
                value != 0 for value in node.delays_us
            ):
                changes_timing = True
            if isinstance(node, ChannelMapNode):
                identity = tuple(range(current_channels))
                if node.output_to_input != identity:
                    changes_channel_assignment = True
                if len(node.output_to_input) != current_channels:
                    changes_channels = True
                current_channels = len(node.output_to_input)
            if isinstance(node, ResampleNode):
                if node.target_rate_hz != current_rate:
                    changes_rate = True
                current_rate = node.target_rate_hz

        dither_entry = executable[-1] if executable else None
        dither_node = (
            dither_entry.node
            if dither_entry is not None and isinstance(dither_entry.node, DitherNode)
            else None
        )
        if dither_node is not None:
            output_format = f"S{dither_node.target_bits}LE"
            output_quantization = True
            dither_mode = dither_node.mode.value
        else:
            output_format = input_format
            output_quantization = not input_is_float
            dither_mode = policy.dither_mode.value
        input_conversion = not input_is_float
        changes_representation = input_conversion or output_quantization

        contract = ProcessingSampleContract(
            input_format=input_format,
            working_format=policy.working_format,
            output_format=output_format,
            input_rate_hz=signal.rate_hz,
            output_rate_hz=current_rate,
            channels_in=signal.layout.channels,
            channels_out=current_channels,
            input_conversion=input_conversion,
            output_quantization=output_quantization,
            dither_mode=dither_mode,
            noise_shaping_mode=policy.noise_shaping_mode,
        )
        node_tuple = tuple(compiled)
        adaptation_reasons = tuple(reason.value for reason in graph.adaptation_reasons)
        evidence_refs = (f"graph:{graph.graph_id}:{graph.graph_revision}",)
        plan_id = self._plan_id(
            graph=graph,
            backend_id=backend.backend_id,
            contract=contract,
            nodes=node_tuple,
            latency=latency,
            asset_hashes=tuple(sorted(asset_hashes)),
            flags=(
                changes_values,
                changes_representation,
                changes_rate,
                changes_channels,
                changes_timing,
                changes_channel_assignment,
                output_quantization,
            ),
            adaptation_reasons=adaptation_reasons,
        )
        return CompiledProcessingPlan(
            plan_id=plan_id,
            graph_id=graph.graph_id,
            graph_revision=graph.graph_revision,
            backend_id=backend.backend_id,
            sample_contract=contract,
            nodes=node_tuple,
            total_latency_samples=latency,
            asset_hashes=tuple(sorted(asset_hashes)),
            changes_sample_values=changes_values,
            changes_representation=changes_representation,
            changes_rate=changes_rate,
            changes_channels=changes_channels,
            changes_timing=changes_timing,
            changes_channel_assignment=changes_channel_assignment,
            quantization_boundary=output_quantization,
            adaptation_reasons=adaptation_reasons,
            evidence_refs=evidence_refs,
        )

    # ------------------------------------------------------------------ #
    # validation
    # ------------------------------------------------------------------ #

    @staticmethod
    def _refuse_non_executable(graph: EffectiveProcessingGraph) -> None:
        for entry in graph.nodes:
            if entry.executable:
                continue
            code = _REFUSED_ADAPTATIONS.get(entry.reason)
            if code is not None:
                raise ProcessingCompilationError(
                    code,
                    f"{entry.node.node_id}: "
                    f"{entry.reason.value if entry.reason else 'unknown'}",
                )

    @staticmethod
    def _require_terminal_dither(
        executable: tuple[EffectiveProcessingNode, ...],
    ) -> None:
        positions = [
            index
            for index, entry in enumerate(executable)
            if isinstance(entry.node, DitherNode)
        ]
        if len(positions) > 1:
            raise ProcessingCompilationError(
                "DSP_DITHER_NOT_TERMINAL", "only one terminal dither node is allowed"
            )
        if positions and positions[0] != len(executable) - 1:
            raise ProcessingCompilationError(
                "DSP_DITHER_NOT_TERMINAL", "dither must be the last processing node"
            )

    @staticmethod
    def _validate_node_for_signal(
        entry: EffectiveProcessingNode,
        *,
        rate_hz: int,
        channels: int,
    ) -> None:
        node = entry.node
        if isinstance(node, ParametricEqNode):
            nyquist = rate_hz / 2.0
            for band in node.bands:
                if band.band_id in entry.inactive_band_ids:
                    continue
                if band.enabled and not (0.0 < band.frequency_hz < nyquist):
                    raise ProcessingCompilationError(
                        "DSP_PEQ_NYQUIST_VIOLATION",
                        f"{band.band_id}: {band.frequency_hz} >= Nyquist {nyquist}",
                    )
        if isinstance(node, ChannelMapNode):
            for index in node.output_to_input:
                if index is not None and not (0 <= index < channels):
                    raise ProcessingCompilationError(
                        "DSP_CHANNEL_MAP_INVALID", repr(node.output_to_input)
                    )

    # ------------------------------------------------------------------ #
    # semantics
    # ------------------------------------------------------------------ #

    def _compile_semantics(
        self,
        entry: EffectiveProcessingNode,
        *,
        rate_hz: int,
        assets: dict[str, ImpulseResponseMetadata],
    ) -> tuple[ProcessingStrategy, tuple[tuple[str, object], ...], int, str | None]:
        node = entry.node
        if isinstance(node, PreampNode):
            return (
                ProcessingStrategy.GAIN,
                (("gain_db", node.gain_db),),
                0,
                None,
            )
        if isinstance(node, GraphicEqNode):
            centers = GRAPHIC_EQ_CENTER_HZ[node.layout_id]
            indices = tuple(
                index
                for index in range(len(centers))
                if f"{node.layout_id.value}:{index}" not in entry.inactive_band_ids
            )
            gains = tuple(node.gains_db[index] for index in indices)
            return (
                ProcessingStrategy.GRAPHIC_EQ_NBANDS,
                (
                    ("layout_id", node.layout_id.value),
                    ("gains_db", gains),
                    ("band_indices", indices),
                ),
                0,
                None,
            )
        if isinstance(node, ParametricEqNode):
            bands = tuple(
                (
                    band.band_id,
                    band.filter_type.value,
                    band.frequency_hz,
                    band.q,
                    band.gain_db,
                    band.enabled,
                )
                for band in node.bands
                if band.band_id not in entry.inactive_band_ids
            )
            return (
                ProcessingStrategy.BIQUAD_CASCADE,
                (("bands", bands), ("rate_hz", rate_hz)),
                0,
                None,
            )
        if isinstance(node, ConvolutionNode):
            asset = assets.get(node.asset_id)
            if asset is None:
                raise ProcessingCompilationError("DSP_ASSET_UNAVAILABLE", node.asset_id)
            return (
                ProcessingStrategy.CONVOLUTION_FIR,
                (
                    ("asset_id", node.asset_id),
                    ("asset_sha256", node.asset_sha256),
                    ("channels", asset.channels),
                    ("gain_db", node.gain_db),
                ),
                0,
                node.asset_sha256,
            )
        if isinstance(node, ChannelDelayNode):
            latency = max(
                (round(rate_hz * value / 1_000_000) for value in node.delays_us),
                default=0,
            )
            return (
                ProcessingStrategy.CHANNEL_DELAY,
                (("delays_us", node.delays_us),),
                latency,
                None,
            )
        if isinstance(node, ChannelMapNode):
            return (
                ProcessingStrategy.CHANNEL_MAP,
                (("output_to_input", node.output_to_input),),
                0,
                None,
            )
        if isinstance(node, ResampleNode):
            return (
                ProcessingStrategy.RESAMPLE,
                (
                    ("target_rate_hz", node.target_rate_hz),
                    ("quality", node.quality.value),
                ),
                0,
                None,
            )
        if isinstance(node, DitherNode):
            return (
                ProcessingStrategy.DITHER_TERMINAL,
                (("mode", node.mode.value), ("target_bits", node.target_bits)),
                0,
                None,
            )
        raise ProcessingCompilationError("DSP_NODE_UNSUPPORTED", type(node).__name__)

    @staticmethod
    def _changes_sample_values(
        node: ProcessingNode,
        *,
        entry: EffectiveProcessingNode,
        rate_hz: int,
    ) -> bool:
        """Conservative, exhaustive mutation semantics for Signal Truth."""
        if isinstance(node, PreampNode):
            return node.gain_db != 0.0
        if isinstance(node, GraphicEqNode):
            return any(
                node.gains_db[index] != 0.0
                for index in range(len(node.gains_db))
                if f"{node.layout_id.value}:{index}" not in entry.inactive_band_ids
            )
        if isinstance(node, ParametricEqNode):
            for band in node.bands:
                if not band.enabled or band.band_id in entry.inactive_band_ids:
                    continue
                if band.filter_type in GAINLESS_BIQUAD_TYPES or band.gain_db != 0.0:
                    return True
            return False
        if isinstance(node, ConvolutionNode):
            # Never guess that an arbitrary IR is mathematically identity.
            return True
        if isinstance(node, ChannelDelayNode):
            # Timing mutation is reported separately by `changes_timing`.
            return False
        if isinstance(node, ChannelMapNode):
            # Routing/assignment mutation is reported separately.
            return False
        if isinstance(node, ResampleNode):
            return node.target_rate_hz != rate_hz
        if isinstance(node, DitherNode):
            return node.mode is not DitherMode.NONE
        # Fail closed for any future node not added to this exhaustive table.
        return True

    @staticmethod
    def _plan_id(
        *,
        graph: EffectiveProcessingGraph,
        backend_id: str,
        contract: ProcessingSampleContract,
        nodes: tuple[CompiledProcessingNode, ...],
        latency: int,
        asset_hashes: tuple[str, ...],
        flags: tuple[bool, ...],
        adaptation_reasons: tuple[str, ...],
    ) -> str:
        """Every execution-significant input, and nothing incidental."""
        signal = graph.input_signal
        payload = {
            "backend": backend_id,
            "graph": [graph.graph_id, graph.graph_revision, graph.bypassed],
            "input": [
                signal.transport_format,
                signal.rate_hz,
                signal.layout.positions,
                signal.significant_bits,
            ],
            "contract": [
                contract.input_format,
                contract.working_format,
                contract.output_format,
                contract.input_rate_hz,
                contract.output_rate_hz,
                contract.channels_in,
                contract.channels_out,
                contract.input_conversion,
                contract.output_quantization,
                contract.dither_mode,
                contract.noise_shaping_mode,
            ],
            "nodes": [
                [
                    node.node_id,
                    node.kind.value,
                    node.strategy.value,
                    _canonical(node.properties),
                    node.expected_latency_samples,
                    node.asset_sha256,
                ]
                for node in nodes
            ],
            "latency": latency,
            "assets": list(asset_hashes),
            "flags": list(flags),
            "adaptations": list(adaptation_reasons),
        }
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
        return "dsp:" + hashlib.sha256(encoded).hexdigest()[:24]
