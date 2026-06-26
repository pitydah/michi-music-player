"""Pipeline Factory — builds GStreamer pipelines per profile and format."""
import logging
import os
import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

from audio.format_probe import AudioFormatInfo  # noqa: E402
from audio.audio_route_plan import AudioRoutePlan  # noqa: E402
from audio.dsp_state import DspState  # noqa: E402
from audio.audio_chain import build_eq_parametric_chain  # noqa: E402

logger = logging.getLogger("michi.pipeline")


class PipelineFactory:
    def __init__(self):
        Gst.init(None)

    def build_for_uri(self, uri: str, fmt: AudioFormatInfo,
                      route: AudioRoutePlan,
                      dsp: DspState,
                      transmit_device=None) -> Gst.Element | None:
        """Build a GStreamer pipeline for the given route plan."""

        if route.bitperfect_expected and fmt.is_pcm and not fmt.is_dsd:
            return self._build_bitperfect(uri, route)

        if fmt.is_dsd and route.dsd_mode == "pcm":
            return self._build_dsd_to_pcm(uri, fmt, route)

        if fmt.is_dsd and route.dsd_mode == "dop":
            return self._build_dop(uri, fmt, route)

        return self._build_standard(uri, route, dsp, transmit_device)

    def build_playbin_audio_sink(self, route: AudioRoutePlan,
                                  dsp: DspState,
                                  transmit_device=None) -> Gst.Bin | None:
        """Build just the audio-sink bin for use with playbin."""
        return self._make_sink_bin(route, dsp, transmit_device)

    def build_dff_pipeline(self, filepath: str, fmt: AudioFormatInfo,
                           route: AudioRoutePlan) -> Gst.Pipeline | None:
        """Build a manual DFF pipeline with appsrc."""
        src = Gst.ElementFactory.make("appsrc", "dff-appsrc")
        dec = Gst.ElementFactory.make("avdec_dsd_msbf", None)
        conv = Gst.ElementFactory.make("audioconvert", None)
        sink = self._make_sink_from_route(route)
        if not all([src, dec, conv, sink]):
            import logging
            logging.getLogger("michi.pipeline").warning(
                "DFF pipeline: missing elements — appsrc=%s avdec_dsd_msbf=%s audioconvert=%s sink=%s",
                src is not None, dec is not None, conv is not None, sink is not None)
            return None

        pipeline = Gst.Pipeline.new("michi-dff")
        for e in [src, dec, conv, sink]:
            pipeline.add(e)
        src.link(dec)
        dec.link(conv)
        conv.link(sink)

        src.set_property("format", Gst.Format.TIME)
        src.set_property("block", True)
        src.set_property("max-bytes", 65536)
        return pipeline

    # ── Internal builders ──

    def _build_standard(self, uri, route, dsp, transmit_device) -> Gst.Element | None:
        pipeline = Gst.Pipeline.new("michi-pipeline")
        playbin = Gst.ElementFactory.make("playbin", "playbin")
        if not playbin:
            return None
        playbin.set_property("uri", uri)
        pipeline.add(playbin)

        audio_sink = self._make_sink_bin(route, dsp, transmit_device)
        if not audio_sink:
            return None
        playbin.set_property("audio-sink", audio_sink)
        if pipeline.set_state(Gst.State.READY) == Gst.StateChangeReturn.FAILURE:
            logger.warning("Standard pipeline failed to reach READY")
            return None
        return pipeline

    def _make_sink_bin(self, route, dsp, transmit_device) -> Gst.Bin | None:
        """Build audio-sink bin with tee for output + spectrum + transmit."""
        audio_sink = Gst.Bin.new("audio-sink-bin")
        queue = Gst.ElementFactory.make("queue", None)
        volume = Gst.ElementFactory.make("volume", "michi_volume")
        if not queue or not volume:
            return None

        audio_sink.add(queue)
        audio_sink.add(volume)
        queue.link(volume)
        last = volume

        # ReplayGain
        if dsp.replaygain_enabled and route.use_replaygain:
            rg = Gst.ElementFactory.make("rgvolume", None)
            if rg:
                if dsp.replaygain_db != 0.0:
                    rg.set_property("fallback-gain", dsp.replaygain_db)
                audio_sink.add(rg)
                last.link(rg)
                last = rg

        # EQ — parametric or graphic
        if dsp.eq_enabled and route.use_eq:
            if dsp.eq_mode == "parametric" and dsp.eq_bands_parametric:
                chain_str = build_eq_parametric_chain(
                    dsp.eq_bands_parametric, dsp.eq_preamp_db)
                if chain_str:
                    try:
                        eq_bin = Gst.parse_bin_from_description(chain_str, True)
                        if eq_bin:
                            audio_sink.add(eq_bin)
                            last.link(eq_bin)
                            last = eq_bin
                        else:
                            import logging
                            logging.getLogger("michi.pipeline").warning(
                                "Parametric EQ: parse_bin_from_description returned None (audioiirfilter missing?)")
                    except Exception as e:
                        import logging
                        logging.getLogger("michi.pipeline").debug(
                            "Parametric EQ build failed: %s", e)
            else:
                eq = Gst.ElementFactory.make("equalizer-nbands", "eq_nbands")
                if eq:
                    audio_sink.add(eq)
                    last.link(eq)
                    last = eq
                else:
                    logger.warning("Graphic EQ: equalizer-nbands element not available — EQ disabled")

        # Convert + resample
        if route.use_audioconvert:
            ac = Gst.ElementFactory.make("audioconvert", None)
            if ac:
                audio_sink.add(ac)
                last.link(ac)
                last = ac

        if route.use_audioresample:
            ar = Gst.ElementFactory.make("audioresample", None)
            if ar:
                audio_sink.add(ar)
                last.link(ar)
                last = ar

        # Tee
        tee = Gst.ElementFactory.make("tee", "t")
        if tee:
            audio_sink.add(tee)
            last.link(tee)

            # Branch 1: main output
            q1 = Gst.ElementFactory.make("queue", None)
            sink = self._make_sink_from_route(route)
            if q1 and sink:
                audio_sink.add(q1)
                audio_sink.add(sink)
                q1.link(sink)
                tee.link(q1)

            # Branch 2: spectrum
            if dsp.spectrum_enabled and route.use_spectrum:
                q2 = Gst.ElementFactory.make("queue", None)
                appsink = Gst.ElementFactory.make("appsink", "spectrum_sink")
                if q2 and appsink:
                    appsink.set_property("sync", False)
                    appsink.set_property("drop", True)
                    appsink.set_property("max-buffers", 4)
                    audio_sink.add(q2)
                    audio_sink.add(appsink)
                    q2.link(appsink)
                    tee.link(q2)

            # Branch 3: transmit
            if transmit_device and route.use_transmit:
                # Extract host string from TransmitDevice or use raw string
                if isinstance(transmit_device, str):
                    host = transmit_device
                elif hasattr(transmit_device, 'address'):
                    host = transmit_device.address
                else:
                    host = str(transmit_device)
                q3 = Gst.ElementFactory.make("queue", None)
                c3 = Gst.ElementFactory.make("audioconvert", None)
                r3 = Gst.ElementFactory.make("audioresample", None)
                caps = Gst.Caps.from_string(
                    "audio/x-raw,rate=48000,channels=2")
                t_sink = Gst.ElementFactory.make("tcpclientsink", None)
                if all([q3, c3, r3, t_sink]):
                    t_sink.set_property("host", host)
                    for e in [q3, c3, r3, t_sink]:
                        audio_sink.add(e)
                    q3.link(c3)
                    c3.link(r3)
                    r3.link_filtered(t_sink, caps)
                    tee.link(q3)
        else:
            s = self._make_sink_from_route(route)
            if s:
                audio_sink.add(s)
                last.link(s)

        audio_sink.add_pad(
            Gst.GhostPad.new("sink", queue.get_static_pad("sink")))
        return audio_sink

    def _build_bitperfect(self, uri, route) -> Gst.Element | None:
        pipeline = Gst.Pipeline.new("michi-bp")
        playbin = Gst.ElementFactory.make("playbin", "playbin")
        if not playbin:
            return None
        playbin.set_property("uri", uri)
        pipeline.add(playbin)
        sink = self._make_sink_from_route(route)
        if not sink:
            return None
        playbin.set_property("audio-sink", sink)
        if pipeline.set_state(Gst.State.READY) == Gst.StateChangeReturn.FAILURE:
            logger.warning("Bitperfect pipeline failed to reach READY")
            return None
        return pipeline

    def _build_dsd_to_pcm(self, uri, fmt, route) -> Gst.Element | None:
        pipeline = Gst.Pipeline.new("michi-dsd-pcm")
        playbin = Gst.ElementFactory.make("playbin", "playbin")
        if not playbin:
            return None
        playbin.set_property("uri", uri)
        pipeline.add(playbin)

        audio_sink = Gst.Bin.new("dsd-pcm-sink")
        conv = Gst.ElementFactory.make("audioconvert", None)
        res = Gst.ElementFactory.make("audioresample", None)
        sink = self._make_sink_from_route(route)
        if not all([conv, res, sink]):
            return None
        for e in [conv, res, sink]:
            audio_sink.add(e)
        conv.link(res)
        res.link(sink)

        audio_sink.add_pad(
            Gst.GhostPad.new("sink", conv.get_static_pad("sink")))
        playbin.set_property("audio-sink", audio_sink)
        if pipeline.set_state(Gst.State.READY) == Gst.StateChangeReturn.FAILURE:
            logger.warning("DSD-to-PCM pipeline failed to reach READY")
            return None
        return pipeline

    def _build_dop(self, uri, fmt, route):
        if not os.environ.get("MICHI_DOP_EXPERIMENTAL"):
            return None

        pipeline = Gst.Pipeline.new("michi-dop")
        src = Gst.ElementFactory.make("filesrc", "dop-src")
        if not src:
            return None
        src.set_property("location", uri.replace("file://", ""))

        dec = Gst.ElementFactory.make("avdec_dsd_msbf", None)
        conv = Gst.ElementFactory.make("audioconvert", None)
        res = Gst.ElementFactory.make("audioresample", None)
        sink = self._make_sink_from_route(route)
        if not all([dec, conv, res, sink]):
            return None

        for e in [src, dec, conv, res, sink]:
            pipeline.add(e)
        src.link(dec)
        dec.link(conv)
        conv.link(res)
        res.link(sink)
        return pipeline

    def _make_sink_from_route(self, route: AudioRoutePlan) -> Gst.Element | None:
        ds = route.device_string or "autoaudiosink"
        parts = ds.split(maxsplit=1)
        sink_name = parts[0]
        sink = Gst.ElementFactory.make(sink_name, None)
        if not sink:
            logger.warning("Sink element '%s' not found, falling back to autoaudiosink", sink_name)
            sink = Gst.ElementFactory.make("autoaudiosink", None)
            if not sink:
                logger.error("autoaudiosink not found — no audio output available")
                return None
            logger.info("Using autoaudiosink as fallback for '%s'", sink_name)
            return sink
        if len(parts) > 1:
            for param in parts[1:]:
                if "=" in param:
                    k, v = param.split("=", 1)
                    try:
                        sink.set_property(k, v)
                    except Exception as e:
                        logger.warning("Failed to set sink property %s=%s: %s", k, v, e)
        return sink
