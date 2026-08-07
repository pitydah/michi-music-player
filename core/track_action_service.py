"""TrackActionService — acciones de biblioteca por ID público, sin filepath.

Delegates every mutation to the canonical services: queue (QueueService),
playlists (PlaylistService), favorites (FavoriteService) and file managers
(FileManagerService). No direct SQL, no subprocess.Popen, no filepath-based
identity. ``ActionContext``-based methods execute with an explicit target
(entity_type + entity_id) instead of the deprecated global selection.
"""
from __future__ import annotations

import logging

from core.action_context import ActionContext

logger = logging.getLogger("michi.track_actions")


class TrackActionService:
    def __init__(self, query_service, queue_service, playlist_service,
                 db=None, favorite_service=None, file_manager_service=None):
        if query_service is None or queue_service is None:
            raise ValueError("TrackActionService requires query_service and queue_service")
        if playlist_service is None:
            raise ValueError("TrackActionService requires playlist_service")
        self._qs = query_service
        self._queue = queue_service
        self._playlists = playlist_service
        self._db = db
        self._favorites = favorite_service
        self._fm = file_manager_service

    # ── internal helpers ────────────────────────────────────────────────

    def _get_track(self, track_id: int) -> dict | None:
        track = self._qs.fetch_track_internal(track_id)
        if not track or not track.get("filepath"):
            return None
        return track

    def _favorite_service(self):
        # P0 FASE 10: no lazy construction — the canonical FavoriteService is
        # injected by composition; callers handle None explicitly.
        return self._favorites

    def _file_manager(self):
        # P0 FASE 10: no lazy construction — the canonical FileManagerService
        # port is injected by composition; callers handle None explicitly.
        return self._fm

    # ── track actions (public id surface, QML stable) ───────────────────

    def play_track(self, track_id: int) -> dict:
        try:
            track = self._get_track(track_id)
            if not track:
                return {"ok": False, "error": "NOT_FOUND"}
            result = self._queue.enqueue(track, play_now=True)
            return {**result, "track_id": track_id} if result.get("ok") else result
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def enqueue_track(self, track_id: int) -> dict:
        try:
            track = self._get_track(track_id)
            if not track:
                return {"ok": False, "error": "NOT_FOUND"}
            result = self._queue.enqueue(track, play_now=False)
            return {**result, "track_id": track_id} if result.get("ok") else result
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def play_next(self, track_id: int) -> dict:
        try:
            track = self._get_track(track_id)
            if not track:
                return {"ok": False, "error": "NOT_FOUND"}
            return self._queue.enqueue_next(track)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def add_to_playlist(self, track_id: int, playlist_id: int) -> dict:
        if self._playlists is None:
            return {"ok": False, "error": "NO_PLAYLIST_SERVICE"}
        detail = self._playlists.get_detail(playlist_id)
        if not (isinstance(detail, dict) and detail.get("ok")):
            return {"ok": False, "error": "PLAYLIST_NOT_FOUND"}
        return self._playlists.add_track(playlist_id, track_id=track_id)

    def reveal_track(self, track_id: int) -> dict:
        if not self._qs:
            return {"ok": False, "error": "NO_QUERY_SERVICE"}
        try:
            track = self._qs.fetch_track_internal(track_id)
            if not track or not track.get("filepath"):
                return {"ok": False, "error": "NOT_FOUND"}
            fm = self._file_manager()
            filepath = track["filepath"]
            ok = bool(fm.reveal_file(filepath)) if hasattr(fm, "reveal_file") else False
            if not ok:
                from pathlib import Path
                parent = str(Path(filepath).parent)
                ok = bool(fm.open_folder(parent)) if hasattr(fm, "open_folder") else False
            return {"ok": ok, "filepath": filepath}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def toggle_favorite(self, track_id: int) -> dict:
        if not self._qs:
            return {"ok": False, "error": "NO_QUERY_SERVICE"}
        if self._favorites is None:
            return {"ok": False, "error": "NO_FAVORITE_SERVICE"}
        try:
            track = self._qs.fetch_track_internal(track_id)
            if not track:
                return {"ok": False, "error": "NOT_FOUND"}
            fp = track.get("filepath", "")
            if not fp:
                return {"ok": False, "error": "NO_FILEPATH"}
            uid = track.get("track_uid") or ""
            entity_id = uid or str(track_id)
            result = self._favorites.toggle_favorite(
                "track", entity_id, public_ref=f"track_{track_id}")
            if result.ok:
                return {"ok": True, "favorite": bool(result.data.get("favorite", True))}
            return {"ok": False, "error": result.code}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── ActionContext surface (explicit target, no global selection) ────

    def _resolve_context_track(self, context: ActionContext) -> dict | None:
        if not self._qs:
            return None
        eid = str(context.entity_id or "")
        if not eid:
            return None
        track = None
        if eid.isdigit():
            track = self._qs.fetch_track_internal(int(eid))
        if track is None and hasattr(self._qs, "fetch_track_by_uid"):
            track = self._qs.fetch_track_by_uid(eid)
        if track is None and hasattr(self._qs, "fetch_track_by_filepath"):
            track = self._qs.fetch_track_by_filepath(eid)
        if track and track.get("filepath"):
            return track
        return None

    def _context_result(self, context: ActionContext,
                        result: dict, track: dict) -> dict:
        if not result.get("ok"):
            return result
        return {**result,
                "track_id": track.get("track_id", context.entity_id),
                "track_uid": track.get("track_uid", ""),
                "context_hash": context.command_hash()}

    def enqueue_context(self, context: ActionContext) -> dict:
        """Append the context track to the queue (explicit target)."""
        try:
            track = self._resolve_context_track(context)
            if track is None:
                return {"ok": False, "code": "NOT_FOUND",
                        "error": "Track not found for context"}
            result = self._queue.enqueue(track, play_now=False)
            return self._context_result(context, result, track)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def play_context(self, context: ActionContext) -> dict:
        """Play the context track now (explicit target)."""
        try:
            track = self._resolve_context_track(context)
            if track is None:
                return {"ok": False, "code": "NOT_FOUND",
                        "error": "Track not found for context"}
            result = self._queue.enqueue(track, play_now=True)
            return self._context_result(context, result, track)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def play_next_context(self, context: ActionContext) -> dict:
        """Insert the context track right after the current one."""
        try:
            track = self._resolve_context_track(context)
            if track is None:
                return {"ok": False, "code": "NOT_FOUND",
                        "error": "Track not found for context"}
            result = self._queue.enqueue_next(track)
            return self._context_result(context, result, track)
        except Exception as e:
            return {"ok": False, "error": str(e)}
