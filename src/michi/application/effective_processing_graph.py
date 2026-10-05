"""Effective processing graph — the ONLY runtime adaptation seam (R11-F04).

Pure application module: saved graph + current signal -> effective graph +
adaptation reasons. The saved intent is never rewritten: every adaptation is
descriptive here and the compiler alone decides what can execute truthfully.
"""

from __future__ import annotations

from dataclasses import dataclass

from michi.domain.audio_processing import (
    GRAPHIC_EQ_CENTER_HZ,
    ChannelMapNode,
    ConvolutionNode,
    GraphicEqNode,
    ImpulseResponseMetadata,
    ParametricEqNode,
    ProcessingAdaptationReason,
    ProcessingGraph,
    ProcessingNode,
)
from michi.domain.audio_signal import PcmSignalFormat


@dataclass(frozen=True, slots=True)
class EffectiveProcessingNode:
    node: ProcessingNode
    executable: bool
    reason: ProcessingAdaptationReason | None
    inactive_band_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EffectiveProcessingGraph:
    graph_id: str
    graph_revision: int
    input_signal: PcmSignalFormat
    nodes: tuple[EffectiveProcessingNode, ...]
    bypassed: bool
    adaptation_reasons: tuple[ProcessingAdaptationReason, ...]

    @property
    def executable_nodes(self) -> tuple[EffectiveProcessingNode, ...]:
        return tuple(entry for entry in self.nodes if entry.executable)


class EffectiveProcessingGraphResolver:
    """Resolve saved intent against the current signal without mutating it."""

    def resolve(
        self,
        graph: ProcessingGraph,
        *,
        input_signal: PcmSignalFormat,
        assets: tuple[ImpulseResponseMetadata, ...] = (),
    ) -> EffectiveProcessingGraph:
        nyquist = input_signal.rate_hz / 2.0
        channels = input_signal.layout.channels
        assets_by_id = {asset.asset_id: asset for asset in assets}
        entries = tuple(
            self._resolve_node(
                node,
                rate_hz=input_signal.rate_hz,
                nyquist=nyquist,
                channels=channels,
                assets=assets_by_id,
                bypassed=graph.bypassed,
            )
            for node in graph.nodes
        )
        reasons: list[ProcessingAdaptationReason] = []
        for entry in entries:
            if entry.reason is not None and entry.reason not in reasons:
                reasons.append(entry.reason)
        return EffectiveProcessingGraph(
            graph_id=graph.graph_id,
            graph_revision=graph.revision,
            input_signal=input_signal,
            nodes=entries,
            bypassed=graph.bypassed,
            adaptation_reasons=tuple(reasons),
        )

    def _resolve_node(
        self,
        node: ProcessingNode,
        *,
        rate_hz: int,
        nyquist: float,
        channels: int,
        assets: dict[str, ImpulseResponseMetadata],
        bypassed: bool,
    ) -> EffectiveProcessingNode:
        if bypassed:
            return EffectiveProcessingNode(
                node, False, ProcessingAdaptationReason.GRAPH_BYPASSED
            )
        if isinstance(node, (GraphicEqNode, ConvolutionNode)) and not node.enabled:
            return EffectiveProcessingNode(
                node, False, ProcessingAdaptationReason.NODE_DISABLED
            )
        if isinstance(node, GraphicEqNode):
            centers = GRAPHIC_EQ_CENTER_HZ[node.layout_id]
            inactive = tuple(
                f"{node.layout_id.value}:{index}"
                for index, center in enumerate(centers)
                if center >= nyquist
            )
            if inactive and len(inactive) == len(centers):
                return EffectiveProcessingNode(
                    node,
                    False,
                    ProcessingAdaptationReason.INACTIVE_ABOVE_NYQUIST,
                    inactive,
                )
            if inactive:
                return EffectiveProcessingNode(
                    node,
                    True,
                    ProcessingAdaptationReason.INACTIVE_ABOVE_NYQUIST,
                    inactive,
                )
            return EffectiveProcessingNode(node, True, None)
        if isinstance(node, ParametricEqNode):
            inactive = tuple(
                band.band_id
                for band in node.bands
                if band.enabled and band.frequency_hz >= nyquist
            )
            enabled_ids = {band.band_id for band in node.bands if band.enabled}
            if inactive and set(inactive) == enabled_ids:
                return EffectiveProcessingNode(
                    node,
                    False,
                    ProcessingAdaptationReason.INACTIVE_ABOVE_NYQUIST,
                    inactive,
                )
            if inactive:
                return EffectiveProcessingNode(
                    node,
                    True,
                    ProcessingAdaptationReason.INACTIVE_ABOVE_NYQUIST,
                    inactive,
                )
            return EffectiveProcessingNode(node, True, None)
        if isinstance(node, ConvolutionNode):
            asset = assets.get(node.asset_id)
            if asset is None:
                return EffectiveProcessingNode(
                    node, False, ProcessingAdaptationReason.ASSET_UNAVAILABLE
                )
            if asset.sha256 != node.asset_sha256:
                return EffectiveProcessingNode(
                    node, False, ProcessingAdaptationReason.ASSET_HASH_MISMATCH
                )
            if asset.rate_hz != rate_hz or asset.channels != channels:
                return EffectiveProcessingNode(
                    node, False, ProcessingAdaptationReason.UNSUPPORTED_CURRENT_SIGNAL
                )
            return EffectiveProcessingNode(node, True, None)
        if isinstance(node, ChannelMapNode):
            if any(
                index is not None and index >= channels
                for index in node.output_to_input
            ):
                return EffectiveProcessingNode(
                    node, False, ProcessingAdaptationReason.CHANNEL_LAYOUT_UNAVAILABLE
                )
            return EffectiveProcessingNode(node, True, None)
        return EffectiveProcessingNode(node, True, None)
