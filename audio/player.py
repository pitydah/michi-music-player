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
import numpy as np
from enum import Enum
from dataclasses import dataclass

import gi
gi.require_version("Gst", "1.0")
gi.require_version("GstPbutils", "1.0")
from gi.repository import Gst, GLib

from PySide6.QtCore import QObject, Signal, QTimer

from audio.audio_chain import DacConfig, build_eq_graphic_sink, build_eq_parametric_sink
from audio.dff_parser import parse_dff
from audio.eq_biquad import compute_biquad

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
        except Exception:
            pass

    @property
    def state(self) -> PlaybackState:
        return self._state

    # ── Playback ──

    def play(self, filepath_or_url: str):
        self.stop()

        if filepath_or_url.startswith("http"):
            self._play_uri(filepath_or_url)
        elif filepath_or_url.lower().endswith(".dff"):
            self._play_dff(filepath_or_url)
        elif filepath_or_url.lower().endswith(".dsf"):
            self._play_uri(f"file://{os.path.abspath(filepath_or_url)}", is_dsd=True)
        else:
            uri = "file://" + os.path.abspath(filepath_or_url)
            self._play_uri(uri)

        self._current = filepath_or_url
        if self._db and not filepath_or_url.startswith("http"):
            from sync.sync_protocol import make_track_id
            self._db.update_play_history(make_track_id(filepath_or_url))

    def _play_uri(self, uri: str, is_dsd: bool = False):
        self._is_dsd = is_dsd
        sink = self._build_sink()

        pipeline_str = f"playbin uri={uri} audio-sink=\"{sink}\""
        self._pipeline = Gst.parse_launch(pipeline_str)
        if not self._pipeline:
            self.error_occurred.emit("Failed to create pipeline")
            return

        self._setup_bus()
        self._setup_timer()
        self._setup_spectrum()

        self._pipeline.set_state(Gst.State.PLAYING)
        self._state = PlaybackState.PLAYING
        self.state_changed.emit(self._state)

    def _play_dff(self, filepath: str):
        self._is_dsd = True
        try:
            header = parse_dff(filepath)
        except Exception as e:
            self.error_occurred.emit(str(e))
            return

        if header.is_dst:
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
        self._pipeline = Gst.parse_launch(pipeline_str)
        if not self._pipeline:
            self.error_occurred.emit("Failed to create DFF pipeline")
            return

        self._appsrc = self._pipeline.get_by_name("dsdsrc")
        self._file_handle = open(filepath, "rb")

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
        appsrc = self._appsrc
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

    def set_volume(self, vol: int):
        pass  # Volume is now managed via GStreamer pipeline element

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

    def _build_sink(self) -> str:
        if self._eq.mode == "bypass" or self._is_dsd:
            base = (f"audioconvert ! audioresample ! "
                    f"alsasink device={self._dac.alsa_device_str}")
        elif self._eq.mode == "graphic":
            base = build_eq_graphic_sink(self._eq.bands_31, self._dac)
        elif self._eq.mode == "parametric":
            base = build_eq_parametric_sink(
                self._eq.bands_parametric, self._eq.preamp_db, self._dac)
        else:
            base = (f"audioconvert ! audioresample ! "
                    f"alsasink device={self._dac.alsa_device_str}")

        # ReplayGain
        if self._replaygain and not self._is_dsd:
            # Insert rganalysis+rgvolume before the sink
            base = (f"rganalysis ! rgvolume album-mode=0 "
                    f"fallback-gain=0 preamp-headroom=0 ! {base}")

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
            self._pipeline.set_state(Gst.State.NULL)
            self._state = PlaybackState.STOPPED
            self.state_changed.emit(self._state)
            self.finished.emit()
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

    def play_url(self, url: str, title: str = "", artist: str = ""):
        self.stop()
        self.play(url)

    def set_volume(self, vol: int):
        if self._pipeline:
            vol_elem = self._pipeline.get_by_name("volume")
            if vol_elem:
                vol_elem.set_property("volume", max(0, min(100, vol)) / 100.0)

    def _on_media_finished(self):
        if not self.play_next():
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
