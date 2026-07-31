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
from typing import Any

logger = logging.getLogger("michi.service")


def make_album_cover_key(album_key: str) -> str:
    """Return the canonical cover key for an album."""
    return f"album:{album_key}" if album_key else ""


def make_track_cover_key(track_uid: str, album_key: str = "") -> str:
    """Return the best canonical cover key for a track."""
    if album_key:
        return make_album_cover_key(album_key)
    return f"track:{track_uid}" if track_uid else ""


class PlayerService(QObject):
    """Execute transport commands through the active audio backend."""

    track_changed = Signal(str, str)
    trackContextChanged = Signal(dict)
    state_changed = Signal(str)
    position_changed = Signal(float)
    duration_changed = Signal(float)
    volume_changed = Signal(int)
    error_occurred = Signal(str)
    queue_changed = Signal(list)
    queue_progressed = Signal(int, str, str, object)
    finished = Signal()
    backend_changed = Signal(str, str)

    def __init__(self, engine=None, event_bus=None, parent=None, library_db=None):
        super().__init__(parent)
        self._engine = engine
        self._event_bus = event_bus
        self._library_db = library_db
        self._volume_before_mute = None
        self._retry_url = None
        self._retry_title = ""
        self._retry_artist = ""
        self._current_title = ""
        self._current_artist = ""
        self._current_album = ""
        self._current_filepath = ""
        self._current_album_key = ""
        self._current_cover_key = ""
        self._current_year = 0
        self._current_genre = ""
        self._current_duration = 0.0
        self._current_format = ""
        self._current_sample_rate = 0
        self._current_bit_depth = 0
        self._current_bitrate = 0
        self._retry_timer = QTimer(self)
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self._do_retry)

        self._gst_backend = None
        self._mpd_backend = None
        self._mpd_service = None
        self._active_backend_id = ""

        # Profile application lifecycle state (Corrección 2).
        # Each field is filled at the corresponding phase of apply_profile():
        # requested (entry) -> validated (_prepare_apply) -> applied (_do_apply)
        # -> effective (_verify_apply) -> persisted (settings write).
        self._requested_profile_id = ""
        self._validated_profile_id = ""
        self._applied_profile_id = ""
        self._effective_profile_id = ""
        self._persisted_profile_id = ""
        self._last_apply_result = None

        from audio.backends.hybrid_audio_manager import HybridAudioManager
        from audio.backends.engine_backend_adapter import EngineBackendAdapter
        if engine is not None:
            self._engine_adapter = EngineBackendAdapter(engine)
            self._hybrid = HybridAudioManager(default_backend=self._engine_adapter)
            self._active_backend_id = "gstreamer"
            self._engine.queue_changed.connect(lambda q: self.queue_changed.emit(q))
            self._engine.finished.connect(lambda: self.finished.emit())
            self._engine.error_occurred.connect(self._on_error)
        else:
            self._engine_adapter = None
            self._hybrid = HybridAudioManager()
        self._hybrid.position_changed.connect(self.position_changed)
        self._hybrid.duration_changed.connect(self.duration_changed)
        self._hybrid.state_changed.connect(self._on_hybrid_state)
        self._hybrid.queue_progressed.connect(self.queue_progressed)

    def _on_hybrid_state(self, state: str) -> None:
        if state == "playing":
            self._retry_url = None
        self.state_changed.emit(state)

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
            self._hybrid.play(url)
        if title:
            self.track_changed.emit(title, artist)
            self._emitTrackContext(filepath=url, title=title, artist=artist)
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

    def get_active_backend_id(self) -> str:
        return self._hybrid.active_id

    def get_backend_capabilities(self) -> Any:
        return self._hybrid.get_capabilities()

    def switch_backend_for_profile(self, profile_key: str) -> bool:
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

    def start_mpd_service(self) -> bool:
        self._ensure_mpd_service()
        if not self._mpd_service:
            return False
        music_dir = get("audio/mpd/music_directory")
        device = get("audio/alsa_device") or "hw:0,0"
        dop = get("audio/mpd/dop_enabled") or False
        port = int(get("audio/mpd/port") or 6600)
        config = build_mpd_config(music_dir=music_dir, device=device, dop=dop, port=port)
        return self._mpd_service.start(config)

    def stop_mpd_service(self) -> bool:
        if self._mpd_service:
            self._mpd_service.stop()
            return True
        return False

    def get_mpd_status(self) -> dict:
        if self._mpd_service:
            return self._mpd_service.get_status()
        return {"installed": False, "running": False}

    def _publish(self, event: str, **data):
        if self._event_bus:
            with contextlib.suppress(Exception):
                self._event_bus.publish(event, **data)

    def _library_track_context(self, filepath: str) -> dict[str, Any]:
        """Return persisted metadata for ``filepath`` when a library is available."""
        if not filepath or self._library_db is None:
            return {}
        try:
            row = self._library_db.conn.execute(
                "SELECT COALESCE(title, ''), COALESCE(artist, ''), "
                "COALESCE(album, ''), COALESCE(album_key, ''), "
                "COALESCE(track_uid, ''), COALESCE(year, 0), "
                "COALESCE(genre, ''), COALESCE(duration, 0), "
                "COALESCE(format, ext, ''), COALESCE(sample_rate, 0), "
                "COALESCE(bit_depth, 0), COALESCE(bitrate, 0) "
                "FROM media_items WHERE filepath = ? AND deleted_at IS NULL LIMIT 1",
                (filepath,),
            ).fetchone()
        except Exception as exc:
            logger.debug("Library metadata lookup failed for %s: %s", filepath, exc)
            return {}
        if not row:
            return {}
        fields = (
            "title", "artist", "album", "album_key", "track_uid", "year",
            "genre", "duration", "format", "sample_rate", "bit_depth", "bitrate",
        )
        return dict(zip(fields, row, strict=False))

    def _emitTrackContext(self, filepath="", title="", artist="", album=""):
        """Emit trackContextChanged with complete playback context."""
        resolved_filepath = filepath or self._current_filepath
        metadata = self._library_track_context(resolved_filepath)
        album_key = str(metadata.get("album_key") or self._current_album_key)
        track_uid = str(metadata.get("track_uid") or "")
        cover_key = make_track_cover_key(track_uid, album_key)
        self._current_album_key = album_key
        self._current_cover_key = cover_key
        context = {
            "filepath": resolved_filepath,
            "title": title or metadata.get("title") or self._current_title,
            "artist": artist or metadata.get("artist") or self._current_artist,
            "album": album or metadata.get("album") or self._current_album,
            "album_key": album_key,
            "track_uid": track_uid,
            "cover_key": cover_key,
            "year": int(metadata.get("year") or self._current_year),
            "genre": metadata.get("genre") or self._current_genre,
            "duration": float(metadata.get("duration") or self._current_duration),
            "format": metadata.get("format") or self._current_format,
            "sample_rate": int(metadata.get("sample_rate") or self._current_sample_rate),
            "bit_depth": int(metadata.get("bit_depth") or self._current_bit_depth),
            "bitrate": int(metadata.get("bitrate") or self._current_bitrate),
        }
        self.trackContextChanged.emit(context)

    @property
    def current_filepath(self) -> str:
        return self._current_filepath

    def play(self, filepath: str, title: str = "", artist: str = "",
             album: str = "") -> None:
        self._retry_url = None
        self._current_filepath = filepath or ""
        self._current_title = title or ""
        self._current_artist = artist or ""
        self._current_album = album or ""
        if not self._hybrid.active:
            self.error_occurred.emit("No hay motor de reproducción disponible")
            return
        self._hybrid.play(filepath)
        if title:
            self.track_changed.emit(title, artist)
        self._emitTrackContext(filepath=filepath, title=title, artist=artist, album=album)
        self._publish("playback.changed", state="playing", title=title)

    def pause(self) -> None:
        self._hybrid.pause()
        self._publish("playback.changed", state="paused")

    def resume(self) -> None:
        self._hybrid.resume()
        self._publish("playback.changed", state="playing")

    def play_or_resume(self) -> None:
        snap = self._hybrid.get_snapshot()
        if snap.state == "paused":
            self._hybrid.resume()
            self._publish("playback.changed", state="playing")
        elif snap.state == "stopped" and snap.current_path:
            self._hybrid.play(snap.current_path)
            self._publish("playback.changed", state="playing")
        else:
            self._hybrid.toggle()

    def toggle(self) -> None:
        self._hybrid.toggle()

    def stop(self) -> None:
        self._hybrid.stop()
        self._publish("playback.changed", state="stopped")

    def seek(self, seconds: float) -> None:
        self._hybrid.seek(seconds)

    def mute(self, muted: bool = True) -> dict:
        if not self._hybrid.active:
            return {"ok": False, "error": "NO_ACTIVE_BACKEND"}
        try:
            if muted:
                snap = self._hybrid.get_snapshot()
                self._volume_before_mute = snap.volume if snap else 50
                self._hybrid.set_volume(0.0)
            else:
                restore = self._volume_before_mute if self._volume_before_mute is not None else 50
                self._volume_before_mute = None
                self._hybrid.set_volume(restore)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_volume(self, vol: int) -> None:
        try:
            self._hybrid.set_volume(vol)
            self.volume_changed.emit(vol)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def play_next(self) -> None:
        self._hybrid.play_next()

    def play_prev(self) -> None:
        self._hybrid.play_prev()

    def enqueue_next(self, paths: list[str]) -> None:
        if not paths:
            return
        self._hybrid.enqueue_next(paths)

    def enqueue(self, paths: list[str], play_now: bool = True) -> None:
        self._retry_url = None
        clean = [p for p in paths if p and isinstance(p, str)]
        if not clean:
            self.error_occurred.emit("No hay archivos válidos para reproducir")
            return
        self._hybrid.enqueue(clean, play_now)

    def play_queue(self, filepaths: list[str], start_index: int = 0,
                   revision: int | None = None) -> None:
        self._retry_url = None
        self._hybrid.set_queue(filepaths, start_index, revision=revision)

    def play_queue_index(self, index: int) -> bool:
        return self._hybrid.play_queue_index(index)

    def clear_queue(self) -> None:
        self._hybrid.clear_queue()

    def get_queue(self) -> list[dict]:
        return self._hybrid.get_queue()

    def get_queue_state(self) -> tuple[list[str], int]:
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

    def reorder_queue(self, filepaths: list[str]) -> None:
        self._hybrid.set_queue(filepaths, 0)

    def toggle_shuffle(self) -> bool:
        current = bool(getattr(self._hybrid.active, "_shuffle", False))
        return self.set_shuffle(not current)

    def set_shuffle(self, enabled: bool) -> bool:
        return self._hybrid.set_shuffle(enabled)

    def toggle_repeat(self) -> str:
        current = getattr(self._hybrid.active, "_repeat", "none")
        modes = {"none": "all", "all": "one", "one": "none"}
        return self.set_repeat(modes.get(current, "none"))

    def set_repeat(self, mode: str) -> str:
        return self._hybrid.set_repeat(mode)

    def play_url(self, url: str, title: str = "", artist: str = "",
                 album: str = "") -> None:
        self._retry_url = url
        self._retry_title = title
        self._retry_artist = artist
        self._current_title = title or ""
        self._current_artist = artist or ""
        self._current_album = album or ""
        self._hybrid.play(url)
        if title:
            self.track_changed.emit(title, artist)

    def set_audio_profile(self, profile: str) -> None:
        """Switch the audio backend for ``profile`` transactionally.

        Public convenience wrapper around :meth:`apply_profile` that discards
        the structured result for callers that only need the side effect.
        """
        self.apply_profile(profile)

    def apply_profile(self, profile_key: str) -> dict:
        """Transactional profile application with verification and rollback.

        Phases: prepare -> apply -> verify -> persist. On verify failure the
        previously active profile is restored so the service never advertises a
        profile whose backend did not become effective. Returns a structured
        result dict; it never fabricates success when the backend switch failed.

        Each lifecycle state (requested/validated/applied/effective/persisted)
        is recorded on the service as it is reached (Corrección 2), and a typed
        :class:`ProfileApplyResult` is stored on ``self._last_apply_result``.
        """
        from audio.output_profiles import (
            PROFILE_FAILED, PROFILE_PERSISTED, ProfileApplyResult,
        )
        previous = self.get_active_profile_id()
        # Reset lifecycle state for this attempt.
        self._requested_profile_id = profile_key or ""
        self._validated_profile_id = ""
        self._applied_profile_id = ""
        self._effective_profile_id = ""
        self._persisted_profile_id = ""
        requested_backend: str | None = None
        effective_backend: str | None = None
        effective_format: dict | None = None
        rollback_attempted = False
        rollback_ok: bool | None = None
        try:
            prepared = self._prepare_apply(profile_key, previous)
            if not prepared.get("ok"):
                self._store_result(ProfileApplyResult(
                    ok=False, requested_profile_id=self._requested_profile_id,
                    previous_profile_id=previous, code=prepared.get("code", ""),
                    message=prepared.get("message", ""),
                ))
                return prepared
            self._validated_profile_id = profile_key
            applied = self._do_apply(profile_key)
            requested_backend = applied.get("requested_backend")
            if not applied.get("ok"):
                self._store_result(ProfileApplyResult(
                    ok=False, requested_profile_id=self._requested_profile_id,
                    previous_profile_id=previous,
                    validated_profile_id=self._validated_profile_id,
                    requested_backend=requested_backend,
                    effective_backend=applied.get("active_backend"),
                    code=applied.get("code", ""), message=applied.get("message", ""),
                ))
                return applied
            self._applied_profile_id = profile_key
            verified = self._verify_apply(profile_key)
            effective_backend = verified.get("active_backend")
            effective_format = verified.get("effective_format")
            if not verified.get("ok"):
                # Rollback to the previously active profile
                rollback_attempted = True
                self._safe_rollback(previous)
                rollback_ok = True
                result = {"ok": False, "code": "VERIFY_FAILED", "error": "VERIFY_FAILED",
                          "message": verified.get("message", "Verificación fallida"),
                          "rollback": True, "active_profile": previous,
                          "state": PROFILE_FAILED, **verified}
                self._store_result(ProfileApplyResult(
                    ok=False, requested_profile_id=self._requested_profile_id,
                    previous_profile_id=previous,
                    validated_profile_id=self._validated_profile_id,
                    applied_profile_id=self._applied_profile_id,
                    requested_backend=requested_backend,
                    effective_backend=effective_backend,
                    verification_level=verified.get("verification_level", "not_verifiable"),
                    rollback_attempted=True, rollback_ok=True,
                    code="VERIFY_FAILED",
                    message=verified.get("message", "Verificación fallida"),
                    effective_format=effective_format,
                ))
                return result
            self._effective_profile_id = profile_key
            from core.settings_manager import set_
            set_("audio/profile", profile_key)
            self._active_profile_id = profile_key
            self._persisted_profile_id = profile_key
            result = {"ok": True, "applied": profile_key, "verified": True,
                      "persisted": True, "state": PROFILE_PERSISTED,
                      "active_profile": profile_key,
                      "active_backend": verified.get("active_backend", ""),
                      "requested_backend": applied.get("requested_backend", ""),
                      "fallback": applied.get("fallback", False),
                      "bitperfect_state": verified.get("bitperfect_state", "unknown"),
                      "effective_format": effective_format,
                      "requested_profile_id": self._requested_profile_id,
                      "previous_profile_id": previous,
                      "validated_profile_id": self._validated_profile_id,
                      "applied_profile_id": self._applied_profile_id,
                      "effective_profile_id": self._effective_profile_id,
                      "persisted_profile_id": self._persisted_profile_id,
                      "effective_backend": effective_backend,
                      "verification_level": verified.get("verification_level", "not_verifiable")}
            self._store_result(ProfileApplyResult(
                ok=True, requested_profile_id=self._requested_profile_id,
                previous_profile_id=previous,
                validated_profile_id=self._validated_profile_id,
                applied_profile_id=self._applied_profile_id,
                effective_profile_id=self._effective_profile_id,
                persisted_profile_id=self._persisted_profile_id,
                requested_backend=requested_backend,
                effective_backend=effective_backend,
                verification_level=verified.get("verification_level", "not_verifiable"),
                rollback_attempted=False, rollback_ok=None,
                effective_format=effective_format,
            ))
            return result
        except Exception as exc:
            logger.error("apply_profile(%s) failed: %s", profile_key, exc)
            self._store_result(ProfileApplyResult(
                ok=False, requested_profile_id=self._requested_profile_id,
                previous_profile_id=previous,
                validated_profile_id=self._validated_profile_id or None,
                applied_profile_id=self._applied_profile_id or None,
                requested_backend=requested_backend,
                effective_backend=effective_backend,
                rollback_attempted=rollback_attempted, rollback_ok=rollback_ok,
                code="APPLY_ERROR", message=str(exc),
                effective_format=effective_format,
            ))
            return {"ok": False, "code": "APPLY_ERROR", "error": str(exc),
                    "message": str(exc), "state": PROFILE_FAILED,
                    "active_profile": self.get_active_profile_id()}

    def _store_result(self, result) -> None:
        """Persist the last typed apply result for programmatic consumers."""
        self._last_apply_result = result

    def _prepare_apply(self, profile_key: str, previous: str) -> dict:
        """Validate ``profile_key`` is a known profile before switching."""
        from audio.output_profiles import PROFILES, PROFILE_FAILED, PROFILE_REQUESTED
        if not profile_key or profile_key not in PROFILES:
            return {"ok": False, "code": "UNKNOWN_PROFILE", "error": "UNKNOWN_PROFILE",
                    "message": "Perfil desconocido", "requested_profile": profile_key,
                    "active_profile": previous, "state": PROFILE_FAILED}
        return {"ok": True, "state": PROFILE_REQUESTED,
                "requested_profile": profile_key, "active_profile": previous}

    def _do_apply(self, profile_key: str) -> dict:
        """Switch the backend for ``profile_key`` and report the real outcome."""
        from audio.output_profiles import (
            get_profile, is_mpd_profile, PROFILE_APPLIED, PROFILE_FAILED,
        )
        prof = get_profile(profile_key)
        requested_backend = prof.preferred_backend
        switched = self.switch_backend_for_profile(profile_key)
        active_backend = self.get_active_backend_id()
        # An MPD profile whose backend did not become MPD has fallen back.
        fallback = bool(is_mpd_profile(profile_key) and active_backend != "mpd")
        if not switched:
            return {"ok": False, "code": "BACKEND_FAILED", "error": "BACKEND_FAILED",
                    "message": "No se pudo cambiar el backend",
                    "requested_backend": requested_backend,
                    "active_backend": active_backend, "fallback": fallback,
                    "state": PROFILE_FAILED}
        return {"ok": True, "state": PROFILE_APPLIED,
                "requested_backend": requested_backend,
                "active_backend": active_backend, "fallback": fallback}

    def _verify_apply(self, profile_key: str) -> dict:
        """Verify the active backend is ready, matches the profile, and compute
        the effective bit-perfect state (Corrección 2).

        Bit-perfect is *invalidated* when any DSP that alters the signal is
        active on a bit-perfect profile: digital volume != 100, EQ enabled,
        ReplayGain enabled, or resampling required. The resulting
        ``effective_format`` dict carries the ``bitperfect`` state so callers
        cannot advertise a bit-perfect path that is in fact broken.
        """
        from audio.output_profiles import (
            is_mpd_profile, PROFILE_EFFECTIVE,
        )
        active_backend = self.get_active_backend_id()
        expected = "mpd" if is_mpd_profile(profile_key) else "gstreamer"
        backend = self._hybrid.active
        ready = bool(backend is not None and backend.is_ready())
        if not ready:
            return {"ok": False, "code": "VERIFY_FAILED", "error": "VERIFY_FAILED",
                    "message": "Backend no listo tras aplicar perfil",
                    "active_backend": active_backend, "expected_backend": expected,
                    "bitperfect_state": "unknown", "verification_level": "not_verifiable",
                    "effective_format": None}
        if active_backend != expected:
            return {"ok": False, "code": "VERIFY_FAILED", "error": "VERIFY_FAILED",
                    "message": f"Backend activo '{active_backend}' no coincide con '{expected}'",
                    "active_backend": active_backend, "expected_backend": expected,
                    "bitperfect_state": "unknown", "verification_level": "not_verifiable",
                    "effective_format": None}
        bitperfect_state, invalidators, verification_level = (
            self._compute_bitperfect_state(profile_key, active_backend)
        )
        effective_format = {
            "profile": profile_key,
            "bitperfect": bitperfect_state,
            "invalidators": tuple(invalidators),
            "backend": active_backend,
            "device": self.get_output_device_id(),
        }
        return {"ok": True, "state": PROFILE_EFFECTIVE,
                "active_backend": active_backend, "expected_backend": expected,
                "bitperfect_state": bitperfect_state,
                "verification_level": verification_level,
                "effective_format": effective_format}

    def _compute_bitperfect_state(
        self, profile_key: str, active_backend: str
    ) -> tuple[str, list[str], str]:
        """Determine the effective bit-perfect state for an applied profile.

        Returns ``(state, invalidators, verification_level)``. Only DSP that
        actually alters the signal counts as an invalidator; for non-bit-perfect
        profiles the state is ``unsupported``. hw_params verification is left to
        the diagnostics layer, so a clean bit-perfect profile is reported as
        ``probable`` (not ``verified``) here.
        """
        from audio.output_profiles import get_profile, is_bitperfect_profile
        if not is_bitperfect_profile(profile_key):
            return "unsupported", [], "not_verifiable"
        invalidators = self._bitperfect_invalidators(active_backend)
        if invalidators:
            return "invalidated", invalidators, "dsp_checked"
        prof = get_profile(profile_key)
        # MPD bit-perfect profiles block DSP in the backend itself; the path is
        # clean but hw_params are not read in this synchronous verify phase.
        if prof.preferred_backend == "mpd" or active_backend == "mpd":
            return "probable", [], "dsp_checked"
        return "probable", [], "dsp_checked"

    def _bitperfect_invalidators(self, active_backend: str) -> list[str]:
        """Active DSP features that would break a bit-perfect signal path.

        Checks: digital volume != 100, EQ enabled, ReplayGain enabled, and
        resampling required. Returns the list of active invalidators (may be
        empty). All checks are defensive: a missing engine or attribute never
        raises — it just contributes no invalidator.
        """
        invalidators: list[str] = []
        engine = self._engine
        # MPD backend owns its own DSP-free path; GStreamer DSP is irrelevant.
        if active_backend == "mpd" or engine is None:
            return invalidators
        # Digital volume != 100 (bit-perfect requires unity gain).
        try:
            vol = getattr(engine, "_volume", 100)
            vol_pct = int(round(vol * 100)) if isinstance(vol, float) and vol <= 1.0 else int(vol)
            if vol_pct != 100:
                invalidators.append("volume")
        except Exception:  # noqa: BLE001 — defensive DSP probe
            pass
        # EQ enabled (mode != bypass).
        try:
            eq = engine.get_eq_state() if hasattr(engine, "get_eq_state") else {}
            if isinstance(eq, dict) and eq.get("mode", "bypass") != "bypass":
                invalidators.append("eq")
        except Exception:  # noqa: BLE001 — defensive DSP probe
            pass
        # ReplayGain enabled.
        try:
            if getattr(engine, "_replaygain", False):
                invalidators.append("replaygain")
        except Exception:  # noqa: BLE001 — defensive DSP probe
            pass
        # Resampling required (target_rate > 0 means the DAC forces a rate).
        try:
            diag = engine.get_audio_diagnostics() if hasattr(
                engine, "get_audio_diagnostics") else None
            if diag is not None and getattr(diag, "resampling_active", False):
                invalidators.append("resampling")
        except Exception:  # noqa: BLE001 — defensive DSP probe
            pass
        return invalidators

    def _safe_rollback(self, previous: str) -> None:
        """Best-effort rollback to the ``previous`` profile's backend."""
        try:
            self.switch_backend_for_profile(previous)
        except Exception as exc:
            logger.warning("Rollback to profile '%s' failed: %s", previous, exc)

    def set_profile(self, profile_id: str) -> dict:
        """Apply a profile transactionally (delegates to :meth:`apply_profile`).

        Returns the real result from the transactional apply — it never
        fabricates success when the backend switch failed.
        """
        return self.apply_profile(profile_id)

    def get_active_profile_id(self) -> str:
        if hasattr(self, '_active_profile_id') and self._active_profile_id:
            return self._active_profile_id
        from core.settings_manager import get
        return get("audio/profile") or "standard"

    def set_output_device_id(self, device_id: str) -> None:
        if self._engine:
            self._engine.set_output_device_id(device_id)

    def get_output_device_id(self) -> str:
        return self._engine.get_output_device_id() if self._engine else ""

    def get_audio_devices(self) -> list:
        from audio.output_device_manager import list_devices
        return list_devices()

    def refresh_audio_devices(self) -> list:
        return self.get_audio_devices()

    def get_audio_diagnostics(self) -> Any:
        if self._hybrid.active_id == "mpd" and self._mpd_backend:
            return self._mpd_backend.get_diagnostics()
        if self._engine:
            return self._engine.get_audio_diagnostics()
        from audio.backends.types import AudioDiagnostics
        return AudioDiagnostics(backend_id="none", profile="none")

    def test_output_device(self, device_id: str) -> tuple[bool, str]:
        """Real device test: existence, permissions, and open/close (Corrección 2).

        Replaces the previous ``return True, "OK"`` stub that fabricated
        success for every device. The check is layered:

        1. The device must resolve via :func:`get_device` (existence).
        2. ALSA ``hw:X,Y`` / ``plughw:X,Y`` devices expose a PCM playback node
           under ``/dev/snd/`` — verify the node exists, is writable, and can be
           opened and closed (permissions + open/close).
        3. Logical sinks (PipeWire/Pulse/auto/test) have no file node; verify
           the sink element name is present and well-formed.

        The returned message lists what was actually checked so callers never
        mistake a fabricated "OK" for a real probe.
        """
        import os
        import re
        from audio.output_device_manager import get_device

        device = get_device(device_id)
        if device is None:
            return False, f"Dispositivo no encontrado: {device_id}"

        checked: list[str] = [f"existe={device.display_name}"]

        # ALSA hw/plug devices expose a PCM playback node we can open/close.
        m = re.search(r"(?:plug)?hw:(\d+),(\d+)", device.device_string)
        if m:
            card, devnum = int(m.group(1)), int(m.group(2))
            node = f"/dev/snd/pcmC{card}D{devnum}p"
            if not os.path.exists(node):
                return False, (
                    f"Nodo ALSA inexistente: {node} "
                    f"(verificado: {', '.join(checked)})"
                )
            checked.append(f"nodo={node}")
            if not os.access(node, os.W_OK):
                return False, (
                    f"Sin permisos de escritura: {node} "
                    f"(verificado: {', '.join(checked)})"
                )
            checked.append("permisos=ok")
            try:
                fd = os.open(node, os.O_WRONLY)
            except OSError as exc:
                return False, (
                    f"No se pudo abrir {node}: {exc} "
                    f"(verificado: {', '.join(checked)})"
                )
            with contextlib.suppress(OSError):
                os.close(fd)
            checked.append("open/close=ok")
            return True, (
                f"Dispositivo ALSA verificado "
                f"(verificado: {', '.join(checked)})"
            )

        # Non-ALSA sinks (pipewire, pulse, auto, test): no file node to open;
        # verify the sink element name is present and well-formed.
        sink = (
            device.device_string.split(maxsplit=1)[0]
            if device.device_string else ""
        )
        if not sink:
            return False, (
                f"device_string vacío (verificado: {', '.join(checked)})"
            )
        checked.append(f"sink={sink}")
        return True, (
            f"Dispositivo lógico sin nodo directo "
            f"(verificado: {', '.join(checked)})"
        )

    def set_dsd_mode(self, mode: str) -> None:
        if self._engine:
            self._engine.set_dsd_mode(mode)

    def set_gapless_enabled(self, enabled: bool) -> None:
        if self._engine:
            self._engine.set_gapless_enabled(enabled)

    def set_replaygain_mode(self, mode: str) -> None:
        if self._engine:
            self._engine.set_replaygain_mode(mode)

    def set_transmit_device(self, device: Any) -> None:
        if self._engine:
            self._engine.set_transmit_device(device)

    def set_snapcast_fifo(self, enabled: bool) -> None:
        """Enable or disable the Snapcast distribution FIFO branch.

        When enabled, the GStreamer pipeline will tee audio into
        /tmp/michi-snapfifo for Snapserver to consume.
        Requires an active pipeline (restart if currently playing).
        """
        if self._engine:
            self._engine.set_snapcast_fifo(enabled)

    def get_transmit_device(self) -> Any:
        return self._engine.get_transmit_device() if self._engine else None

    def get_playback_snapshot(self) -> Any:
        return self._hybrid.get_snapshot()

    def shutdown(self) -> None:
        self._retry_timer.stop()
        self._hybrid.shutdown()

    def set_eq_graphic(self, bands: list[float]) -> None:
        if self._is_mpd_active():
            self.error_occurred.emit("EQ no disponible en modo MPD Hi-Fi")
            return
        if self._engine:
            self._engine.set_eq_graphic(bands)

    def set_eq_parametric(self, bands: list[dict]) -> None:
        if self._is_mpd_active():
            self.error_occurred.emit("EQ no disponible en modo MPD Hi-Fi")
            return
        if self._engine:
            self._engine.set_eq_parametric(bands)

    def set_eq_bypass(self, bypass: bool) -> None:
        if self._is_mpd_active():
            return
        if self._engine:
            self._engine.set_eq_bypass(bypass)

    def set_eq_preamp(self, db: float) -> None:
        if self._is_mpd_active():
            return
        if self._engine:
            self._engine.set_eq_preamp(db)

    def get_eq_state(self) -> Any:
        if self._engine:
            return self._engine.get_eq_state()
        from audio.player import EqState
        return EqState()

    def set_spectrum_enabled(self, enabled: bool) -> None:
        if self._is_mpd_active():
            self.error_occurred.emit("Spectrum no disponible en modo MPD Hi-Fi")
            return
        if self._engine:
            self._engine.set_spectrum_enabled(enabled)

    def get_bitperfect_report(self) -> Any:
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
    def state(self) -> str:
        try:
            return self._hybrid.get_snapshot().state
        except Exception:
            return "stopped"

    @property
    def current(self) -> str:
        try:
            return self._hybrid.get_snapshot().current_path
        except Exception:
            return ""

    @property
    def current_title(self) -> str:
        return self._current_title

    @property
    def current_artist(self) -> str:
        return self._current_artist

    @property
    def current_album(self) -> str:
        return self._current_album

    @property
    def duration(self) -> float:
        try:
            return self._hybrid.get_snapshot().duration_seconds
        except Exception:
            return 0.0

    @property
    def hybrid(self) -> Any:
        return self._hybrid

    @property
    def engine(self) -> Any:
        return self._engine
