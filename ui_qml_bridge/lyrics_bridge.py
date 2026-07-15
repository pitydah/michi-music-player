"""LyricsBridge — real LRCLIB lyrics with async search, cache, timeout, cancel.

No synchronous HTTP in QML thread. Uses WorkerManager when available.
Returns dict ok/error. Caches by title+artist+album+duration.
"""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer

if TYPE_CHECKING:
    from core.worker_manager import WorkerManager
    from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge

logger = logging.getLogger("michi.lyrics")

_CACHE_MAX = 50


def _make_cache_key(title: str, artist: str, album: str = "", duration: int = 0) -> str:
    return f"{title}||{artist}||{album}||{duration}"


def _search_impl(title: str, artist: str, album: str = "", duration: int = 0) -> dict:
    """Actual LRCLIB search — runs in worker thread."""
    from lyrics.lrclib_client import LrcLibClient
    client = LrcLibClient()
    result = client.get_lyrics(title, artist, album, float(duration))
    if not result:
        return {"ok": False, "error": "NOT_FOUND"}
    plain = getattr(result, 'plain_lyrics', '') or result.get("plainLyrics", "") if isinstance(result, dict) else ""
    synced = getattr(result, 'synced_lyrics', '') or result.get("syncedLyrics", "") if isinstance(result, dict) else ""
    source = "LRCLIB"
    return {
        "ok": True,
        "lyrics": plain,
        "synced_lyrics": synced,
        "source": source,
    }


def _parse_lrc(text: str) -> list[dict]:
    lines = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("[") and "]" in line:
            try:
                close = line.index("]")
                ts = line[1:close]
                txt = line[close + 1:].strip()
                minutes, seconds = ts.split(":")
                secs = int(minutes) * 60 + float(seconds)
                lines.append({"time": secs, "text": txt})
            except (ValueError, IndexError):
                lines.append({"time": 0, "text": line})
        else:
            lines.append({"time": 0, "text": line})
    return lines


class LyricsBridge(QObject):
    dataChanged = Signal()

    def __init__(self, worker_manager: WorkerManager | None = None, nowplaying_bridge: NowPlayingBridge | None = None, parent=None):
        super().__init__(parent)
        assert worker_manager is not None, "LyricsBridge: worker_manager is REQUIRED"
        self._wm = worker_manager
        self._np_bridge = nowplaying_bridge

        self._lyrics = ""
        self._synced_lyrics: list[dict] = []
        self._source = ""
        self._status = "idle"
        self._error_message = ""
        self._current_title = ""
        self._current_artist = ""
        self._current_album = ""
        self._current_duration = 0

        self._search_counter = 0
        self._active_search_id = 0
        self._cache: dict[str, dict] = {}
        self._cache_order: list[str] = []

        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.setInterval(15000)
        self._timeout_timer.timeout.connect(self._on_timeout)

        if self._np_bridge:
            from contextlib import suppress
            with suppress(Exception):
                self._np_bridge.trackChanged.connect(self._on_track_changed)

    # ── Properties ──

    @Property(str, notify=dataChanged)
    def lyrics(self) -> str:
        return self._lyrics

    @Property("QVariantList", notify=dataChanged)
    def syncedLyrics(self) -> list[dict]:
        return self._synced_lyrics

    @Property(str, notify=dataChanged)
    def source(self) -> str:
        return self._source

    @Property(str, notify=dataChanged)
    def status(self) -> str:
        return self._status

    @Property(str, notify=dataChanged)
    def errorMessage(self) -> str:
        return self._error_message

    @Property(str, notify=dataChanged)
    def currentTitle(self) -> str:
        return self._current_title

    @Property(str, notify=dataChanged)
    def currentArtist(self) -> str:
        return self._current_artist

    @Property(bool, notify=dataChanged)
    def hasSyncedLyrics(self) -> bool:
        return len(self._synced_lyrics) > 0

    # ── Private ──

    def _trim_cache(self):
        while len(self._cache) > _CACHE_MAX:
            oldest = self._cache_order.pop(0)
            self._cache.pop(oldest, None)

    def _set_result(self, status: str, lyrics: str = "", synced: str = "",
                    source: str = "", error: str = ""):
        self._status = status
        self._lyrics = lyrics
        self._source = source
        self._error_message = error
        if synced:
            self._synced_lyrics = _parse_lrc(synced)
        else:
            self._synced_lyrics = []
        self.dataChanged.emit()

    def _on_search_complete(self, search_id: int, result: dict):
        if search_id != self._active_search_id:
            logger.debug("Lyrics: ignoring stale search #%d (active: #%d)", search_id, self._active_search_id)
            return
        self._timeout_timer.stop()
        if result.get("ok"):
            plain = result.get("lyrics", "")
            synced = result.get("synced_lyrics", "")
            lrc = _parse_lrc(synced) if synced else []
            self._synced_lyrics = lrc
            self._lyrics = plain
            self._source = result.get("source", "LRCLIB")
            self._status = "done"
            # Cache
            key = _make_cache_key(self._current_title, self._current_artist,
                                  self._current_album, self._current_duration)
            self._cache[key] = {
                "lyrics": plain, "synced_lyrics": synced,
                "source": self._source, "timestamp": time.time(),
            }
            self._cache_order.append(key)
            self._trim_cache()
        else:
            err = result.get("error", "NOT_FOUND")
            if err == "NOT_FOUND":
                self._set_result("not_found")
            else:
                self._set_result("error", error=err)
        self.dataChanged.emit()

    def _on_timeout(self):
        if self._status == "searching":
            self._set_result("error", error="TIMEOUT")

    def _on_track_changed(self):
        if self._np_bridge:
            title = getattr(self._np_bridge, 'trackTitle', '') or ''
            artist = getattr(self._np_bridge, 'trackArtist', '') or ''
            if title and artist and (title != self._current_title or artist != self._current_artist):
                self.searchCurrentTrack()

    # ── Public API ──

    @Slot(result=dict)
    def searchCurrentTrack(self):
        if not self._np_bridge:
            return {"ok": False, "error": "NO_NOWPLAYING_BRIDGE"}
        title = getattr(self._np_bridge, 'trackTitle', '') or ''
        artist = getattr(self._np_bridge, 'trackArtist', '') or ''
        album = getattr(self._np_bridge, 'trackAlbum', '') or ''
        duration = getattr(self._np_bridge, 'trackDuration', 0) or 0
        return self.search(title, artist, album, duration)

    @Slot(str, str, str, int, result=dict)
    def search(self, title: str, artist: str, album: str = "", duration: int = 0):
        self._current_title = title
        self._current_artist = artist
        self._current_album = album
        self._current_duration = duration

        # Check cache
        key = _make_cache_key(title, artist, album, duration)
        cached = self._cache.get(key)
        if cached:
            logger.debug("Lyrics: cache hit for '%s'", title)
            lrc = _parse_lrc(cached.get("synced_lyrics", "")) if cached.get("synced_lyrics") else []
            self._synced_lyrics = lrc
            self._lyrics = cached.get("lyrics", "")
            self._source = cached.get("source", "LRCLIB")
            self._status = "done"
            self._error_message = ""
            self.dataChanged.emit()
            return {"ok": True, "cached": True}

        self._search_counter += 1
        self._active_search_id = self._search_counter
        self._status = "searching"
        self._error_message = ""
        self.dataChanged.emit()
        self._timeout_timer.start()

        if self._wm and hasattr(self._wm, 'run_task'):
            search_id = self._search_counter
            self._wm.run_task(
                f"lyrics_{search_id}",
                lambda: _search_impl(title, artist, album, duration),
                on_done=lambda r: self._on_search_complete(search_id, r),
                cancellable=True, owner="lyrics",
            )
        else:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._sync_fallback(title, artist, album, duration))

        return {"ok": True}

    def _sync_fallback(self, title: str, artist: str, album: str = "", duration: int = 0):
        sid = self._active_search_id
        result = _search_impl(title, artist, album, duration)
        self._on_search_complete(sid, result)

    @Slot(str, result=dict)
    def searchManual(self, query: str):
        """Manual search by free-text query."""
        if not query:
            return {"ok": False, "error": "EMPTY_QUERY"}
        self._current_title = query
        self._current_artist = ""
        self._current_album = ""
        self._current_duration = 0

        self._search_counter += 1
        self._active_search_id = self._search_counter
        self._status = "searching"
        self._error_message = ""
        self.dataChanged.emit()
        self._timeout_timer.start()

        search_id = self._search_counter

        def search_manual_impl(q: str) -> dict:
            from lyrics.lrclib_client import search_lyrics
            result = search_lyrics(q)
            if not result:
                return {"ok": False, "error": "NOT_FOUND"}
            plain = result.get("plainLyrics", result.get("lyrics", "")) or ""
            synced = result.get("syncedLyrics", "") or ""
            source = result.get("source", "LRCLIB")
            return {"ok": True, "lyrics": plain, "synced_lyrics": synced, "source": source}

        if self._wm and hasattr(self._wm, 'run_task'):
            self._wm.run_task(
                f"lyrics_manual_{search_id}",
                lambda: search_manual_impl(query),
                on_done=lambda r: self._on_search_complete(search_id, r),
                cancellable=True, owner="lyrics",
            )
        else:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._on_search_complete(search_id, search_manual_impl(query)))
        return {"ok": True}

    @Slot()
    def cancelSearch(self):
        self._active_search_id = 0
        self._timeout_timer.stop()
        if self._status == "searching":
            self._set_result("idle")

    @Slot(result=dict)
    def refresh(self):
        if self._current_title:
            return self.search(self._current_title, self._current_artist,
                              self._current_album, self._current_duration)
        return {"ok": True}

    @Slot(result=dict)
    def clearCacheForCurrentTrack(self):
        key = _make_cache_key(self._current_title, self._current_artist,
                              self._current_album, self._current_duration)
        self._cache.pop(key, None)
        self._cache_order = [k for k in self._cache_order if k != key]
        return {"ok": True}

    @Slot(str, result=dict)
    def saveLocalLyrics(self, text: str):
        self._lyrics = text
        self._synced_lyrics = []
        self._status = "done"
        self._source = "local"
        self.dataChanged.emit()
        return {"ok": True}

    def getActiveLine(self, position_ms: float) -> int | None:
        """Return index of active synced line for a given position in ms."""
        if not self._synced_lyrics:
            return None
        secs = position_ms / 1000.0
        for i, line in enumerate(self._synced_lyrics):
            if line["time"] > secs:
                return max(0, i - 1)
        return len(self._synced_lyrics) - 1 if self._synced_lyrics else None
