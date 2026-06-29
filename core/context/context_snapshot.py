"""Context snapshots — compact, deterministic builders for UI and Assistant.

Each snapshot is a small dict (no track lists, no absolute paths).
"""

from __future__ import annotations

import logging
import os
from typing import Any


logger = logging.getLogger("michi.context_snapshot")


def sanitize_snapshot(value):
    """Return a JSON-safe snapshot without absolute paths or huge payloads."""
    PATH_KEYS = {"filepath", "filepaths", "path", "paths", "uri"}
    if isinstance(value, dict):
        clean = {}
        for k, v in value.items():
            if k in PATH_KEYS:
                continue
            clean[k] = sanitize_snapshot(v)
        return clean
    if isinstance(value, list):
        return [sanitize_snapshot(v) for v in value[:10]]
    if isinstance(value, str):
        if value.startswith("/") or ":\\" in value:
            return os.path.basename(value)
        return value[:300]
    return value


def build_library_health_snapshot(db) -> dict:
    """Quick health overview — reuses get_dashboard_stats if available."""
    result: dict[str, Any] = {
        "track_count": 0,
        "album_count": 0,
        "artist_count": 0,
        "genre_count": 0,
        "missing_metadata_count": 0,
        "missing_cover_count": 0,
        "tracks_without_audio_features": 0,
        "index_error_count": 0,
        "last_scan": None,
    }
    if db is None:
        return result
    try:
        if hasattr(db, "get_dashboard_stats"):
            stats = db.get_dashboard_stats()
            result["track_count"] = stats.get("total_songs", 0)
            result["album_count"] = stats.get("total_albums", 0)
            result["artist_count"] = stats.get("total_artists", 0)
            result["missing_metadata_count"] = stats.get("missing_metadata", 0)
        elif hasattr(db, "get_stats"):
            stats = db.get_stats()
            result["track_count"] = stats.get("total", 0)
    except Exception as e:
        logger.debug("Library health snapshot error (dashboard): %s", e)
    try:
        conn = db.conn if hasattr(db, "conn") else None
        if conn:
            result["genre_count"] = conn.execute(
                "SELECT COUNT(DISTINCT COALESCE(NULLIF(genre,''),'Sin género')) "
                "FROM media_items WHERE deleted_at IS NULL"
            ).fetchone()[0]
            result["index_error_count"] = conn.execute(
                "SELECT COUNT(*) FROM media_items WHERE scan_status=? AND deleted_at IS NULL",
                ("error",),
            ).fetchone()[0]
            result["tracks_without_audio_features"] = _count_tracks_without_audio_features(conn)
    except Exception:
        logger.debug("Library health snapshot error (extra queries)")
    return result


def _count_tracks_without_audio_features(conn) -> int:
    try:
        rows = conn.execute(
            "SELECT COALESCE(NULLIF(track_uid,''), filepath) "
            "FROM media_items WHERE deleted_at IS NULL AND kind='audio'"
        ).fetchall()
        track_keys = [r[0] for r in rows if r and r[0]]
        if not track_keys:
            return 0
        from audio_analysis.feature_repository import FeatureRepository
        repo = FeatureRepository()
        try:
            return repo.count_missing(track_keys)
        finally:
            repo.close()
    except Exception:
        logger.debug("Audio feature missing count unavailable", exc_info=True)
        return 0


def build_playback_snapshot(playback=None) -> dict:
    result = {
        "now_playing": None,
        "queue_length": 0,
        "recently_played_count": 0,
        "favorites_count": 0,
        "current_source": "local",
    }
    if playback is None:
        return result
    try:
        if hasattr(playback, "current_track") and playback.current_track:
            track = playback.current_track
            result["now_playing"] = {
                "title": getattr(track, "title", None) or getattr(track, "name", None),
                "artist": getattr(track, "artist", None),
                "album": getattr(track, "album", None),
            }
        if hasattr(playback, "queue_length"):
            result["queue_length"] = playback.queue_length
        if hasattr(playback, "recent_count"):
            result["recently_played_count"] = playback.recent_count
        if hasattr(playback, "favorites_count"):
            result["favorites_count"] = playback.favorites_count
        if hasattr(playback, "source_type"):
            result["current_source"] = playback.source_type
    except Exception as e:
        logger.debug("Playback snapshot error: %s", e)
    return result


def _suggested_actions(health: dict, playback: dict) -> list[dict]:
    actions = []
    mm = health.get("missing_metadata_count", 0)
    mc = health.get("missing_cover_count", 0)
    af = health.get("tracks_without_audio_features", 0)
    ie = health.get("index_error_count", 0)
    tc = health.get("track_count", 0)
    np = playback.get("now_playing")
    rp = playback.get("recently_played_count", 0)
    fv = playback.get("favorites_count", 0)

    if mm > 50:
        actions.append({
            "title": "Revisar metadatos pendientes",
            "desc": f"{mm} canciones con metadatos incompletos.",
            "target": "metadata_editor",
            "kind": "metadata",
        })
    if mc > 50:
        actions.append({
            "title": "Buscar carátulas faltantes",
            "desc": f"{mc} álbumes sin carátula.",
            "target": "metadata_editor",
            "kind": "metadata",
        })
    if af > 50:
        actions.append({
            "title": "Analizar audio faltante",
            "desc": f"{af} canciones sin análisis acústico.",
            "target": "audio_lab",
            "kind": "diagnóstico",
        })
    if ie > 0:
        actions.append({
            "title": "Revisar errores de indexación",
            "desc": f"{ie} archivos con errores al escanear.",
            "target": "audio_lab",
            "kind": "diagnóstico",
        })
    if tc > 0 and rp < 5:
        actions.append({
            "title": "Reproducir música",
            "desc": "Aún no hay suficiente historial de reproducción.",
            "target": "library",
            "kind": "reproducción",
        })
    if tc > 0 and fv < 3:
        actions.append({
            "title": "Marcar favoritos",
            "desc": "Aún hay pocos favoritos. Empieza marcando canciones que te gusten.",
            "target": "favs",
            "kind": "favorito",
        })
    if not np and tc > 0:
        actions.append({
            "title": "Reproducir algo ahora",
            "desc": "No hay ninguna canción reproduciéndose.",
            "target": "library",
            "kind": "reproducción",
        })
    return actions[:5]


def build_assistant_snapshot(db, playback=None,
                              current_section: str = "",
                              current_tab: str = "",
                              recent_events: list | None = None) -> dict:
    health = build_library_health_snapshot(db)
    pb = build_playback_snapshot(playback)
    result = {
        "route": {"current_section": current_section, "current_tab": current_tab},
        "playback": {
            "now_playing": pb.get("now_playing"),
            "queue_length": pb.get("queue_length", 0),
            "current_source": pb.get("current_source", "local"),
            "recently_played_count": pb.get("recently_played_count", 0),
            "favorites_count": pb.get("favorites_count", 0),
        },
        "library_health": health,
        "recent_events": sanitize_snapshot(recent_events or [])[:10],
        "suggested_actions": _suggested_actions(health, pb),
    }
    # Compatibility keys
    result["current_section"] = current_section
    result["current_library_tab"] = current_tab
    result["now_playing"] = pb.get("now_playing")
    result["queue_length"] = pb.get("queue_length", 0)
    return sanitize_snapshot(result)


def build_home_snapshot(db, playback=None, sync=None) -> dict:
    health = build_library_health_snapshot(db)
    pb = build_playback_snapshot(playback)
    result = {
        "library_health": health,
        "now_playing": pb.get("now_playing"),
        "queue_length": pb.get("queue_length", 0),
        "favorites_count": pb.get("favorites_count", 0),
        "sync_peers": 0,
    }
    if sync is not None:
        try:
            if hasattr(sync, "peer_count"):
                result["sync_peers"] = sync.peer_count
            elif hasattr(sync, "get_all_peers"):
                result["sync_peers"] = len(sync.get_all_peers())
        except Exception as e:
            logger.debug("Home snapshot sync error: %s", e)
    return result


def build_mix_snapshot(db) -> dict:
    health = build_library_health_snapshot(db)
    result = {
        "total_tracks": health.get("track_count", 0),
        "total_artists": health.get("artist_count", 0),
        "total_albums": health.get("album_count", 0),
        "missing_metadata": health.get("missing_metadata_count", 0),
        "available_mixes": [
            "mix_daily", "mix_unplayed", "mix_popular",
            "mix_favorites", "favs", "recent",
        ],
        "mix_health": {
            "has_library": health.get("track_count", 0) > 0,
            "has_enough_history": False,
            "has_favorites": False,
            "has_audio_features": health.get("tracks_without_audio_features", 0) < health.get("track_count", 0),
        },
    }
    try:
        if db and hasattr(db, "get_favorites"):
            result["mix_health"]["has_favorites"] = len(db.get_favorites()) > 0
        if db and hasattr(db, "get_play_history"):
            result["mix_health"]["has_enough_history"] = len(db.get_play_history(limit=10)) >= 5
    except Exception:
        logger.debug("Mix snapshot health unavailable")
    return result
