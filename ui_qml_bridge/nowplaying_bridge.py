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


def _err(error_code: str, message: str = "") -> dict:
    return {"ok": False, "error_code": error_code, "message": message or error_code}


def _ok(data: dict | None = None) -> dict:
    result: dict = {"ok": True}
    if data:
        result.update(data)
    return result


class NowPlayingBridge(QObject):
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
        self._previous_volume = 80
        self._muted = False
        self._source_type = "local_file"
        self._quality_label = ""
        self._repeat_mode = "none"
        self._shuffle_enabled = False
        self._queue: list[dict[str, Any]] = []
        self._history: list[dict[str, Any]] = []
        self._backend_available = self._player is not None
        self._playback_status = "idle" if self._backend_available else "unavailable"
        self._error_message = ""
        self._last_command = ""
        self._last_command_ok = False
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
        ):
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

    # ── Signal handlers (update state from backend) ──

    def _on_track(self, title="", artist="", album=""):
        self._track_title = title or ""
        self._track_artist = artist or ""
        self._track_album = album or ""
        self._set_cover_from_current_path()
        self._emit_state()

    def _on_state(self, state: str):
        self._is_playing = state == "playing"
        self._playback_status = state
        self._error_message = ""
        self._emit_state()

    def _on_position(self, pos: float):
        self._position = int(pos)
        self._emit_state()

    def _on_duration(self, dur: float):
        self._duration = int(dur)
        self._emit_state()

    def _on_volume(self, vol: int):
        self._volume = vol
        self._muted = vol == 0
        self._emit_state()

    def _on_queue(self, q: list):
        self._queue = list(q) if q else []
        self._emit_state()

    def _on_error(self, msg: str):
        self._error_message = msg
        self._emit_state()

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

    # ── Data loading ──

    @Slot(result=dict)
    def refresh(self):
        if not self._player:
            return _err(NO_PLAYER_SERVICE)
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
                    self._queue = list(q)
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
            return _ok()
        except Exception as e:
            logger.debug("refresh failed: %s", e)
            return _err(PLAYBACK_ERROR, str(e))

    # ── Playback commands ──

    @Slot(result=dict)
    def togglePlay(self):
        self._last_command = "togglePlay"
        if not self._player:
            return _err(NO_PLAYER_SERVICE)
        try:
            if self._is_playing:
                if hasattr(self._player, 'pause'):
                    self._player.pause()
                    return _ok({"playing": False})
                return _err(UNSUPPORTED, "pause not available")
            if hasattr(self._player, 'play_or_resume'):
                self._player.play_or_resume()
                return _ok({"playing": True})
            if hasattr(self._player, 'resume'):
                self._player.resume()
                return _ok({"playing": True})
            return _err(UNSUPPORTED, "play/resume not available")
        except Exception as e:
            logger.warning("togglePlay failed: %s", e)
            return _err(PLAYBACK_ERROR, str(e))

    @Slot(result=dict)
    def next(self):
        self._last_command = "next"
        if not self._player:
            return _err(NO_PLAYER_SERVICE)
        try:
            if hasattr(self._player, 'play_next'):
                self._player.play_next()
                return _ok()
            if hasattr(self._player, 'next'):
                self._player.next()
                return _ok()
            return _err(UNSUPPORTED, "next not available")
        except Exception as e:
            logger.warning("next failed: %s", e)
            return _err(PLAYBACK_ERROR, str(e))

    @Slot(result=dict)
    def previous(self):
        self._last_command = "previous"
        if not self._player:
            return _err(NO_PLAYER_SERVICE)
        try:
            if hasattr(self._player, 'play_prev'):
                self._player.play_prev()
                return _ok()
            if hasattr(self._player, 'previous'):
                self._player.previous()
                return _ok()
            return _err(UNSUPPORTED, "previous not available")
        except Exception as e:
            logger.warning("previous failed: %s", e)
            return _err(PLAYBACK_ERROR, str(e))

    @Slot(int, result=dict)
    def seek(self, position: int):
        self._last_command = "seek"
        if not self._player:
            return _err(NO_PLAYER_SERVICE)
        if self._duration <= 0:
            return _err(UNKNOWN_DURATION)
        pos = max(0, min(int(position), self._duration))
        try:
            if hasattr(self._player, 'seek'):
                self._player.seek(pos)
                self._position = pos
                self._emit_state()
                return _ok({"position": pos})
            return _err(UNSUPPORTED, "seek not available")
        except Exception as e:
            logger.warning("seek failed: %s", e)
            return _err(PLAYBACK_ERROR, str(e))

    @Slot(int, result=dict)
    def seekRelative(self, seconds: int):
        return self.seek(self._position + int(seconds))

    @Slot(int, result=dict)
    def setVolume(self, volume: int):
        self._last_command = "setVolume"
        if not self._player:
            return _err(NO_PLAYER_SERVICE)
        vol = max(0, min(100, int(volume)))
        try:
            if hasattr(self._player, 'set_volume'):
                self._player.set_volume(vol)
                self._volume = vol
                self._muted = vol == 0
                self._emit_state()
                return _ok({"volume": vol, "muted": self._muted})
            return _err(UNSUPPORTED, "volume not available")
        except Exception as e:
            logger.warning("setVolume failed: %s", e)
            return _err(PLAYBACK_ERROR, str(e))

    @Slot(result=dict)
    def toggleMute(self):
        self._last_command = "toggleMute"
        if not self._player:
            return _err(NO_PLAYER_SERVICE)
        try:
            if not hasattr(self._player, 'set_volume'):
                return _err(UNSUPPORTED, "volume not available")
            target = 0 if self._volume > 0 else (self._previous_volume or 80)
            self._player.set_volume(target)
            self._previous_volume = self._volume if self._volume > 0 else self._previous_volume
            self._volume = target
            self._muted = target == 0
            self._emit_state()
            return _ok({"volume": target, "muted": self._muted})
        except Exception as e:
            logger.warning("toggleMute failed: %s", e)
            return _err(PLAYBACK_ERROR, str(e))

    @Slot(result=dict)
    def toggleShuffle(self):
        self._last_command = "toggleShuffle"
        if not self._player:
            return _err(NO_PLAYER_SERVICE)
        try:
            call = self._player_call("toggle_shuffle")
            if call:
                result = call()
                if result is not None:
                    self._shuffle_enabled = bool(result)
                    self._emit_state()
                    return _ok({"shuffle": self._shuffle_enabled, "state_confirmed": True})
                return _ok({"state_confirmed": False})
            return _err(UNSUPPORTED, "shuffle not available")
        except Exception as e:
            logger.warning("toggleShuffle failed: %s", e)
            return _err(PLAYBACK_ERROR, str(e))

    @Slot(result=dict)
    def toggleRepeat(self):
        self._last_command = "toggleRepeat"
        if not self._player:
            return _err(NO_PLAYER_SERVICE)
        try:
            call = self._player_call("toggle_repeat")
            if call:
                mode = call()
                if mode:
                    self._repeat_mode = str(mode)
                    self._emit_state()
                    return _ok({"repeat": self._repeat_mode, "state_confirmed": True})
                return _ok({"state_confirmed": False})
            return _err(UNSUPPORTED, "repeat not available")
        except Exception as e:
            logger.warning("toggleRepeat failed: %s", e)
            return _err(PLAYBACK_ERROR, str(e))

    # ── Queue commands ──

    @Slot(str, result=dict)
    def enqueueSong(self, filepath: str):
        self._last_command = "enqueueSong"
        if not filepath:
            return _err(INVALID_POSITION, "empty filepath")
        if not self._player:
            return _err(NO_PLAYER_SERVICE)
        try:
            if hasattr(self._player, 'enqueue'):
                self._player.enqueue([filepath], play_now=False)
                return _ok({"filepath": filepath})
            if hasattr(self._player, 'add_to_queue'):
                self._player.add_to_queue(filepath)
                return _ok({"filepath": filepath})
            return _err(UNSUPPORTED, "queue not available")
        except Exception as e:
            logger.warning("enqueueSong failed: %s", e)
            return _err(PLAYBACK_ERROR, str(e))

    @Slot(int, result=dict)
    def removeFromQueue(self, index: int):
        self._last_command = "removeFromQueue"
        if not self._player:
            return _err(NO_PLAYER_SERVICE)
        if index < 0 or index >= len(self._queue):
            return _err(INVALID_INDEX, f"index {index} out of range")
        try:
            if hasattr(self._player, 'remove_queue_item'):
                self._player.remove_queue_item(index)
                return _ok({"index": index})
            if hasattr(self._player, 'remove_from_queue'):
                self._player.remove_from_queue(index)
                return _ok({"index": index})
            return _err(UNSUPPORTED, "remove from queue not available")
        except Exception as e:
            logger.warning("removeFromQueue failed: %s", e)
            return _err(PLAYBACK_ERROR, str(e))

    @Slot(result=dict)
    def clearQueue(self):
        self._last_command = "clearQueue"
        if not self._player:
            return _err(NO_PLAYER_SERVICE)
        try:
            if hasattr(self._player, 'clear_queue'):
                self._player.clear_queue()
                return _ok()
            if hasattr(self._player, 'stop'):
                self._player.stop()
                return _ok()
            return _err(UNSUPPORTED, "clear queue not available")
        except Exception as e:
            logger.warning("clearQueue failed: %s", e)
            return _err(PLAYBACK_ERROR, str(e))

    @Slot(int, int, result=dict)
    def moveQueueItem(self, from_index: int, to_index: int):
        self._last_command = "moveQueueItem"
        if not self._player:
            return _err(NO_PLAYER_SERVICE)
        if from_index < 0 or from_index >= len(self._queue):
            return _err(INVALID_INDEX, f"from_index {from_index} out of range")
        if to_index < 0 or to_index >= len(self._queue):
            return _err(INVALID_INDEX, f"to_index {to_index} out of range")
        try:
            if hasattr(self._player, 'move_queue_item'):
                self._player.move_queue_item(from_index, to_index)
                return _ok({"from": from_index, "to": to_index})
            return _err(UNSUPPORTED, "move queue item not available")
        except Exception as e:
            logger.warning("moveQueueItem failed: %s", e)
            return _err(PLAYBACK_ERROR, str(e))

    @Slot(int, result=dict)
    def playQueueItem(self, index: int):
        self._last_command = "playQueueItem"
        if not self._player:
            return _err(NO_PLAYER_SERVICE)
        if index < 0 or index >= len(self._queue):
            return _err(INVALID_INDEX, f"index {index} out of range")
        try:
            if hasattr(self._player, 'play_queue_item'):
                self._player.play_queue_item(index)
                return _ok({"index": index})
            if hasattr(self._player, 'play'):
                item = self._queue[index]
                fp = item.get("filepath", "") if isinstance(item, dict) else ""
                if fp:
                    self._player.play(fp)
                    return _ok({"index": index, "filepath": fp})
            return _err(UNSUPPORTED, "play queue item not available")
        except Exception as e:
            logger.warning("playQueueItem failed: %s", e)
            return _err(PLAYBACK_ERROR, str(e))

    def set_cover_from_path(self, filepath: str):
        self._cover_key = _cover_key_for_path(filepath)
        self.coverChanged.emit()
        self._emit_state()
