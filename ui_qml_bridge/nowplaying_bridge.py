"""NowPlayingBridge — QML-facing playback state backed by PlayerService.

All commands return dict with structured errors.
State is only updated after backend confirmation.
"""
from __future__ import annotations

import contextlib
import logging
import time
from typing import Any

from PySide6.QtCore import QObject, Property, Signal, Slot

from core.worker_manager import WorkerManager

logger = logging.getLogger("michi.nowplaying")

# ── Error codes ──
NO_PLAYER_SERVICE = "NO_PLAYER_SERVICE"
BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
UNSUPPORTED = "UNSUPPORTED"
INVALID_POSITION = "INVALID_POSITION"
INVALID_INDEX = "INVALID_INDEX"
UNKNOWN_DURATION = "UNKNOWN_DURATION"
PLAYBACK_ERROR = "PLAYBACK_ERROR"
QUEUE_UNAVAILABLE = "QUEUE_UNAVAILABLE"
INTERNAL_ERROR = "INTERNAL_ERROR"
EMPTY_FILEPATH = "EMPTY_FILEPATH"

_CMD_STATE_IDLE = "idle"
_CMD_STATE_PENDING = "pending"
_CMD_STATE_CONFIRMED = "confirmed"
_CMD_STATE_FAILED = "failed"


def _field(source, *names: str) -> str:
    if source is None:
        return ""
    if isinstance(source, dict):
        for name in names:
            value = source.get(name)
            if value:
                return str(value)
        return ""
    if isinstance(source, str):
        return source if "filepath" in names or "path" in names else ""
    for name in names:
        value = getattr(source, name, "")
        if callable(value):
            with contextlib.suppress(AttributeError):
                value = value()
        if value:
            return str(value)
    return ""


_SAFE_MESSAGES = {
    "NO_PLAYER_SERVICE": "Reproductor no disponible",
    "BACKEND_UNAVAILABLE": "Backend de audio no disponible",
    "UNSUPPORTED": "Operación no soportada por el backend actual",
    "INVALID_POSITION": "Posición inválida",
    "INVALID_INDEX": "Índice inválido",
    "UNKNOWN_DURATION": "No se conoce la duración de la pista",
    "PLAYBACK_ERROR": "No se pudo ejecutar la operación de reproducción",
    "QUEUE_UNAVAILABLE": "La cola no está disponible en el backend actual",
    "INTERNAL_ERROR": "Error interno de reproducción",
    "EMPTY_FILEPATH": "No se recibió una pista válida",
    "NOT_FOUND": "Elemento no encontrado",
}


def _safe_message(error_code: str) -> str:
    return _SAFE_MESSAGES.get(error_code, error_code)


def _err(operation: str, error_code: str, message: str = "", data: dict | None = None) -> dict:
    return {
        "ok": False,
        "operation": operation or "",
        "data": data or {},
        "error_code": error_code or "INTERNAL_ERROR",
        "message": message or _safe_message(error_code),
    }


def _ok(operation: str = "", data: dict | None = None) -> dict:
    return {
        "ok": True,
        "operation": operation or "",
        "data": data or {},
        "error_code": "",
        "message": "",
    }


class NowPlayingBridge(QObject):
    """Expose transport, history, and quality state to QML."""

    # QML-facing public API: preserve Qt camelCase for notify/Connections contracts.
    # Legacy signal (kept for compatibility)
    stateChanged = Signal()
    coverChanged = Signal()

    # Specific signals for QML Connections
    trackChanged = Signal()
    playbackStateChanged = Signal()
    positionChanged = Signal()
    durationChanged = Signal()
    volumeChanged = Signal()
    historyChanged = Signal()
    errorChanged = Signal()
    commandStateChanged = Signal()
    qualityChanged = Signal()
    capabilitiesChanged = Signal()
    backendInfoChanged = Signal()

    def __init__(
        self,
        player_service=None,
        queue_service=None,
        audio_quality_adapter=None,
        cover_provider=None,
        worker_manager=None,
        parent=None,
    ):
        super().__init__(parent)
        if player_service is None:
            logger.warning("NowPlayingBridge: player_service is None — running in degraded mode")
        self._player = player_service
        self._queue_service = queue_service
        self._cover_provider = cover_provider
        self._quality_adapter = audio_quality_adapter
        adapter_worker_manager = getattr(audio_quality_adapter, "_wm", None)
        self._worker_manager = worker_manager
        if self._worker_manager is None and isinstance(adapter_worker_manager, WorkerManager):
            self._worker_manager = adapter_worker_manager
        self._quality_probe_handle = None
        self._quality_probe_generation = 0
        self._track_title = "—"
        self._track_artist = ""
        self._track_album = ""
        self._cover_key = ""
        self._is_playing = False
        self._position = 0
        self._duration = 0
        self._volume = 80
        self._previous_volume = 80
        self._muted = False
        self._last_volume_request = self._volume
        self._last_volume_time = 0.0
        self._source_type = "local_file"
        self._quality_label = ""
        self._format_label = ""
        self._sample_rate = ""
        self._bit_depth = ""
        self._channels = ""
        self._bitrate = ""
        self._quality_info_available = False
        self._quality_loading = False
        self._quality_error = ""
        self._repeat_mode = "none"
        self._shuffle_enabled = False
        self._history: list[dict[str, Any]] = []
        self._history_internal_refs: dict[str, dict[str, Any]] = {}
        self._history_max = 50
        self._history_counter = 0
        self._backend_available = self._player is not None
        self._playback_status = "idle" if self._backend_available else "unavailable"
        self._backend_id = ""
        self._backend_state = "ready" if self._backend_available else "unavailable"
        self._error_message = ""
        self._emitted_error_keys: set[tuple[str, str]] = set()
        self._last_command = ""
        self._last_command_ok = False
        self._last_command_error = ""
        self._last_command_message = ""
        self._last_command_timestamp = 0.0
        self._command_pending = False
        self._command_state = _CMD_STATE_IDLE
        self._requested_confirmation: tuple[str, Any] | None = None
        self._connect_player()
        self.refresh()

    # ── Signal wiring ──

    def _connect_player(self):
        if not self._player:
            return
        # Connect trackContextChanged if available (new pipeline)
        ctx_signal = getattr(self._player, "trackContextChanged", None)
        if ctx_signal is not None:
            ctx_signal.connect(self._on_track_context)

        backend_signal = getattr(self._player, "backend_changed", None)
        if backend_signal is not None:
            with contextlib.suppress(TypeError):
                backend_signal.connect(self._on_backend_changed)

        for signal_name, slot in (
            ("track_changed", self._on_track),
            ("state_changed", self._on_state),
            ("position_changed", self._on_position),
            ("duration_changed", self._on_duration),
            ("volume_changed", self._on_volume),
            ("error_occurred", self._on_error),
        ):
            signal = getattr(self._player, signal_name, None)
            if signal is None:
                continue
            with contextlib.suppress(TypeError):
                signal.connect(slot)

    def _begin_command(
        self,
        operation: str,
        confirmation: tuple[str, Any] | None = None,
    ) -> None:
        self._last_command = operation
        self._last_command_ok = False
        self._last_command_error = ""
        self._last_command_message = "En ejecución..."
        self._last_command_timestamp = time.time()
        self._command_pending = True
        self._command_state = _CMD_STATE_PENDING
        self._requested_confirmation = confirmation
        self._emit_command()

    def _set_command_success(self, operation: str, data: dict | None = None) -> None:
        self._last_command = operation
        self._last_command_ok = True
        self._last_command_error = ""
        self._last_command_message = ""
        self._last_command_timestamp = time.time()
        self._command_pending = False
        self._command_state = _CMD_STATE_CONFIRMED
        self._requested_confirmation = None
        self._emit_command()

    def _set_command_failure(self, operation: str, error_code: str, message: str = "") -> None:
        self._last_command = operation
        self._last_command_ok = False
        self._last_command_error = error_code or "INTERNAL_ERROR"
        self._last_command_message = message or _safe_message(error_code)
        self._last_command_timestamp = time.time()
        self._command_pending = False
        self._command_state = _CMD_STATE_FAILED
        self._requested_confirmation = None
        self._emit_command()
        self._handle_error(operation, self._last_command_error, self._last_command_message, False)

    def _confirm_command(self, confirmation_type: str, value: Any) -> None:
        if self._command_state != _CMD_STATE_PENDING or not self._requested_confirmation:
            return
        expected_type, expected_value = self._requested_confirmation
        if expected_type != confirmation_type:
            return
        if expected_value is not None and expected_value != value:
            return
        self._set_command_success(self._last_command)

    def _handle_error(
        self,
        operation: str,
        error_code: str,
        message: str = "",
        update_command: bool = True,
    ) -> None:
        """Publish one error notification for each code/operation pair."""
        code = error_code or INTERNAL_ERROR
        op = operation or "playback"
        safe_message = message or _safe_message(code)
        if update_command and self._last_command == op:
            self._last_command_ok = False
            self._last_command_error = code
            self._last_command_message = safe_message
            self._last_command_timestamp = time.time()
            self._command_pending = False
            self._command_state = _CMD_STATE_FAILED
            self._requested_confirmation = None
            self._emit_command()
        error_key = (code, op)
        if error_key in self._emitted_error_keys:
            return
        self._emitted_error_keys.add(error_key)
        self._error_message = safe_message
        self._emit_error()

    def _emit_state(self):
        self.stateChanged.emit()

    def _emit_track(self):
        self.trackChanged.emit()
        self.stateChanged.emit()

    def _emit_playback(self):
        self.playbackStateChanged.emit()
        self.stateChanged.emit()

    def _emit_position(self):
        self.positionChanged.emit()

    def _emit_duration(self):
        self.durationChanged.emit()

    def _emit_volume(self):
        self.volumeChanged.emit()
        self.stateChanged.emit()

    def _emit_history(self):
        self.historyChanged.emit()
        self.stateChanged.emit()

    def _emit_error(self):
        self.errorChanged.emit()
        self.stateChanged.emit()

    def _emit_command(self):
        self.commandStateChanged.emit()
        self.stateChanged.emit()

    def _emit_quality(self):
        self.qualityChanged.emit()
        self.stateChanged.emit()

    def _emit_capabilities(self):
        self.capabilitiesChanged.emit()
        self.stateChanged.emit()

    def _set_cover_from_context(self, context: dict):
        """Set cover key from the track context dict."""
        cover = context.get("cover_key", "") or ""
        if not cover:
            album_key = str(context.get("album_key", "") or "")
            track_uid = str(context.get("track_uid", "") or "")
            if album_key:
                cover = f"album:{album_key}"
            elif track_uid:
                cover = f"track:{track_uid}"
            else:
                filepath = context.get("filepath", "") or self._current_path()
                cover = f"file:{filepath}" if filepath else ""
        if cover != self._cover_key:
            self._cover_key = cover
            self.coverChanged.emit()

    def _apply_quality_from_context(self, context: dict) -> bool:
        """Populate format/quality fields from the canonical track context."""
        def _str_val(value: Any) -> str:
            if value is None or value == 0 or value == "":
                return ""
            return str(value)

        candidates = {
            "_format_label": str(context.get("format") or ""),
            "_sample_rate": _str_val(context.get("sample_rate")),
            "_bit_depth": _str_val(context.get("bit_depth")),
            "_channels": _str_val(context.get("channels")),
            "_bitrate": _str_val(context.get("bitrate")),
        }
        changed = any(getattr(self, attr) != value for attr, value in candidates.items())
        for attr, value in candidates.items():
            if getattr(self, attr) != value:
                setattr(self, attr, value)
        has_quality = any(candidates.values())
        if has_quality:
            if not self._quality_info_available:
                self._quality_info_available = True
                changed = True
            if self._quality_loading:
                self._quality_loading = False
                changed = True
            if self._quality_error:
                self._quality_error = ""
                changed = True
        return changed

    def _add_history_from_context(self, context: dict) -> bool:
        """Record or enrich a history entry from the canonical track context."""
        title = str(context.get("title", "") or "")
        artist = str(context.get("artist", "") or "")
        album = str(context.get("album", "") or "")
        if not title or title == "—":
            return False

        track_uid = str(context.get("track_uid", "") or "")
        album_key = str(context.get("album_key", "") or "")
        cover_key = str(context.get("cover_key", "") or "")
        if not cover_key:
            cover_key = (
                f"album:{album_key}" if album_key
                else f"track:{track_uid}" if track_uid
                else self._cover_key
            )
        duration = int(context.get("duration") or 0)
        source_type = str(context.get("source_type") or "") or self._source_type
        track_id = ""
        current = getattr(self._player, "current", None) if self._player else None
        if current:
            track_id = str(getattr(current, "id", getattr(current, "track_id", "")) or "")

        if self._history:
            top = self._history[0]
            if (
                top.get("title") == title
                and top.get("artist") == artist
                and top.get("album") == album
            ):
                enrichment = {
                    "track_id": track_id or top.get("track_id", ""),
                    "track_uid": track_uid or top.get("track_uid", ""),
                    "cover_key": cover_key or top.get("cover_key", ""),
                    "duration": duration or top.get("duration", 0),
                    "source_type": source_type or top.get("source_type", ""),
                }
                changed = False
                for field, value in enrichment.items():
                    if value and top.get(field) != value:
                        top[field] = value
                        changed = True
                if changed:
                    hid = top.get("history_id", "")
                    ref = self._history_internal_refs.setdefault(hid, {})
                    ref["filepath"] = context.get("filepath", "") or self._current_path()
                    if track_id:
                        ref["track_id"] = track_id
                return changed

        self._history_counter += 1
        hid = f"h{self._history_counter}_{time.time():.0f}"
        entry = {
            "history_id": hid,
            "track_id": track_id,
            "track_uid": track_uid,
            "title": title,
            "artist": artist,
            "album": album,
            "cover_key": cover_key or self._cover_key,
            "duration": duration or self._duration,
            "source_type": source_type or self._source_type,
            "played_at": time.time(),
        }
        self._history_internal_refs[hid] = {
            "filepath": context.get("filepath", "") or self._current_path(),
            "track_id": track_id,
        }
        self._history.insert(0, entry)
        if len(self._history) > self._history_max:
            removed = self._history.pop()
            self._history_internal_refs.pop(removed.get("history_id", ""), None)
        return True

    def _on_track_context(self, context: dict):
        """Handle the canonical track context from PlayerService (single source)."""
        if not isinstance(context, dict):
            return
        self._last_context = context
        self._context_source = context.get("filepath", "") or ""

        title = str(context.get("title", "") or "")
        artist = str(context.get("artist", "") or "")
        album = str(context.get("album", "") or "")
        if title:
            self._track_title = title
        if artist:
            self._track_artist = artist
        if album:
            self._track_album = album

        self._set_cover_from_context(context)
        quality_changed = self._apply_quality_from_context(context)

        filepath = self._context_source or self._current_path()
        new_source_type = str(context.get("source_type") or "") or self._detect_source_type(filepath)
        source_changed = new_source_type != self._source_type
        if source_changed:
            self._source_type = new_source_type

        new_duration = int(context.get("duration") or 0)
        duration_changed = new_duration != self._duration
        if duration_changed:
            self._duration = new_duration

        history_changed = self._add_history_from_context(context)

        self._emit_track()
        if duration_changed:
            self._emit_duration()
        if quality_changed or source_changed:
            self._emit_quality()
        if source_changed:
            self._emit_playback()
        if history_changed:
            self._emit_history()

    def _set_cover_from_current_path(self):
        filepath = self._current_path()
        context = getattr(self, "_last_context", {})
        context_filepath = context.get("filepath", "") if isinstance(context, dict) else ""
        if context_filepath and context_filepath == filepath:
            cover_key = context.get("cover_key", "") or ""
            album_key = context.get("album_key", "") or ""
            track_uid = context.get("track_uid", "") or ""
            new_key = cover_key or (
                f"album:{album_key}" if album_key else f"track:{track_uid}" if track_uid else ""
            )
        else:
            new_key = f"file:{filepath}" if filepath else ""
        if new_key != self._cover_key:
            self._cover_key = new_key
            self.coverChanged.emit()

    def _current_path(self) -> str:
        if not self._player:
            return ""
        current = getattr(self._player, "current", None)
        path = _field(current, "filepath", "path", "url", "uri")
        if path:
            return path
        for attr in ("current_filepath", "current_path"):
            value = getattr(self._player, attr, "")
            if callable(value):
                try:
                    value = value()
                except Exception:
                    value = ""
            if value:
                return str(value)
        return ""

    # ── Signal handlers (update state from backend) ──

    def _add_to_history(self, title: str, artist: str, album: str) -> bool:
        if not title or title == "—":
            return False
        if (
            self._history
            and self._history[0].get("title") == title
            and self._history[0].get("artist") == artist
            and self._history[0].get("album") == album
        ):
            return False
        self._history_counter += 1
        hid = f"h{self._history_counter}_{time.time():.0f}"
        fp = self._current_path()
        track_id = ""
        track_uid = ""
        if hasattr(self._player, 'current'):
            c = self._player.current
            if c:
                track_id = str(getattr(c, 'id', getattr(c, 'track_id', '')) or '')
                track_uid = str(getattr(c, 'track_uid', '') or '')
        entry = {
            "history_id": hid,
            "track_id": track_id,
            "track_uid": track_uid,
            "title": title,
            "artist": artist,
            "album": album,
            "cover_key": self._cover_key,
            "duration": self._duration,
            "source_type": self._source_type,
            "played_at": time.time(),
        }
        self._history_internal_refs[hid] = {"filepath": fp, "track_id": track_id}
        self._history.insert(0, entry)
        if len(self._history) > self._history_max:
            removed = self._history.pop()
            self._history_internal_refs.pop(removed.get("history_id", ""), None)
        return True

    def _on_track(self, title="", artist="", album=""):
        previous_source_type = self._source_type
        self._track_title = title or ""
        self._track_artist = artist or ""
        self._track_album = album or ""
        self._set_cover_from_current_path()
        history_changed = self._add_to_history(
            self._track_title,
            self._track_artist,
            self._track_album,
        )
        fp = self._current_path()
        self._source_type = self._detect_source_type(fp)
        if self._source_type != previous_source_type:
            self._emit_playback()
            self._emit_quality()
        self._probe_quality(fp)
        self._confirm_command("track", None)
        self._emit_track()
        if history_changed:
            self._emit_history()

    def _on_state(self, state: str):
        had_error = bool(self._error_message)
        self._is_playing = state == "playing"
        self._playback_status = state
        self._error_message = ""
        self._emit_playback()
        self._confirm_command("playback", state)
        if had_error:
            self._emit_error()

    def _on_backend_changed(self, old_id: str, new_id: str):
        """Re-sync effective backend info after a backend switch."""
        if self._sync_backend_info():
            self._emit_playback()
            self._emit_capabilities()

    def _sync_backend_info(self) -> bool:
        """Read the effective backend id/state from the player service.

        Returns True when the exposed values changed. A fallback backend maps
        to the ``degraded`` state so QML can flag degraded output honestly.
        """
        backend_id = ""
        backend_state = "ready" if self._backend_available else "unavailable"
        if self._player:
            info = None
            getter = getattr(self._player, "get_backend_state", None)
            if callable(getter):
                with contextlib.suppress(Exception):
                    candidate = getter()
                if isinstance(candidate, dict):
                    info = candidate
            if info is not None:
                backend_id = str(info.get("id", "") or "")
                state = str(info.get("state", "") or "")
                backend_state = "degraded" if info.get("fallback") else (state or "ready")
            else:
                id_getter = getattr(self._player, "get_active_backend_id", None)
                if callable(id_getter):
                    with contextlib.suppress(Exception):
                        candidate = id_getter()
                    if isinstance(candidate, str):
                        backend_id = candidate
        changed = backend_id != self._backend_id or backend_state != self._backend_state
        if changed:
            self._backend_id = backend_id
            self._backend_state = backend_state
            self.backendInfoChanged.emit()
        return changed

    def _on_position(self, pos: float):
        self._position = int(pos)
        self._emit_position()
        self._confirm_command("position", self._position)

    def _on_duration(self, dur: float):
        self._duration = int(dur)
        self._emit_duration()

    def _on_volume(self, vol: int):
        self._volume = vol
        self._muted = vol == 0
        self._emit_volume()
        self._confirm_command("volume", self._volume)

    def _on_error(self, msg: str):
        safe_msg = str(msg) if msg else "Unknown error"
        operation = self._last_command or "playback"
        self._handle_error(operation, PLAYBACK_ERROR, _safe_message(safe_msg))

    # ── Properties ──

    @Property(str, notify=trackChanged)
    def trackTitle(self):
        return self._track_title

    @Property(str, notify=trackChanged)
    def trackArtist(self):
        return self._track_artist

    @Property(str, notify=trackChanged)
    def trackAlbum(self):
        return self._track_album

    @Property(str, notify=coverChanged)
    def coverKey(self):
        return self._cover_key

    @Property(str, notify=coverChanged)
    def coverPath(self):
        """Deprecated alias for ``coverKey``; kept for QML compatibility."""
        return self._cover_key

    @Property(bool, notify=playbackStateChanged)
    def isPlaying(self):
        return self._is_playing

    @Property(str, notify=playbackStateChanged)
    def playbackStatus(self):
        """Raw playback status: idle/playing/paused/stopped/buffering/
        reconnecting/unavailable or any state string a backend emits."""
        return self._playback_status

    @Property(int, notify=positionChanged)
    def position(self):
        return self._position

    @Property(int, notify=durationChanged)
    def duration(self):
        return self._duration

    @Property(int, notify=volumeChanged)
    def volume(self):
        return self._volume

    @Property(bool, notify=volumeChanged)
    def muted(self):
        return self._muted

    @Property(str, notify=playbackStateChanged)
    def repeatMode(self):
        return self._queue_service.repeat if self._queue_service else self._repeat_mode

    @Property(bool, notify=playbackStateChanged)
    def shuffleEnabled(self):
        return self._queue_service.shuffle if self._queue_service else self._shuffle_enabled

    @Property(str, notify=trackChanged)
    def currentFilePath(self):
        return self._current_path()

    # ── Quality / Source info ──

    def _detect_source_type(self, filepath: str) -> str:
        if not filepath:
            return "unknown"
        if filepath.startswith("radio://"):
            return "radio"
        if filepath.startswith(("http://", "https://")):
            return "remote"
        if filepath.startswith("michi://"):
            return "michi_server"
        if filepath.startswith("smb://"):
            return "network_share"
        if filepath.startswith("nfs://"):
            return "network_share"
        if filepath.startswith("/dev/"):
            return "disc"
        return "local_file"

    @Property(bool, notify=playbackStateChanged)
    def liveSource(self):
        st = self._source_type
        return st in ("radio", "stream", "remote")

    @Property(bool, notify=playbackStateChanged)
    def remoteSource(self):
        st = self._source_type
        return st in ("remote", "michi_server", "network_share")

    @Property(bool, notify=playbackStateChanged)
    def seekableSource(self):
        return not self.liveSource and not self.remoteSource

    def _probe_quality(self, filepath: str) -> None:
        self._quality_probe_generation += 1
        generation = self._quality_probe_generation
        if self._quality_probe_handle is not None:
            self._quality_probe_handle.cancel()
            self._quality_probe_handle = None
        if not filepath or not self._quality_adapter:
            changed = self._quality_info_available or self._quality_loading
            self._quality_info_available = False
            self._quality_loading = False
            if changed:
                self._emit_quality()
            return
        self._quality_loading = True
        self._quality_error = ""
        self._emit_quality()
        if self._worker_manager is None:
            try:
                result = self._quality_adapter.probe(filepath)
            except Exception as exc:
                self._finish_quality_probe_error(generation, str(exc))
            else:
                self._finish_quality_probe(generation, filepath, result)
            return

        task_id = f"nowplaying-quality-probe-{generation}"
        self._quality_probe_handle = self._worker_manager.run_task(
            task_id,
            self._quality_adapter.probe,
            filepath,
            owner="nowplaying",
            cancellable=True,
            on_done=lambda result: self._finish_quality_probe(generation, filepath, result),
            on_error=lambda _code, message: self._finish_quality_probe_error(
                generation, message
            ),
            on_cancelled=lambda: self._finish_quality_probe_cancelled(generation),
        )
        if getattr(self._quality_probe_handle, "state", "") == "failed":
            message = getattr(self._quality_probe_handle, "message", "")
            code = getattr(self._quality_probe_handle, "error_code", "")
            self._finish_quality_probe_error(generation, message or _safe_message(code))

    def _finish_quality_probe(self, generation: int, filepath: str, result: Any) -> None:
        if generation != self._quality_probe_generation:
            return
        previous_source_type = self._source_type
        try:
            if result and result.get("ok"):
                self._format_label = result.get("format_label", "")
                self._sample_rate = result.get("sample_rate", "")
                self._bit_depth = result.get("bit_depth", "")
                self._channels = result.get("channels", "")
                self._bitrate = result.get("bitrate", "")
                self._quality_label = result.get("quality_label", "")
                self._source_type = result.get("source_type", self._detect_source_type(filepath))
                self._quality_info_available = True
                self._quality_error = ""
            else:
                self._quality_info_available = False
                self._quality_error = result.get("error", "") if result else ""
                self._source_type = self._detect_source_type(filepath)
        except (AttributeError, TypeError) as exc:
            logger.debug("Invalid quality probe result: %s", exc)
            self._quality_info_available = False
            self._quality_error = str(exc)
        self._quality_loading = False
        self._quality_probe_handle = None
        if self._source_type != previous_source_type:
            self._emit_playback()
        self._emit_quality()

    def _finish_quality_probe_error(self, generation: int, message: str) -> None:
        if generation != self._quality_probe_generation:
            return
        self._quality_info_available = False
        self._quality_loading = False
        self._quality_error = message or _safe_message(INTERNAL_ERROR)
        self._quality_probe_handle = None
        self._emit_quality()

    def _finish_quality_probe_cancelled(self, generation: int) -> None:
        if generation != self._quality_probe_generation:
            return
        self._quality_loading = False
        self._quality_probe_handle = None
        self._emit_quality()

    @Property(str, notify=qualityChanged)
    def sourceType(self):
        return self._source_type

    @Property(str, notify=qualityChanged)
    def formatLabel(self):
        return self._format_label

    @Property(str, notify=qualityChanged)
    def qualityLabel(self):
        return self._quality_label

    @Property(str, notify=qualityChanged)
    def sampleRate(self):
        return self._sample_rate

    @Property(str, notify=qualityChanged)
    def bitDepth(self):
        return self._bit_depth

    @Property(str, notify=qualityChanged)
    def channels(self):
        return self._channels

    @Property(str, notify=qualityChanged)
    def bitrate(self):
        return self._bitrate

    @Property(bool, notify=qualityChanged)
    def qualityInfoAvailable(self):
        return self._quality_info_available

    @Property(bool, notify=qualityChanged)
    def qualityLoading(self):
        return self._quality_loading

    @Property(str, notify=qualityChanged)
    def qualityError(self):
        return self._quality_error

    @Property("QVariantList", notify=historyChanged)
    def history(self):
        return list(self._history)

    @Property(bool, notify=trackChanged)
    def hasTrack(self):
        return bool(
            (self._track_title and self._track_title != "—")
            or bool(self._current_path())
        )

    @Property(bool, notify=capabilitiesChanged)
    def backendAvailable(self):
        return self._backend_available

    @Property(str, notify=backendInfoChanged)
    def backendId(self):
        """Effective backend id (e.g. ``gstreamer``, ``mpd``)."""
        return self._backend_id

    @Property(str, notify=backendInfoChanged)
    def backendState(self):
        """Effective backend lifecycle state: ready/initializing/degraded/
        failed/uninitialized/unavailable."""
        return self._backend_state

    @Property(bool, notify=backendInfoChanged)
    def backendSwitching(self):
        return self._backend_state == "initializing"

    @Property(bool, notify=backendInfoChanged)
    def degradedOutput(self):
        return self._backend_state == "degraded"

    @Property(str, notify=errorChanged)
    def errorMessage(self):
        return self._error_message

    @Property(str, notify=commandStateChanged)
    def lastCommand(self):
        return self._last_command

    @Property(bool, notify=commandStateChanged)
    def lastCommandOk(self):
        return self._last_command_ok

    @Property(str, notify=commandStateChanged)
    def lastCommandError(self):
        return self._last_command_error

    @Property(str, notify=commandStateChanged)
    def lastCommandMessage(self):
        return self._last_command_message

    @Property(float, notify=commandStateChanged)
    def lastCommandTimestamp(self):
        return self._last_command_timestamp

    @Property(bool, notify=commandStateChanged)
    def commandPending(self):
        return self._command_pending

    @Property(str, notify=commandStateChanged)
    def commandState(self):
        return self._command_state

    # ── Capabilities ──

    def _has_player_method(self, *names: str) -> bool:
        if not self._player:
            return False
        return any(hasattr(self._player, name) for name in names)

    @Property(bool, notify=stateChanged)
    def playPauseSupported(self):
        return self._has_player_method("pause", "play_or_resume", "resume")

    @Property(bool, notify=stateChanged)
    def seekSupported(self):
        return self._has_player_method("seek") and self._duration > 0 and self.seekableSource

    @Property(bool, notify=stateChanged)
    def volumeSupported(self):
        return self._has_player_method("set_volume")

    @Property(bool, notify=stateChanged)
    def muteSupported(self):
        return self._has_player_method("set_volume", "toggle_mute")

    @Property(bool, notify=stateChanged)
    def nextSupported(self):
        return self._queue_service is not None

    @Property(bool, notify=stateChanged)
    def previousSupported(self):
        return self._queue_service is not None

    @Property(bool, notify=stateChanged)
    def queueSupported(self):
        return self._queue_service is not None

    @Property(bool, notify=stateChanged)
    def queueRemoveSupported(self):
        return self._queue_service is not None

    @Property(bool, notify=stateChanged)
    def queueClearSupported(self):
        return self._queue_service is not None

    @Property(bool, notify=stateChanged)
    def queueMoveSupported(self):
        return self._queue_service is not None

    @Property(bool, notify=stateChanged)
    def queuePlayItemSupported(self):
        return self._queue_service is not None

    @Property(bool, notify=stateChanged)
    def shuffleSupported(self):
        return self._queue_service is not None

    @Property(bool, notify=stateChanged)
    def repeatSupported(self):
        return self._queue_service is not None

    @Property(bool, notify=stateChanged)
    def historySupported(self):
        return True

    # ── Data loading ──

    @Slot(result=dict)
    def refresh(self):
        if not self._player:
            return _err("refresh", NO_PLAYER_SERVICE)
        try:
            previous_track = (
                self._track_title,
                self._track_artist,
                self._track_album,
            )
            previous_playback = (self._is_playing, self._playback_status)
            previous_duration = self._duration
            if hasattr(self._player, 'current'):
                current = self._player.current
                if current:
                    self._track_title = _field(current, "title", "name") or self._track_title
                    self._track_artist = _field(current, "artist") or self._track_artist
                    self._track_album = _field(current, "album") or self._track_album
                    self._set_cover_from_current_path()
            if hasattr(self._player, 'state'):
                st = self._player.state
                if st:
                    self._is_playing = st == "playing"
                    self._playback_status = st
            if hasattr(self._player, 'duration'):
                d = self._player.duration
                if d:
                    self._duration = int(d)
            if previous_track != (
                self._track_title,
                self._track_artist,
                self._track_album,
            ):
                self._emit_track()
            if previous_playback != (self._is_playing, self._playback_status):
                self._emit_playback()
            if previous_duration != self._duration:
                self._emit_duration()
            self._sync_backend_info()
            self._emit_state()
            return _ok("refresh")
        except Exception as e:
            logger.debug("refresh failed: %s", e)
            return _err("refresh", PLAYBACK_ERROR, str(e))

    # ── Playback commands ──

    @Slot(result=dict)
    def togglePlay(self) -> dict:
        op = "togglePlay"
        if not self._player:
            self._begin_command(op)
            self._set_command_failure(op, NO_PLAYER_SERVICE)
            return _err(op, NO_PLAYER_SERVICE)
        try:
            if self._is_playing:
                if hasattr(self._player, 'pause'):
                    self._begin_command(op, ("playback", "paused"))
                    self._player.pause()
                    return _ok(op, {"playing": False, "state_confirmed": False})
                self._begin_command(op)
                self._set_command_failure(op, UNSUPPORTED)
                return _err(op, UNSUPPORTED)
            if hasattr(self._player, 'play_or_resume'):
                self._begin_command(op, ("playback", "playing"))
                self._player.play_or_resume()
                return _ok(op, {"playing": True, "state_confirmed": False})
            if hasattr(self._player, 'resume'):
                self._begin_command(op, ("playback", "playing"))
                self._player.resume()
                return _ok(op, {"playing": True, "state_confirmed": False})
            self._begin_command(op)
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        except Exception as e:
            logger.warning("togglePlay failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(result=dict)
    def next(self) -> dict:
        op = "next"
        self._begin_command(op, ("track", None))
        if not self._queue_service:
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        try:
            result = self._queue_service.next()
            if result.get("ok"):
                return result
            code = result.get("error", PLAYBACK_ERROR)
            self._set_command_failure(op, code, result.get("message", ""))
            return result
        except Exception as e:
            logger.warning("next failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(result=dict)
    def previous(self) -> dict:
        op = "previous"
        self._begin_command(op, ("track", None))
        if not self._queue_service:
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        try:
            result = self._queue_service.previous()
            if result.get("ok"):
                return result
            code = result.get("error", PLAYBACK_ERROR)
            self._set_command_failure(op, code, result.get("message", ""))
            return result
        except Exception as e:
            logger.warning("previous failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(int, result=dict)
    def seek(self, position: int) -> dict:
        op = "seek"
        if not self._player:
            self._begin_command(op)
            self._set_command_failure(op, NO_PLAYER_SERVICE)
            return _err(op, NO_PLAYER_SERVICE)
        if self._duration <= 0:
            self._begin_command(op)
            self._set_command_failure(op, UNKNOWN_DURATION)
            return _err(op, UNKNOWN_DURATION)
        pos = max(0, min(int(position), self._duration))
        self._begin_command(op, ("position", pos))
        try:
            if hasattr(self._player, 'seek'):
                self._player.seek(pos)
                self._position = pos
                self._emit_position()
                return _ok(op, {"requested_position": pos, "state_confirmed": False})
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        except Exception as e:
            logger.warning("seek failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(int, result=dict)
    def seekRelative(self, seconds: int) -> dict:
        return self.seek(self._position + int(seconds))

    @Slot(int, result=dict)
    def setVolume(self, volume: int) -> dict:
        op = "setVolume"
        if not self._player:
            self._begin_command(op)
            self._set_command_failure(op, NO_PLAYER_SERVICE)
            return _err(op, NO_PLAYER_SERVICE)
        vol = max(0, min(100, int(volume)))
        now = time.time()
        if abs(vol - self._last_volume_request) < 2 and now - self._last_volume_time < 0.1:
            self._last_volume_request = vol
            self._last_volume_time = now
            return _ok(op, {"volume": vol, "coalesced": True})
        self._last_volume_request = vol
        self._last_volume_time = now
        self._begin_command(op, ("volume", vol))
        try:
            if hasattr(self._player, 'set_volume'):
                self._player.set_volume(vol)
                self._volume = vol
                self._muted = vol == 0
                self._emit_volume()
                return _ok(op, {"volume": vol, "muted": vol == 0, "state_confirmed": False})
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        except Exception as e:
            logger.warning("setVolume failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(result=dict)
    def toggleMute(self) -> dict:
        op = "toggleMute"
        if not self._player:
            self._begin_command(op)
            self._set_command_failure(op, NO_PLAYER_SERVICE)
            return _err(op, NO_PLAYER_SERVICE)
        try:
            if not hasattr(self._player, 'set_volume'):
                self._begin_command(op)
                self._set_command_failure(op, UNSUPPORTED)
                return _err(op, UNSUPPORTED)
            target = 0 if self._volume > 0 else (self._previous_volume or 80)
            self._begin_command(op, ("volume", target))
            self._player.set_volume(target)
            self._previous_volume = self._volume if self._volume > 0 else self._previous_volume
            self._volume = target
            self._muted = target == 0
            self._emit_volume()
            return _ok(op, {"volume": target, "muted": target == 0, "state_confirmed": False})
        except Exception as e:
            logger.warning("toggleMute failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(result=dict)
    def stop(self) -> dict:
        """Stop playback and reset position (transport control)."""
        op = "stop"
        self._begin_command(op, ("playback", "stopped"))
        if not self._player:
            self._set_command_failure(op, NO_PLAYER_SERVICE)
            return _err(op, NO_PLAYER_SERVICE)
        try:
            if hasattr(self._player, 'stop'):
                self._player.stop()
                self._position = 0
                self._emit_position()
                return _ok(op, {"state_confirmed": False})
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        except Exception as e:
            logger.warning("stop failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(result=dict)
    def toggleShuffle(self) -> dict:
        op = "toggleShuffle"
        self._begin_command(op)
        if not self._queue_service:
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        try:
            result = self._queue_service.toggle_shuffle()
            if not result.get("ok"):
                self._set_command_failure(op, result.get("error", PLAYBACK_ERROR))
                return result
            self._shuffle_enabled = self._queue_service.shuffle
            self._set_command_success(op)
            self._emit_playback()
            return result
        except Exception as e:
            logger.warning("toggleShuffle failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(result=dict)
    def toggleRepeat(self) -> dict:
        op = "toggleRepeat"
        self._begin_command(op)
        if not self._queue_service:
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        try:
            result = self._queue_service.toggle_repeat()
            if not result.get("ok"):
                self._set_command_failure(op, result.get("error", PLAYBACK_ERROR))
                return result
            self._repeat_mode = self._queue_service.repeat
            self._set_command_success(op)
            self._emit_playback()
            return result
        except Exception as e:
            logger.warning("toggleRepeat failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    # ── Queue commands ──

    @Slot(str, result=dict)
    def enqueueSong(self, filepath: str) -> dict:
        op = "enqueueSong"
        self._begin_command(op)
        if not filepath:
            self._set_command_failure(op, EMPTY_FILEPATH)
            return _err(op, EMPTY_FILEPATH)
        if not self._queue_service:
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        try:
            result = self._queue_service.enqueue({"filepath": filepath}, play_now=False)
            if result.get("ok"):
                self._set_command_success(op)
                return result
            code = result.get("error", PLAYBACK_ERROR)
            self._set_command_failure(op, code, result.get("message", ""))
            return result
        except Exception as e:
            logger.warning("enqueueSong failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(int, result=dict)
    def removeFromQueue(self, index: int) -> dict:
        op = "removeFromQueue"
        self._begin_command(op)
        if not self._queue_service:
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        if index < 0 or index >= self._queue_service.count:
            self._set_command_failure(op, INVALID_INDEX)
            return _err(op, INVALID_INDEX)
        try:
            result = self._queue_service.remove([index])
            if result.get("ok"):
                self._set_command_success(op)
                return result
            code = result.get("error", PLAYBACK_ERROR)
            self._set_command_failure(op, code, result.get("message", ""))
            return result
        except Exception as e:
            logger.warning("removeFromQueue failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(result=dict)
    def clearQueue(self) -> dict:
        op = "clearQueue"
        self._begin_command(op)
        if not self._queue_service:
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        try:
            result = self._queue_service.clear()
            if result.get("ok"):
                self._set_command_success(op)
                return result
            code = result.get("error", PLAYBACK_ERROR)
            self._set_command_failure(op, code, result.get("message", ""))
            return result
        except Exception as e:
            logger.warning("clearQueue failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(int, int, result=dict)
    def moveQueueItem(self, from_index: int, to_index: int) -> dict:
        op = "moveQueueItem"
        self._begin_command(op)
        if not self._queue_service:
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        if from_index < 0 or from_index >= self._queue_service.count:
            self._set_command_failure(op, INVALID_INDEX)
            return _err(op, INVALID_INDEX)
        if to_index < 0 or to_index >= self._queue_service.count:
            self._set_command_failure(op, INVALID_INDEX)
            return _err(op, INVALID_INDEX)
        try:
            result = self._queue_service.reorder(from_index, to_index)
            if result.get("ok"):
                self._set_command_success(op)
                return result
            code = result.get("error", PLAYBACK_ERROR)
            self._set_command_failure(op, code, result.get("message", ""))
            return result
        except Exception as e:
            logger.warning("moveQueueItem failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(int, result=dict)
    def playQueueItem(self, index: int) -> dict:
        op = "playQueueItem"
        self._begin_command(op)
        if not self._queue_service:
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        if index < 0 or index >= self._queue_service.count:
            self._set_command_failure(op, INVALID_INDEX)
            return _err(op, INVALID_INDEX)
        try:
            result = self._queue_service.play_from_index(index)
            if result.get("ok"):
                self._set_command_success(op)
                return result
            code = result.get("error", PLAYBACK_ERROR)
            self._set_command_failure(op, code, result.get("message", ""))
            return result
        except Exception as e:
            logger.warning("playQueueItem failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(result=dict)
    def clearHistory(self) -> dict:
        op = "clearHistory"
        self._begin_command(op)
        self._history.clear()
        if hasattr(self, "_history_internal_refs"):
            self._history_internal_refs.clear()
        self._set_command_success(op)
        self._emit_history()
        return _ok(op)

    @Slot(int, result=dict)
    def playHistoryItem(self, index: int) -> dict:
        op = "playHistoryItem"
        self._begin_command(op, ("track", None))
        if index < 0 or index >= len(self._history):
            self._set_command_failure(op, INVALID_INDEX)
            return _err(op, INVALID_INDEX)
        entry = self._history[index]
        internal_key = entry.get("history_id", "")
        ref = self._history_internal_refs.get(internal_key, {})
        fp = ref.get("filepath", "")
        if fp and self._player and hasattr(self._player, 'play'):
            self._player.play(fp)
            return _ok(op, {"history_id": internal_key})
        self._set_command_failure(op, UNSUPPORTED)
        return _err(op, UNSUPPORTED)

    def set_cover_from_path(self, filepath: str) -> None:
        self._cover_key = f"file:{filepath}" if filepath else ""
        self.coverChanged.emit()
        self._emit_state()

    # ── Scoring helpers ──

    @Slot(result=int)
    def totalPlayed(self) -> int:
        return len(self._history)

    @Slot(result=int)
    def queueDuration(self) -> int:
        items = self._queue_service.items if self._queue_service else []
        return sum(item.get("duration", 0) for item in items)

    @Slot(result=dict)
    def playbackScore(self) -> dict:
        """Return a playback quality score based on real state."""
        score = 0
        if self._backend_available:
            score += 25
        if self._queue_service:
            score += 15
        if self._track_title and self._track_title != "—":
            score += 20
        if self._duration > 0:
            score += 10
        if self._player and hasattr(self._player, 'state'):
            score += 15
        queue_count = self._queue_service.count if self._queue_service else 0
        if queue_count > 0:
            score += 15
        return {
            "score": min(100, score),
            "has_backend": self._backend_available,
            "has_track": self._track_title != "—",
            "has_queue": queue_count > 0,
            "has_position": self._position >= 0,
            "has_duration": self._duration > 0,
            "queue_count": queue_count,
            "history_count": len(self._history),
        }
