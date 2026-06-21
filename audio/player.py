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
import numpy as np
from enum import Enum
from dataclasses import dataclass

import gi
gi.require_version("Gst", "1.0")
gi.require_version("GstPbutils", "1.0")
from gi.repository import Gst, GLib  # noqa: E402

from PySide6.QtCore import QObject, Signal, QTimer  # noqa: E402

from audio.audio_chain import DacConfig, build_eq_graphic_chain, build_eq_parametric_chain  # noqa: E402
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

    def set_library_db(self, db):
        self._db = db
        queue, idx = db.load_queue()
        if queue:
            self._queue = queue
            self._queue_index = idx
            self.queue_changed.emit(self._queue)

        self._load_settings()

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
        except Exception as e:
            logging.getLogger("astra.player").debug("Settings load failed: %s", e)

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
            if filepath_or_url.startswith(("http://", "https://", "icy://")):
                self._play_uri(filepath_or_url)
            elif filepath_or_url.lower().endswith(".dff"):
                self._play_dff(filepath_or_url)
            elif filepath_or_url.lower().endswith(".dsf"):
                self._play_uri(self._to_uri(filepath_or_url), is_dsd=True)
            else:
                self._play_uri(self._to_uri(filepath_or_url))

            self._current = filepath_or_url
            if self._db and not filepath_or_url.startswith(("http://", "https://", "icy://")):
                from sync.sync_protocol import make_track_id
                self._db.update_play_history(make_track_id(filepath_or_url))

        except Exception as e:
            logging.getLogger("astra.player").exception("Playback failed: %s", filepath_or_url)
            self.error_occurred.emit(f"No se pudo reproducir: {e}")
            self._state = PlaybackState.STOPPED
            self.state_changed.emit(self._state)

    def _play_uri(self, uri: str, is_dsd: bool = False):
        self._is_dsd = is_dsd
        sink = self._build_sink()

        try:
            self._pipeline = Gst.ElementFactory.make("playbin", "player")
            if not self._pipeline:
                self.error_occurred.emit("Failed to create playbin")
                return

            self._pipeline.set_property("uri", uri)

            audio_sink = Gst.parse_bin_from_description(sink, True)
            if not audio_sink:
                self.error_occurred.emit("Failed to create audio sink")
                return

            self._pipeline.set_property("audio-sink", audio_sink)

        except GLib.Error as e:
            logging.getLogger("astra.player").exception("GStreamer pipeline creation failed")
            self.error_occurred.emit(f"GStreamer: {e.message}")
            self._pipeline = None
            self._state = PlaybackState.STOPPED
            self.state_changed.emit(self._state)
            return
        except Exception as e:
            logging.getLogger("astra.player").exception("Pipeline creation failed")
            self.error_occurred.emit(f"No se pudo crear el pipeline: {e}")
            self._pipeline = None
            self._state = PlaybackState.STOPPED
            self.state_changed.emit(self._state)
            return

        self._setup_bus()
        self._setup_timer()
        self._setup_spectrum()

        # Configure EQ bands programmatically (GstChildProxy)
        if self._eq.mode == "graphic" and not self._is_dsd:
            try:
                eq_elem = self._pipeline.get_by_name("eq_nbands")
                if not eq_elem:
                    # Try to find in the audio-sink bin
                    audio_sink = self._pipeline.get_property("audio-sink")
                    if audio_sink:
                        eq_elem = audio_sink.get_by_name("eq_nbands")
                if eq_elem:
                    for i, db in enumerate(self._eq.bands_31[:31]):
                        band = eq_elem.get_child_by_index(i)
                        if band:
                            band.set_property("gain", float(db))
            except Exception:
                logging.getLogger("astra").debug("EQ bands application failed")

        ret = self._pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            logging.getLogger("astra.player").error(
                "set_state PLAYING failed for URI: %s, sink: %s", uri, sink)
            self.error_occurred.emit("No se pudo iniciar reproducción")
            self._state = PlaybackState.STOPPED
            self.state_changed.emit(self._state)
            return

        logging.getLogger("astra.player").info(
            "Playing URI: %s, sink chain: %s", uri[:100], sink[:100])
        self._state = PlaybackState.PLAYING
        self.state_changed.emit(self._state)

    def _play_dff(self, filepath: str):
        self._is_dsd = True
        try:
            header = parse_dff(filepath)
        except Exception as e:
            logging.getLogger("astra.player").warning("DSF/DFF parse failed: %s", e)
            self.error_occurred.emit(str(e))
            return

        if header.is_dst:
            logging.getLogger("astra.player").warning("DST-compressed DFF not supported: %s", filepath)
            self.error_occurred.emit("DST-compressed DFF not supported")
            return

        self._dff_header = header

        caps = (f"audio/x-dsd,format=DSDU8,reversed-bytes=false,"
                f"layout=interleaved,channels={header.channels},"
                f"rate={header.sample_rate}")

        sink = self._build_sink()
        pipeline_str = (
            f"appsrc name=dsdsrc emit-signals=true format=time caps={caps} "
            f"! avdec_dsd_msbf "
            f"! audioconvert "
            f"! {sink}"
        )
        try:
            self._pipeline = Gst.parse_launch(pipeline_str)
        except GLib.Error as e:
            logging.getLogger("astra.player").exception("DFF pipeline failed")
            self.error_occurred.emit(f"DFF: {e.message}")
            return
        if not self._pipeline:
            self.error_occurred.emit("Failed to create DFF pipeline")
            return

        self._appsrc = self._pipeline.get_by_name("dsdsrc")
        self._file_handle = open(filepath, "rb")  # noqa: SIM115 — handle lives across thread

        self._setup_bus()
        self._setup_timer()
        self._setup_spectrum()

        self._dff_running = True
        self._dff_thread = threading.Thread(target=self._dff_feed, daemon=True)
        self._dff_thread.start()

        self._pipeline.set_state(Gst.State.PLAYING)
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
        if remaining <= 0 and self._dff_running:
            GLib.idle_add(self._push_dff_eos)

    def _push_dff(self, data: bytes, is_last: bool) -> bool:
        if not self._appsrc:
            return False
        buf = Gst.Buffer.new_allocate(None, len(data), None)
        buf.fill(0, data)
        self._appsrc.emit("push-buffer", buf)
        return False

    def _push_dff_eos(self) -> bool:
        if self._appsrc:
            self._appsrc.emit("end-of-stream")
        return False

    # ── Controls ──

    def pause(self):
        if self._pipeline and self._state == PlaybackState.PLAYING:
            self._pipeline.set_state(Gst.State.PAUSED)
            self._state = PlaybackState.PAUSED
            self.state_changed.emit(self._state)

    def resume(self):
        if self._pipeline and self._state == PlaybackState.PAUSED:
            self._pipeline.set_state(Gst.State.PLAYING)
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
        self._restart_if_playing()

    def set_eq_parametric(self, bands: list[dict]):
        self._eq.mode = "parametric"
        self._eq.bands_parametric = list(bands)
        self._restart_if_playing()

    def set_eq_preamp(self, db: float):
        self._eq.preamp_db = db
        self._restart_if_playing()

    def set_eq_bypass(self, bypass: bool):
        self._eq.mode = "bypass" if bypass else (
            "graphic" if self._eq.bands_parametric else "graphic")
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

    def set_output_device(self, device) -> None:
        self._transmit_device = device
        self._restart_if_playing()

    def get_output_device(self):
        return self._transmit_device

    # ── Pipeline Building ──

    @staticmethod
    def _gst_element_exists(name: str) -> bool:
        return Gst.ElementFactory.find(name) is not None

    def _output_sink_str(self) -> str:
        """Return the best available output sink string."""
        if self._dac.mode in ("bitperfect", "dop"):
            return f"alsasink device={self._dac.alsa_device_str}"

        # Standard mode: prefer PipeWire > PulseAudio > Auto > ALSA
        if self._gst_element_exists("pipewiresink"):
            logging.getLogger("astra.player").debug("Using pipewiresink")
            return "pipewiresink"
        if self._gst_element_exists("pulsesink"):
            logging.getLogger("astra.player").debug("Using pulsesink")
            return "pulsesink"
        if self._gst_element_exists("autoaudiosink"):
            logging.getLogger("astra.player").debug("Using autoaudiosink")
            return "autoaudiosink"
        logging.getLogger("astra.player").debug("Falling back to alsasink")
        return f"alsasink device={self._dac.alsa_device_str}"

    def _build_sink(self) -> str:
        parts = []

        # Volume control (always first)
        parts.append(f"volume name=astra_volume volume={self._volume:.4f}")

        # EQ chain (before audioconvert)
        if not self._is_dsd:
            if self._eq.mode == "graphic":
                parts.append(build_eq_graphic_chain(self._eq.bands_31))
            elif self._eq.mode == "parametric":
                eq_part = build_eq_parametric_chain(
                    self._eq.bands_parametric, self._eq.preamp_db)
                if eq_part:
                    parts.append(eq_part)

        # ReplayGain
        if self._replaygain and not self._is_dsd:
            parts.append("rganalysis ! rgvolume album-mode=0 fallback-gain=0 preamp-headroom=0")

        # Converter + resampler
        parts.append("audioconvert")
        parts.append("audioresample")

        # Output sink
        sink = self._output_sink_str()
        parts.append(sink)

        base = " ! ".join(p for p in parts if p)

        # Transmit
        if self._transmit_device and not self._is_dsd:
            dev = self._transmit_device
            if dev.stype == "snapcast":
                host = dev.address or "127.0.0.1"
                port = dev.port or 1704
                base = (f"tee name=transmit_tee {base} "
                        f"transmit_tee. ! queue ! audioconvert ! audioresample ! "
                        f"audio/x-raw,rate=48000,channels=2 ! "
                        f"tcpclientsink host={host} port={port}")
            elif dev.stype == "http":
                port = dev.port or 8554
                base = (f"tee name=transmit_tee {base} "
                        f"transmit_tee. ! queue ! audioconvert ! audioresample ! "
                        f"audio/x-raw,rate=44100,channels=2 ! "
                        f"tcpserversink host=0.0.0.0 port={port}")

        # Spectrum
        if self._spectrum_enabled and not self._is_dsd:
            base += (" ! tee name=spectrum_tee "
                     "spectrum_tee. ! queue ! appsink name=spectrum_sink "
                     "emit-signals=true max-buffers=10 drop=true sync=false")

        return base

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

    def _setup_timer(self):
        if self._timer:
            self._timer.stop()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(self.POLL_MS)

    def _on_bus_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self._on_media_finished()
        elif t == Gst.MessageType.ERROR:
            err, _ = message.parse_error()
            self.error_occurred.emit(f"GStreamer: {err}")

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
            vol_elem = self._pipeline.get_by_name("astra_volume")
            if vol_elem:
                vol_elem.set_property("volume", self._volume)

    def _on_media_finished(self):
        if not self.play_next():
            self._pipeline.set_state(Gst.State.NULL)
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
