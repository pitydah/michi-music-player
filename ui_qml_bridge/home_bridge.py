"""HomeBridge — snapshot dashboard conectado a servicios reales."""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Property, Slot

logger = logging.getLogger("michi.home_bridge")


class HomeBridge(QObject):
    snapshotChanged = Signal()

    def __init__(self, db=None, player_service=None, library_bridge=None,
                 library_sources_service=None, job_bridge=None, playback_service=None,
                 library_query_service=None, library_mutation_service=None,
                 track_action_service=None, query_executor=None, parent=None):
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
        self._has_library = False
        self._errors: list[dict] = []
        if self._player and hasattr(self._player, 'track_changed'):
            self._player.track_changed.connect(self._on_playback_changed)
        if self._player and hasattr(self._player, 'state_changed'):
            self._player.state_changed.connect(self._on_playback_changed)
        if self._job_bridge and hasattr(self._job_bridge, 'jobsChanged'):
            self._job_bridge.jobsChanged.connect(self._load_jobs)

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
        return self._has_library

    @Slot(result="QVariantMap")
    def refresh(self):
        """Refresh the dashboard snapshot and report per-section errors."""
        self._loading = True
        self._ready = False
        self._error_message = ""
        errors: list[dict] = []

        for section, loader in (
            ("library_stats", self._load_library_stats),
            ("playback", self._load_playback),
            ("sources", self._load_sources),
            ("jobs", self._load_jobs),
            ("audio", self._load_audio),
        ):
            try:
                loader()
            except Exception as exc:
                logger.exception("Home snapshot section %s failed", section)
                errors.append({"section": section, "error": str(exc)})

        self._has_library = bool(self._tracks or self._albums or self._artists)
        self._error_message = "; ".join(
            item["section"] for item in errors
        ) if errors else ""
        self._errors = errors
        self._loading = False
        self._ready = True
        self.snapshotChanged.emit()
        return {"ok": not errors, "ready": True, "errors": errors,
                "has_library": self._has_library, "sources": self._sources_count}

    def _load_library_stats(self):
        if self._lib:
            self._tracks = getattr(self._lib, 'songCount', 0)
            self._albums = getattr(self._lib, 'albumCount', 0)
            self._artists = getattr(self._lib, 'artistCount', 0)

    def _load_playback(self):
        if self._player:
            try:
                self._current_track = self._read_field('title') or '—'
                self._current_artist = self._read_field('artist') or '—'
                self._has_playback = bool(self._current_track != '—')
            except Exception:
                pass

    def _read_field(self, field: str) -> str:
        if not self._player:
            return ""
        try:
            if hasattr(self._player, 'current'):
                cur = self._player.current
                if cur:
                    val = getattr(cur, field, '')
                    return str(val) if val else ''
            elif hasattr(self._player, 'get_current_track'):
                cur = self._player.get_current_track()
                if cur and isinstance(cur, dict):
                    return str(cur.get(field, ''))
            return ""
        except Exception:
            return ""

    def _load_sources(self):
        if self._src_svc:
            srcs = self._src_svc.list()
            self._sources_count = len(srcs)

    def _load_jobs(self):
        try:
            if self._job_bridge:
                self._active_jobs = getattr(self._job_bridge, 'activeCount', 0)
                return
        except Exception:
            pass

    def _on_playback_changed(self):
        self._load_playback()
        self._load_audio()
        self.snapshotChanged.emit()

    def _load_audio(self):
        if not self._player:
            return
        try:
            if hasattr(self._player, 'get_active_backend_id'):
                self._backend = self._player.get_active_backend_id() or ""
            if hasattr(self._player, 'get_output_device_id'):
                self._output = self._player.get_output_device_id() or ""
        except Exception:
            pass

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
        if self._player and hasattr(self._player, 'state'):
            score += 15
        if hasattr(self, 'refresh'):
            score += 15
        return {
            "score": min(100, score),
            "ready": self._ready,
            "error": self._error_message,
            "has_db": self._db is not None,
            "has_player": self._player is not None,
            "tracks": self._tracks,
            "albums": self._albums,
        }

    @Slot(int, int, int)
    def set_library_stats(self, albums: int, artists: int, tracks: int):
        self._albums = max(0, albums)
        self._artists = max(0, artists)
        self._tracks = max(0, tracks)
        self.snapshotChanged.emit()
