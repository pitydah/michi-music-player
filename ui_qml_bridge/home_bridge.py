from PySide6.QtCore import QObject, Signal, Property, Slot


class HomeBridge(QObject):
    snapshotChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._albums = 0
        self._artists = 0
        self._tracks = 0
        self._micro_server_state = "not_configured"
        self._current_track = "—"
        self._current_artist = "—"
        self._has_playback = False

    @Property(int, notify=snapshotChanged)
    def libraryAlbums(self):
        return self._albums

    @Property(int, notify=snapshotChanged)
    def libraryArtists(self):
        return self._artists

    @Property(int, notify=snapshotChanged)
    def libraryTracks(self):
        return self._tracks

    @Property(str, notify=snapshotChanged)
    def microServerState(self):
        return self._micro_server_state

    @Property(str, notify=snapshotChanged)
    def currentTrackTitle(self):
        return self._current_track

    @Property(str, notify=snapshotChanged)
    def currentArtist(self):
        return self._current_artist

    @Slot()
    def refresh(self):
        self.snapshotChanged.emit()

    @Slot(int, int, int)
    def set_library_stats(self, albums: int, artists: int, tracks: int):
        self._albums = albums
        self._artists = artists
        self._tracks = tracks
        self.snapshotChanged.emit()
