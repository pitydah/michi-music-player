"""QML bridge for playback — observes PlaybackService."""

import logging
from collections.abc import Callable

from PySide6.QtCore import Property, QObject, Signal, Slot

from michi.application.audio_quality import make_track_quality_label
from michi.application.library_service import LibraryService
from michi.application.playback_service import (
    EngineSwitchLeaseHeldError,
    PlaybackService,
)
from michi.application.ports import (
    AudioLoadError,
    AudioTransportError,
    AudioTransportUnavailableError,
)
from michi.domain.library import make_album_key, resolve_album_artist
from michi.domain.playback import PlaybackStatus

logger = logging.getLogger(__name__)


def _friendly_command_message(exc: Exception) -> str:
    """P1-3: semantic user copy for playback command failures — never raw
    backend internals."""
    if isinstance(exc, EngineSwitchLeaseHeldError):
        return "Michi is changing the audio engine. Try again in a moment."
    if isinstance(exc, AudioTransportUnavailableError):
        return "Playback is not available right now."
    if isinstance(exc, AudioTransportError):
        return "The audio engine rejected the command."
    if isinstance(exc, AudioLoadError):
        return "The selected track could not be loaded."
    return "Playback could not complete the command."


_EXPECTED_COMMAND_ERRORS = (
    EngineSwitchLeaseHeldError,
    AudioTransportError,
    AudioLoadError,
)


class PlaybackBridge(QObject):
    """Thin adapter: PlaybackService state → QML properties, QML intent → service."""

    _status_map = {
        PlaybackStatus.STOPPED: "stopped",
        PlaybackStatus.PLAYING: "playing",
        PlaybackStatus.PAUSED: "paused",
    }

    state_changed = Signal()
    # PLAYBACK-CONTROLS-R1: command failures surface to the user (ToastHost
    # via AppShell) — a click that "does nothing" must never hide the
    # diagnostic (lease held, transport unavailable, backend rejection).
    command_failed = Signal(str, str)  # (command, friendlyMessage)

    def __init__(
        self,
        service: PlaybackService,
        library_service: LibraryService | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._library_service = library_service
        service.subscribe_changed(self._on_service_changed)
        if library_service is not None:
            library_service.subscribe_changed(self._on_service_changed)

    def dispose(self) -> None:
        self._service.unsubscribe_changed(self._on_service_changed)
        if self._library_service is not None:
            self._library_service.unsubscribe_changed(self._on_service_changed)

    def _on_service_changed(self) -> None:
        # P2-2 telemetry: canonical state transitions (debug)
        logger.debug("playback state -> %s", self._service.state.status.value)
        self.state_changed.emit()

    def _get_status(self) -> str:
        return self._status_map.get(self._service.state.status, "stopped")

    def _get_file_name(self) -> str:
        p = self._service.state.file_path
        return p.name if p else ""

    def _get_current_path(self) -> str:
        path = self._service.state.file_path
        return str(path) if path is not None else ""

    def _current_track(self):
        path = self._service.state.file_path
        if self._library_service is None or path is None:
            return None
        return self._library_service.resolve_trackref(path)

    def _get_title(self) -> str:
        track = self._current_track()
        return (
            (track.title or track.display_name)
            if track is not None
            else self._get_file_name()
        )

    def _get_artist(self) -> str:
        track = self._current_track()
        return track.artist if track is not None else ""

    def _get_album(self) -> str:
        track = self._current_track()
        return track.album if track is not None else ""

    def _get_quality_label(self) -> str:
        track = self._current_track()
        return make_track_quality_label(track) if track is not None else ""

    def _get_format_label(self) -> str:
        path = self._service.state.file_path
        return path.suffix.removeprefix(".").upper() if path is not None else ""

    def _get_artwork_path(self) -> str:
        track = self._current_track()
        if track is None or self._library_service is None:
            return ""
        album_title = track.album.strip() or "Unknown Album"
        album_artist = resolve_album_artist(track).strip() or "Unknown Artist"
        key = make_album_key(album_title, album_artist)
        return self._library_service.artwork_path_for(key) or ""

    def _get_position(self) -> int:
        return self._service.state.position_ms // 1000

    def _get_duration(self) -> int:
        return self._service.state.duration_ms // 1000

    def _get_volume(self) -> int:
        return self._service.state.volume

    def _get_muted(self) -> bool:
        return self._service.state.muted

    def _get_error(self) -> str:
        return self._service.state.error_message or ""

    status = Property(str, _get_status, notify=state_changed)
    fileName = Property(str, _get_file_name, notify=state_changed)
    currentPath = Property(str, _get_current_path, notify=state_changed)
    title = Property(str, _get_title, notify=state_changed)
    artist = Property(str, _get_artist, notify=state_changed)
    album = Property(str, _get_album, notify=state_changed)
    qualityLabel = Property(str, _get_quality_label, notify=state_changed)
    formatLabel = Property(str, _get_format_label, notify=state_changed)
    artworkPath = Property(str, _get_artwork_path, notify=state_changed)
    position = Property(int, _get_position, notify=state_changed)
    duration = Property(int, _get_duration, notify=state_changed)
    volume = Property(int, _get_volume, notify=state_changed)
    muted = Property(bool, _get_muted, notify=state_changed)
    errorMessage = Property(str, _get_error, notify=state_changed)

    def _command(self, name: str, fn: Callable[[], None]) -> None:
        """P1-3: run a playback command; typed failures surface via
        command_failed (friendly) + logged technical detail. Unexpected
        exceptions are NEVER swallowed."""
        # P2-2 telemetry: UI intent → service (debug diagnostics)
        logger.debug("playback UI intent: %s", name)
        try:
            fn()
        except _EXPECTED_COMMAND_ERRORS as exc:
            self.command_failed.emit(name, _friendly_command_message(exc))
            logger.warning("playback command %s failed: %s", name, exc, exc_info=True)
        except Exception as exc:
            self.command_failed.emit(name, _friendly_command_message(exc))
            logger.exception("unexpected playback command %s failure", name)
            raise
        else:
            logger.debug("playback command %s accepted", name)

    @Slot()
    def play(self) -> None:
        self._command("play", self._service.play)

    @Slot()
    def pause(self) -> None:
        self._command("pause", self._service.pause)

    @Slot()
    def resume(self) -> None:
        self._command("resume", self._service.resume)

    @Slot()
    def toggle_play_pause(self) -> None:
        """PLAYBACK-CONTROLS-R1: canonical three-state toggle — QML never
        knows transport semantics.

        STOPPED → play()
        PLAYING → pause()
        PAUSED  → resume()

        (The previous QML ternary PLAYING ? pause : play sent playid again
        for a paused MPD instead of pause 0.)"""
        status = self._service.state.status
        if status is PlaybackStatus.PLAYING:
            self.pause()
        elif status is PlaybackStatus.PAUSED:
            self.resume()
        else:
            self.play()

    @Slot()
    def stop(self) -> None:
        self._command("stop", self._service.stop)

    @Slot(int)
    def seek_seconds(self, seconds: int) -> None:
        self._command("seek", lambda: self._service.seek(seconds * 1000))

    @Slot(int)
    def set_volume(self, value: int) -> None:
        self._command("set_volume", lambda: self._service.set_volume(value))

    @Slot(bool)
    def set_muted(self, muted: bool) -> None:
        self._command("set_muted", lambda: self._service.set_muted(muted))

    # M4-R1 final seal: track SELECTION bypass removed — a new track is
    # selected ONLY through PlaybackSessionService (SINGLE context). The
    # transport controls above remain direct PlaybackService operations.
