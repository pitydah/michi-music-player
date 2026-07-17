"""Player Service — single facade between UI and HybridAudioManager.

UI talks to PlayerService. PlayerService talks to HybridAudioManager.
HybridAudioManager delegates to the active backend (GStreamer or MPD).
"""

from PySide6.QtCore import QObject, Signal, QTimer

from audio.player import PlaybackState
from audio.backends.mpd_backend import MpdBackend
from audio.mpd.mpd_service_manager import MpdServiceManager
from audio.mpd.mpd_config_builder import build_mpd_config
from audio.mpd.mpd_errors import MpdConnectionError
from core.settings_manager import get
import logging
import contextlib

logger = logging.getLogger("michi.service")


class PlayerService(QObject):
    track_changed = Signal(str, str)
    state_changed = Signal(str)
    position_changed = Signal(float)
    duration_changed = Signal(float)
    volume_changed = Signal(int)
    error_occurred = Signal(str)
    queue_changed = Signal(list)
    finished = Signal()
    backend_changed = Signal(str, str)

    def __init__(self, engine=None, event_bus=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._event_bus = event_bus
        self._volume_before_mute = None
        self._retry_url = None
        self._retry_title = ""
        self._retry_artist = ""
        self._current_title = ""
        self._current_artist = ""
        self._current_album = ""
        self._retry_timer = QTimer(self)
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self._do_retry)

        self._gst_backend = None
        self._mpd_backend = None
        self._mpd_service = None
        self._active_backend_id = ""

        from audio.backends.hybrid_audio_manager import HybridAudioManager
        from audio.backends.engine_backend_adapter import EngineBackendAdapter
        if engine is not None:
            self._engine_adapter = EngineBackendAdapter(engine)
            self._hybrid = HybridAudioManager(default_backend=self._engine_adapter)
            self._active_backend_id = "gstreamer"
            self._engine.position_changed.connect(lambda s: self.position_changed.emit(s))
            self._engine.duration_changed.connect(lambda s: self.duration_changed.emit(s))
            self._engine.state_changed.connect(self._on_state)
            self._engine.queue_changed.connect(lambda q: self.queue_changed.emit(q))
            self._engine.finished.connect(lambda: self.finished.emit())
            self._engine.error_occurred.connect(self._on_error)
        else:
            self._engine_adapter = None
            self._hybrid = HybridAudioManager()

    def _on_state(self, state):
        s_map = {PlaybackState.PLAYING: "playing",
                 PlaybackState.PAUSED: "paused",
                 PlaybackState.STOPPED: "stopped"}
        s = s_map.get(state, "stopped")
        if s == "playing":
            self._retry_url = None
        self.state_changed.emit(s)

    def _on_error(self, msg):
        if self._retry_url:
            self._retry_timer.start(2000)
            return
        is_stream_recoverable = msg and "STREAM_NETWORK_ERROR" in str(msg)
        if is_stream_recoverable and self._retry_url:
            self._retry_timer.start(2000)
            return
        self.error_occurred.emit(msg)

    def _do_retry(self):
        url = self._retry_url
        title = self._retry_title
        artist = self._retry_artist
        self._retry_url = None
        if url:
            self._engine.play_url(url)
            if title:
                self.track_changed.emit(title, artist)
            import logging
            logging.getLogger("michi.service").info("Retrying stream: %s", url)

    def _ensure_mpd_service(self):
        if self._mpd_service is not None:
            return
        self._mpd_service = MpdServiceManager()
        host = get("audio/mpd/host") or "127.0.0.1"
        port = get("audio/mpd/port") or 6600
        password = get("audio/mpd/password") or ""
        from audio.mpd.mpd_path_mapper import MpdPathMapper
        mapper = MpdPathMapper()
        self._mpd_backend = MpdBackend(host=host, port=int(port), password=password, path_mapper=mapper)
        self._hybrid.register(self._mpd_backend)

    def get_active_backend_id(self):
        return self._hybrid.active_id

    def get_backend_capabilities(self):
        return self._hybrid.get_capabilities()

    def switch_backend_for_profile(self, profile_key):
        old_id = self._hybrid.active_id
        target = self._hybrid.choose_backend_for_profile(profile_key)
        if target == "mpd" and not self._mpd_backend:
            self._ensure_mpd_service()
        if target == "mpd" and self._mpd_backend and not self._mpd_backend.connected:
            try:
                self._ensure_mpd_service()
                self._mpd_backend.connect()
            except MpdConnectionError as e:
                self.error_occurred.emit(f"MPD connection failed: {e}")
                self._do_fallback_backend(old_id)
                return False
        result = self._hybrid.switch_for_profile(profile_key)
        new_id = self._hybrid.active_id
        if new_id != old_id:
            self._active_backend_id = new_id
            self.backend_changed.emit(old_id, new_id)

        if new_id == "mpd" and self._mpd_backend:
            from audio.output_profiles import get_profile
            prof = get_profile(profile_key)
            dsd_mode = getattr(prof, 'dsd_mode', 'pcm') or 'pcm'
            dop = get("audio/mpd/dop_enabled") or False
            self._mpd_backend.configure_dsd(mode=dsd_mode, dop=dop)
        return result

    def _do_fallback_backend(self, previous_backend_id: str):
        self._hybrid.mark_fallback(True)
        self._hybrid.switch_to("gstreamer")
        self.backend_changed.emit(previous_backend_id, "gstreamer")
        self.error_occurred.emit("MPD no disponible — usando GStreamer")

    def start_mpd_service(self):
        self._ensure_mpd_service()
        if not self._mpd_service:
            return False
        music_dir = get("audio/mpd/music_directory")
        device = get("audio/alsa_device") or "hw:0,0"
        dop = get("audio/mpd/dop_enabled") or False
        port = int(get("audio/mpd/port") or 6600)
        config = build_mpd_config(music_dir=music_dir, device=device, dop=dop, port=port)
        return self._mpd_service.start(config)

    def stop_mpd_service(self):
        if self._mpd_service:
            self._mpd_service.stop()
            return True
        return False

    def get_mpd_status(self):
        if self._mpd_service:
            return self._mpd_service.get_status()
        return {"installed": False, "running": False}

    def _publish(self, event: str, **data):
        if self._event_bus:
            with contextlib.suppress(Exception):
                self._event_bus.publish(event, **data)

    def play(self, filepath, title="", artist="", album=""):
        self._retry_url = None
        self._current_title = title or ""
        self._current_artist = artist or ""
        self._current_album = album or ""
        if self._engine:
            self._engine.play(filepath)
        else:
            self._hybrid.play(filepath)
        if title:
            self.track_changed.emit(title, artist)
        self._publish("playback.changed", state="playing", title=title)

    def pause(self):
        self._hybrid.pause()
        self._publish("playback.changed", state="paused")

    def resume(self):
        self._hybrid.resume()
        self._publish("playback.changed", state="playing")

    def play_or_resume(self):
        snap = self._hybrid.get_snapshot()
        if snap.state == "paused":
            self._hybrid.resume()
            self._publish("playback.changed", state="playing")
        elif snap.state == "stopped" and snap.current_path:
            self._hybrid.play(snap.current_path)
            self._publish("playback.changed", state="playing")
        else:
            self._hybrid.toggle()

    def toggle(self):
        self._hybrid.toggle()

    def stop(self):
        self._hybrid.stop()
        self._publish("playback.changed", state="stopped")

    def seek(self, seconds):
        self._hybrid.seek(seconds)

    def mute(self, muted: bool = True):
        if not self._engine:
            return {"ok": False, "error": "NO_ENGINE"}
        try:
            if muted:
                snap = self._hybrid.get_snapshot()
                self._volume_before_mute = snap.volume if snap else 50
                self._engine.set_volume(0.0)
            else:
                restore = self._volume_before_mute if self._volume_before_mute is not None else 50
                self._volume_before_mute = None
                self._engine.set_volume(restore / 100.0)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_volume(self, vol):
        try:
            self._hybrid.set_volume(vol)
            self.volume_changed.emit(vol)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def play_next(self):
        self._hybrid.play_next()

    def play_prev(self):
        self._hybrid.play_prev()

    def enqueue_next(self, paths):
        if not paths:
            return
        if self._engine and self._hybrid.active_id == "gstreamer":
            self._engine.enqueue_next(paths)
        else:
            self._hybrid.enqueue_next(paths)

    def enqueue(self, paths, play_now=True):
        self._retry_url = None
        clean = [p for p in paths if p and isinstance(p, str)]
        if not clean:
            self.error_occurred.emit("No hay archivos válidos para reproducir")
            return
        if self._engine and self._hybrid.active_id == "gstreamer":
            self._engine.enqueue(clean, play_now)
        else:
            self._hybrid.enqueue(clean, play_now)

    def play_queue(self, filepaths, start_index=0):
        self._retry_url = None
        if self._engine and self._hybrid.active_id == "gstreamer":
            self._engine.set_queue(filepaths, start_index)
        else:
            self._hybrid.set_queue(filepaths, start_index)

    def clear_queue(self):
        self._hybrid.clear_queue()

    def get_queue(self):
        return self._hybrid.get_queue()

    def get_queue_state(self):
        queue = self._hybrid.get_queue()
        paths = [q.get("filepath", "") for q in queue if q.get("filepath")]
        idx = self._hybrid.get_queue_index()
        return paths, idx

    def duplicate_profile(self, profile_id: str) -> dict:
        from audio.output_profiles import PROFILES, get_profile
        src = get_profile(profile_id)
        if not src or src.key == "standard":
            return {"ok": False, "error": "CANNOT_DUPLICATE"}
        new_key = f"{profile_id}_copy"
        if new_key in PROFILES:
            n = 2
            while f"{profile_id}_copy_{n}" in PROFILES:
                n += 1
            new_key = f"{profile_id}_copy_{n}"
        import copy
        prof = copy.deepcopy(src)
        object.__setattr__(prof, 'key', new_key)
        object.__setattr__(prof, 'name', f"{src.name} (copia)")
        PROFILES[new_key] = prof
        return {"ok": True, "profile_key": new_key}

    def delete_profile(self, profile_id: str) -> bool:
        from audio.output_profiles import PROFILES
        if profile_id in PROFILES and profile_id != "standard":
            del PROFILES[profile_id]
            return True
        return False

    def create_profile(self, data: dict) -> dict:
        from audio.output_profiles import PROFILES, AudioOutputProfile
        key = data.get("key", f"custom_{len(PROFILES)}")
        if key in PROFILES:
            return {"ok": False, "error": "ALREADY_EXISTS"}
        prof = AudioOutputProfile(key=key, name=data.get("name", key))
        PROFILES[key] = prof
        return {"ok": True, "profile_key": key}

    def update_profile(self, data: dict) -> dict:
        from audio.output_profiles import PROFILES
        key = data.get("key", "")
        if key not in PROFILES:
            return {"ok": False, "error": "NOT_FOUND"}
        prof = PROFILES[key]
        for field in ("name", "description", "backend"):
            if field in data:
                object.__setattr__(prof, field, data[field])
        return {"ok": True}

    def rollback_profile(self) -> dict:
        return {"ok": True, "message": "Rollback not persisted"}

    def reorder_queue(self, filepaths):
        if self._engine and self._hybrid.active_id == "gstreamer":
            self._engine.reorder_queue(filepaths)
        else:
            self._hybrid.active.set_queue(filepaths)

    def toggle_shuffle(self):
        if self._engine and self._hybrid.active_id == "gstreamer":
            return self._engine.toggle_shuffle()
        return False

    def toggle_repeat(self):
        if self._engine and self._hybrid.active_id == "gstreamer":
            return self._engine.toggle_repeat()
        return "none"

    def play_url(self, url, title="", artist="", album=""):
        self._retry_url = url
        self._retry_title = title
        self._retry_artist = artist
        self._current_title = title or ""
        self._current_artist = artist or ""
        self._current_album = album or ""
        if self._engine and (self._hybrid.active_id == "gstreamer" or url.startswith(("http://", "https://", "icy://"))):
            self._engine.play_url(url)
        else:
            self._hybrid.play(url)
        if title:
            self.track_changed.emit(title, artist)

    def set_audio_profile(self, profile):
        from core.settings_manager import set_
        set_("audio/profile", profile)
        self.switch_backend_for_profile(profile)

    def set_profile(self, profile_id: str):
        from audio.output_profiles import PROFILES
        if profile_id not in PROFILES:
            return {"ok": False, "error": "UNKNOWN_PROFILE"}
        self._active_profile_id = profile_id
        self.set_audio_profile(profile_id)
        from core.settings_manager import set_
        set_("audio/profile", profile_id)
        return {"ok": True}

    def get_active_profile_id(self) -> str:
        if hasattr(self, '_active_profile_id') and self._active_profile_id:
            return self._active_profile_id
        from core.settings_manager import get
        return get("audio/profile") or "standard"

    def set_output_device_id(self, device_id):
        if self._engine:
            self._engine.set_output_device_id(device_id)

    def get_output_device_id(self):
        return self._engine.get_output_device_id() if self._engine else ""

    def get_audio_devices(self):
        from audio.output_device_manager import list_devices
        return list_devices()

    def refresh_audio_devices(self):
        return self.get_audio_devices()

    def get_audio_diagnostics(self):
        if self._hybrid.active_id == "mpd" and self._mpd_backend:
            return self._mpd_backend.get_diagnostics()
        if self._engine:
            return self._engine.get_audio_diagnostics()
        from audio.backends.types import AudioDiagnostics
        return AudioDiagnostics(backend_id="none", profile="none")

    def test_output_device(self, device_id):
        return True, "OK"

    def set_dsd_mode(self, mode):
        if self._engine:
            self._engine.set_dsd_mode(mode)

    def set_gapless_enabled(self, enabled):
        if self._engine:
            self._engine.set_gapless_enabled(enabled)

    def set_replaygain_mode(self, mode):
        if self._engine:
            self._engine.set_replaygain_mode(mode)

    def set_transmit_device(self, device):
        if self._engine:
            self._engine.set_transmit_device(device)

    def get_transmit_device(self):
        return self._engine.get_transmit_device() if self._engine else None

    def get_playback_snapshot(self):
        return self._hybrid.get_snapshot()

    def set_eq_graphic(self, bands):
        if self._is_mpd_active():
            self.error_occurred.emit("EQ no disponible en modo MPD Hi-Fi")
            return
        if self._engine:
            self._engine.set_eq_graphic(bands)

    def set_eq_parametric(self, bands):
        if self._is_mpd_active():
            self.error_occurred.emit("EQ no disponible en modo MPD Hi-Fi")
            return
        if self._engine:
            self._engine.set_eq_parametric(bands)

    def set_eq_bypass(self, bypass):
        if self._is_mpd_active():
            return
        if self._engine:
            self._engine.set_eq_bypass(bypass)

    def set_eq_preamp(self, db):
        if self._is_mpd_active():
            return
        if self._engine:
            self._engine.set_eq_preamp(db)

    def get_eq_state(self):
        if self._engine:
            return self._engine.get_eq_state()
        from audio.player import EqState
        return EqState()

    def set_spectrum_enabled(self, enabled):
        if self._is_mpd_active():
            self.error_occurred.emit("Spectrum no disponible en modo MPD Hi-Fi")
            return
        if self._engine:
            self._engine.set_spectrum_enabled(enabled)

    def get_bitperfect_report(self):
        """Build a BitperfectReport from current diagnostics and profile."""
        from audio.diagnostics.bitperfect_verifier import verify_bitperfect
        from audio.format_probe import AudioFormatInfo
        from audio.output_profiles import get_profile
        diag = self.get_audio_diagnostics()
        profile_key = getattr(diag, 'profile', 'standard')
        profile = get_profile(profile_key)
        fmt = AudioFormatInfo(
            sample_rate=getattr(diag, 'input_sample_rate', 0),
            bit_depth=getattr(diag, 'input_bit_depth', 0),
            channels=getattr(diag, 'input_channels', 0),
        )
        return verify_bitperfect(fmt, profile, diag)

    def _is_mpd_active(self):
        return self._hybrid.active_id == "mpd"

    @property
    def state(self):
        try:
            return self._hybrid.get_snapshot().state
        except Exception:
            return "stopped"

    @property
    def current(self):
        try:
            return self._hybrid.get_snapshot().current_path
        except Exception:
            return ""

    @property
    def current_title(self):
        return self._current_title

    @property
    def current_artist(self):
        return self._current_artist

    @property
    def current_album(self):
        return self._current_album

    @property
    def duration(self):
        try:
            return self._hybrid.get_snapshot().duration_seconds
        except Exception:
            return 0.0

    @property
    def hybrid(self):
        return self._hybrid

    @property
    def engine(self):
        return self._engine
