from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_MAX_TRACKS = 50
_MAX_QUEUE_ITEMS = 50
_MAX_SELECTED = 100
_MAX_JOBS = 20
_MAX_ERRORS = 20
_MAX_TEXT_CHARS = 32000


class PlaybackContextProvider:
    def __init__(self, player_service: Any = None) -> None:
        self._ps = player_service

    def get_context(self) -> dict[str, Any]:
        if self._ps is None:
            return {"available": False}
        try:
            state = self._ps.state
            return {
                "state": state,
                "is_playing": state == "playing",
                "is_paused": state == "paused",
                "current_title": self._ps.current_title or "",
                "current_artist": self._ps.current_artist or "",
                "current_album": self._ps.current_album or "",
                "duration": self._ps.duration,
                "volume": int(self._ps.get_volume()) if hasattr(self._ps, "get_volume") else None,
            }
        except Exception as e:
            logger.debug("PlaybackContextProvider error: %s", e)
            return {"available": False}


class QueueContextProvider:
    def __init__(self, player_service: Any = None) -> None:
        self._ps = player_service

    def get_context(self) -> dict[str, Any]:
        if self._ps is None:
            return {"available": False}
        try:
            q = self._ps.get_queue()
            q = q or []
            limited = q[:_MAX_QUEUE_ITEMS]
            return {"count": len(q), "total_count": len(q), "items": limited}
        except Exception as e:
            logger.debug("QueueContextProvider error: %s", e)
            return {"available": False}


class LibraryContextProvider:
    def __init__(self, db: Any = None) -> None:
        self._db = db

    def get_context(self) -> dict[str, Any]:
        if self._db is None:
            return {"available": False}
        try:
            stats = self._db.get_dashboard_stats() if hasattr(self._db, "get_dashboard_stats") else self._db.get_stats()
            if not isinstance(stats, dict):
                stats = {}
            return {
                "track_count": stats.get("track_count", stats.get("total_tracks", 0)),
                "album_count": stats.get("album_count", stats.get("total_albums", 0)),
                "artist_count": stats.get("artist_count", stats.get("total_artists", 0)),
                "genre_count": stats.get("genre_count", stats.get("total_genres", 0)),
                "missing_metadata_count": stats.get("missing_metadata_count", 0),
                "missing_cover_count": stats.get("missing_cover_count", 0),
            }
        except Exception as e:
            logger.debug("LibraryContextProvider error: %s", e)
            return {"available": False}


class SelectionContextProvider:
    def __init__(self, selection_service: Any = None) -> None:
        self._ss = selection_service

    def get_context(self) -> dict[str, Any]:
        if self._ss is None:
            return {"available": False}
        try:
            sel = self._ss.get_selection() if hasattr(self._ss, "get_selection") else {}
            if not isinstance(sel, dict):
                sel = {}
            items = sel.get("items", [])[: _MAX_SELECTED]
            return {
                "count": len(items),
                "total_count": sel.get("total_count", len(items)),
                "scope": sel.get("scope", ""),
            }
        except Exception as e:
            logger.debug("SelectionContextProvider error: %s", e)
            return {"available": False}


class NavigationContextProvider:
    def __init__(self, navigation_service: Any = None) -> None:
        self._nav = navigation_service

    def get_context(self) -> dict[str, Any]:
        if self._nav is None:
            return {"available": False}
        try:
            req = self._nav.peek_last_request() if hasattr(self._nav, "peek_last_request") else None
            route = req.get("route", "") if req else ""
            return {"current_section": route}
        except Exception as e:
            logger.debug("NavigationContextProvider error: %s", e)
            return {"available": False}


class DeviceContextProvider:
    def __init__(self, sync_manager: Any = None) -> None:
        self._sm = sync_manager

    def get_context(self) -> dict[str, Any]:
        if self._sm is None:
            return {"available": False}
        try:
            peers = self._sm.get_all_peers() if hasattr(self._sm, "get_all_peers") else []
            return {"device_count": len(peers), "paired_devices": peers[:10]}
        except Exception as e:
            logger.debug("DeviceContextProvider error: %s", e)
            return {"available": False}


class ServerContextProvider:
    def __init__(self, subsonic: Any = None) -> None:
        self._subsonic = subsonic

    def get_context(self) -> dict[str, Any]:
        return {"available": False}


class SettingsContextProvider:
    def __init__(self, settings_service: Any = None) -> None:
        self._ss = settings_service

    def get_context(self) -> dict[str, Any]:
        if self._ss is None:
            return {"available": False}
        try:
            keys = ["audio/volume", "playback/repeat", "playback/shuffle", "ai/model", "ai/provider"]
            result = {}
            for k in keys:
                try:
                    result[k] = self._ss.get(k)
                except Exception:
                    result[k] = None
            return result
        except Exception as e:
            logger.debug("SettingsContextProvider error: %s", e)
            return {"available": False}


class JobContextProvider:
    def __init__(self, job_service: Any = None) -> None:
        self._js = job_service

    def get_context(self) -> dict[str, Any]:
        if self._js is None:
            return {"available": False}
        try:
            active = self._js.list_active() if hasattr(self._js, "list_active") else []
            active = active[:_MAX_JOBS]
            return {"active_count": len(active), "jobs": [{"id": j.job_id, "kind": j.kind, "status": j.status.value} for j in active]}
        except Exception as e:
            logger.debug("JobContextProvider error: %s", e)
            return {"available": False}


class DiagnosticsContextProvider:
    def __init__(self, diagnostics_service: Any = None) -> None:
        self._ds = diagnostics_service

    def get_context(self) -> dict[str, Any]:
        return {"status": "operational"}


def register_all_context_providers(assembler: Any, services: dict[str, Any]) -> None:
    assembler.register("playback", PlaybackContextProvider(services.get("player_service")))
    assembler.register("queue", QueueContextProvider(services.get("player_service")))
    assembler.register("library", LibraryContextProvider(services.get("library_db")))
    assembler.register("selection", SelectionContextProvider(services.get("selection_service")))
    assembler.register("navigation", NavigationContextProvider(services.get("navigation_service")))
    assembler.register("devices", DeviceContextProvider(services.get("sync_manager")))
    assembler.register("servers", ServerContextProvider(services.get("subsonic_client")))
    assembler.register("settings", SettingsContextProvider(services.get("settings_service")))
    assembler.register("jobs", JobContextProvider(services.get("job_service")))
    assembler.register("diagnostics", DiagnosticsContextProvider(services.get("diagnostics_service")))
