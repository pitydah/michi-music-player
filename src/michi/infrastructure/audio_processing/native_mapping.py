"""PARENT-SAFE native mapping for compiled processing plans (AP2-F05).

Infrastructure-layer translation: semantic compiled strategies -> native
execution DTO, plus the expected native readback shape. Uses the F04 biquad
math (pure, deterministic, no I/O). The application layer depends on this by
injection only; the child host never decides any of it.
"""

from __future__ import annotations

from typing import Any

from michi.application.processing_graph_compiler import (
    CompiledProcessingNode,
    CompiledProcessingPlan,
)
from michi.domain.audio_processing import (
    GRAPHIC_EQ_CENTER_HZ,
    BiquadType,
    GraphicEqLayout,
    ProcessingStrategy,
)

#: RBJ Q for a one-octave peaking band (graphic EQ native mapping).
GRAPHIC_OCTAVE_Q = 2.0 ** 0.5 / (2.0 - 1.0)


def json_normalize(value: Any) -> Any:
    """Wire-shape normalization: tuples become lists (JSON has no tuples)."""
    if isinstance(value, dict):
        return {str(key): json_normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_normalize(item) for item in value]
    return value


def graphic_cascade(
    rate_hz: int, centers: list[float], gains: list[float]
) -> list[dict[str, Any]]:
    """Parent-computed RBJ peaking cascade for the active graphic bands."""
    from michi.infrastructure.audio_processing.biquad import (
        biquad_coefficients,
    )

    cascade: list[dict[str, Any]] = []
    for center, gain in zip(centers, gains, strict=True):
        coefficients = biquad_coefficients(
            BiquadType.PEAK,
            rate_hz=float(rate_hz),
            frequency_hz=float(center),
            q=GRAPHIC_OCTAVE_Q,
            gain_db=float(gain),
        )
        cascade.append(
            {
                "b": [
                    coefficients.b0,
                    coefficients.b1,
                    coefficients.b2,
                ],
                "a": [1.0, coefficients.a1, coefficients.a2],
            }
        )
    return cascade


class NativeProcessingMapping:
    """Compiled plan -> native DTO + expected readback translator."""

    @staticmethod
    def expected_native_properties(
        node: CompiledProcessingNode, *, rate_hz: int
    ) -> dict[str, Any]:
        """Expected NATIVE readback shape for one compiled node."""
        properties = {str(key): json_normalize(value) for key, value in node.properties}
        if node.strategy is ProcessingStrategy.GAIN:
            return {"gain_db": float(properties["gain_db"])}
        if node.strategy is ProcessingStrategy.GRAPHIC_EQ_NBANDS:
            layout = GraphicEqLayout(str(properties["layout_id"]))
            indices = [int(value) for value in properties["band_indices"]]
            centers = [GRAPHIC_EQ_CENTER_HZ[layout][index] for index in indices]
            gains = [float(value) for value in properties["gains_db"]]
            return {
                "layout_id": layout.value,
                "band_indices": indices,
                "biquad": graphic_cascade(rate_hz, centers, gains),
            }
        raise ValueError(f"no native mapping for strategy {node.strategy.value!r}")

    def plan_to_wire(self, plan: CompiledProcessingPlan) -> dict[str, Any]:
        """Build the bounded native execution DTO for one compiled plan.

        Semantic enrichment stays parent-side: graphic band centers are
        derived from the canonical layout, never from the child.
        """
        nodes: list[dict[str, Any]] = []
        for node in plan.nodes:
            properties = {
                str(key): json_normalize(value) for key, value in node.properties
            }
            if node.strategy is ProcessingStrategy.GRAPHIC_EQ_NBANDS:
                layout = GraphicEqLayout(str(properties["layout_id"]))
                indices = [int(value) for value in properties["band_indices"]]
                properties["band_centers_hz"] = [
                    GRAPHIC_EQ_CENTER_HZ[layout][index] for index in indices
                ]
                properties["biquad_cascade"] = graphic_cascade(
                    plan.sample_contract.input_rate_hz,
                    [float(value) for value in properties["band_centers_hz"]],
                    [float(value) for value in properties["gains_db"]],
                )
            nodes.append(
                {
                    "node_id": node.node_id,
                    "kind": node.kind.value,
                    "strategy": node.strategy.value,
                    "properties": properties,
                }
            )
        contract = plan.sample_contract
        return {
            "plan_id": plan.plan_id,
            "graph_id": plan.graph_id,
            "graph_revision": plan.graph_revision,
            "input_format": contract.input_format,
            "working_format": contract.working_format,
            "input_rate_hz": contract.input_rate_hz,
            "channels": contract.channels_in,
            "nodes": nodes,
        }

