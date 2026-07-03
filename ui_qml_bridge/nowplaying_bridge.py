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
        current = getattr(self._player, "current", None) if self._player else None
        self._track_title = title or _field(current, "title", "name") or "—"
        self._track_artist = artist or _field(current, "artist", "albumartist")
        self._track_album = album or _field(current, "album") or self._track_album
        self._set_cover_from_current_path()
        self._emit_state()

    def _on_state(self, state):
        normalized = str(state).lower()
        self._is_playing = normalized in {"playing", "resumed"}
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
        title = _field(current, "title", "name")
        artist = _field(current, "artist", "albumartist")
        album = _field(current, "album")
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

    @Slot()
    def togglePlay(self):
        if self._player:
            if self._is_playing:
                call = self._player_call("pause")
            else:
                call = self._player_call("play_or_resume", "resume", "toggle")
            if call:
                call()
                return
        self._is_playing = not self._is_playing
        self._emit_state()

    @Slot()
    def next(self):
        call = self._player_call("play_next", "next")
        if call:
            call()
        self._emit_state()

    @Slot()
    def previous(self):
        call = self._player_call("play_prev", "previous")
        if call:
            call()
        self._emit_state()

    @Slot(int)
    def setVolume(self, volume: int):
        self._volume = max(0, min(100, int(volume)))
        self._muted = self._volume == 0
        call = self._player_call("set_volume")
        if call:
            call(self._volume)
        self._emit_state()

    @Slot()
    def toggleMute(self):
        self._muted = not self._muted
        call = self._player_call("set_volume")
        if call:
            call(0 if self._muted else self._volume)
        self._emit_state()

    @Slot(int)
    def seek(self, position: int):
        self._position = max(0, min(int(position), self._duration or int(position)))
        call = self._player_call("seek")
        if call:
            call(self._position)
        self._emit_state()

    @Slot(int)
    def seekRelative(self, seconds: int):
        self.seek(self._position + int(seconds))

    @Slot()
    def toggleShuffle(self):
        self._shuffle_enabled = not self._shuffle_enabled
        self._emit_state()

    @Slot()
    def toggleRepeat(self):
        modes = ["none", "one", "all"]
        idx = modes.index(self._repeat_mode) if self._repeat_mode in modes else 0
        self._repeat_mode = modes[(idx + 1) % len(modes)]
        self._emit_state()

    def set_cover_from_path(self, filepath: str):
        self._cover_key = _cover_key_for_path(filepath)
        self.coverChanged.emit()
        self._emit_state()
