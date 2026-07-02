from PySide6.QtCore import QObject, Signal, Property, Slot


class PlaybackBridge(QObject):
    stateChanged = Signal()

    def __init__(self, player_service=None, playback_ctrl=None, parent=None):
        super().__init__(parent)
        self._player = player_service
        self._playback_ctrl = playback_ctrl
        self._track_title = "—"
        self._track_artist = "—"
        self._track_album = "—"
        self._cover_path = ""
        self._is_playing = False
        self._position = 0
        self._duration = 0
        self._volume = 80
        self._source_type = "local_file"
        self._quality_label = ""
        self._repeat_mode = "none"
        self._shuffle_enabled = False
        self._queue = []
        self._history = []

        if self._player:
            try:
                self._player.track_changed.connect(self._on_track)
                self._player.state_changed.connect(self._on_state)
                self._player.position_changed.connect(self._on_position)
                self._player.duration_changed.connect(self._on_duration)
                self._player.volume_changed.connect(self._on_volume)
            except Exception:
                pass

    # ── Señales del PlayerService ──
    def _on_track(self, title: str, artist: str):
        self._track_title = title or "—"
        self._track_artist = artist or "—"
        self.stateChanged.emit()

    def _on_state(self, state: str):
        self._is_playing = state in ("playing", "resumed")
        self.stateChanged.emit()

    def _on_position(self, secs: float):
        self._position = int(secs)
        self.stateChanged.emit()

    def _on_duration(self, secs: float):
        self._duration = int(secs)
        self.stateChanged.emit()

    def _on_volume(self, vol: int):
        self._volume = vol
        self.stateChanged.emit()

    # ── Propiedades QML ──
    @Property(str, notify=stateChanged)
    def trackTitle(self): return self._track_title

    @Property(str, notify=stateChanged)
    def trackArtist(self): return self._track_artist

    @Property(str, notify=stateChanged)
    def trackAlbum(self): return self._track_album

    @Property(str, notify=stateChanged)
    def coverPath(self): return self._cover_path

    @Property(bool, notify=stateChanged)
    def isPlaying(self): return self._is_playing

    @Property(int, notify=stateChanged)
    def position(self): return self._position

    @Property(int, notify=stateChanged)
    def duration(self): return self._duration

    @Property(int, notify=stateChanged)
    def volume(self): return self._volume

    @Property(str, notify=stateChanged)
    def sourceType(self): return self._source_type

    @Property(str, notify=stateChanged)
    def qualityLabel(self): return self._quality_label

    @Property(str, notify=stateChanged)
    def repeatMode(self): return self._repeat_mode

    @Property(bool, notify=stateChanged)
    def shuffleEnabled(self): return self._shuffle_enabled

    @Property("QVariantList", notify=stateChanged)
    def queue(self): return self._queue

    @Property("QVariantList", notify=stateChanged)
    def history(self): return self._history

    # ── Slots QML ──
    @Slot()
    def togglePlay(self):
        if self._player:
            if self._is_playing:
                self._player.pause()
            else:
                self._player.play_or_resume()
        else:
            self._is_playing = not self._is_playing
            self.stateChanged.emit()

    @Slot()
    def next(self):
        if self._player:
            self._player.play_next()
        self.stateChanged.emit()

    @Slot()
    def previous(self):
        if self._player:
            self._player.play_prev()
        self.stateChanged.emit()

    @Slot(int)
    def setVolume(self, vol: int):
        self._volume = max(0, min(100, vol))
        if self._player:
            self._player.set_volume(self._volume)
        self.stateChanged.emit()

    @Slot(int)
    def seek(self, pos: int):
        self._position = pos
        self.stateChanged.emit()

    @Slot()
    def toggleShuffle(self):
        self._shuffle_enabled = not self._shuffle_enabled
        self.stateChanged.emit()

    @Slot()
    def toggleRepeat(self):
        modes = ["none", "one", "all"]
        idx = modes.index(self._repeat_mode) if self._repeat_mode in modes else 0
        self._repeat_mode = modes[(idx + 1) % len(modes)]
        self.stateChanged.emit()

    @Slot(int)
    def seekRelative(self, secs: int):
        self._position = max(0, self._position + secs)
        self.stateChanged.emit()
