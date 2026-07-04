"""LyricsBridge — connects QML Lyrics page to real LRCLIB lyrics service."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging

logger = logging.getLogger("michi.lyrics")


class LyricsBridge(QObject):
    dataChanged = Signal()

    def __init__(self, worker_manager=None, nowplaying_bridge=None, parent=None):
        super().__init__(parent)
        self._worker_manager = worker_manager
        self._np_bridge = nowplaying_bridge
        self._lyrics = ""
        self._synced_lyrics = []
        self._source = ""
        self._status = "idle"
        self._error_message = ""
        self._current_title = ""
        self._current_artist = ""
        self._search_counter = 0

    @Property(str, notify=dataChanged)
    def lyrics(self):
        return self._lyrics

    @Property("QVariantList", notify=dataChanged)
    def syncedLyrics(self):
        return self._synced_lyrics

    @Property(str, notify=dataChanged)
    def source(self):
        return self._source

    @Property(str, notify=dataChanged)
    def status(self):
        return self._status

    @Property(str, notify=dataChanged)
    def errorMessage(self):
        return self._error_message

    @Slot(str, str)
    def search(self, title: str, artist: str):
        self._current_title = title
        self._current_artist = artist
        self._status = "searching"
        self.dataChanged.emit()
        try:
            from lyrics.lrclib_client import search_lyrics
            result = search_lyrics(title, artist)
            if result:
                self._lyrics = result.get("plainLyrics", result.get("lyrics", "")) or ""
                synced = result.get("syncedLyrics", "")
                if synced:
                    self._synced_lyrics = self._parse_synced(synced)
                else:
                    self._synced_lyrics = []
                self._source = result.get("source", "LRCLIB")
                self._status = "done"
            else:
                self._lyrics = ""
                self._synced_lyrics = []
                self._status = "not_found"
        except Exception as e:
            logger.debug("Lyrics search failed", exc_info=True)
            self._status = "error"
            self._error_message = str(e)
        self.dataChanged.emit()

    @Slot()
    def refresh(self):
        if self._current_title:
            self.search(self._current_title, self._current_artist)

    def _parse_synced(self, text: str):
        lines = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("[") and "]" in line:
                try:
                    ts = line[1:line.index("]")]
                    text = line[line.index("]") + 1:].strip()
                    minutes, seconds = ts.split(":")
                    secs = int(minutes) * 60 + float(seconds)
                    lines.append({"time": secs, "text": text})
                except (ValueError, IndexError):
                    lines.append({"time": 0, "text": line})
            else:
                lines.append({"time": 0, "text": line})
        return lines
