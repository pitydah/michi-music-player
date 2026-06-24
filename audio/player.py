"""GStreamerEngine — unified audio engine replacing QMediaPlayer.

Architecture:
    playbin → audioconvert → EQ (graphic/parametric) → tee
    ├── alsasink (or pipewiresink)
    └── appsink → numpy FFT → SpectrumWidget

Supports: common audio, DSD (.dsf/.dff), streaming URLs.
DAC: bit-perfect, DoP, standard. EQ: graphic 31-band, parametric biquads.
"""

import os
import threading
import logging
import contextlib
import numpy as np
from enum import Enum
from dataclasses import dataclass

import gi
gi.require_version("Gst", "1.0")
gi.require_version("GstPbutils", "1.0")
from gi.repository import Gst, GLib  # noqa: E402

from PySide6.QtCore import QObject, Signal, QTimer  # noqa: E402

from audio.audio_chain import DacConfig  # noqa: E402
from audio.dff_parser import parse_dff  # noqa: E402

Gst.init(None)


class PlaybackState(Enum):
    STOPPED = 0
    PLAYING = 1
    PAUSED = 2


@dataclass
class EqState:
    mode: str = "graphic"           # "graphic" | "parametric" | "bypass"
    bands_31: list[float] = None    # 31 floats for graphic
    bands_parametric: list[dict] = None  # parametric band configs
    preamp_db: float = 0.0

    def __post_init__(self):
        if self.bands_31 is None:
            self.bands_31 = [0.0] * 31
        if self.bands_parametric is None:
            self.bands_parametric = []


class GStreamerEngine(QObject):
    """Unified audio playback via GStreamer with DSP chain."""

    position_changed = Signal(float)    # seconds
    duration_changed = Signal(float)    # seconds
    state_changed = Signal(PlaybackState)
    finished = Signal()
    error_occurred = Signal(str)
    spectrum_data = Signal(object)      # numpy array for FFT
    queue_changed = Signal(list)
    audio_route_changed = Signal(object)  # AudioRouteDiagnostics
    eq_bitperfect_warning = Signal()  # Emitted when EQ conflicts with bit-perfect

    POLL_MS = 250

    def __init__(self, dac: DacConfig = None, parent=None):
        super().__init__(parent)
        self._dac = dac or DacConfig()
        self._pipeline: Gst.Pipeline | None = None
        self._bus_id = 0
        self._timer = None
        self._state = PlaybackState.STOPPED
        self._duration = 0.0
        self._current = None
        self._is_dsd = False

        # EQ state
        self._eq = EqState()

        # Spectrum
        self._spectrum_enabled = False
        self._spectrum_sink = None

        # DFF support
        self._dff_header = None
        self._dff_thread = None
        self._dff_running = False
        self._file_handle = None
        self._appsrc = None

        # Queue
        self._queue: list[str] = []
        self._queue_index = -1
        self._shuffle = False
        self._repeat = "none"
        self._db = None

        # Transmit
        self._transmit_device = None

        # Crossfade / ReplayGain
        self._volume = 0.70
        self._crossfade = 0       # seconds
        self._replaygain = False
        self._gapless_enabled = True
        self._audio_profile = "standard"

    def set_library_db(self, db):
        self._db = db
        queue, idx = db.load_queue()
        if queue:
            self._queue = queue
            self._queue_index = idx
            self.queue_changed.emit(self._queue)

        self._load_settings()

    def set_audio_profile(self, profile_key: str):
        self._audio_profile = profile_key
        self._restart_if_playing()

    def set_dsd_mode(self, mode: str):
        self._dac.dsd_mode = mode

    def set_gapless_enabled(self, enabled: bool):
        self._gapless_enabled = enabled

    def set_replaygain_mode(self, mode: str):
        self._replaygain = (mode != "off")

    def get_position_ns(self) -> int:
        """Return current playback position in nanoseconds, or 0."""
        if self._pipeline:
            ok, pos_ns = self._pipeline.query_position(Gst.Format.TIME)
            if ok:
                return pos_ns
        return 0

    @property
    def current(self) -> str:
        """Current playing filepath or URL."""
        return self._current

    def set_output_device_id(self, device_id: str):
        """Select a local audio output device (ALSA hw:, PipeWire, etc.).

        This is the LOCAL output branch — does NOT affect network transmit.
        """
        from audio.output_device_manager import get_device
        dev = get_device(device_id)
        if dev:
            self._dac.device = dev.device_string
        else:
            self._dac.device = device_id or "Predeterminada del sistema"
            self._dac.output_device_id = device_id or "auto"
        self._restart_if_playing()

    def get_output_device_id(self) -> str:
        return self._dac.device or self._dac.output_device_id

    def set_transmit_device(self, device) -> None:
        """Set the network transmit device (TransmitDevice or None for none).

        This is the TRANSMIT branch — sends audio over TCP to remote device.
        Does NOT affect the local audio output sink.
        """
        self._transmit_device = device
        self._restart_if_playing()

    def get_transmit_device(self):
        return self._transmit_device

    def get_audio_diagnostics(self):
        from audio.audio_diagnostics import AudioRouteDiagnostics
        from audio.output_profiles import get_profile
        profile = get_profile(self._audio_profile)
        return AudioRouteDiagnostics(
            current_uri=self._current or "",
            profile=profile.key,
            backend=self._dac.mode,
            device_name=self._dac.device,
            device_string=self._dac.alsa_device_str,
            bitperfect_status=(
                "yes" if profile.bitperfect and not self._is_dsd else "no"),
            dsp_active=self._eq.mode != "bypass" if hasattr(self, '_eq') else False,
            eq_active=getattr(getattr(self, '_eq', None), 'mode', 'bypass') != 'bypass',
            replaygain_active=self._replaygain,
            spectrum_active=self._spectrum_enabled,
            resampling_active=self._dac.target_rate > 0,
        )

    def _load_settings(self):
        try:
            import core.settings_manager as sm
            self._dac.device = sm.get("audio/device")
            self._dac.mode = sm.get("audio/mode")
            self._dac.buffer_ms = sm.get("audio/buffer_ms")
            self._eq.mode = sm.get("eq/mode")
            self._eq.preamp_db = sm.get("eq/preamp")
            self._crossfade = sm.get("playback/crossfade")
            self._replaygain = sm.get("playback/replaygain")
            self._gapless_enabled = sm.get("audio/gapless_enabled")
            self._audio_profile = sm.get("audio/profile") or "standard"
        except Exception as e:
            logging.getLogger("michi.player").debug("Settings load failed: %s", e)

    @property
    def state(self) -> PlaybackState:
        return self._state

    def _to_uri(self, filepath_or_url: str) -> str:
        if filepath_or_url.startswith(("http://", "https://", "icy://")):
            return filepath_or_url
        if filepath_or_url.startswith("file://"):
            return filepath_or_url
        return GLib.filename_to_uri(os.path.abspath(filepath_or_url), None)

    # ── Playback ──

    def play(self, filepath_or_url: str):
        self.stop()

        try:
            # DFF uses separate appsrc pipeline
            if filepath_or_url.lower().endswith(".dff"):
                self._play_dff(filepath_or_url)
                self._current = filepath_or_url
                return

            uri = self._to_uri(filepath_or_url)
            self._is_dsd = filepath_or_url.lower().endswith(".dsf")

            # Build pipeline via PipelineFactory
            from audio.format_probe import probe_format
            from audio.output_profiles import get_profile
            from audio.output_device_manager import get_device
            from audio.pipeline_factory import PipelineFactory
            from audio.dsp_state import DspState
            from audio.audio_diagnostics import AudioRouteDiagnostics

            fmt = probe_format(filepath_or_url)
            profile = get_profile(self._audio_profile)
            dev = get_device(self._dac.output_device_id or "auto")
            if not dev:
                from audio.output_device_manager import list_devices
                devs = list_devices()
                dev = devs[0] if devs else None

            # ReplayGain advanced — extract tags, compute safe gain
            rg_gain_db: float | None = None
            if self._replaygain and profile.allows_replaygain:
                try:
                    from audio.replaygain import ReplayGainConfig, apply_full, linear_to_db
                    from library.metadata_extractor import extract_metadata_full
                    meta_full = extract_metadata_full(filepath_or_url)
                    track_gain = meta_full.get("replaygain_track") or 0.0
                    album_gain = meta_full.get("replaygain_album") or 0.0
                    config = ReplayGainConfig(
                        mode=self._replaygain_mode if hasattr(self, '_replaygain_mode') else "track",
                        preamp_db=getattr(self, '_replaygain_preamp', 0.0),
                        headroom_db=getattr(self, '_replaygain_headroom', 0.0),
                        anti_clip=getattr(self, '_replaygain_anticlip', True),
                    )
                    gain, _label = apply_full(config, track_gain, album_gain)
                    if gain != 1.0:
                        rg_gain_db = linear_to_db(gain)
                except Exception:
                    pass

            dsp = DspState(
                eq_enabled=(hasattr(self, '_eq') and self._eq.mode != "bypass"),
                eq_mode=getattr(self._eq, 'mode', 'bypass'),
                eq_bands_parametric=getattr(self._eq, 'bands_parametric', []),
                eq_preamp_db=getattr(self._eq, 'preamp_db', 0.0),
                replaygain_enabled=(self._replaygain and rg_gain_db is not None),
                replaygain_db=(rg_gain_db or 0.0),
                spectrum_enabled=self._spectrum_enabled,
                transmit_enabled=self._transmit_device is not None,
            )
            from audio.dac_manager import DacManager
            dm = DacManager(self)
            dm.refresh_devices()
            route = dm.select_output_route(fmt, profile, dev)

            factory = PipelineFactory()
            self._pipeline = factory.build_for_uri(
                uri, fmt, route, dsp,
                transmit_device=(
                    self._transmit_device if profile.allows_transmit else None))

            if not self._pipeline:
                self.error_occurred.emit("Failed to create pipeline")
                self._state = PlaybackState.STOPPED
                self.state_changed.emit(self._state)
                return

            self._current = filepath_or_url
            self._setup_bus()
            self._setup_timer()
            ret = self._pipeline.set_state(Gst.State.PLAYING)
            if ret == Gst.StateChangeReturn.FAILURE:
                self.error_occurred.emit("Failed to start playback")
                self._state = PlaybackState.STOPPED
                self.state_changed.emit(self._state)
                return
            self._state = PlaybackState.PLAYING
            self.state_changed.emit(self._state)

            # Audio diagnostics
            diag = AudioRouteDiagnostics(
                current_uri=filepath_or_url,
                profile=profile.key,
                backend=dev.backend if dev else "auto",
                device_name=dev.display_name if dev else "",
                device_string=dev.device_string if dev else "autoaudiosink",
                input_codec=fmt.codec,
                input_sample_rate=fmt.sample_rate,
                input_bit_depth=fmt.bit_depth,
                input_channels=fmt.channels,
                dsd_mode=fmt.dsd_speed if fmt.is_dsd else "",
                eq_active=(hasattr(self, '_eq') and self._eq.mode != "bypass"),
                replaygain_active=self._replaygain if hasattr(self, '_replaygain') else False,
                spectrum_active=self._spectrum_enabled,
                bitperfect_status="yes" if profile.bitperfect and not fmt.is_dsd else "no",
            )
            self.audio_route_changed.emit(diag)

            if self._db and not filepath_or_url.startswith(("http://", "https://", "icy://")):
                from sync.sync_protocol import make_track_id
                self._db.update_play_history(make_track_id(filepath_or_url))
                self._db.increment_play_count(filepath_or_url)

        except Exception as e:
            logging.getLogger("michi.player").exception("Playback failed: %s", filepath_or_url)
            self.error_occurred.emit(f"No se pudo reproducir: {e}")
            self._state = PlaybackState.STOPPED
            self.state_changed.emit(self._state)

    def _play_dff(self, filepath: str):
        self._is_dsd = True
        try:
            header = parse_dff(filepath)
        except Exception as e:
            logging.getLogger("michi.player").warning("DFF parse failed: %s", e)
            self.error_occurred.emit(str(e))
            return

        if header.is_dst:
            logging.getLogger("michi.player").warning("DST-compressed DFF not supported: %s", filepath)
            self.error_occurred.emit("DST-compressed DFF not supported")
            return

        self._dff_header = header

        # Use PipelineFactory for unified pipeline construction
        from audio.format_probe import probe_format
        from audio.output_profiles import get_profile
        from audio.dac_manager import DacManager
        from audio.pipeline_factory import PipelineFactory

        fmt = probe_format(filepath)
        profile = get_profile(self._audio_profile)
        dm = DacManager(self)
        dm.refresh_devices()
        route = dm.select_output_route(fmt, profile, None)

        factory = PipelineFactory()
        self._pipeline = factory.build_dff_pipeline(filepath, fmt, route)
        if not self._pipeline:
            self.error_occurred.emit("Failed to create DFF pipeline")
            return

        # Set caps on appsrc
        caps_str = (f"audio/x-dsd,format=DSDU8,reversed-bytes=false,"
                    f"layout=interleaved,channels={header.channels},"
                    f"rate={header.sample_rate}")
        appsrc = self._pipeline.get_by_name("dff-appsrc")
        if appsrc:
            caps = Gst.Caps.from_string(caps_str)
            appsrc.set_property("caps", caps)
        self._appsrc = appsrc
        self._file_handle = open(filepath, "rb")  # noqa: SIM115 — handle lives across DFF thread

        self._setup_bus()
        self._setup_timer()
        self._setup_spectrum()

        self._dff_running = True
        self._dff_thread = threading.Thread(target=self._dff_feed, daemon=True)
        self._dff_thread.start()

        ret = self._pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            self.error_occurred.emit("Failed to start DFF playback")
            self._state = PlaybackState.STOPPED
            self.state_changed.emit(self._state)
            return
        self._state = PlaybackState.PLAYING
        self.state_changed.emit(self._state)

    def _dff_feed(self):
        h = self._dff_header
        fh = self._file_handle
        if not fh or not h:
            return
        fh.seek(h.data_offset)
        remaining = h.data_size
        while self._dff_running and remaining > 0:
            data = fh.read(min(16384, remaining))
            if not data:
                break
            remaining -= len(data)
            GLib.idle_add(self._push_dff, bytes(data), remaining <= 0)
            if remaining > 0 and self._dff_running:
                import time
                time.sleep(0.005)  # throttle to avoid flooding the event loop
        if remaining <= 0 and self._dff_running:
            GLib.idle_add(self._push_dff_eos)

    def _push_dff(self, data: bytes, is_last: bool) -> bool:
        if not self._appsrc:
            return False
        buf = Gst.Buffer.new_allocate(None, len(data), None)
        buf.fill(0, data)
        ret = self._appsrc.emit("push-buffer", buf)
        if ret != Gst.FlowReturn.OK:
            logging.getLogger("michi.player").warning("DFF push-buffer failed: %s", ret)
        return False  # one-shot via GLib.idle_add

    def _push_dff_eos(self) -> bool:
        if self._appsrc:
            self._appsrc.emit("end-of-stream")
        return False

    # ── Controls ──

    def pause(self):
        if self._pipeline and self._state == PlaybackState.PLAYING:
            ret = self._pipeline.set_state(Gst.State.PAUSED)
            if ret == Gst.StateChangeReturn.FAILURE:
                return
            self._state = PlaybackState.PAUSED
            self.state_changed.emit(self._state)

    def resume(self):
        if self._pipeline and self._state == PlaybackState.PAUSED:
            ret = self._pipeline.set_state(Gst.State.PLAYING)
            if ret == Gst.StateChangeReturn.FAILURE:
                return
            self._state = PlaybackState.PLAYING
            self.state_changed.emit(self._state)

    def toggle(self):
        if self._state == PlaybackState.PLAYING:
            self.pause()
        elif self._state == PlaybackState.PAUSED:
            self.resume()
        elif self._current:
            self.play(self._current)

    def stop(self):
        self._dff_running = False
        if self._pipeline:
            self._pipeline.set_state(Gst.State.NULL)
            result = self._pipeline.get_state(2 * Gst.SECOND)
            if result[0] == Gst.StateChangeReturn.FAILURE:
                import logging
                logging.getLogger("michi.player").warning(
                    "Pipeline NULL transition failed in stop()")
        if self._bus_id and self._pipeline:
            bus = self._pipeline.get_bus()
            bus.disconnect(self._bus_id)
            bus.remove_signal_watch()
            self._bus_id = 0
        self._pipeline = None
        self._appsrc = None
        if self._dff_thread and self._dff_thread.is_alive():
            self._dff_thread.join(timeout=2.0)
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
        if self._timer:
            self._timer.stop()
            self._timer = None
        self._state = PlaybackState.STOPPED
        self.state_changed.emit(self._state)

    def seek(self, seconds: float):
        if self._pipeline:
            ns = int(seconds * 1e9)
            self._pipeline.seek_simple(
                Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, ns)

    # ── EQ Control ──

    def set_eq_graphic(self, bands: list[float]):
        self._eq.mode = "graphic"
        self._eq.bands_31 = bands[:31]
        self._check_dsp_vs_bitperfect()
        self._restart_if_playing()

    def set_eq_parametric(self, bands: list[dict]):
        self._eq.mode = "parametric"
        self._eq.bands_parametric = list(bands)
        self._check_dsp_vs_bitperfect()
        self._restart_if_playing()

    def set_eq_bypass(self, bypass: bool):
        self._eq.mode = "bypass" if bypass else (
            "parametric" if self._eq.bands_parametric else "graphic")
        self._restart_if_playing()

    def _check_dsp_vs_bitperfect(self):
        """Emit warning if DSP is active in bit-perfect mode."""
        from audio.output_profiles import get_profile
        profile = get_profile(self._audio_profile)
        if profile.bitperfect and self._eq.mode != "bypass":
            self.eq_bitperfect_warning.emit()

    def set_eq_preamp(self, db: float):
        self._eq.preamp_db = db
        self._restart_if_playing()

    def set_spectrum_enabled(self, enabled: bool):
        self._spectrum_enabled = enabled
        if self._pipeline and self._state == PlaybackState.PLAYING:
            self._restart_if_playing()

    def _restart_if_playing(self):
        if self._current and self._state in (PlaybackState.PLAYING, PlaybackState.PAUSED):
            pos = 0
            if self._pipeline:
                ok, pos_ns = self._pipeline.query_position(Gst.Format.TIME)
                if ok:
                    pos = pos_ns / 1e9
            self.play(self._current)
            if pos > 0.5:
                self.seek(pos)

    # ── Pipeline Building ──

    @staticmethod
    def _gst_element_exists(name: str) -> bool:
        return Gst.ElementFactory.find(name) is not None

    def _setup_spectrum(self):
        if not self._spectrum_enabled or not self._pipeline:
            return
        sink = self._pipeline.get_by_name("spectrum_sink")
        if sink:
            self._spectrum_sink = sink
            sink.connect("new-sample", self._on_spectrum_sample)

    def _on_spectrum_sample(self, appsink):
        sample = appsink.emit("pull-sample")
        if sample:
            buf = sample.get_buffer()
            ok, map_info = buf.map(Gst.MapFlags.READ)
            if ok:
                # Interpret as float32 audio
                arr = np.frombuffer(map_info.data, dtype=np.float32)
                buf.unmap(map_info)
                if len(arr) > 0:
                    fft = np.fft.rfft(arr[-2048:] if len(arr) >= 2048 else arr)
                    self.spectrum_data.emit(np.abs(fft))
        return Gst.FlowReturn.OK

    # ── Bus / Timer ──

    def _setup_bus(self):
        if not self._pipeline:
            return
        bus = self._pipeline.get_bus()
        bus.add_signal_watch()
        self._bus_id = bus.connect("message", self._on_bus_message)
        # Gapless: preload next URI when current track is about to end
        self._gapless_active = False
        playbin = self._pipeline.get_by_name("playbin")
        if not playbin:
            playbin = self._pipeline.get_by_name("player")
        if not playbin:
            playbin = self._pipeline
        if hasattr(playbin, "connect"):
            playbin.connect("about-to-finish", self._on_about_to_finish)

    def _on_about_to_finish(self, playbin):
        """Preload next track URI for gapless playback."""
        if not getattr(self, '_gapless_enabled', True):
            return
        current_uri = getattr(self, '_current', '')
        if current_uri and (current_uri.startswith("http") or "icy" in current_uri):
            return  # No gapless for streams
        if (self._queue_index >= 0
                and self._queue_index < len(self._queue) - 1):
            next_fp = self._queue[self._queue_index + 1]
            next_uri = self._to_uri(next_fp)
            playbin.set_property("uri", next_uri)
            self._gapless_active = True

    def _on_media_finished_eos(self):
        """Handle track end — gapless-aware."""
        if self._gapless_active:
            # Gapless already preloaded next track via about-to-finish
            # Just advance queue index without restarting
            self._gapless_active = False
            self._queue_index += 1
            if self._db:
                self._db.save_queue(self._queue, self._queue_index)
        else:
            self._on_media_finished()

    def _setup_timer(self):
        if self._timer:
            self._timer.stop()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(self.POLL_MS)

    def _on_bus_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self._on_media_finished_eos()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logging.getLogger("michi.player").warning(
                "GStreamer error: %s | %s", err, debug)
            self.error_occurred.emit(f"GStreamer: {err}")
            # Cleanup pipeline after error
            self._dff_running = False
            if self._pipeline:
                self._pipeline.set_state(Gst.State.NULL)
                self._pipeline.get_state(2 * Gst.SECOND)
            if self._bus_id and self._pipeline:
                with contextlib.suppress(Exception):
                    bus = self._pipeline.get_bus()
                    bus.disconnect(self._bus_id)
                    bus.remove_signal_watch()
            self._bus_id = 0
            self._pipeline = None
            self._appsrc = None
            self._state = PlaybackState.STOPPED
            self.state_changed.emit(self._state)
            if self._file_handle:
                with contextlib.suppress(Exception):
                    self._file_handle.close()
                self._file_handle = None
            self._timer.stop() if hasattr(self, '_timer') and self._timer else None
        elif t == Gst.MessageType.WARNING:
            err, debug = message.parse_warning()
            logging.getLogger("michi.player").debug(
                "GStreamer warning: %s | %s", err, debug)
        elif t == Gst.MessageType.BUFFERING:
            pct = message.parse_buffering()
            logging.getLogger("michi.player").debug("Buffering: %d%%", pct)
            if pct < 100 and self._state == PlaybackState.PLAYING:
                self._pipeline.set_state(Gst.State.PAUSED)
            elif pct >= 100 and self._state == PlaybackState.PLAYING:
                self._pipeline.set_state(Gst.State.PLAYING)
        elif t == Gst.MessageType.TAG:
            pass  # Stream metadata — could emit track_changed for radio
        elif t == Gst.MessageType.STATE_CHANGED:
            if message.src == self._pipeline:
                old, new, pending = message.parse_state_changed()
                logging.getLogger("michi.player").debug(
                    "State: %s → %s (pending: %s)",
                    old.value_nick, new.value_nick, pending.value_nick)
        elif t == Gst.MessageType.DURATION_CHANGED:
            ok, dur = self._pipeline.query_duration(Gst.Format.TIME)
            if ok and dur > 0:
                self._duration = dur / 1e9
                self.duration_changed.emit(self._duration)

    def _poll(self):
        if self._pipeline and self._state == PlaybackState.PLAYING:
            ok, pos = self._pipeline.query_position(Gst.Format.TIME)
            if ok:
                self.position_changed.emit(pos / 1e9)
            ok, dur = self._pipeline.query_duration(Gst.Format.TIME)
            if ok and dur > 0:
                d = dur / 1e9
                if abs(d - self._duration) > 0.1:
                    self._duration = d
                    self.duration_changed.emit(d)

    # ── Queue ──

    def enqueue(self, filepaths: list[str], play_now: bool = True):
        if play_now:
            self._queue = list(filepaths)
            self._queue_index = 0
            if self._queue:
                self.play(self._queue[0])
        else:
            self._queue.extend(filepaths)
            if self._queue_index < 0 and self._queue:
                self._queue_index = 0
                self.play(self._queue[0])
        self.queue_changed.emit(self._queue)
        if self._db:
            self._db.save_queue(self._queue, self._queue_index)

    def set_queue(self, filepaths: list[str], start_index: int = 0):
        """Replace the entire queue and start playing from start_index."""
        self._queue = list(filepaths)
        self._queue_index = max(0, min(start_index, len(self._queue) - 1)) if self._queue else 0
        self.queue_changed.emit(self._queue)
        if self._db:
            self._db.save_queue(self._queue, self._queue_index)
        if self._queue and self._queue_index < len(self._queue):
            self.play(self._queue[self._queue_index])

    def clear_queue(self):
        self._queue = []
        self._queue_index = -1
        self.queue_changed.emit([])
        if self._db:
            self._db.clear_queue_state()

    def play_next(self) -> bool:
        if self._queue_index < len(self._queue) - 1:
            self._queue_index += 1
            self.play(self._queue[self._queue_index])
            if self._db:
                self._db.save_queue(self._queue, self._queue_index)
            return True
        return False

    def play_prev(self) -> bool:
        if self._queue_index > 0:
            self._queue_index -= 1
            self.play(self._queue[self._queue_index])
            if self._db:
                self._db.save_queue(self._queue, self._queue_index)
            return True
        return False

    def get_queue(self) -> list[dict]:
        items = []
        for i, fp in enumerate(self._queue):
            name = os.path.basename(fp)
            items.append({
                "filepath": fp, "title": name, "artist": "",
                "duration": 0, "is_current": (i == self._queue_index),
            })
        return items

    def reorder_queue(self, filepaths: list[str]):
        """Reorder the queue preserving the current track."""
        current_fp = self._queue[self._queue_index] if self._queue_index >= 0 else None
        self._queue = filepaths
        if current_fp:
            try:
                self._queue_index = self._queue.index(current_fp)
            except ValueError:
                self._queue_index = 0
        else:
            self._queue_index = -1
        self.queue_changed.emit(self._queue)
        if self._db:
            self._db.save_queue(self._queue, self._queue_index)

    def play_url(self, url: str, title: str = "", artist: str = ""):
        self.stop()
        self.play(url)

    def set_volume(self, vol: int):
        self._volume = max(0.0, min(1.0, vol / 100.0))
        if self._pipeline:
            vol_elem = self._pipeline.get_by_name("michi_volume")
            if vol_elem:
                vol_elem.set_property("volume", self._volume)

    def _on_media_finished(self):
        if not self.play_next():
            self._pipeline.set_state(Gst.State.NULL)
            result = self._pipeline.get_state(2 * Gst.SECOND)
            if result[0] == Gst.StateChangeReturn.FAILURE:
                import logging
                logging.getLogger("michi.player").warning(
                    "Pipeline NULL transition failed in _on_media_finished")
            self._state = PlaybackState.STOPPED
            self.state_changed.emit(self._state)
            self.finished.emit()

    def toggle_shuffle(self):
        self._shuffle = not self._shuffle
        if self._shuffle and len(self._queue) > 1:
            import random
            current_fp = self._queue[self._queue_index] if self._queue_index >= 0 else None
            rest = [fp for fp in self._queue if fp != current_fp]
            random.shuffle(rest)
            if current_fp:
                self._queue = [current_fp] + rest
                self._queue_index = 0
            else:
                self._queue = rest
                self._queue_index = 0
        if self._db:
            self._db.save_queue(self._queue, self._queue_index)
        return self._shuffle

    def toggle_repeat(self) -> str:
        modes = {"none": "all", "all": "one", "one": "none"}
        self._repeat = modes.get(self._repeat, "none")
        return self._repeat


# Backwards compatibility alias
PlayerEngine = GStreamerEngine
