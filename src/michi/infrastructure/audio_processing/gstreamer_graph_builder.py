"""CHILD-NATIVE processing graph builder (AP2-F05).

Runs ONLY inside the supervised GStreamer Output Host. It turns a compiled
processing DTO into a real, prerolled candidate graph and never decides
semantics: it reports primitive native facts for the parent to compare.

Canonical shape (R11-F05):

    audiotestsrc (quiescent, non-live)
      -> capsfilter[input carrier]
      -> audioconvert [dithering=none, noise-shaping=none]
      -> capsfilter[explicit working format/rate/channels]
      -> typed DSP chain (volume / equalizer-nbands)
      -> fakesink

No hidden resample/remix/dither: every conversion element here is explicitly
configured and represented by the compiled plan.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

PREROLL_TIMEOUT_NS = 8 * 1_000_000_000

#: 1-octave peaking width for graphic bands (bandwidth in Hz at the center).
_GRAPHIC_BANDWIDTH_FACTOR = 1.0 / math.sqrt(2.0)


class ProcessingGraphBuildError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass
class BuiltProcessingCandidate:
    pipeline: Any
    plan_id: str
    working_format: str
    input_rate_hz: int
    channels: int
    node_elements: dict[str, Any]
    node_factories: dict[str, tuple[str, ...]]
    working_capsfilter: Any
    graph_factories: tuple[str, ...]


def gst_available() -> bool:
    try:
        import gi

        gi.require_version("Gst", "1.0")
        return True
    except Exception:  # noqa: BLE001 - reported by the capability probe
        return False


def _make(gst, factory: str, name: str | None = None):
    element = gst.ElementFactory.make(factory, name)
    if element is None:
        raise ProcessingGraphBuildError(
            "DSP_ELEMENT_UNAVAILABLE", f"factory {factory!r} could not be created"
        )
    return element


def build_processing_candidate(plan: dict[str, Any]) -> BuiltProcessingCandidate:
    """Build + preroll + keep a real candidate for one compiled plan DTO."""
    import gi

    gi.require_version("Gst", "1.0")
    from gi.repository import Gst  # noqa: PLC0415 - child-native import

    if not Gst.is_initialized():
        Gst.init(None)

    plan_id = str(plan.get("plan_id") or "")
    working_format = str(plan.get("working_format") or "")
    input_rate_hz = int(plan.get("input_rate_hz") or 0)
    channels = int(plan.get("channels") or 0)
    input_format = str(plan.get("input_format") or working_format)
    nodes = plan.get("nodes")
    if (
        not plan_id
        or working_format not in {"F32LE", "F64LE"}
        or input_rate_hz <= 0
        or channels <= 0
        or not isinstance(nodes, list)
        or not nodes
    ):
        raise ProcessingGraphBuildError(
            "DSP_PLAN_INVALID", "compiled plan DTO is incomplete"
        )

    pipeline = Gst.Pipeline.new("michi-processing-candidate")
    source = _make(Gst, "audiotestsrc")
    source.set_property("is-live", False)
    source_caps = _make(Gst, "capsfilter")
    source_caps.set_property(
        "caps",
        Gst.Caps.from_string(
            f"audio/x-raw,format={input_format},rate={input_rate_hz},"
            f"channels={channels}"
        ),
    )
    convert = _make(Gst, "audioconvert")
    # Explicit internal converter policy: never accept audioconvert defaults.
    convert.set_property("dithering", 0)
    convert.set_property("noise-shaping", 0)
    working_caps = _make(Gst, "capsfilter")
    working_caps.set_property(
        "caps",
        Gst.Caps.from_string(
            f"audio/x-raw,format={working_format},rate={input_rate_hz},"
            f"channels={channels}"
        ),
    )
    sink = _make(Gst, "fakesink")
    sink.set_property("sync", False)

    elements = [source, source_caps, convert, working_caps]
    node_elements: dict[str, Any] = {}
    node_factories: dict[str, tuple[str, ...]] = {}
    try:
        for node in nodes:
            if not isinstance(node, dict):
                raise ProcessingGraphBuildError(
                    "DSP_PLAN_INVALID", "node entry is not an object"
                )
            strategy = str(node.get("strategy"))
            node_id = str(node.get("node_id"))
            properties = node.get("properties") or {}
            if strategy == "gain":
                element = _make(Gst, "volume", node_id)
                gain_db = float(properties["gain_db"])
                element.set_property("volume", 10.0 ** (gain_db / 20.0))
            elif strategy == "graphic_eq_nbands":
                cascade = properties.get("biquad_cascade")
                if isinstance(cascade, list) and cascade:
                    element = _build_biquad_cascade(Gst, node_id, cascade)
                else:
                    element = _build_equalizer(Gst, node_id, properties)
            else:
                raise ProcessingGraphBuildError(
                    "DSP_STRATEGY_UNAVAILABLE",
                    f"the host builder does not implement {strategy!r}",
                )
            node_elements[node_id] = element
            node_factories[node_id] = (
                tuple(item.get_factory().get_name() for item in element)
                if isinstance(element, (list, tuple))
                else (element.get_factory().get_name(),)
            )
            if isinstance(element, (list, tuple)):
                elements.extend(element)
            else:
                elements.append(element)
        elements.append(sink)
        for element in elements:
            pipeline.add(element)
        chain = [source, source_caps, convert, working_caps]
        for element in node_elements.values():
            if isinstance(element, (list, tuple)):
                chain.extend(element)
            else:
                chain.append(element)
        chain.append(sink)
        for upstream, downstream in zip(chain, chain[1:], strict=False):
            if not upstream.link(downstream):
                raise ProcessingGraphBuildError(
                    "DSP_GRAPH_LINK_FAILED",
                    f"cannot link {upstream.get_name()} -> {downstream.get_name()}",
                )

        change = pipeline.set_state(Gst.State.PAUSED)
        if change == Gst.StateChangeReturn.FAILURE:
            raise ProcessingGraphBuildError(
                "DSP_GRAPH_BUILD_FAILED", "candidate pipeline refused PAUSED"
            )
        ret, state, _pending = pipeline.get_state(PREROLL_TIMEOUT_NS)
        if ret == Gst.StateChangeReturn.FAILURE or state != Gst.State.PAUSED:
            raise ProcessingGraphBuildError(
                "DSP_PREROLL_FAILED",
                f"candidate did not preroll (return={ret!r}, state={state!r})",
            )
    except Exception:
        pipeline.set_state(Gst.State.NULL)
        raise

    factories = tuple(element.get_factory().get_name() for element in elements)
    return BuiltProcessingCandidate(
        pipeline=pipeline,
        plan_id=plan_id,
        working_format=working_format,
        input_rate_hz=input_rate_hz,
        channels=channels,
        node_elements=node_elements,
        node_factories=node_factories,
        working_capsfilter=working_caps,
        graph_factories=factories,
    )


def build_processing_filter(plan: dict[str, Any]) -> dict[str, Any]:
    """Build the PRODUCTIVE filter bin (ghost sink -> DSP -> ghost src).

    No audio source/sink: playbin3 owns the stream and the sink. Returns the
    bin plus primitive element facts; the caller installs it.
    """
    import gi

    gi.require_version("Gst", "1.0")
    from gi.repository import Gst  # noqa: PLC0415 - child-native import

    if not Gst.is_initialized():
        Gst.init(None)

    working_format = str(plan.get("working_format") or "")
    input_rate_hz = int(plan.get("input_rate_hz") or 0)
    channels = int(plan.get("channels") or 0)
    nodes = plan.get("nodes")
    if (
        working_format not in {"F32LE", "F64LE"}
        or input_rate_hz <= 0
        or channels <= 0
        or not isinstance(nodes, list)
        or not nodes
    ):
        raise ProcessingGraphBuildError(
            "DSP_PLAN_INVALID", "compiled plan DTO is incomplete"
        )

    bin_ = Gst.Bin.new("michi-processing-filter")
    convert = _make(Gst, "audioconvert")
    convert.set_property("dithering", 0)
    convert.set_property("noise-shaping", 0)
    working_caps = _make(Gst, "capsfilter")
    working_caps.set_property(
        "caps",
        Gst.Caps.from_string(
            f"audio/x-raw,format={working_format},rate={input_rate_hz},"
            f"channels={channels}"
        ),
    )
    elements = [convert, working_caps]
    node_elements: dict[str, Any] = {}
    node_factories: dict[str, tuple[str, ...]] = {}
    for node in nodes:
        if not isinstance(node, dict):
            raise ProcessingGraphBuildError(
                "DSP_PLAN_INVALID", "node entry is not an object"
            )
        strategy = str(node.get("strategy"))
        node_id = str(node.get("node_id"))
        properties = node.get("properties") or {}
        if strategy == "gain":
            element = _make(Gst, "volume", node_id)
            element.set_property(
                "volume", 10.0 ** (float(properties["gain_db"]) / 20.0)
            )
        elif strategy == "graphic_eq_nbands":
            cascade = properties.get("biquad_cascade")
            if not isinstance(cascade, list) or not cascade:
                raise ProcessingGraphBuildError(
                    "DSP_PLAN_INVALID", "graphic EQ requires a biquad cascade"
                )
            element = _build_biquad_cascade(Gst, node_id, cascade)
        else:
            raise ProcessingGraphBuildError(
                "DSP_STRATEGY_UNAVAILABLE",
                f"the host builder does not implement {strategy!r}",
            )
        node_elements[node_id] = element
        node_factories[node_id] = (
            tuple(item.get_factory().get_name() for item in element)
            if isinstance(element, (list, tuple))
            else (element.get_factory().get_name(),)
        )
        elements.extend(element if isinstance(element, (list, tuple)) else [element])
    for element in elements:
        bin_.add(element)
    chain = [convert, working_caps]
    for element in node_elements.values():
        chain.extend(element if isinstance(element, (list, tuple)) else [element])
    for upstream, downstream in zip(chain, chain[1:], strict=False):
        if not upstream.link(downstream):
            raise ProcessingGraphBuildError(
                "DSP_GRAPH_LINK_FAILED",
                f"cannot link {upstream.get_name()} -> {downstream.get_name()}",
            )
    sink_ghost = Gst.GhostPad.new("sink", convert.get_static_pad("sink"))
    src_ghost = Gst.GhostPad.new("src", chain[-1].get_static_pad("src"))
    if sink_ghost is None or src_ghost is None or not bin_.add_pad(sink_ghost):
        raise ProcessingGraphBuildError(
            "DSP_GRAPH_BUILD_FAILED", "cannot expose the filter ghost pads"
        )
    if not bin_.add_pad(src_ghost):
        raise ProcessingGraphBuildError(
            "DSP_GRAPH_BUILD_FAILED", "cannot expose the filter src ghost pad"
        )
    return {
        "bin": bin_,
        "node_elements": node_elements,
        "node_factories": node_factories,
        "working_capsfilter": working_caps,
        "graph_factories": tuple(
            element.get_factory().get_name() for element in elements
        ),
    }


def _build_biquad_cascade(gst, node_id: str, cascade: list[dict[str, Any]]):
    """One audioiirfilter per RBJ band: exact coefficients, exact readback."""
    elements = []
    for position, band in enumerate(cascade):
        element = _make(gst, "audioiirfilter", f"{node_id}-{position}")
        a = [float(value) for value in band.get("a", [])]
        b = [float(value) for value in band.get("b", [])]
        if len(a) != 3 or len(b) != 3:
            raise ProcessingGraphBuildError(
                "DSP_PLAN_INVALID", "biquad band must carry 3 a/b coefficients"
            )
        element.set_property("a", a)
        element.set_property("b", b)
        elements.append(element)
    return elements


def _build_equalizer(gst, node_id: str, properties: dict[str, Any]):
    element = _make(gst, "equalizer-nbands", node_id)
    gains = [float(value) for value in properties.get("gains_db", [])]
    indices = [int(value) for value in properties.get("band_indices", [])]
    if not gains or len(gains) != len(indices):
        raise ProcessingGraphBuildError(
            "DSP_PLAN_INVALID", "graphic EQ gains/indices mismatch"
        )
    element.set_property("num-bands", len(gains))
    centers = [float(value) for value in properties.get("band_centers_hz", [])]
    if len(centers) != len(indices):
        raise ProcessingGraphBuildError(
            "DSP_PLAN_INVALID", "graphic EQ band centers mismatch"
        )
    for position, (center, gain) in enumerate(zip(centers, gains, strict=True)):
        element.set_property(f"band{position}-freq", float(center))
        element.set_property(f"band{position}-gain", float(gain))
        element.set_property(
            f"band{position}-bandwidth", float(center) * _GRAPHIC_BANDWIDTH_FACTOR
        )
    return element
