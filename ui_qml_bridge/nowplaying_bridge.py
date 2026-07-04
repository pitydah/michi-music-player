"""NowPlayingBridge — QML-facing playback state backed by PlayerService."""

from __future__ import annotations

import hashlib
import contextlib
from typing import Any

from PySide6.QtCore import QObject, Property, Signal, Slot


def _cover_key_for_path(filepath: str) -> str:
    if not filepath:
        return ""
    digest = hashlib.md5(filepath.encode()).hexdigest()[:12]
    return f"track_{digest}"


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


class NowPlayingBridge(QObject):
    """Expose current playback state and commands to QML.

    PlayerService remains the single command facade. This bridge mirrors its
    signals into stable QML properties and keeps an offline fallback so QML can
    still load in safe/test mode.
    """

    stateChanged = Signal()
    coverChanged = Signal()

    def __init__(self, player_service=None, parent=None):
        super().__init__(parent)
        self._player = player_service
        self._track_title = "—"
        self._track_artist = ""
        self._track_album = ""
        self._cover_key = ""
        self._is_playing = False
        self._position = 0
        self._duration = 0
        self._volume = 80
        self._muted = False
        self._source_type = "local_file"
        self._quality_label = ""
        self._repeat_mode = "none"
        self._shuffle_enabled = False
        self._queue: list[dict[str, Any]] = []
        self._history: list[dict[str, Any]] = []
        self._backend_available = False
        self._playback_status = "unavailable"
        self._error_message = ""
        self._last_command = ""
        self._last_command_ok = False
        self._safe_mode = False

        self._backend_available = self._player is not None
        self._playback_status = "idle" if self._backend_available else "unavailable"
        self._safe_mode = not self._backend_available

        self._connect_player()
        self.refresh()

    def _connect_player(self):
        if not self._player:
            return
        connections = (
            ("track_changed", self._on_track),
            ("state_changed", self._on_state),
            ("position_changed", self._on_position),
            ("duration_changed", self._on_duration),
            ("volume_changed", self._on_volume),
            ("queue_changed", self._on_queue),
        )
        for signal_name, slot in connections:
            signal = getattr(self._player, signal_name, None)
            if signal is None:
                continue
            with contextlib.suppress(Exception):
                signal.connect(slot)

    def _emit_state(self):
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

    def _on_track(self, title: str = "", artist: str = "", album: str = ""):
        # Push current track to history if it's not a duplicate
        if self._track_title and self._track_title != "—":
            last = self._history[-1] if self._history else {}
            if last.get("title") != self._track_title:
                self._history.append({
                    "title": self._track_title,
                    "artist": self._track_artist,
                    "album": self._track_album,
                })
                if len(self._history) > 50:
                    self._history.pop(0)
        current = getattr(self._player, "current", None) if self._player else None
        self._track_title = (
            title
            or _player_field(self._player, "current_title", "title")
            or _field(current, "title", "name")
            or "—"
        )
        self._track_artist = (
            artist
            or _player_field(self._player, "current_artist", "artist")
            or _field(current, "artist", "albumartist")
        )
        self._track_album = (
            album
            or _player_field(self._player, "current_album", "album")
            or _field(current, "album")
            or self._track_album
        )
        if self._player and hasattr(self._player, 'current'):
            current = self._player.current
            if current:
                fmt = getattr(current, 'format', '') or getattr(current, 'filepath', '').split('.')[-1] if '.' in getattr(current, 'filepath', '') else ''
                if fmt:
                    self._quality_label = fmt.upper()
                self._source_type = "radio" if getattr(current, 'source_type', '') == 'radio' else "local_file"
        self._set_cover_from_current_path()
        self._emit_state()

    def _on_state(self, state):
        normalized = str(state).lower()
        self._is_playing = normalized in {"playing", "resumed"}
        if normalized == "playing":
            self._playback_status = "playing"
        elif normalized in ("paused", "pause"):
            self._playback_status = "paused"
        elif normalized in ("stopped", "stop"):
            self._playback_status = "stopped"
        elif normalized in ("error", "failed"):
            self._playback_status = "error"
        self._emit_state()

    def _on_position(self, seconds: float):
        self._position = max(0, int(seconds or 0))
        self._emit_state()

    def _on_duration(self, seconds: float):
        self._duration = max(0, int(seconds or 0))
        self._emit_state()

    def _on_volume(self, volume: int):
        self._volume = max(0, min(100, int(volume)))
        self._muted = self._volume == 0
        self._emit_state()

    def _on_queue(self, queue):
        self._queue = list(queue or [])
        self._emit_state()

    @Slot()
    def refresh(self):
        if not self._player:
            self._emit_state()
            return
        state = getattr(self._player, "state", None)
        if state is not None:
            self._on_state(state)
        duration = getattr(self._player, "duration", None)
        if duration is not None:
            self._duration = max(0, int(duration or 0))
        get_queue = getattr(self._player, "get_queue", None)
        if callable(get_queue):
            try:
                self._queue = list(get_queue() or [])
            except Exception:
                self._queue = []
        current = getattr(self._player, "current", None)
        title = (
            _player_field(self._player, "current_title", "title")
            or _field(current, "title", "name")
        )
        artist = (
            _player_field(self._player, "current_artist", "artist")
            or _field(current, "artist", "albumartist")
        )
        album = (
            _player_field(self._player, "current_album", "album")
            or _field(current, "album")
        )
        if title:
            self._track_title = title
        if artist:
            self._track_artist = artist
        if album:
            self._track_album = album
        self._set_cover_from_current_path()
        self._emit_state()

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
    def coverKey(self):
        return self._cover_key

    @Property(str, notify=coverChanged)
    def coverPath(self):
        return self._cover_key

    @Property(bool, notify=stateChanged)
    def hasTrack(self):
        return self._track_title != "—" or bool(self._current_path())

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
    def sourceType(self):
        return self._source_type

    @Property(str, notify=stateChanged)
    def qualityLabel(self):
        return self._quality_label

    @Property(str, notify=stateChanged)
    def repeatMode(self):
        return self._repeat_mode

    @Property(bool, notify=stateChanged)
    def shuffleEnabled(self):
        return self._shuffle_enabled

    @Property("QVariantList", notify=stateChanged)
    def queue(self):
        return self._queue

    @Property("QVariantList", notify=stateChanged)
    def history(self):
        return self._history

    @Property(bool, notify=stateChanged)
    def backendAvailable(self):
        return self._backend_available

    @Property(str, notify=stateChanged)
    def playbackStatus(self):
        return self._playback_status

    @Property(str, notify=stateChanged)
    def errorMessage(self):
        return self._error_message

    @Property(str, notify=stateChanged)
    def lastCommand(self):
        return self._last_command

    @Property(bool, notify=stateChanged)
    def lastCommandOk(self):
        return self._last_command_ok

    @Property(bool, notify=stateChanged)
    def safeMode(self):
        return self._safe_mode

    @Property(bool, notify=stateChanged)
    def shuffleSupported(self):
        return self._player is not None and hasattr(self._player, 'toggle_shuffle')

    @Property(bool, notify=stateChanged)
    def repeatSupported(self):
        return self._player is not None and hasattr(self._player, 'toggle_repeat')

    @Slot()
    def togglePlay(self):
        self._last_command = "togglePlay"
        if self._player:
            if self._is_playing:
                call = self._player_call("pause")
            else:
                call = self._player_call("play_or_resume", "resume", "toggle")
            if call:
                call()
                self._last_command_ok = True
                self._playback_status = "playing" if not self._is_playing else "paused"
                self._error_message = ""
                self._emit_state()
                return
        if not self._backend_available:
            self._last_command_ok = False
            self._error_message = "Playback no disponible"
            self._emit_state()
            return

    @Slot()
    def next(self):
        self._last_command = "next"
        call = self._player_call("play_next", "next")
        if call:
            call()
            self._last_command_ok = True
        else:
            self._last_command_ok = False
            self._error_message = "No se puede avanzar — backend no disponible"
        self._emit_state()

    @Slot()
    def previous(self):
        self._last_command = "previous"
        call = self._player_call("play_prev", "previous")
        if call:
            call()
            self._last_command_ok = True
        else:
            self._last_command_ok = False
            self._error_message = "No se puede retroceder — backend no disponible"
        self._emit_state()

    @Slot(int)
    def setVolume(self, volume: int):
        self._last_command = "setVolume"
        self._volume = max(0, min(100, int(volume)))
        self._muted = self._volume == 0
        call = self._player_call("set_volume")
        if call:
            call(self._volume)
            self._last_command_ok = True
        else:
            self._last_command_ok = False
        self._emit_state()

    @Slot()
    def toggleMute(self):
        self._last_command = "toggleMute"
        self._muted = not self._muted
        call = self._player_call("set_volume")
        if call:
            call(0 if self._muted else self._volume)
            self._last_command_ok = True
        else:
            self._last_command_ok = False
        self._emit_state()

    @Slot(int)
    def seek(self, position: int):
        self._last_command = "seek"
        if self._duration <= 0:
            self._last_command_ok = False
            self._error_message = "No se puede buscar — duración desconocida"
            self._emit_state()
            return
        self._position = max(0, min(int(position), self._duration))
        call = self._player_call("seek")
        if call:
            call(self._position)
            self._last_command_ok = True
            self._error_message = ""
        else:
            self._last_command_ok = False
        self._emit_state()

    @Slot(int)
    def seekRelative(self, seconds: int):
        self.seek(self._position + int(seconds))

    @Slot()
    def toggleShuffle(self):
        self._last_command = "toggleShuffle"
        call = self._player_call("toggle_shuffle")
        if call:
            result = call()
            if result is not None:
                self._shuffle_enabled = bool(result)
            else:
                self._shuffle_enabled = not self._shuffle_enabled
            self._last_command_ok = True
        else:
            self._last_command_ok = False
            self._error_message = "Aleatorio no soportado por el backend"
        self._emit_state()

    @Slot()
    def toggleRepeat(self):
        self._last_command = "toggleRepeat"
        call = self._player_call("toggle_repeat")
        if call:
            mode = call()
            if mode:
                self._repeat_mode = str(mode)
            else:
                self._cycle_repeat_mode()
            self._last_command_ok = True
        else:
            self._last_command_ok = False
            self._error_message = "Repetición no soportada por el backend"
        self._emit_state()

    def _cycle_repeat_mode(self):
        modes = ["none", "all", "one"]
        idx = modes.index(self._repeat_mode) if self._repeat_mode in modes else 0
        self._repeat_mode = modes[(idx + 1) % len(modes)]

    def set_cover_from_path(self, filepath: str):
        self._cover_key = _cover_key_for_path(filepath)
        self.coverChanged.emit()
        self._emit_state()
