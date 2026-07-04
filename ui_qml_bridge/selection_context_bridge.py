"""SelectionContextBridge — shared selection context for QML workflow integration."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property


class SelectionContextBridge(QObject):
    selectionChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._track_id = ""
        self._title = ""
        self._artist = ""
        self._album = ""
        self._filepath = ""
        self._cover_key = ""
        self._source = ""

    @Property(str, notify=selectionChanged)
    def selectedTrackId(self):
        return self._track_id

    @Property(str, notify=selectionChanged)
    def selectedTitle(self):
        return self._title

    @Property(str, notify=selectionChanged)
    def selectedArtist(self):
        return self._artist

    @Property(str, notify=selectionChanged)
    def selectedAlbum(self):
        return self._album

    @Property(str, notify=selectionChanged)
    def selectedFilepath(self):
        return self._filepath

    @Property(str, notify=selectionChanged)
    def selectedCoverKey(self):
        return self._cover_key

    @Property(str, notify=selectionChanged)
    def selectedSource(self):
        return self._source

    @Property(bool, notify=selectionChanged)
    def hasSelection(self):
        return bool(self._track_id) or bool(self._filepath)

    def setSelected(self, track_dict: dict):
        self._track_id = str(track_dict.get("id", track_dict.get("track_id", "")))
        self._title = track_dict.get("title", "")
        self._artist = track_dict.get("artist", "")
        self._album = track_dict.get("album", "")
        self._filepath = track_dict.get("filepath", "")
        self._cover_key = track_dict.get("cover_key", track_dict.get("coverKey", ""))
        self._source = "track_id" if self._track_id else ("filepath" if self._filepath else "")
        self.selectionChanged.emit()

    def clearSelection(self):
        self._track_id = ""
        self._title = ""
        self._artist = ""
        self._album = ""
        self._filepath = ""
        self._cover_key = ""
        self._source = ""
        self.selectionChanged.emit()
