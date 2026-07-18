"""NowPlayingBridge — QML-facing playback state backed by PlayerService.

All commands return dict with structured errors.
State is only updated after backend confirmation.
"""
from __future__ import annotations

import hashlib
import contextlib
import logging
from typing import Any

from PySide6.QtCore import QObject, Property, Signal, Slot

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


def _cover_key_for_path(filepath: str) -> str:
    if not filepath:
        return ""
    return f"track_{hashlib.md5(filepath.encode()).hexdigest()[:12]}"


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
            with contextlib.suppress(Exception):
                value = value()
        if value:
            return str(value)
    return ""


def _player_field(player, *names: str) -> str:
    return _field(player, *names)


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
    return {"ok": True, "operation": operation or "", "data": data or {}, "error_code": "", "message": ""}


class NowPlayingBridge(QObject):
    # Legacy signal (kept for compatibility)
    stateChanged = Signal()
    coverChanged = Signal()

    # Specific signals for QML Connections
    trackChanged = Signal()
    playbackStateChanged = Signal()
    positionChanged = Signal()
    durationChanged = Signal()
    volumeChanged = Signal()
    queueChanged = Signal()
    historyChanged = Signal()
    errorChanged = Signal()
    commandStateChanged = Signal()
    qualityChanged = Signal()
    capabilitiesChanged = Signal()

    def __init__(self, player_service=None, audio_quality_adapter=None, parent=None):
        super().__init__(parent)
        assert player_service is not None, "NowPlayingBridge: player_service is REQUIRED"
        assert audio_quality_adapter is not None, "NowPlayingBridge: audio_quality_adapter is REQUIRED"
        self._player = player_service
        self._quality_adapter = audio_quality_adapter
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
        self._queue: list[dict[str, Any]] = []
        self._queue_internal_refs: dict[int, dict[str, Any]] = {}
        self._history: list[dict[str, Any]] = []
        self._history_internal_refs: dict[str, dict[str, Any]] = {}
        self._history_max = 50
        self._history_counter = 0
        self._backend_available = self._player is not None
        self._playback_status = "idle" if self._backend_available else "unavailable"
        self._error_message = ""
        self._last_command = ""
        self._last_command_ok = False
        self._last_command_error = ""
        self._last_command_message = ""
        self._last_command_timestamp = 0.0
        self._command_pending = False
        self._safe_mode = not self._backend_available

        self._connect_player()
        self.refresh()

    # ── Signal wiring ──

    def _connect_player(self):
        if not self._player:
            return
        for signal_name, slot in (
            ("track_changed", self._on_track),
            ("state_changed", self._on_state),
            ("position_changed", self._on_position),
            ("duration_changed", self._on_duration),
            ("volume_changed", self._on_volume),
            ("queue_changed", self._on_queue),
            ("error_occurred", self._on_error),
        ):
            signal = getattr(self._player, signal_name, None)
            if signal is None:
                continue
            with contextlib.suppress(Exception):
                signal.connect(slot)

    def _begin_command(self, operation: str):
        self._last_command = operation
        self._last_command_ok = False
        self._last_command_error = ""
        self._last_command_message = "En ejecución..."
        self._last_command_timestamp = __import__("time").time()
        self._command_pending = True
        self._emit_command()

    def _set_command_success(self, operation: str, data: dict | None = None):
        self._last_command = operation
        self._last_command_ok = True
        self._last_command_error = ""
        self._last_command_message = ""
        self._last_command_timestamp = __import__("time").time()
        self._command_pending = False
        self._emit_command()

    def _set_command_failure(self, operation: str, error_code: str, message: str = ""):
        self._last_command = operation
        self._last_command_ok = False
        self._last_command_error = error_code or "INTERNAL_ERROR"
        self._last_command_message = message or _safe_message(error_code)
        self._last_command_timestamp = __import__("time").time()
        self._command_pending = False
        self._emit_command()

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

    def _emit_queue(self):
        self.queueChanged.emit()
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

    def _set_cover_from_current_path(self):
        filepath = self._current_path()
        new_key = _cover_key_for_path(filepath)
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

    def _player_call(self, *names: str, fallback=None):
        if not self._player:
            return fallback
        for name in names:
            method = getattr(self._player, name, None)
            if callable(method):
                return method
        return fallback

    # ── Signal handlers (update state from backend) ──

    def _add_to_history(self, title: str, artist: str, album: str):
        if not title or title == "—":
            return
        if self._history and self._history[0].get("title") == title and self._history[0].get("artist") == artist and self._history[0].get("album") == album:
            return
        self._history_counter += 1
        hid = f"h{self._history_counter}_{__import__('time').time():.0f}"
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
            "played_at": __import__("time").time(),
        }
        self._history_internal_refs[hid] = {"filepath": fp, "track_id": track_id}
        self._history.insert(0, entry)
        if len(self._history) > self._history_max:
            removed = self._history.pop()
            self._history_internal_refs.pop(removed.get("history_id", ""), None)

    def _on_track(self, title="", artist="", album=""):
        self._track_title = title or ""
        self._track_artist = artist or ""
        self._track_album = album or ""
        self._set_cover_from_current_path()
        self._add_to_history(self._track_title, self._track_artist, self._track_album)
        fp = self._current_path()
        self._source_type = self._detect_source_type(fp)
        self._probe_quality(fp)
        self._emit_track()

    def _on_state(self, state: str):
        self._is_playing = state == "playing"
        self._playback_status = state
        self._error_message = ""
        self._emit_playback()

    def _on_position(self, pos: float):
        self._position = int(pos)
        self._emit_position()

    def _on_duration(self, dur: float):
        self._duration = int(dur)
        self._emit_duration()

    def _on_volume(self, vol: int):
        self._volume = vol
        self._muted = vol == 0
        self._emit_volume()

    def _normalize_queue_item(self, item: Any, index: int) -> dict:
        if isinstance(item, dict):
            title = str(item.get("title", item.get("name", "")) or "")
            artist = str(item.get("artist", "") or "")
            album = str(item.get("album", "") or "")
            duration = int(item.get("duration", 0) or 0)
            track_id = str(item.get("track_id", item.get("id", "")) or "")
            track_uid = str(item.get("track_uid", "") or "")
            source = str(item.get("source_type", "local_file") or "local_file")
            raw_fp = item.get("filepath", item.get("path", item.get("url", "")) or "")
        else:
            title = getattr(item, "title", getattr(item, "name", "")) or ""
            artist = getattr(item, "artist", "") or ""
            album = getattr(item, "album", "") or ""
            duration = int(getattr(item, "duration", 0) or 0)
            track_id = str(getattr(item, "track_id", getattr(item, "id", "")) or "")
            track_uid = str(getattr(item, "track_uid", "") or "")
            source = "local_file"
            raw_fp = getattr(item, "filepath", getattr(item, "path", getattr(item, "url", ""))) or ""

        self._queue_internal_refs[index] = {
            "filepath": raw_fp,
            "backend_id": track_id,
        }

        cover_key = ""
        if raw_fp:
            cover_key = _cover_key_for_path(raw_fp)

        return {
            "queue_index": index,
            "track_id": track_id,
            "track_uid": track_uid,
            "title": title,
            "artist": artist,
            "album": album,
            "duration": duration,
            "cover_key": cover_key,
            "source_type": source,
            "is_current": index == 0,
        }

    def _normalize_queue(self, items: list) -> list[dict]:
        self._queue_internal_refs.clear()
        result = []
        for i, item in enumerate(items or []):
            result.append(self._normalize_queue_item(item, i))
        return result

    def _on_queue(self, q: list):
        self._queue = self._normalize_queue(q) if q else []
        self._emit_queue()

    def _on_error(self, msg: str):
        safe_msg = str(msg) if msg else "Unknown error"
        self._error_message = _safe_message(safe_msg)
        if self._last_command:
            self._last_command_ok = False
            self._last_command_error = "PLAYBACK_ERROR"
            self._last_command_message = self._error_message
            self._command_pending = False
            self._emit_command()
        self._emit_error()

    # ── Properties ──

    @Property(str, notify=stateChanged)
    def trackTitle(self):
        return self._track_title

    @Property(str, notify=stateChanged)
    def trackArtist(self):
        return self._track_artist

    @Property(str, notify=stateChanged)
    def trackAlbum(self):
        return self._track_album

    @Property(str, notify=coverChanged)
    def coverPath(self):
        return self._cover_key

    @Property(bool, notify=stateChanged)
    def isPlaying(self):
        return self._is_playing

    @Property(int, notify=stateChanged)
    def position(self):
        return self._position

    @Property(int, notify=stateChanged)
    def duration(self):
        return self._duration

    @Property(int, notify=stateChanged)
    def volume(self):
        return self._volume

    @Property(bool, notify=stateChanged)
    def muted(self):
        return self._muted

    @Property(str, notify=stateChanged)
    def repeatMode(self):
        return self._repeat_mode

    @Property(bool, notify=stateChanged)
    def shuffleEnabled(self):
        return self._shuffle_enabled

    @Property(str, notify=stateChanged)
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

    @Property(bool, notify=stateChanged)
    def liveSource(self):
        st = self._source_type
        return st in ("radio", "stream", "remote")

    @Property(bool, notify=stateChanged)
    def remoteSource(self):
        st = self._source_type
        return st in ("remote", "michi_server", "network_share")

    @Property(bool, notify=stateChanged)
    def seekableSource(self):
        return not self.liveSource and not self.remoteSource

    def _probe_quality(self, filepath: str):
        if not filepath or not self._quality_adapter:
            self._quality_info_available = False
            self._quality_loading = False
            return
        self._quality_loading = True
        self._emit_quality()
        try:
            result = self._quality_adapter.probe(filepath)
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
                self._quality_error = result.get("error", "")
                self._source_type = self._detect_source_type(filepath)
        except Exception as e:
            logger.debug("Quality probe error: %s", e)
            self._quality_info_available = False
            self._quality_error = str(e)
        self._quality_loading = False
        self._emit_quality()

    @Property(str, notify=stateChanged)
    def sourceType(self):
        return self._source_type

    @Property(str, notify=stateChanged)
    def formatLabel(self):
        return self._format_label

    @Property(str, notify=stateChanged)
    def qualityLabel(self):
        return self._quality_label

    @Property(str, notify=stateChanged)
    def sampleRate(self):
        return self._sample_rate

    @Property(str, notify=stateChanged)
    def bitDepth(self):
        return self._bit_depth

    @Property(str, notify=stateChanged)
    def channels(self):
        return self._channels

    @Property(str, notify=stateChanged)
    def bitrate(self):
        return self._bitrate

    @Property(bool, notify=stateChanged)
    def qualityInfoAvailable(self):
        return self._quality_info_available

    @Property(bool, notify=stateChanged)
    def qualityLoading(self):
        return self._quality_loading

    @Property(str, notify=stateChanged)
    def qualityError(self):
        return self._quality_error

    @Property("QVariantList", notify=stateChanged)
    def queue(self):
        return list(self._queue)

    @Property("QVariantList", notify=stateChanged)
    def history(self):
        return list(self._history)

    @Property(bool, notify=stateChanged)
    def hasTrack(self):
        return self._track_title != "—" or bool(self._current_path())

    @Property(bool, notify=stateChanged)
    def backendAvailable(self):
        return self._backend_available

    @Property(str, notify=stateChanged)
    def errorMessage(self):
        return self._error_message

    @Property(str, notify=stateChanged)
    def lastCommand(self):
        return self._last_command

    @Property(bool, notify=stateChanged)
    def lastCommandOk(self):
        return self._last_command_ok

    @Property(str, notify=stateChanged)
    def lastCommandError(self):
        return self._last_command_error

    @Property(str, notify=stateChanged)
    def lastCommandMessage(self):
        return self._last_command_message

    @Property(float, notify=stateChanged)
    def lastCommandTimestamp(self):
        return self._last_command_timestamp

    @Property(bool, notify=stateChanged)
    def commandPending(self):
        return self._command_pending

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
        return self._has_player_method("play_next", "next")

    @Property(bool, notify=stateChanged)
    def previousSupported(self):
        return self._has_player_method("play_prev", "previous")

    @Property(bool, notify=stateChanged)
    def queueSupported(self):
        return self._has_player_method("get_queue") or self._has_player_method("queue")

    @Property(bool, notify=stateChanged)
    def queueRemoveSupported(self):
        return self._has_player_method("remove_queue_item", "remove_from_queue")

    @Property(bool, notify=stateChanged)
    def queueClearSupported(self):
        return self._has_player_method("clear_queue")

    @Property(bool, notify=stateChanged)
    def queueMoveSupported(self):
        return self._has_player_method("move_queue_item")

    @Property(bool, notify=stateChanged)
    def queuePlayItemSupported(self):
        return self._has_player_method("play_queue_item")

    @Property(bool, notify=stateChanged)
    def shuffleSupported(self):
        return self._has_player_method("toggle_shuffle")

    @Property(bool, notify=stateChanged)
    def repeatSupported(self):
        return self._has_player_method("toggle_repeat")

    @Property(bool, notify=stateChanged)
    def historySupported(self):
        return True

    # ── Data loading ──

    @Slot(result=dict)
    def refresh(self):
        if not self._player:
            return _err("refresh", NO_PLAYER_SERVICE)
        try:
            if hasattr(self._player, 'current'):
                current = self._player.current
                if current:
                    self._track_title = _field(current, "title", "name") or self._track_title
                    self._track_artist = _field(current, "artist") or self._track_artist
                    self._track_album = _field(current, "album") or self._track_album
                    self._set_cover_from_current_path()
            if hasattr(self._player, 'get_queue'):
                q = self._player.get_queue()
                if q is not None:
                    self._queue = self._normalize_queue(q)
            if hasattr(self._player, 'state'):
                st = self._player.state
                if st:
                    self._is_playing = st == "playing"
                    self._playback_status = st
            if hasattr(self._player, 'duration'):
                d = self._player.duration
                if d:
                    self._duration = int(d)
            self._emit_state()
            return _ok("refresh")
        except Exception as e:
            logger.debug("refresh failed: %s", e)
            return _err("refresh", PLAYBACK_ERROR, str(e))

    # ── Playback commands ──

    @Slot(result=dict)
    def togglePlay(self):
        op = "togglePlay"
        self._begin_command(op)
        if not self._player:
            self._set_command_failure(op, NO_PLAYER_SERVICE)
            return _err(op, NO_PLAYER_SERVICE)
        try:
            if self._is_playing:
                if hasattr(self._player, 'pause'):
                    self._player.pause()
                    self._set_command_success(op)
                    return _ok(op, {"playing": False, "state_confirmed": False})
                self._set_command_failure(op, UNSUPPORTED)
                return _err(op, UNSUPPORTED)
            if hasattr(self._player, 'play_or_resume'):
                self._player.play_or_resume()
                self._set_command_success(op)
                return _ok(op, {"playing": True, "state_confirmed": False})
            if hasattr(self._player, 'resume'):
                self._player.resume()
                self._set_command_success(op)
                return _ok(op, {"playing": True, "state_confirmed": False})
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        except Exception as e:
            logger.warning("togglePlay failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(result=dict)
    def next(self):
        op = "next"
        self._begin_command(op)
        if not self._player:
            self._set_command_failure(op, NO_PLAYER_SERVICE)
            return _err(op, NO_PLAYER_SERVICE)
        try:
            if hasattr(self._player, 'play_next'):
                self._player.play_next()
                self._set_command_success(op)
                return _ok(op)
            if hasattr(self._player, 'next'):
                self._player.next()
                self._set_command_success(op)
                return _ok(op)
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        except Exception as e:
            logger.warning("next failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(result=dict)
    def previous(self):
        op = "previous"
        self._begin_command(op)
        if not self._player:
            self._set_command_failure(op, NO_PLAYER_SERVICE)
            return _err(op, NO_PLAYER_SERVICE)
        try:
            if hasattr(self._player, 'play_prev'):
                self._player.play_prev()
                self._set_command_success(op)
                return _ok(op)
            if hasattr(self._player, 'previous'):
                self._player.previous()
                self._set_command_success(op)
                return _ok(op)
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        except Exception as e:
            logger.warning("previous failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(int, result=dict)
    def seek(self, position: int):
        op = "seek"
        self._begin_command(op)
        if not self._player:
            self._set_command_failure(op, NO_PLAYER_SERVICE)
            return _err(op, NO_PLAYER_SERVICE)
        if self._duration <= 0:
            self._set_command_failure(op, UNKNOWN_DURATION)
            return _err(op, UNKNOWN_DURATION)
        pos = max(0, min(int(position), self._duration))
        try:
            if hasattr(self._player, 'seek'):
                self._player.seek(pos)
                self._position = pos
                self._set_command_success(op)
                self._emit_state()
                return _ok(op, {"requested_position": pos, "state_confirmed": False})
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        except Exception as e:
            logger.warning("seek failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(int, result=dict)
    def seekRelative(self, seconds: int):
        return self.seek(self._position + int(seconds))

    @Slot(int, result=dict)
    def setVolume(self, volume: int):
        op = "setVolume"
        self._begin_command(op)
        if not self._player:
            self._set_command_failure(op, NO_PLAYER_SERVICE)
            return _err(op, NO_PLAYER_SERVICE)
        vol = max(0, min(100, int(volume)))
        try:
            if hasattr(self._player, 'set_volume'):
                self._player.set_volume(vol)
                self._volume = vol
                self._muted = vol == 0
                self._set_command_success(op)
                self._emit_state()
                return _ok(op, {"volume": vol, "muted": self._muted, "state_confirmed": False})
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        except Exception as e:
            logger.warning("setVolume failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(result=dict)
    def toggleMute(self):
        op = "toggleMute"
        self._begin_command(op)
        if not self._player:
            self._set_command_failure(op, NO_PLAYER_SERVICE)
            return _err(op, NO_PLAYER_SERVICE)
        try:
            if not hasattr(self._player, 'set_volume'):
                self._set_command_failure(op, UNSUPPORTED)
                return _err(op, UNSUPPORTED)
            target = 0 if self._volume > 0 else (self._previous_volume or 80)
            self._player.set_volume(target)
            self._previous_volume = self._volume if self._volume > 0 else self._previous_volume
            self._volume = target
            self._muted = target == 0
            self._set_command_success(op)
            self._emit_state()
            return _ok(op, {"volume": target, "muted": self._muted, "state_confirmed": False})
        except Exception as e:
            logger.warning("toggleMute failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(result=dict)
    def toggleShuffle(self):
        op = "toggleShuffle"
        self._begin_command(op)
        if not self._player:
            self._set_command_failure(op, NO_PLAYER_SERVICE)
            return _err(op, NO_PLAYER_SERVICE)
        try:
            call = self._player_call("toggle_shuffle")
            if call:
                result = call()
                if result is not None:
                    self._shuffle_enabled = bool(result)
                    self._set_command_success(op)
                    self._emit_state()
                    return _ok(op, {"shuffle": self._shuffle_enabled, "state_confirmed": True})
                self._set_command_success(op)
                return _ok(op, {"state_confirmed": False})
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        except Exception as e:
            logger.warning("toggleShuffle failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(result=dict)
    def toggleRepeat(self):
        op = "toggleRepeat"
        self._begin_command(op)
        if not self._player:
            self._set_command_failure(op, NO_PLAYER_SERVICE)
            return _err(op, NO_PLAYER_SERVICE)
        try:
            call = self._player_call("toggle_repeat")
            if call:
                mode = call()
                if mode:
                    self._repeat_mode = str(mode)
                    self._set_command_success(op)
                    self._emit_state()
                    return _ok(op, {"repeat": self._repeat_mode, "state_confirmed": True})
                self._set_command_success(op)
                return _ok(op, {"state_confirmed": False})
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        except Exception as e:
            logger.warning("toggleRepeat failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    # ── Queue commands ──

    @Slot(str, result=dict)
    def enqueueSong(self, filepath: str):
        op = "enqueueSong"
        self._begin_command(op)
        if not filepath:
            self._set_command_failure(op, EMPTY_FILEPATH)
            return _err(op, EMPTY_FILEPATH)
        if not self._player:
            self._set_command_failure(op, NO_PLAYER_SERVICE)
            return _err(op, NO_PLAYER_SERVICE)
        try:
            if hasattr(self._player, 'enqueue'):
                self._player.enqueue([filepath], play_now=False)
                self._set_command_success(op)
                return _ok(op, {"queued": True})
            if hasattr(self._player, 'add_to_queue'):
                self._player.add_to_queue(filepath)
                self._set_command_success(op)
                return _ok(op, {"queued": True})
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        except Exception as e:
            logger.warning("enqueueSong failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(int, result=dict)
    def removeFromQueue(self, index: int):
        op = "removeFromQueue"
        self._begin_command(op)
        if not self._player:
            self._set_command_failure(op, NO_PLAYER_SERVICE)
            return _err(op, NO_PLAYER_SERVICE)
        if index < 0 or index >= len(self._queue):
            self._set_command_failure(op, INVALID_INDEX)
            return _err(op, INVALID_INDEX)
        try:
            if hasattr(self._player, 'remove_queue_item'):
                self._player.remove_queue_item(index)
                self._set_command_success(op)
                return _ok(op, {"index": index})
            if hasattr(self._player, 'remove_from_queue'):
                self._player.remove_from_queue(index)
                self._set_command_success(op)
                return _ok(op, {"index": index})
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        except Exception as e:
            logger.warning("removeFromQueue failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(result=dict)
    def clearQueue(self):
        op = "clearQueue"
        self._begin_command(op)
        if not self._player:
            self._set_command_failure(op, NO_PLAYER_SERVICE)
            return _err(op, NO_PLAYER_SERVICE)
        try:
            if hasattr(self._player, 'clear_queue'):
                self._player.clear_queue()
                self._set_command_success(op)
                return _ok(op)
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        except Exception as e:
            logger.warning("clearQueue failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(int, int, result=dict)
    def moveQueueItem(self, from_index: int, to_index: int):
        op = "moveQueueItem"
        self._begin_command(op)
        if not self._player:
            self._set_command_failure(op, NO_PLAYER_SERVICE)
            return _err(op, NO_PLAYER_SERVICE)
        if from_index < 0 or from_index >= len(self._queue):
            self._set_command_failure(op, INVALID_INDEX)
            return _err(op, INVALID_INDEX)
        if to_index < 0 or to_index >= len(self._queue):
            self._set_command_failure(op, INVALID_INDEX)
            return _err(op, INVALID_INDEX)
        try:
            if hasattr(self._player, 'move_queue_item'):
                self._player.move_queue_item(from_index, to_index)
                self._set_command_success(op)
                return _ok(op, {"from": from_index, "to": to_index})
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        except Exception as e:
            logger.warning("moveQueueItem failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(int, result=dict)
    def playQueueItem(self, index: int):
        op = "playQueueItem"
        self._begin_command(op)
        if not self._player:
            self._set_command_failure(op, NO_PLAYER_SERVICE)
            return _err(op, NO_PLAYER_SERVICE)
        if index < 0 or index >= len(self._queue):
            self._set_command_failure(op, INVALID_INDEX)
            return _err(op, INVALID_INDEX)
        try:
            if hasattr(self._player, 'play_queue_item'):
                self._player.play_queue_item(index)
                self._set_command_success(op)
                return _ok(op, {"index": index})
            self._set_command_failure(op, UNSUPPORTED)
            return _err(op, UNSUPPORTED)
        except Exception as e:
            logger.warning("playQueueItem failed: %s", e)
            self._set_command_failure(op, PLAYBACK_ERROR)
            return _err(op, PLAYBACK_ERROR)

    @Slot(result=dict)
    def clearHistory(self):
        op = "clearHistory"
        self._begin_command(op)
        self._history.clear()
        self._set_command_success(op)
        self._emit_state()
        return _ok(op)

    @Slot(int, result=dict)
    def playHistoryItem(self, index: int):
        op = "playHistoryItem"
        self._begin_command(op)
        if index < 0 or index >= len(self._history):
            self._set_command_failure(op, INVALID_INDEX)
            return _err(op, INVALID_INDEX)
        entry = self._history[index]
        internal_key = entry.get("history_id", "")
        ref = self._history_internal_refs.get(internal_key, {})
        fp = ref.get("filepath", "")
        if fp and self._player and hasattr(self._player, 'play'):
            self._player.play(fp)
            self._set_command_success(op)
            return _ok(op, {"history_id": internal_key})
        self._set_command_failure(op, UNSUPPORTED)
        return _err(op, UNSUPPORTED)

    def set_cover_from_path(self, filepath: str):
        self._cover_key = _cover_key_for_path(filepath)
        self.coverChanged.emit()
        self._emit_state()

    # ── Scoring helpers ──

    @Slot(result=int)
    def totalPlayed(self) -> int:
        return len(self._history)

    @Slot(result=int)
    def queueDuration(self) -> int:
        return sum(item.get("duration", 0) for item in self._queue)

    @Slot(result=dict)
    def playbackScore(self) -> dict:
        """Return a playback quality score based on real state."""
        score = 0
        if self._backend_available:
            score += 25
        if self._player and hasattr(self._player, 'get_queue'):
            score += 15
        if self._track_title and self._track_title != "—":
            score += 20
        if self._duration > 0:
            score += 10
        if self._player and hasattr(self._player, 'state'):
            score += 15
        if len(self._queue) > 0:
            score += 15
        return {
            "score": min(100, score),
            "has_backend": self._backend_available,
            "has_track": self._track_title != "—",
            "has_queue": len(self._queue) > 0,
            "has_position": self._position >= 0,
            "has_duration": self._duration > 0,
            "queue_count": len(self._queue),
            "history_count": len(self._history),
        }
