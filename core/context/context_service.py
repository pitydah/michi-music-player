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
    sanitize_snapshot,
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
        safe_payload = sanitize_snapshot(payload or {})
        repo.record_event(event_type, safe_payload)
        invalidate_for_event(event_type)

    def record_scan_finished(self, summary: dict | None = None) -> None:
        self.record_event(AppEvent.SCAN_FINISHED, summary or {})

    def record_library_reloaded(self, reason: str = "", count: int = 0) -> None:
        self.record_event(AppEvent.LIBRARY_RELOADED, {"reason": reason, "tracks": count})

    def record_import_finished(self, reason: str = "", count: int = 0) -> None:
        self.record_event(AppEvent.IMPORT_FINISHED, {"reason": reason, "tracks": count})

    def record_metadata_saved(self, count: int = 0) -> None:
        self.record_event(AppEvent.METADATA_SAVED, {"count": count})

    def record_playback_stopped(self, reason: str = "") -> None:
        self.record_event(AppEvent.PLAYBACK_STOPPED, {"reason": reason})

    def record_quality_updated(self, quality: str = "", category: str = "") -> None:
        self.record_event(AppEvent.QUALITY_UPDATED, {"quality": quality, "quality_category": category})

    def record_now_playing_updated(self, title: str = "", artist: str = "", album: str = "") -> None:
        self.record_event(AppEvent.NOW_PLAYING_UPDATED, {"title": title, "artist": artist, "album": album})

    def record_assistant_action_confirmed(self, tool_name: str = "", affected_count: int = 0) -> None:
        self.record_event(AppEvent.ASSISTANT_ACTION_CONFIRMED, {"tool_name": tool_name, "affected_count": affected_count})

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

    def record_track_played_title_artist(self, title: str = "", artist: str = "") -> None:
        self.record_event(AppEvent.TRACK_PLAYED, {"title": title, "artist": artist})

    def record_track_paused(self) -> None:
        self.record_event(AppEvent.TRACK_PAUSED)

    def record_playlist_imported(self, playlist_id: int = 0, name: str = "",
                                  count: int = 0) -> None:
        self.record_event(AppEvent.PLAYLIST_IMPORTED, {
            "playlist_id": playlist_id, "name": name, "count": count,
        })

    def record_playlist_exported(self, playlist_id: int = 0, name: str = "",
                                  count: int = 0) -> None:
        self.record_event(AppEvent.PLAYLIST_EXPORTED, {
            "playlist_id": playlist_id, "name": name, "count": count,
        })

    # ── Queue ──

    def record_queue_updated(self, count: int, source: str = "") -> None:
        self.record_event(AppEvent.QUEUE_UPDATED, {"count": count, "source": source})

    def record_queue_cleared(self, reason: str = "") -> None:
        self.record_event(AppEvent.QUEUE_CLEARED, {"reason": reason})

    def record_track_queued(self, title: str = "", artist: str = "",
                            source: str = "") -> None:
        self.record_event(AppEvent.TRACK_QUEUED, {
            "title": title, "artist": artist, "source": source,
        })

    def record_playback_mode_changed(self, shuffle: bool | None = None,
                                     repeat: str | None = None) -> None:
        payload = {}
        if shuffle is not None:
            payload["shuffle"] = shuffle
        if repeat is not None:
            payload["repeat"] = repeat
        self.record_event(AppEvent.PLAYBACK_MODE_CHANGED, payload)

    # ── Metadata ──

    def record_metadata_review_opened(self, scope: str, count: int = 0) -> None:
        self.record_event(AppEvent.METADATA_REVIEW_OPENED, {"scope": scope, "count": count})

    def record_cover_updated(self, scope: str = "", count: int = 1) -> None:
        self.record_event(AppEvent.COVER_UPDATED, {"scope": scope, "count": count})

    def record_lyrics_updated(self, count: int = 1) -> None:
        self.record_event(AppEvent.LYRICS_UPDATED, {"count": count})

    def record_tags_batch_updated(self, count: int) -> None:
        self.record_event(AppEvent.TAGS_BATCH_UPDATED, {"count": count})

    # ── Audio analysis ──

    def record_audio_analysis_started(self, count: int, scope: str = "") -> None:
        self.record_event(AppEvent.AUDIO_ANALYSIS_STARTED, {"count": count, "scope": scope})

    def record_audio_analysis_failed(self, count: int = 0, reason: str = "") -> None:
        self.record_event(AppEvent.AUDIO_ANALYSIS_FAILED, {"count": count, "reason": reason[:200]})

    def record_audio_features_updated(self, count: int) -> None:
        self.record_event(AppEvent.AUDIO_FEATURES_UPDATED, {"count": count})

    # ── Disc Lab ──

    def record_disc_detected(self, source: str = "cd") -> None:
        self.record_event(AppEvent.DISC_DETECTED, {"source": source})

    def record_rip_started(self, source: str = "cd", format: str = "") -> None:
        self.record_event(AppEvent.RIP_STARTED, {"source": source, "format": format})

    def record_rip_finished(self, source: str = "cd", count: int = 0) -> None:
        self.record_event(AppEvent.RIP_FINISHED, {"source": source, "count": count})

    def record_rip_failed(self, source: str = "cd", error_type: str = "") -> None:
        self.record_event(AppEvent.RIP_FAILED, {"source": source, "error_type": error_type[:100]})

    # ── Identifier / Radio ──

    def record_identification_started(self) -> None:
        self.record_event(AppEvent.IDENTIFICATION_STARTED, {})

    def record_identification_matched(self, title: str = "", artist: str = "",
                                      confidence: float = 0.0) -> None:
        self.record_event(AppEvent.IDENTIFICATION_MATCHED, {
            "title": title, "artist": artist, "confidence": confidence,
        })

    def record_identification_failed(self) -> None:
        self.record_event(AppEvent.IDENTIFICATION_FAILED, {})

    def record_radio_station_selected(self, station_name: str = "") -> None:
        self.record_event(AppEvent.RADIO_STATION_SELECTED, {"station_name": station_name})

    def record_radio_played(self, station_name: str = "") -> None:
        self.record_event(AppEvent.RADIO_PLAYED, {"station_name": station_name})

    # ── Operational errors ──

    def record_operational_error(self, area: str, code: str,
                                 message: str = "") -> None:
        self.record_event(AppEvent.CONTEXT_ERROR_RECORDED, {
            "area": area, "code": code, "message": message[:300],
        })

    # ── Navigation & state ──

    def update_navigation(self, section: str, tab: str = "",
                          extra: dict | None = None) -> None:
        self._current_section = section
        self._current_tab = tab
        repo.set_state("navigation", {"section": section, "tab": tab, **(extra or {})})
        self.record_event(AppEvent.SECTION_CHANGED, {"section": section, "tab": tab})

    def get_navigation_state(self) -> dict:
        return repo.get_state("navigation", {"section": "", "tab": ""})

    def update_selection(self, track=None,
                          album: str | None = None,
                          artist: str | None = None,
                          genre: str | None = None,
                          playlist_id: int | None = None,
                          playlist_name: str | None = None,
                          folder_name: str | None = None,
                          mix_key: str | None = None,
                          search_query: str | None = None,
                          scope: str | None = None) -> None:
        current = repo.get_state("selection", {})
        payload = dict(current)

        inferred_scope = scope
        if inferred_scope is None:
            if track is not None:
                inferred_scope = "track"
            elif album is not None:
                inferred_scope = "album"
            elif artist is not None:
                inferred_scope = "artist"
            elif genre is not None:
                inferred_scope = "genre"
            elif playlist_id is not None or playlist_name is not None:
                inferred_scope = "playlist"
            elif folder_name is not None:
                inferred_scope = "folder"
            elif mix_key is not None:
                inferred_scope = "mix"
            elif search_query is not None:
                inferred_scope = "search"

        if inferred_scope is not None:
            payload["selection_scope"] = inferred_scope

        if album is not None:
            payload["album"] = album
        if artist is not None:
            payload["artist"] = artist
        if genre is not None:
            payload["genre"] = genre
        if playlist_id is not None:
            payload["playlist_id"] = playlist_id
        if playlist_name is not None:
            payload["playlist_name"] = playlist_name
        if folder_name is not None:
            payload["folder_name"] = folder_name
        if mix_key is not None:
            payload["mix_key"] = mix_key
        if search_query is not None:
            payload["search_query"] = search_query[:80] if search_query else ""
        if track is not None:
            payload["track"] = getattr(track, "title", None) or getattr(track, "name", None)
            payload["track_artist"] = getattr(track, "artist", None)
            payload["track_album"] = getattr(track, "album", None)

        repo.set_state("selection", payload)
        if inferred_scope == "track":
            self.record_event(AppEvent.TRACK_SELECTED, payload)
        else:
            self.record_event(AppEvent.SELECTION_CHANGED, payload)

    def clear_selection_for_scope(self, scope: str) -> dict:
        base = {
            "selection_scope": scope,
            "track": None,
            "track_artist": None,
            "track_album": None,
            "album": "",
            "artist": "",
            "genre": "",
            "playlist_id": None,
            "playlist_name": "",
            "folder_name": "",
            "mix_key": "",
            "search_query": "",
        }
        repo.set_state("selection", base)
        return base

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
        def _build():
            sel = repo.get_state("selection", {})
            scope = sel.get("selection_scope")
            label = sel.get("album") or sel.get("artist") or sel.get("genre") or sel.get("playlist_name") or sel.get("folder_name") or sel.get("mix_key") or sel.get("search_query") or ""
            return build_home_snapshot(
                self._db, self._playback, self._sync,
                current_section=self._current_section,
                selection_scope=scope,
                selection_label=label,
            )
        return self._rebuild_if_dirty("home_snapshot", _build)

    @staticmethod
    def _assistant_capabilities_for_scope(scope):
        return {
            "can_search_library": True,
            "can_create_playlist_from_selection": scope in {
                "track", "album", "artist", "genre", "playlist",
                "mix", "folder", "search",
            },
            "can_queue_selection": scope in {
                "track", "album", "artist", "genre", "playlist",
                "mix", "folder", "search",
            },
            "can_edit_metadata": scope in {"track", "album", "artist", "genre"},
            "can_analyze_selected_tracks": scope in {
                "track", "album", "artist", "genre", "playlist",
                "mix", "search",
            },
        }

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

            scope = sel.get("selection_scope")
            selection = {
                "scope": scope,
                "track": sel.get("track"),
                "track_artist": sel.get("track_artist"),
                "track_album": sel.get("track_album"),
                "album": sel.get("album"),
                "artist": sel.get("artist"),
                "genre": sel.get("genre"),
                "playlist_id": sel.get("playlist_id"),
                "playlist_name": sel.get("playlist_name"),
                "folder_name": sel.get("folder_name"),
                "mix_key": sel.get("mix_key"),
                "search_query": sel.get("search_query"),
            }
            snap["route"] = {"current_section": section, "current_tab": tab}
            snap["selection"] = selection
            snap["selection_scope"] = scope
            snap["selected_track"] = selection["track"]
            snap["selected_album"] = selection["album"]
            snap["selected_artist"] = selection["artist"]
            snap["selected_genre"] = selection["genre"]

            snap["assistant_capabilities"] = self._assistant_capabilities_for_scope(scope)
            snap["contextual_action_hints"] = _contextual_action_hints(snap)
            return sanitize_snapshot(snap)
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


def _contextual_action_hints(snapshot: dict) -> list[str]:
    """Generate brief contextual hints from an assistant snapshot."""
    caps = snapshot.get("assistant_capabilities", {})
    scope = snapshot.get("selection_scope")
    can_create = caps.get("can_create_playlist_from_selection", False)
    can_queue = caps.get("can_queue_selection", False)
    can_edit = caps.get("can_edit_metadata", False)
    can_analyze = caps.get("can_analyze_selected_tracks", False)
    hints = []
    if scope == "track":
        if can_edit:
            hints.append("Editar metadatos de la pista seleccionada")
        if can_create:
            hints.append("Agregar pista a una playlist")
        if can_analyze:
            hints.append("Analizar audio de la pista")
        hints.append("Buscar información similar")
    elif scope == "album":
        if can_create:
            hints.append("Crear playlist con este álbum")
        hints.append("Revisar carátula del álbum")
        if can_edit:
            hints.append("Completar metadatos del álbum")
    elif scope == "artist":
        hints.append("Ver discografía completa")
        if can_create:
            hints.append("Crear playlist del artista")
        if can_edit:
            hints.append("Revisar metadatos del artista")
    elif scope == "genre":
        if can_create:
            hints.append("Crear playlist del género")
        if can_analyze:
            hints.append("Analizar distribución del género")
    elif scope == "playlist":
        hints.append("Reproducir playlist")
        if can_queue:
            hints.append("Encolar playlist")
        hints.append("Exportar playlist")
        hints.append("Revisar duplicados en la playlist")
    elif scope == "mix":
        if can_create:
            hints.append("Guardar mix como playlist")
        if can_queue:
            hints.append("Encolar mix")
        hints.append("Refrescar mix")
    elif scope == "folder":
        hints.append("Escanear la carpeta")
        if can_create:
            hints.append("Crear playlist desde la carpeta")
        if can_queue:
            hints.append("Encolar contenido de la carpeta")
    elif scope == "search":
        if can_create:
            hints.append("Crear playlist con los resultados")
        hints.append("Refinar búsqueda")
    elif scope is None:
        hints.append("Escanear biblioteca musical")
        hints.append("Abrir una sección de la biblioteca")
    return hints[:4]
