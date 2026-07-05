"""MixBridge — connects QML Mix page to real library data.

Favorites: actual favorites table JOIN (not play_count heuristic).
Recent: last_played column (not added_at).
Unplayed/Discover: play_count == 0.
Daily mix: recommendation engine or genre/artist fallback.
AI recommended: only if AI service enabled.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging

logger = logging.getLogger("michi.mix")

MIX_CATEGORIES = [
    {"id": "favorites", "title": "Favoritos", "icon": "FV", "desc": "Tus canciones marcadas como favoritas"},
    {"id": "recent", "title": "Escuchadas recientemente", "icon": "RC", "desc": "Canciones reproducidas recientemente"},
    {"id": "most_played", "title": "Más escuchadas", "icon": "MP", "desc": "Tus canciones con más reproducciones"},
    {"id": "unplayed", "title": "No escuchadas", "icon": "UN", "desc": "Canciones que aún no has reproducido"},
    {"id": "daily_mix", "title": "Mix diario", "icon": "MX", "desc": "Recomendaciones basadas en tu historial"},
    {"id": "ai_recommended", "title": "Recomendaciones IA", "icon": "AI", "desc": "Sugerencias inteligentes (IA)"},
]


def _to_dict(s, reason: str = "") -> dict:
    return {
        "title": getattr(s, 'title', '') or '',
        "artist": getattr(s, 'artist', '') or '',
        "album": getattr(s, 'album', '') or '',
        "duration": getattr(s, 'duration', 0) or 0,
        "filepath": getattr(s, 'filepath', '') or getattr(s, 'track_id', '') and "" or "",
        "track_id": getattr(s, 'id', 0) or getattr(s, 'track_id', 0) or 0,
        "reason": reason,
    }


class MixBridge(QObject):
    dataChanged = Signal()

    def __init__(self, db=None, playback_ctrl=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._player = playback_ctrl
        self._current_mix_id = ""
        self._current_mix_title = ""
        self._current_songs: list[dict] = []
        self._error_message = ""
        self._ai_enabled = False

    @Property("QVariantList", notify=dataChanged)
    def categories(self):
        cats = list(MIX_CATEGORIES)
        if not self._ai_enabled:
            cats = [c for c in cats if c["id"] != "ai_recommended"]
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

    @Slot(str, result=dict)
    def loadMix(self, mix_id: str):
        self._current_mix_id = mix_id
        category = next((c for c in MIX_CATEGORIES if c["id"] == mix_id), None)
        self._current_mix_title = category["title"] if category else "Mix"
        self._error_message = ""
        try:
            songs = self._load_mix_items(mix_id)
            self._current_songs = songs
        except Exception as e:
            logger.debug("Mix load failed: %s", e, exc_info=True)
            self._error_message = str(e)
            self._current_songs = []
        self.dataChanged.emit()
        return {"ok": True, "count": len(self._current_songs)}

    def _get_favorite_track_ids(self) -> set[str]:
        if not self._db or not hasattr(self._db, 'get_favorites'):
            return set()
        try:
            favs = self._db.get_favorites()
            return set(str(f) for f in (favs or []))
        except Exception:
            return set()

    def _get_all_items(self) -> list:
        if not self._db or not hasattr(self._db, 'fetch_all'):
            return []
        return self._db.fetch_all() or []

    def _load_mix_items(self, mix_id: str) -> list[dict]:
        items = self._get_all_items()
        if not items:
            return []

        if mix_id == "favorites":
            fav_ids = self._get_favorite_track_ids()
            matched = [s for s in items if getattr(s, 'filepath', '') in fav_ids]
            matched.sort(key=lambda x: getattr(x, 'title', '') or '')
            return [_to_dict(s, "Favorito") for s in matched[:50]]

        elif mix_id == "recent":
            played = [s for s in items if getattr(s, 'last_played', 0) or 0 > 0]
            played.sort(key=lambda x: getattr(x, 'last_played', 0) or 0, reverse=True)
            return [_to_dict(s, "Reproducida recientemente") for s in played[:30]]

        elif mix_id == "most_played":
            played = [s for s in items if getattr(s, 'play_count', 0) or 0 > 0]
            played.sort(key=lambda x: getattr(x, 'play_count', 0) or 0, reverse=True)
            return [_to_dict(s, f"{getattr(s, 'play_count', 0)} reproducciones") for s in played[:30]]

        elif mix_id == "unplayed":
            unplayed = [s for s in items if (getattr(s, 'play_count', 0) or 0) == 0]
            return [_to_dict(s, "No escuchada aún") for s in unplayed[:30]]

        elif mix_id == "daily_mix":
            return self._build_daily_mix(items)

        elif mix_id == "ai_recommended":
            if not self._ai_enabled:
                return []
            return self._build_ai_mix(items)

        return [_to_dict(s) for s in items[:25]]

    def _smart_mix_to_dict(self, track) -> dict:
        """Convert RecommendationResult to dict."""
        return {
            "title": getattr(track, 'title', '') or '',
            "artist": getattr(track, 'artist', '') or '',
            "album": getattr(track, 'album', '') or '',
            "duration": getattr(track, 'duration', 0) or 0,
            "track_id": getattr(track, 'track_id', 0) or 0,
            "reason": "Recomendado",
        }

    def _build_daily_mix(self, items: list) -> list[dict]:
        try:
            from recommendation.smart_mix_service import SmartMixService
            if self._db:
                svc = SmartMixService(self._db)
                mix = svc.create_mix(strategy="balanced_mix", limit=25)
                tracks = getattr(mix, 'tracks', []) or []
                if tracks:
                    return [self._smart_mix_to_dict(t) for t in tracks[:25]]
        except Exception as e:
            logger.debug("SmartMix daily_mix failed: %s", e)

        # Fallback: genre mix from recent tracks
        recent_with_play = [s for s in items if getattr(s, 'last_played', 0) or 0 > 0]
        recent_with_play.sort(key=lambda x: getattr(x, 'last_played', 0) or 0, reverse=True)
        recent_artists = set()
        recent_genres = set()
        for s in recent_with_play[:10]:
            artist = getattr(s, 'artist', '') or ''
            genre = getattr(s, 'genre', '') or ''
            if artist:
                recent_artists.add(artist.lower())
            if genre:
                recent_genres.add(genre.lower())

        scored = []
        for s in items:
            score = 0
            artist = (getattr(s, 'artist', '') or '').lower()
            genre = (getattr(s, 'genre', '') or '').lower()
            if artist in recent_artists:
                score += 3
            if genre in recent_genres:
                score += 1
            if score > 0:
                scored.append((score, s))

        scored.sort(key=lambda x: (-x[0], getattr(x[1], 'title', '') or ''))
        seen = set()
        result = []
        for _, s in scored:
            fp = getattr(s, 'filepath', '')
            if fp not in seen:
                seen.add(fp)
                result.append(_to_dict(s, "Mix diario"))
                if len(result) >= 25:
                    break

        if result:
            return result

        # Ultimate fallback: newest additions
        sorted_items = sorted(items, key=lambda x: getattr(x, 'created_at', 0) or 0, reverse=True)
        return [_to_dict(s, "Mix diario") for s in sorted_items[:25]]

    def _build_ai_mix(self, items: list) -> list[dict]:
        return []

    @Slot(result=dict)
    def refresh(self):
        if self._current_mix_id:
            return self.loadMix(self._current_mix_id)
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def playMix(self):
        if not self._current_songs:
            return {"ok": False, "error": "EMPTY_MIX"}
        first = self._current_songs[0]
        fp = first.get("filepath", "")
        if not fp or not self._player:
            return {"ok": False, "error": "NO_PLAYER"}
        try:
            if hasattr(self._player, 'play_file'):
                self._player.play_file(fp)
            elif hasattr(self._player, 'play'):
                self._player.play(fp)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def enqueueMix(self):
        if not self._current_songs:
            return {"ok": False, "error": "EMPTY_MIX"}
        fps = [s.get("filepath", "") for s in self._current_songs if s.get("filepath")]
        if not fps or not self._player:
            return {"ok": False, "error": "NO_PLAYER"}
        try:
            if hasattr(self._player, 'enqueue_multiple'):
                self._player.enqueue_multiple(fps)
            elif hasattr(self._player, 'enqueue'):
                for fp in fps:
                    self._player.enqueue(fp)
            return {"ok": True, "count": len(fps)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def saveMixAsPlaylist(self, name: str):
        if not name:
            return {"ok": False, "error": "EMPTY_NAME"}
        return {"ok": False, "error": "UNSUPPORTED"}

    @Slot(result=dict)
    def explainCurrentMix(self):
        if not self._current_songs:
            return {"ok": False, "error": "EMPTY_MIX"}
        reasons = set()
        for s in self._current_songs[:5]:
            r = s.get("reason", "")
            if r:
                reasons.add(r)
        return {"ok": True, "reasons": list(reasons)[:3]}
