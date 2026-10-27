"""Explicit gst-libav DSD→PCM runtime (AP2-F10, R11-F10)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from michi.application.dsd_to_pcm_plan import DsdToPcmPlan

DECODER_FACTORIES = (
    "avdec_dsd_lsbf",
    "avdec_dsd_msbf",
    "avdec_dsd_lsbf_planar",
    "avdec_dsd_msbf_planar",
)


class DsdPcmRuntimeError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class DsdPcmBackend:
    version: str
    factories: tuple[str, ...]
    missing: tuple[str, ...]
    available: bool


@dataclass(frozen=True, slots=True)
class DsdPcmRunEvidence:
    status: str
    eos: bool
    negotiated_caps: str
    target_rate_hz: int
    decoder_factory: str
    backend_version: str
    sink_factory: str


def discover_dsd_pcm_backend() -> DsdPcmBackend:
    try:
        import gi

        gi.require_version("Gst", "1.0")
        from gi.repository import Gst
    except Exception as exc:  # noqa: BLE001
        raise DsdPcmRuntimeError(
            "DSD_PCM_DECODER_UNAVAILABLE",
            f"GStreamer Python bindings unavailable: {exc}",
        ) from exc
    if not Gst.is_initialized():
        Gst.init(None)
    found: list[str] = []
    missing: list[str] = []
    version = ""
    plugin = Gst.Registry.get().find_plugin("libav")
    if plugin is not None:
        version = str(plugin.get_version() or "")
    for name in DECODER_FACTORIES:
        factory = Gst.ElementFactory.find(name)
        if factory is None:
            missing.append(name)
            continue
        found.append(name)
    return DsdPcmBackend(
        version=version or "unknown",
        factories=tuple(found),
        missing=tuple(missing),
        available=bool(found),
    )


class DsdToPcmRuntime:
    """One explicit decoder node; no playbin/decodebin fallback."""

    def run(
        self,
        plan: DsdToPcmPlan,
        source_path: Path,
        *,
        sink_factory: str = "fakesink",
        timeout_s: float = 30.0,
    ) -> DsdPcmRunEvidence:
        if not isinstance(plan, DsdToPcmPlan):
            raise TypeError("plan must be a DsdToPcmPlan")
        path = Path(source_path)
        if not path.is_file():
            raise DsdPcmRuntimeError("DSD_PCM_SOURCE_MISSING", str(path))
        try:
            import gi

            gi.require_version("Gst", "1.0")
            from gi.repository import GLib, Gst
        except Exception as exc:  # noqa: BLE001
            raise DsdPcmRuntimeError(
                "DSD_PCM_DECODER_UNAVAILABLE", f"GStreamer bindings unavailable: {exc}"
            ) from exc
        if not Gst.is_initialized():
            Gst.init(None)
        if Gst.ElementFactory.find(plan.decoder_factory) is None:
            raise DsdPcmRuntimeError(
                "DSD_PCM_DECODER_UNAVAILABLE",
                f"missing explicit factory {plan.decoder_factory}",
            )
        if Gst.ElementFactory.find(sink_factory) is None:
            raise DsdPcmRuntimeError(
                "DSD_PCM_SINK_UNAVAILABLE", f"missing sink {sink_factory}"
            )
        pipeline = Gst.Pipeline.new("michi-dsd2pcm")
        elements: list[Any] = []
        try:
            filesrc = Gst.ElementFactory.make("filesrc", "source")
            demux = Gst.ElementFactory.make("avdemux_dsf", "dsf")
            decoder = Gst.ElementFactory.make(plan.decoder_factory, "decoder")
            convert = Gst.ElementFactory.make("audioconvert", "convert")
            sink = Gst.ElementFactory.make(sink_factory, "sink")
            if None in (filesrc, demux, decoder, convert, sink):
                raise DsdPcmRuntimeError(
                    "DSD_PCM_DECODER_UNAVAILABLE", "required element factory missing"
                )
            filesrc.set_property("location", str(path))
            dsdconvert = Gst.ElementFactory.make("dsdconvert", "dsdconvert")
            if dsdconvert is None:
                raise DsdPcmRuntimeError(
                    "DSD_PCM_DECODER_UNAVAILABLE", "dsdconvert is not installed"
                )
            source_caps = Gst.Caps.from_string(
                "audio/x-dsd,format=DSDU8,layout=interleaved,"
                "reversed-bytes=true,"
                f"channels={plan.channels},"
                f"rate={plan.source_format.bit_rate_hz // 8}"
            )
            source_filter = Gst.ElementFactory.make("capsfilter", "dsd-caps")
            source_filter.set_property("caps", source_caps)
            decoder_caps = Gst.Caps.from_string(
                f"audio/x-raw,format=F32LE,channels={plan.channels},"
                f"rate={plan.target_rate_hz}"
            )
            output_filter = Gst.ElementFactory.make("capsfilter", "pcm-caps")
            output_filter.set_property("caps", decoder_caps)
            elements = [filesrc, demux, dsdconvert, source_filter, decoder, convert]
            if plan.target_rate_hz != plan.decoder_native_rate_hz:
                resampler = Gst.ElementFactory.make("audioresample", "resampler")
                if resampler is None:
                    raise DsdPcmRuntimeError(
                        "DSD_PCM_RESAMPLER_CONTRACT_UNAVAILABLE",
                        "audioresample is not installed",
                    )
                for prop, value in plan.resampler_policy:
                    try:
                        resampler.set_property(prop, value)
                    except Exception as exc:  # noqa: BLE001
                        raise DsdPcmRuntimeError(
                            "DSD_PCM_RESAMPLER_CONTRACT_UNAVAILABLE",
                            f"resampler property {prop}: {exc}",
                        ) from exc
                elements.append(resampler)
            elements.extend([output_filter, sink])
            for element in elements:
                pipeline.add(element)
            if not filesrc.link(demux):
                raise DsdPcmRuntimeError("DSD_PCM_LINK_FAILED", "filesrc -> dsf")

            def _link_demux(_demux, pad) -> None:
                sink_pad = dsdconvert.get_static_pad("sink")
                if sink_pad is not None and not sink_pad.is_linked():
                    pad.link(sink_pad)

            demux.connect("pad-added", _link_demux)
            downstream = elements[2:]
            for upstream, target in zip(downstream, downstream[1:], strict=False):
                if not upstream.link(target):
                    raise DsdPcmRuntimeError(
                        "DSD_PCM_LINK_FAILED",
                        f"{upstream.get_name()} -> {target.get_name()}",
                    )
            result = pipeline.set_state(Gst.State.PLAYING)
            bus = pipeline.get_bus()
            if result is Gst.StateChangeReturn.FAILURE:
                failure = bus.timed_pop_filtered(0, Gst.MessageType.ERROR)
                detail = "pipeline refused PLAYING"
                if failure is not None:
                    detail = failure.parse_error()[1]
                raise DsdPcmRuntimeError("DSD_PCM_PIPELINE_FAILED", detail)
            deadline = GLib.get_monotonic_time() + int(timeout_s * 1_000_000)
            eos = False
            error: str | None = None
            while GLib.get_monotonic_time() < deadline:
                message = bus.timed_pop_filtered(
                    100 * GLib.TIME_SPAN_MILLISECOND,
                    Gst.MessageType.ERROR | Gst.MessageType.EOS,
                )
                if message is None:
                    continue
                if message.type == Gst.MessageType.EOS:
                    eos = True
                    break
                error = message.parse_error()[1]
                break
            if error is not None:
                raise DsdPcmRuntimeError("DSD_PCM_PIPELINE_FAILED", error)
            if not eos:
                raise DsdPcmRuntimeError(
                    "DSD_PCM_TIMEOUT", f"no EOS within {timeout_s:.1f}s"
                )
            pad = sink.get_static_pad("sink")
            decoder_pad = decoder.get_static_pad("sink")
            decoder_caps = (
                decoder_pad.get_current_caps() if decoder_pad is not None else None
            )
            if decoder_caps is None or decoder_caps.get_size() < 1:
                raise DsdPcmRuntimeError(
                    "DSD_PCM_CAPS_MISMATCH", "decoder sink caps were not negotiated"
                )
            structure = decoder_caps.get_structure(0)
            if (
                structure.get_string("format") != "DSDU8"
                or structure.get_string("layout") != "interleaved"
                or structure.get_boolean("reversed-bytes")[1] is not True
                or structure.get_int("channels")[1] != plan.channels
            ):
                raise DsdPcmRuntimeError(
                    "DSD_PCM_CAPS_MISMATCH",
                    f"decoder sink caps contradict plan: {decoder_caps.to_string()}",
                )
            negotiated = pad.get_current_caps() if pad is not None else None
            caps_text = negotiated.to_string() if negotiated is not None else ""
            pipeline.set_state(Gst.State.NULL)
            pipeline.get_state(Gst.SECOND)
            return DsdPcmRunEvidence(
                status="PASS",
                eos=eos,
                negotiated_caps=caps_text,
                target_rate_hz=plan.target_rate_hz,
                decoder_factory=plan.decoder_factory,
                backend_version=plan.backend_version,
                sink_factory=sink_factory,
            )
        finally:
            pipeline.set_state(Gst.State.NULL)
