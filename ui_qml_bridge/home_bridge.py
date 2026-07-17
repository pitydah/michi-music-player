"""HomeBridge — snapshot dashboard connected to productive services."""
from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QObject, Property, Signal, Slot

logger = logging.getLogger("michi.home_bridge")


class HomeBridge(QObject):
    snapshotChanged = Signal()

    def __init__(
        self,
        db=None,
        player_service=None,
        library_bridge=None,
        library_sources_service=None,
        job_bridge=None,
        playback_service=None,
        library_query_service=None,
        library_mutation_service=None,
        track_action_service=None,
        query_executor=None,
        parent=None,
    ):
        super().__init__(parent)
        self._db = db
        self._player = player_service or playback_service
        self._lib = library_bridge
        self._src_svc = library_sources_service
        self._job_bridge = job_bridge
        self._albums = 0
        self._artists = 0
        self._tracks = 0
        self._sources_count = 0
        self._last_scan = ""
        self._current_track = "—"
        self._current_artist = "—"
        self._has_playback = False
        self._active_jobs = 0
        self._backend = ""
        self._output = ""
        self._loading = False
        self._ready = False
        self._error_message = ""

        if self._player and hasattr(self._player, "track_changed"):
            self._player.track_changed.connect(self._on_playback_changed)
        if self._player and hasattr(self._player, "state_changed"):
            self._player.state_changed.connect(self._on_playback_changed)
        if self._job_bridge and hasattr(self._job_bridge, "jobsChanged"):
            self._job_bridge.jobsChanged.connect(self._on_jobs_changed)

    @Property(int, notify=snapshotChanged)
    def libraryAlbums(self):
        return self._albums

    @Property(int, notify=snapshotChanged)
    def libraryArtists(self):
        return self._artists

    @Property(int, notify=snapshotChanged)
    def libraryTracks(self):
        return self._tracks

    @Property(int, notify=snapshotChanged)
    def sourcesCount(self):
        return self._sources_count

    @Property(str, notify=snapshotChanged)
    def lastScan(self):
        return self._last_scan

    @Property(str, notify=snapshotChanged)
    def currentTrackTitle(self):
        return self._current_track

    @Property(str, notify=snapshotChanged)
    def currentArtist(self):
        return self._current_artist

    @Property(bool, notify=snapshotChanged)
    def hasPlayback(self):
        return self._has_playback

    @Property(int, notify=snapshotChanged)
    def activeJobs(self):
        return self._active_jobs

    @Property(str, notify=snapshotChanged)
    def backend(self):
        return self._backend

    @Property(str, notify=snapshotChanged)
    def output(self):
        return self._output

    @Property(bool, notify=snapshotChanged)
    def loading(self):
        return self._loading

    @Property(bool, notify=snapshotChanged)
    def ready(self):
        return self._ready

    @Property(str, notify=snapshotChanged)
    def errorMessage(self):
        return self._error_message

    @Property(bool, notify=snapshotChanged)
    def hasLibrary(self):
        return self._tracks > 0 or self._albums > 0 or self._artists > 0

    @Slot(result=dict)
    def refresh(self) -> dict[str, Any]:
        self._loading = True
        self._error_message = ""
        self.snapshotChanged.emit()

        errors: list[str] = []
        for label, loader in (
            ("biblioteca", self._load_library_stats),
            ("reproducción", self._load_playback),
            ("fuentes", self._load_sources),
            ("trabajos", self._load_jobs),
            ("audio", self._load_audio),
        ):
            try:
                loader()
            except Exception as exc:
                logger.warning("Home snapshot %s failed: %s", label, exc)
                errors.append(f"{label}: {exc}")

        self._loading = False
        self._ready = True
        self._error_message = "; ".join(errors)
        self.snapshotChanged.emit()
        return {
            "ok": not errors,
            "errors": errors,
            "has_library": self.hasLibrary,
            "sources": self._sources_count,
        }

    def _load_library_stats(self) -> None:
        if not self._lib:
            return
        self._tracks = int(getattr(self._lib, "songCount", 0) or 0)
        self._albums = int(getattr(self._lib, "albumCount", 0) or 0)
        self._artists = int(getattr(self._lib, "artistCount", 0) or 0)

    def _load_playback(self) -> None:
        if not self._player:
            self._has_playback = False
            return

        current = getattr(self._player, "current", None)
        if callable(current):
            current = current()

        if current:
            self._current_track = self._read_field(current, "title", "name") or "—"
            self._current_artist = self._read_field(current, "artist") or "—"
            self._has_playback = True
            return

        getter = getattr(self._player, "get_current_track", None)
        if callable(getter):
            current = getter()
            if current:
                self._current_track = self._read_field(current, "title", "name") or "—"
                self._current_artist = self._read_field(current, "artist") or "—"
                self._has_playback = True
                return

        title = str(getattr(self._player, "_current_title", "") or "")
        artist = str(getattr(self._player, "_current_artist", "") or "")
        snapshot = self._player_snapshot()
        current_path = str(getattr(snapshot, "current_path", "") or "") if snapshot else ""
        self._has_playback = bool(title or current_path)
        self._current_track = title or (current_path.rsplit("/", 1)[-1] if current_path else "—")
        self._current_artist = artist or "—"

    def _load_sources(self) -> None:
        if not self._src_svc:
            self._sources_count = 0
            return
        sources = self._src_svc.list()
        self._sources_count = len(sources or [])

    def _load_jobs(self) -> None:
        self._active_jobs = (
            int(getattr(self._job_bridge, "activeCount", 0) or 0)
            if self._job_bridge
            else 0
        )

    def _on_jobs_changed(self, *_args) -> None:
        try:
            self._load_jobs()
            self.snapshotChanged.emit()
        except Exception as exc:
            logger.warning("Home jobs update failed: %s", exc)

    def _on_playback_changed(self, *_args) -> None:
        try:
            self._load_playback()
            self._load_audio()
            self._error_message = ""
        except Exception as exc:
            logger.warning("Home playback update failed: %s", exc)
            self._error_message = f"reproducción: {exc}"
        self.snapshotChanged.emit()

    def _load_audio(self) -> None:
        if not self._player:
            self._backend = ""
            self._output = ""
            return
        backend_getter = getattr(self._player, "get_active_backend_id", None)
        output_getter = getattr(self._player, "get_output_device_id", None)
        self._backend = str(backend_getter() or "") if callable(backend_getter) else ""
        self._output = str(output_getter() or "") if callable(output_getter) else ""

    def _player_snapshot(self):
        hybrid = getattr(self._player, "_hybrid", None)
        getter = getattr(hybrid, "get_snapshot", None)
        return getter() if callable(getter) else None

    @staticmethod
    def _read_field(source, *names: str) -> str:
        if isinstance(source, dict):
            for name in names:
                value = source.get(name)
                if value:
                    return str(value)
            return ""
        for name in names:
            value = getattr(source, name, "")
            if callable(value):
                value = value()
            if value:
                return str(value)
        return ""

    @Slot(result=dict)
    def homeScore(self) -> dict:
        score = 0
        if self._db:
            score += 20
        if self._player:
            score += 20
        if self._tracks > 0:
            score += 15
        if self._albums > 0:
            score += 15
        if self._backend:
            score += 15
        if self._ready:
            score += 15
        return {
            "score": min(100, score),
            "has_db": self._db is not None,
            "has_player": self._player is not None,
            "tracks": self._tracks,
            "albums": self._albums,
            "ready": self._ready,
            "error": self._error_message,
        }

    @Slot(int, int, int)
    def set_library_stats(self, albums: int, artists: int, tracks: int) -> None:
        self._albums = max(0, int(albums))
        self._artists = max(0, int(artists))
        self._tracks = max(0, int(tracks))
        self.snapshotChanged.emit()
