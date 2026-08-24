"""PlaybackSessionBridge — QML projection of the active playback session
(M4-R1). Exposes context/navigation projections and intents. No backend
details, no Queue playback authority."""

from PySide6.QtCore import Property, QObject, Signal, Slot

from michi.application.playback_session_service import PlaybackSessionService
from michi.domain.playback_session import (
    RepeatMode,
)


class PlaybackSessionBridge(QObject):
    """QML surface for PlaybackSessionState."""

    session_changed = Signal()

    def __init__(
        self,
        playback_session: PlaybackSessionService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._session = playback_session
        self._session.subscribe_changed(self.session_changed.emit)

    # ------------------------------------------------------------------
    # Projections
    # ------------------------------------------------------------------

    def _get_context_type(self) -> str:
        return self._session.state.context_type.name.lower()

    def _get_source_id(self) -> str:
        source = self._session.state.source_id
        return source if source is not None else ""

    def _get_current_index(self) -> int:
        return self._session.state.current_index

    def _get_count(self) -> int:
        return self._session.state.count

    def _get_has_next(self) -> bool:
        return self._session.state.has_next

    def _get_has_previous(self) -> bool:
        return self._session.state.has_previous

    def _get_repeat_mode(self) -> str:
        return self._session.state.repeat_mode.name.lower()

    def _get_shuffle_enabled(self) -> bool:
        return self._session.state.shuffle_enabled

    contextType = Property(str, _get_context_type, notify=session_changed)
    sourceId = Property(str, _get_source_id, notify=session_changed)
    currentIndex = Property(int, _get_current_index, notify=session_changed)
    count = Property(int, _get_count, notify=session_changed)
    hasNext = Property(bool, _get_has_next, notify=session_changed)
    hasPrevious = Property(bool, _get_has_previous, notify=session_changed)
    repeatMode = Property(str, _get_repeat_mode, notify=session_changed)
    shuffleEnabled = Property(bool, _get_shuffle_enabled, notify=session_changed)

    # ------------------------------------------------------------------
    # Intents
    # ------------------------------------------------------------------

    @Slot()
    def next_track(self) -> None:
        self._session.next()

    @Slot()
    def previous_track(self) -> None:
        self._session.previous()

    @Slot(int)
    def play_queue_index(self, index: int) -> None:
        self._session.play_queue_index(index)

    @Slot(str)
    def set_repeat_mode(self, name: str) -> None:
        try:
            mode = RepeatMode[name.upper()]
        except KeyError:
            return
        self._session.set_repeat_mode(mode)

    @Slot(bool)
    def set_shuffle_enabled(self, enabled: bool) -> None:
        self._session.set_shuffle_enabled(enabled)
