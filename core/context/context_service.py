"""ContextService — public facade for the context system.

Controllers and UI use this service, not repository or snapshot builders directly.
"""

from __future__ import annotations

import logging

from core.context import context_repository as repo
from core.context.context_events import AppEvent
from core.context.context_invalidator import invalidate_for_event, clear_dirty, is_dirty
from core.context.context_snapshot import (
    build_assistant_snapshot,
    build_home_snapshot,
    build_library_health_snapshot,
    build_mix_snapshot,
    build_playback_snapshot,
)

logger = logging.getLogger("michi.context_service")

_SNAPSHOT_TTL = 120


class ContextService:
    def __init__(self, db=None, playback=None, sync=None):
        self._db = db
        self._playback = playback
        self._sync = sync
        self._current_section = ""
        self._current_tab = ""

    # ── Helpers ──

    @staticmethod
    def _track_payload(track) -> dict:
        if track is None:
            return {}
        return {
            "title": getattr(track, "title", None) or getattr(track, "name", None),
            "artist": getattr(track, "artist", None),
            "album": getattr(track, "album", None),
        }

    # ── Events ──

    def record_event(self, event_type: str, payload: dict | None = None) -> None:
        repo.record_event(event_type, payload)
        invalidate_for_event(event_type)

    def record_scan_finished(self, summary: dict | None = None) -> None:
        self.record_event(AppEvent.SCAN_FINISHED, summary or {})

    def record_favorite_changed(self, track=None, favorite: bool = True) -> None:
        self.record_event(
            AppEvent.TRACK_FAVORITED if favorite else AppEvent.TRACK_UNFAVORITED,
            self._track_payload(track),
        )

    def record_sync_finished(self, payload: dict | None = None) -> None:
        self.record_event(AppEvent.SYNC_FINISHED, payload or {})

    def record_audio_analysis_finished(self, payload: dict | None = None) -> None:
        self.record_event(AppEvent.AUDIO_ANALYSIS_FINISHED, payload or {})

    def record_track_played(self, track=None) -> None:
        self.record_event(AppEvent.TRACK_PLAYED, self._track_payload(track))

    # ── Navigation & state ──

    def update_navigation(self, section: str, tab: str = "",
                          extra: dict | None = None) -> None:
        self._current_section = section
        self._current_tab = tab
        repo.set_state("navigation", {"section": section, "tab": tab, **(extra or {})})
        self.record_event(AppEvent.SECTION_CHANGED, {"section": section, "tab": tab})

    def get_navigation_state(self) -> dict:
        return repo.get_state("navigation", {"section": "", "tab": ""})

    def update_selection(self, track=None, album: str = "", artist: str = "",
                          genre: str = "") -> None:
        payload = {"album": album, "artist": artist, "genre": genre}
        if track is not None:
            payload["track"] = getattr(track, "title", None) or getattr(track, "name", None)
            payload["track_artist"] = getattr(track, "artist", None)
        repo.set_state("selection", payload)
        self.record_event(AppEvent.TRACK_SELECTED, payload)

    def get_selection_state(self) -> dict:
        return repo.get_state("selection", {})

    # ── Snapshots ──

    def _rebuild_if_dirty(self, key: str, builder, ttl: int = _SNAPSHOT_TTL):
        if is_dirty(key) or repo.get_summary(key) is None:
            snapshot = builder()
            repo.set_summary(key, snapshot, ttl_seconds=ttl)
            clear_dirty(key)
        return repo.get_summary(key) or {}

    def get_library_health(self) -> dict:
        return self._rebuild_if_dirty(
            "library_health", lambda: build_library_health_snapshot(self._db))

    def get_home_snapshot(self) -> dict:
        return self._rebuild_if_dirty(
            "home_snapshot", lambda: build_home_snapshot(self._db, self._playback, self._sync))

    def get_assistant_snapshot(self) -> dict:
        def _build():
            nav = repo.get_state("navigation", {})
            sel = repo.get_state("selection", {})
            section = nav.get("section", self._current_section)
            tab = nav.get("tab", self._current_tab)
            snap = build_assistant_snapshot(
                self._db, self._playback,
                current_section=section, current_tab=tab,
                recent_events=repo.recent_events(limit=10),
            )
            snap.update({
                "selected_track": sel.get("track"),
                "selected_album": sel.get("album"),
                "selected_artist": sel.get("artist"),
                "selected_genre": sel.get("genre"),
            })
            return snap
        return self._rebuild_if_dirty("assistant_snapshot", _build)

    def get_mix_snapshot(self) -> dict:
        return self._rebuild_if_dirty(
            "mix_preview", lambda: build_mix_snapshot(self._db))

    def get_playback_context(self) -> dict:
        return self._rebuild_if_dirty(
            "playback_context", lambda: build_playback_snapshot(self._playback), ttl=60)

    def invalidate(self, key: str) -> None:
        repo.mark_dirty(key)

    def recent_events(self, limit: int = 20) -> list[dict]:
        return repo.recent_events(limit=limit)
