"""PlaybackBridge — command-compatible facade for QML playback pages."""

from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot

from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge


class PlaybackBridge(QObject):
    """Compatibility layer that delegates playback state to NowPlayingBridge."""

    stateChanged = Signal()

    def __init__(self, player_service=None, playback_ctrl=None, nowplaying_bridge=None, parent=None):
        super().__init__(parent)
        player = player_service or playback_ctrl
        self._nowplaying = nowplaying_bridge or NowPlayingBridge(player_service=player)
        self._nowplaying.stateChanged.connect(self.stateChanged.emit)
        self._nowplaying.coverChanged.connect(self.stateChanged.emit)

    @Property(str, notify=stateChanged)
    def trackTitle(self):
        return self._nowplaying.trackTitle

    @Property(str, notify=stateChanged)
    def trackArtist(self):
        return self._nowplaying.trackArtist

    @Property(str, notify=stateChanged)
    def trackAlbum(self):
        return self._nowplaying.trackAlbum

    @Property(str, notify=stateChanged)
    def coverPath(self):
        return self._nowplaying.coverPath

    @Property(bool, notify=stateChanged)
    def isPlaying(self):
        return self._nowplaying.isPlaying

    @Property(int, notify=stateChanged)
    def position(self):
        return self._nowplaying.position

    @Property(int, notify=stateChanged)
    def duration(self):
        return self._nowplaying.duration

    @Property(int, notify=stateChanged)
    def volume(self):
        return self._nowplaying.volume

    @Property(bool, notify=stateChanged)
    def muted(self):
        return self._nowplaying.muted

    @Property(str, notify=stateChanged)
    def sourceType(self):
        return self._nowplaying.sourceType

    @Property(str, notify=stateChanged)
    def qualityLabel(self):
        return self._nowplaying.qualityLabel

    @Property(str, notify=stateChanged)
    def repeatMode(self):
        return self._nowplaying.repeatMode

    @Property(bool, notify=stateChanged)
    def shuffleEnabled(self):
        return self._nowplaying.shuffleEnabled

    @Property("QVariantList", notify=stateChanged)
    def queue(self):
        return self._nowplaying.queue

    @Property("QVariantList", notify=stateChanged)
    def history(self):
        return self._nowplaying.history

    @Slot()
    def togglePlay(self):
        self._nowplaying.togglePlay()

    @Slot()
    def next(self):
        self._nowplaying.next()

    @Slot()
    def previous(self):
        self._nowplaying.previous()

    @Slot(int)
    def setVolume(self, volume: int):
        self._nowplaying.setVolume(volume)

    @Slot()
    def toggleMute(self):
        self._nowplaying.toggleMute()

    @Slot(int)
    def seek(self, position: int):
        self._nowplaying.seek(position)

    @Slot()
    def toggleShuffle(self):
        self._nowplaying.toggleShuffle()

    @Slot()
    def toggleRepeat(self):
        self._nowplaying.toggleRepeat()

    @Slot(int)
    def seekRelative(self, seconds: int):
        self._nowplaying.seekRelative(seconds)
