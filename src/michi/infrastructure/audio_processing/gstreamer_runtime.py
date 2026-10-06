"""CHILD-NATIVE candidate runtime: inspect (readback) and abort (AP2-F05).

Primitive readback only: property values actually read from the live native
elements after preroll, plus the negotiated working caps. The parent compares
expected vs observed; this module never decides effectiveness.
"""

from __future__ import annotations

import math
from typing import Any

from michi.infrastructure.audio_processing.gstreamer_graph_builder import (
    BuiltProcessingCandidate,
    ProcessingGraphBuildError,
)


def inspect_processing_candidate(
    built: BuiltProcessingCandidate, plan: dict[str, Any]
) -> dict[str, Any]:
    """Read back the live candidate: properties + negotiated working caps."""
    nodes = plan.get("nodes") or []
    observed_nodes: list[dict[str, Any]] = []
    for node in nodes:
        node_id = str(node.get("node_id"))
        strategy = str(node.get("strategy"))
        element = built.node_elements.get(node_id)
        if element is None:
            raise ProcessingGraphBuildError(
                "DSP_READBACK_MISSING", f"no native element for {node_id!r}"
            )
        properties = node.get("properties") or {}
        observed_nodes.append(
            {
                "node_id": node_id,
                "strategy": strategy,
                "factories": list(built.node_factories.get(node_id, ())),
                "observed": _read_node(strategy, element, properties),
            }
        )
    return {
        "plan_id": built.plan_id,
        "graph_revision": int(plan.get("graph_revision") or 0),
        "nodes": observed_nodes,
        "working_caps": _working_caps(built),
        "graph_factories": list(built.graph_factories),
    }


def _read_node(
    strategy: str, element: Any, properties: dict[str, Any]
) -> dict[str, Any]:
    if strategy == "gain":
        linear = float(element.get_property("volume"))
        gain_db = float("-inf") if linear <= 0.0 else 20.0 * math.log10(linear)
        return {"gain_db": gain_db}
    if strategy == "graphic_eq_nbands":
        if isinstance(element, (list, tuple)):
            # audioiirfilter cascade: report the coefficients actually set.
            return {
                "layout_id": str(properties.get("layout_id")),
                "band_indices": [
                    int(value) for value in properties.get("band_indices", [])
                ],
                "biquad": [
                    {
                        "a": [float(value) for value in band.get_property("a")],
                        "b": [float(value) for value in band.get_property("b")],
                    }
                    for band in element
                ],
            }
        num_bands = int(element.get_property("num-bands"))
        gains = [
            float(element.get_property(f"band{index}-gain"))
            for index in range(num_bands)
        ]
        return {
            "layout_id": str(properties.get("layout_id")),
            "gains_db": gains,
            "band_indices": [
                int(value) for value in properties.get("band_indices", [])
            ],
        }
    raise ProcessingGraphBuildError(
        "DSP_READBACK_UNSUPPORTED", f"no readback for strategy {strategy!r}"
    )


def _working_caps(built: BuiltProcessingCandidate) -> dict[str, Any]:
    caps = built.working_capsfilter.get_static_pad("src").get_current_caps()
    if caps is None:
        raise ProcessingGraphBuildError(
            "DSP_READBACK_MISSING", "working caps were not negotiated"
        )
    structure = caps.get_structure(0)
    return {
        "format": str(structure.get_value("format")),
        "rate_hz": int(structure.get_value("rate")),
        "channels": int(structure.get_value("channels")),
    }


def inspect_processing_filter(
    filter_info: dict[str, Any], plan: dict[str, Any]
) -> dict[str, Any]:
    """Post-install readback of the PRODUCTIVE filter bin (primitive facts)."""
    nodes = plan.get("nodes") or []
    observed_nodes: list[dict[str, Any]] = []
    node_elements = filter_info.get("node_elements") or {}
    node_factories = filter_info.get("node_factories") or {}
    for node in nodes:
        node_id = str(node.get("node_id"))
        strategy = str(node.get("strategy"))
        element = node_elements.get(node_id)
        if element is None:
            raise ProcessingGraphBuildError(
                "DSP_READBACK_MISSING", f"no installed element for {node_id!r}"
            )
        properties = node.get("properties") or {}
        observed_nodes.append(
            {
                "node_id": node_id,
                "strategy": strategy,
                "factories": list(node_factories.get(node_id, ())),
                "observed": _read_node(strategy, element, properties),
            }
        )
    capsfilter = filter_info.get("working_capsfilter")
    caps = capsfilter.get_static_pad("src").get_current_caps()
    if caps is not None:
        caps_source = "negotiated"
        structure = caps.get_structure(0)
        working_caps = {
            "format": str(structure.get_value("format")),
            "rate_hz": int(structure.get_value("rate")),
            "channels": int(structure.get_value("channels")),
        }
    else:
        # Not yet negotiated (pipeline quiescent): report the CONFIGURED
        # boundary truthfully; the productive media test proves negotiation.
        configured = capsfilter.get_property("caps").get_structure(0)
        caps_source = "configured"
        working_caps = {
            "format": str(configured.get_value("format")),
            "rate_hz": int(configured.get_value("rate")),
            "channels": int(configured.get_value("channels")),
        }
    return {
        "plan_id": str(plan.get("plan_id")),
        "graph_revision": int(plan.get("graph_revision") or 0),
        "nodes": observed_nodes,
        "working_caps": working_caps,
        "caps_source": caps_source,
        "graph_factories": list(filter_info.get("graph_factories") or ()),
    }


def abort_processing_candidate(built: BuiltProcessingCandidate) -> None:
    """Terminate the candidate pipeline (bounded native teardown).

    A teardown failure is RAISED: the caller must never report a candidate
    as retired when the native teardown did not provably succeed.
    """
    import gi

    gi.require_version("Gst", "1.0")
    from gi.repository import Gst  # noqa: PLC0415 - child-native import

    returned = built.pipeline.set_state(Gst.State.NULL)
    if returned == Gst.StateChangeReturn.FAILURE:
        raise ProcessingGraphBuildError(
            "DSP_ABORT_FAILED", "candidate pipeline refused to terminate"
        )
    _ret, state, _pending = built.pipeline.get_state(2 * 1_000_000_000)
    if state != Gst.State.NULL:
        raise ProcessingGraphBuildError(
            "DSP_ABORT_FAILED", f"candidate did not reach NULL (state={state!r})"
        )
