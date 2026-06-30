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
            return os.path.basename(value.replace("\\", "/"))
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
            "SELECT filepath FROM media_items WHERE deleted_at IS NULL AND kind='audio'"
        ).fetchall()
        filepaths = [r[0] for r in rows if r and r[0]]
        if not filepaths:
            return 0
        from audio_analysis.feature_extractor import make_track_key
        track_keys = [make_track_key(fp) for fp in filepaths]
        from audio_analysis.feature_repository import FeatureRepository
        repo = FeatureRepository()
        try:
            return repo.count_missing(track_keys)
        finally:
            repo.close()
    except Exception:
        logger.debug("Audio feature missing count unavailable", exc_info=True)
        return 0


def build_playback_snapshot(playback=None, recent_events: list | None = None) -> dict:
    result = {
        "now_playing": None,
        "queue_length": 0,
        "queue": {
            "active": False,
            "count": 0,
        },
        "recently_played_count": 0,
        "favorites_count": 0,
        "current_source": "local",
    }
    if playback is None:
        # Fallback: use recent events to infer queue status
        if recent_events:
            for ev in recent_events[:20]:
                if ev.get("event_type") == "queue_updated":
                    p = ev.get("payload", {})
                    c = p.get("count", 0)
                    result["queue"] = {"active": bool(c), "count": c}
                    result["queue_length"] = c
                    break
                if ev.get("event_type") == "queue_cleared":
                    result["queue"] = {"active": False, "count": 0}
                    result["queue_length"] = 0
                    break
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
            ql = playback.queue_length
            result["queue_length"] = ql
            result["queue"] = {"active": bool(ql), "count": ql}
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
    _VALID_TARGETS = frozenset({
        "metadata_editor", "audio_lab", "library", "favs",
    })

    def _safe_target(t: str) -> str:
        return t if t in _VALID_TARGETS else "library"

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
            "target": _safe_target("analysis"),
            "kind": "diagnóstico",
        })
    if ie > 0:
        actions.append({
            "title": "Revisar errores de indexación",
            "desc": f"{ie} archivos con errores al escanear.",
            "target": _safe_target("index_errors"),
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
    pb = build_playback_snapshot(playback, recent_events=recent_events)
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


def build_home_snapshot(db, playback=None, sync=None,
                        current_section: str = "",
                        selection_scope: str | None = None,
                        selection_label: str = "",
                        recent_events: list | None = None) -> dict:
    health = build_library_health_snapshot(db)
    pb = build_playback_snapshot(playback, recent_events=recent_events)
    result = {
        "library_health": health,
        "playback": pb,
        "current_context": {
            "section": current_section,
            "selection_scope": selection_scope,
            "selection_label": selection_label,
        },
        "next_actions": [],
        "warnings": [],
        "sync_peers": 0,
    }
    if pb.get("now_playing"):
        result["current_context"]["now_playing"] = pb["now_playing"]
    if pb.get("queue_length", 0) > 0:
        result["current_context"]["queue_active"] = True
    tc = health.get("track_count", 0)
    if tc > 0:
        if health.get("missing_metadata_count", 0) > 50:
            result["warnings"].append({
                "kind": "metadata",
                "message": f'{health["missing_metadata_count"]} canciones con metadatos incompletos',
            })
        if health.get("missing_cover_count", 0) > 50:
            result["warnings"].append({
                "kind": "cover",
                "message": f'{health["missing_cover_count"]} álbumes sin carátula',
            })
        if health.get("tracks_without_audio_features", 0) > 50:
            result["warnings"].append({
                "kind": "audio_features",
                "message": f'{health["tracks_without_audio_features"]} canciones sin análisis acústico',
            })
        if health.get("index_error_count", 0) > 0:
            result["warnings"].append({
                "kind": "index_error",
                "message": f'{health["index_error_count"]} errores de indexación',
            })
    elif tc == 0 and db is not None:
        result["next_actions"].append({
            "kind": "scan",
            "message": "Agregar música para empezar",
        })
    if not pb.get("now_playing") and tc > 0:
        result["next_actions"].append({
            "kind": "playback",
            "message": "Reproducir algo ahora",
        })
    if pb.get("recently_played_count", 0) < 5 and tc > 0:
        result["next_actions"].append({
            "kind": "explore",
            "message": "Descubrir nueva música",
        })
    if result["warnings"]:
        result["next_actions"].append({
            "kind": "warnings",
            "message": f'{len(result["warnings"])} aspecto(s) por revisar',
        })
    if sync is not None:
        try:
            if hasattr(sync, "peer_count"):
                result["sync_peers"] = sync.peer_count
            elif hasattr(sync, "get_all_peers"):
                result["sync_peers"] = len(sync.get_all_peers())
        except Exception as e:
            logger.debug("Home snapshot sync error: %s", e)
    result["next_actions"] = result["next_actions"][:4]
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
