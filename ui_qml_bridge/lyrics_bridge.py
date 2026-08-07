"""LyricsBridge — thin adapter over the canonical LyricsService.

QML emits intention; the bridge validates, converts types and delegates to the
injected ``LyricsService`` (``resolve``/``search_manual``/``save_local``/
``invalidate_identity``). The bridge constructs no HTTP client and keeps no
second cache: caching lives in the service. Async search still runs through
the WorkerManager; results arrive via the callback and are exposed through the
same QML properties/slots as before.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer

if TYPE_CHECKING:
    from core.worker_manager import WorkerManager
    from core.lyrics.models import TrackIdentity
    from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge

logger = logging.getLogger("michi.lyrics")


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


def _result_to_dict(result) -> dict:
    """Map a canonical LyricsOperationResult to the legacy bridge dict shape."""
    if result is None:
        return {"ok": False, "error": "NOT_FOUND"}
    if not result.ok:
        code = getattr(result, "code", None)
        error = code.value if hasattr(code, "value") else (code or "NOT_FOUND")
        if error == "not_found":
            error = "NOT_FOUND"
        return {"ok": False, "error": error}
    doc = result.document
    if doc is None:
        return {"ok": False, "error": "NOT_FOUND"}
    return {
        "ok": True,
        "lyrics": doc.plain_text or "",
        "synced_lyrics": doc.synced_text or "",
        "source": (doc.source.value if hasattr(doc.source, "value") else str(doc.source))
        or "LRCLIB",
    }


def _identity_for(title: str, artist: str, album: str = "", duration: int = 0,
                  filepath: str = "") -> "TrackIdentity":
    from core.lyrics.models import TrackIdentity
    return TrackIdentity(
        title=title, artist=artist, album=album,
        duration_ms=int(duration) * 1000, filepath=filepath,
    )


def _search_impl(service, title: str, artist: str, album: str = "",
                 duration: int = 0) -> dict:
    """Canonical resolve — runs in the worker thread."""
    if service is None:
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
    identity = _identity_for(title, artist, album, duration)
    return _result_to_dict(service.resolve(identity))


def _search_manual_impl(service, query: str) -> dict:
    """Canonical free-text search — runs in the worker thread."""
    if service is None:
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
    return _result_to_dict(service.search_manual(query))


class LyricsBridge(QObject):
    dataChanged = Signal()

    def __init__(self, worker_manager: WorkerManager | None = None,
                 nowplaying_bridge: NowPlayingBridge | None = None,
                 lyrics_service=None, parent=None):
        super().__init__(parent)
        assert worker_manager is not None, "LyricsBridge: worker_manager is REQUIRED"
        self._wm = worker_manager
        self._np_bridge = nowplaying_bridge
        self._lyrics_svc = lyrics_service

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

        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.setInterval(15000)
        self._timeout_timer.timeout.connect(self._on_timeout)

        if self._np_bridge:
            from contextlib import suppress
            with suppress(AttributeError):
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
                lambda: _search_impl(self._lyrics_svc, title, artist, album, duration),
                on_done=lambda r: self._on_search_complete(search_id, r),
                cancellable=True, owner="lyrics",
            )
        else:
            QTimer.singleShot(0, lambda: self._sync_fallback(title, artist, album, duration))

        return {"ok": True}

    def _sync_fallback(self, title: str, artist: str, album: str = "", duration: int = 0):
        sid = self._active_search_id
        result = _search_impl(self._lyrics_svc, title, artist, album, duration)
        self._on_search_complete(sid, result)

    @Slot(str, result=dict)
    def searchManual(self, query: str):
        """Manual search by free-text query — delegates to the service."""
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

        if self._wm and hasattr(self._wm, 'run_task'):
            self._wm.run_task(
                f"lyrics_manual_{search_id}",
                lambda: _search_manual_impl(self._lyrics_svc, query),
                on_done=lambda r: self._on_search_complete(search_id, r),
                cancellable=True, owner="lyrics",
            )
        else:
            QTimer.singleShot(0, lambda: self._on_search_complete(search_id, _search_manual_impl(self._lyrics_svc, query)))
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
        return {"ok": True, "refreshed": True}

    @Slot(result=dict)
    def clearCacheForCurrentTrack(self):
        if self._lyrics_svc is None:
            return {"ok": True}
        try:
            identity = _identity_for(
                self._current_title, self._current_artist,
                self._current_album, self._current_duration,
            )
            self._lyrics_svc.invalidate_identity(identity)
        except Exception as exc:
            logger.warning("clearCacheForCurrentTrack failed: %s", exc)
        return {"ok": True}

    @Slot(str, result=dict)
    def saveLocalLyrics(self, text: str):
        self._lyrics = text
        self._synced_lyrics = []
        self._status = "done"
        self._source = "local"
        self.dataChanged.emit()
        audio_path = getattr(self._np_bridge, "currentFilePath", "") or ""
        if not isinstance(audio_path, str) or not audio_path:
            return {"ok": True, "source": "local"}
        if self._lyrics_svc is None:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
        try:
            from core.lyrics.models import LyricsDocument, LyricsSource

            has_timestamps = "[" in text and "]" in text
            title = getattr(self._np_bridge, 'trackTitle', '') or ''
            artist = getattr(self._np_bridge, 'trackArtist', '') or ''
            identity = _identity_for(title, artist, filepath=audio_path)
            doc = LyricsDocument(
                identity=identity,
                plain_text="" if has_timestamps else text,
                synced_text=text if has_timestamps else "",
                source=LyricsSource.MANUAL,
            )
            result = self._lyrics_svc.save_local(audio_path, doc)
            if result.ok:
                path = result.details.get("path", "")
                return {
                    "ok": True,
                    "path": path,
                    "embedded": bool(result.details.get("embedded", False)),
                    "source": "local",
                }
            code = getattr(result, "code", None)
            error = code.value if hasattr(code, "value") else "SAVE_FAILED"
            return {"ok": False, "error": error or "SAVE_FAILED", "source": "local"}
        except Exception as exc:
            logger.warning("saveLocalLyrics: sidecar write failed: %s", exc)
            return {"ok": False, "error": str(exc), "source": "local"}

    def getActiveLine(self, position_ms: float) -> int | None:
        """Return index of active synced line for a given position in ms."""
        if not self._synced_lyrics:
            return None
        secs = position_ms / 1000.0
        for i, line in enumerate(self._synced_lyrics):
            if line["time"] > secs:
                return max(0, i - 1)
        return len(self._synced_lyrics) - 1 if self._synced_lyrics else None
