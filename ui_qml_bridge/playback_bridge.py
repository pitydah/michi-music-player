"""PlaybackBridge — delegates to NowPlayingBridge, propagates real results."""
from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot

from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge


class PlaybackBridge(QObject):
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

    @Property(bool, notify=stateChanged)
    def hasTrack(self):
        return self._nowplaying.hasTrack

    @Property(bool, notify=stateChanged)
    def backendAvailable(self):
        return self._nowplaying.backendAvailable

    # ── Playback commands — propagate real results ──

    @Slot(result=dict)
    def togglePlay(self):
        return self._nowplaying.togglePlay()

    @Slot(result=dict)
    def next(self):
        return self._nowplaying.next()

    @Slot(result=dict)
    def previous(self):
        return self._nowplaying.previous()

    @Slot(int, result=dict)
    def setVolume(self, volume: int):
        return self._nowplaying.setVolume(volume)

    @Slot(result=dict)
    def toggleMute(self):
        return self._nowplaying.toggleMute()

    @Slot(int, result=dict)
    def seek(self, position: int):
        return self._nowplaying.seek(position)

    @Slot(result=dict)
    def toggleShuffle(self):
        return self._nowplaying.toggleShuffle()

    @Slot(result=dict)
    def toggleRepeat(self):
        return self._nowplaying.toggleRepeat()

    @Slot(int, result=dict)
    def seekRelative(self, seconds: int):
        return self._nowplaying.seekRelative(seconds)

    @Slot(str, result=dict)
    def enqueueSong(self, filepath: str):
        return self._nowplaying.enqueueSong(filepath)

    @Slot(int, result=dict)
    def removeFromQueue(self, index: int):
        return self._nowplaying.removeFromQueue(index)

    @Slot(result=dict)
    def clearQueue(self):
        return self._nowplaying.clearQueue()

    @Slot(int, int, result=dict)
    def moveQueueItem(self, from_index: int, to_index: int):
        return self._nowplaying.moveQueueItem(from_index, to_index)

    @Slot(int, result=dict)
    def playQueueItem(self, index: int):
        return self._nowplaying.playQueueItem(index)
