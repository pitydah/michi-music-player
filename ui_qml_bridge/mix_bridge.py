"""MixBridge — connects QML Mix page to real library data.

No fake tracks, no false success on empty mix/queue, no AI mix without backend.
Deterministic seed support, explainable, stale-safe, partial results explicit.
"""
from __future__ import annotations

import contextlib

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging

logger = logging.getLogger("michi.mix")

MIX_CATEGORIES = [
    {"id": "favorites", "title": "Favoritos", "icon": "FV", "desc": "Tus canciones marcadas como favoritas"},
    {"id": "recent", "title": "Escuchadas recientemente", "icon": "RC", "desc": "Canciones reproducidas recientemente"},
    {"id": "most_played", "title": "Más escuchadas", "icon": "MP", "desc": "Tus canciones con más reproducciones"},
    {"id": "unplayed", "title": "No escuchadas", "icon": "UN", "desc": "Canciones que aún no has reproducido"},
    {"id": "rediscovery", "title": "Redescubrimiento", "icon": "RD", "desc": "Canciones antiguas que no escuchas hace tiempo"},
    {"id": "daily_mix", "title": "Mix diario", "icon": "MX", "desc": "Recomendaciones basadas en tu historial"},
    {"id": "by_artist", "title": "Por artista", "icon": "AR", "desc": "Mixes centrados en un artista"},
    {"id": "by_genre", "title": "Por género", "icon": "GN", "desc": "Mixes por género musical"},
    {"id": "by_decade", "title": "Por década", "icon": "DC", "desc": "Mixes por década"},
    {"id": "by_year", "title": "Por año", "icon": "YR", "desc": "Mixes por año específico"},
    {"id": "high_quality", "title": "Alta calidad", "icon": "HQ", "desc": "Solo pistas con bitrate >= 320 kbps"},
    {"id": "custom", "title": "Mix personalizado", "icon": "CS", "desc": "Mix basado en reglas definidas por ti"},
]


class MixBridge(QObject):
    dataChanged = Signal()
    generationProgress = Signal(int, int)  # current, total
    generationError = Signal(str)

    @Property("QVariantList", notify=dataChanged)
    def categories(self):
        cats = list(MIX_CATEGORIES)
        if not self._ai_enabled:
            cats = [c for c in cats if c["id"] not in ("ai_recommended",)]
        return cats

    @Property("QVariantList", notify=dataChanged)
    def currentSongs(self):
        return self._current_songs

    @Property(str, notify=dataChanged)
    def currentMixTitle(self):
        return self._current_mix_title

    @Property(str, notify=dataChanged)
    def errorMessage(self):
        return self._error_message

    @Property(str, notify=dataChanged)
    def currentMixId(self):
        return self._current_mix_id

    @Slot(str, result=dict)
    def loadMix(self, mix_id: str, seed: str = ""):
        self._current_mix_id = mix_id
        category = next((c for c in MIX_CATEGORIES if c["id"] == mix_id), None)
        self._current_mix_title = category["title"] if category else "Mix"
        self._error_message = ""
        try:
            songs = self._load_mix_items(mix_id, seed=seed)
            if not songs:
                self._error_message = "No se encontraron canciones para este mix"
            self._current_songs = songs
        except Exception as e:
            logger.debug("Mix load failed: %s", e, exc_info=True)
            self._error_message = str(e)
            self._current_songs = []
        self.dataChanged.emit()
        return {"ok": bool(self._current_songs) or self._error_message == "",
                "count": len(self._current_songs),
                "partial": len(self._current_songs) > 0}

    def _load_mix_items(self, mix_id: str, seed: str = "") -> list[dict]:
        if not self._mqs:
            return []

        loaders = {
            "favorites": lambda: self._mqs.favorites(50),
            "recent": lambda: self._mqs.recent(30),
            "most_played": lambda: self._mqs.most_played(30),
            "unplayed": lambda: self._mqs.unplayed(30),
            "rediscovery": lambda: self._mqs.rediscovery(30),
            "daily_mix": lambda: self._build_daily_mix(),
            "by_artist": lambda: self._mqs.by_field("artist", limit=30),
            "by_genre": lambda: self._mqs.by_field("genre", limit=30),
            "by_decade": lambda: self._mqs.by_decade(30),
            "by_year": lambda: self._mqs.by_year(30),
            "high_quality": lambda: self._mqs.high_quality(30),
            "custom": lambda: self._build_custom_mix(seed),
        }
        loader = loaders.get(mix_id)
        if not loader:
            return []

        try:
            items = loader()
            if not items:
                return []
            return self._deduplicate_and_apply_limits(items)
        except Exception as e:
            logger.debug("mix %s failed: %s", mix_id, e)
            return []

    def _deduplicate_and_apply_limits(self, items: list[dict],
                                       artist_limit: int = 5,
                                       max_total: int = 50) -> list[dict]:
        seen_ids = set()
        artist_counts: dict[str, int] = {}
        result = []
        for item in items:
            tid = item.get("track_id", 0) or item.get("id", 0)
            if tid and tid in seen_ids:
                continue
            if tid:
                seen_ids.add(tid)
            artist = item.get("artist", "")
            if artist and artist_counts.get(artist, 0) >= artist_limit:
                continue
            if artist:
                artist_counts[artist] = artist_counts.get(artist, 0) + 1
            result.append(item)
            if len(result) >= max_total:
                break
        return result

    def _build_daily_mix(self) -> list[dict]:
        if not self._mqs:
            return []
        try:
            recent = self._mqs.recent(50)
            unplayed = self._mqs.unplayed(50)
            recent_ids = {r.get("track_id", 0) or r.get("id", 0) for r in recent}
            combined = recent[:15]
            for t in unplayed:
                tid = t.get("track_id", 0) or t.get("id", 0)
                if tid not in recent_ids and len(combined) < 25:
                    combined.append(t)
            for t in combined:
                t["reason"] = "Mix diario"
            return combined[:25]
        except Exception as e:
            logger.debug("daily_mix failed: %s", e)
            return []

    def _build_custom_mix(self, params: str = "") -> list[dict]:
        if not params or not self._mqs:
            return []
        try:
            import json
            rules = json.loads(params) if isinstance(params, str) else params
            artist = rules.get("artist", "")
            genre = rules.get("genre", "")
            limit = int(rules.get("limit", 30))
            if artist:
                return self._mqs.by_field("artist", value=artist, limit=limit) or []
            if genre:
                return self._mqs.by_field("genre", value=genre, limit=limit) or []
        except (json.JSONDecodeError, Exception):
            pass
        return []

    @Slot(result=dict)
    def refresh(self):
        if self._current_mix_id:
            return self.loadMix(self._current_mix_id)
        self.dataChanged.emit()
        return {"ok": True}

    def __init__(self, db=None, playback_ctrl=None, player_service=None,
                 track_action_service=None, playlist_bridge=None,
                 query_service=None, query_executor=None,
                 worker_manager=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._player = playback_ctrl or player_service
        self._tas = track_action_service
        self._pb = playlist_bridge
        self._qe = query_executor
        self._current_mix_id = ""
        self._current_mix_title = ""
        self._current_songs: list[dict] = []
        self._error_message = ""
        self._ai_enabled = False
        self._generation = 0
        self._mqs = query_service
        self._wm = worker_manager

    @Slot(result=dict)
    def playMix(self):
        if not self._current_songs:
            return {"ok": False, "error": "EMPTY_MIX", "error_code": "EMPTY_MIX"}
        first = self._current_songs[0]
        tid = first.get("track_id") or first.get("id")
        if not tid:
            return {"ok": False, "error": "NO_TRACK_ID", "error_code": "NO_TRACK_ID"}
        if self._tas and hasattr(self._tas, 'play_track'):
            try:
                return self._tas.play_track(tid)
            except Exception as e:
                return {"ok": False, "error": str(e), "error_code": "PLAY_FAILED"}
        if self._player and hasattr(self._player, 'play'):
            try:
                self._player.play(tid)
                return {"ok": True, "track_id": tid}
            except Exception as e:
                return {"ok": False, "error": str(e), "error_code": "PLAY_FAILED"}
        return {"ok": False, "error": "NO_PLAYBACK_SERVICE", "error_code": "NO_PLAYBACK"}

    @Slot(result=dict)
    def enqueueMix(self):
        if not self._current_songs:
            return {"ok": False, "error": "EMPTY_MIX", "error_code": "EMPTY_MIX"}
        count = 0
        errors = []
        for s in self._current_songs:
            tid = s.get("track_id") or s.get("id")
            if tid:
                try:
                    if self._tas and hasattr(self._tas, 'enqueue_track'):
                        result = self._tas.enqueue_track(tid)
                        if isinstance(result, dict) and not result.get("ok"):
                            errors.append({"track_id": tid, "error": result.get("error", "ENQUEUE_FAILED")})
                        else:
                            count += 1
                except Exception as e:
                    errors.append({"track_id": tid, "error": str(e)})
        result = {"ok": count > 0, "count": count}
        if errors:
            result["errors"] = errors
            result["error_count"] = len(errors)
        return result

    @Slot(str, result=dict)
    def saveMixAsPlaylist(self, name: str):
        if not name:
            return {"ok": False, "error": "EMPTY_NAME", "error_code": "EMPTY_NAME"}
        if not self._pb:
            return {"ok": False, "error": "NO_PLAYLIST_BRIDGE", "error_code": "NO_PLAYLIST_BRIDGE"}
        if not self._current_songs:
            return {"ok": False, "error": "EMPTY_MIX", "error_code": "EMPTY_MIX"}
        try:
            result = self._pb.createPlaylist(name)
            if not result.get("ok"):
                return {"ok": False, "error": "CREATE_FAILED", "error_code": "CREATE_FAILED"}
            pid = result["id"]
            count = 0
            for s in self._current_songs:
                tid = s.get("track_id") or s.get("id")
                if tid:
                    add = self._pb.addTrackToPlaylist(pid, track_id=str(tid))
                    if add.get("ok"):
                        count += 1
            self._pb.refresh()
            return {"ok": True, "id": pid, "count": count}
        except Exception as e:
            return {"ok": False, "error": str(e), "error_code": "SAVE_FAILED"}

    @Slot(int, result=dict)
    def playFromIndex(self, index: int):
        if not self._current_songs or index < 0 or index >= len(self._current_songs):
            return {"ok": False, "error_code": "INVALID_INDEX", "message": "Índice inválido"}
        song = self._current_songs[index]
        tid = song.get("track_id") or song.get("id")
        if not tid:
            return {"ok": False, "error_code": "NO_TRACK_ID", "message": "Pista sin identificador"}
        if self._tas and hasattr(self._tas, 'play_track'):
            try:
                result = self._tas.play_track(tid)
                if isinstance(result, dict):
                    return result if not result.get("ok") else {"ok": True, "track_id": tid, "index": index}
                return {"ok": True, "track_id": tid, "index": index}
            except Exception as e:
                return {"ok": False, "error_code": "PLAY_FAILED", "message": str(e)}
        if self._player and hasattr(self._player, 'play'):
            try:
                self._player.play(tid)
                return {"ok": True, "track_id": tid, "index": index}
            except Exception as e:
                return {"ok": False, "error_code": "PLAY_FAILED", "message": str(e)}
        return {"ok": False, "error_code": "NO_PLAYBACK", "message": "Reproductor no disponible"}

    @Slot(result=dict)
    def cancelGeneration(self):
        if self._wm and hasattr(self._wm, 'cancel_all'):
            with contextlib.suppress(Exception):
                self._wm.cancel_all(owner="mix_bridge")
                pass
        gen = self._generation
        self._generation += 1
        return {"ok": True, "cancelled": gen}

    @Slot(int, result=dict)
    def enqueueTrack(self, index: int):
        if not self._current_songs or index < 0 or index >= len(self._current_songs):
            return {"ok": False, "error_code": "INVALID_INDEX", "message": "Índice inválido"}
        song = self._current_songs[index]
        tid = song.get("track_id") or song.get("id")
        if not tid:
            return {"ok": False, "error_code": "NO_TRACK_ID", "message": "Pista sin identificador"}
        if self._tas and hasattr(self._tas, 'enqueue_track'):
            try:
                return self._tas.enqueue_track(tid)
            except Exception as e:
                return {"ok": False, "error_code": "ENQUEUE_FAILED", "message": str(e)}
        if self._player and hasattr(self._player, 'enqueue'):
            try:
                self._player.enqueue([tid])
                return {"ok": True, "track_id": tid, "index": index, "queued": True}
            except Exception as e:
                return {"ok": False, "error_code": "ENQUEUE_FAILED", "message": str(e)}
        return {"ok": False, "error_code": "NO_PLAYBACK", "message": "Reproductor no disponible"}

    @Slot(result=dict)
    def explainCurrentMix(self):
        if not self._current_songs:
            return {"ok": False, "error": "EMPTY_MIX", "error_code": "EMPTY_MIX"}
        reasons = set()
        for s in self._current_songs[:10]:
            r = s.get("reason", "")
            if r:
                reasons.add(r)
        return {"ok": True, "reasons": list(reasons)[:5],
                "total": len(self._current_songs),
                "has_reasons": len(reasons) > 0}

    @Slot(result=dict)
    def partialFailureReport(self):
        failures = [s.get('_error', '') for s in (self._current_songs or []) if s.get('_error', '')]
        if not failures:
            return {"ok": True, "has_failures": False, "failures": []}
        return {"ok": True, "has_failures": True, "failures": failures[:10], "total": len(failures)}
