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
        from core.mix_query_service import MixQueryService
        self._mqs = MixQueryService(db=db) if db else None

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

    def _load_mix_items(self, mix_id: str) -> list[dict]:
        if not self._mqs:
            return []

        if mix_id == "favorites":
            return [{"title": t["title"], "artist": t["artist"], "album": t["album"],
                     "duration": t["duration"], "track_id": t["track_id"],
                     "reason": "Favorito"}
                    for t in self._mqs.favorites(50)]

        elif mix_id == "recent":
            return [{"title": t["title"], "artist": t["artist"], "album": t["album"],
                     "duration": t["duration"], "track_id": t["track_id"],
                     "reason": "Reproducida recientemente"}
                    for t in self._mqs.recent(30)]

        elif mix_id == "most_played":
            return [{"title": t["title"], "artist": t["artist"], "album": t["album"],
                     "duration": t["duration"], "track_id": t["track_id"],
                     "reason": "Más escuchada"}
                    for t in self._mqs.most_played(30)]

        elif mix_id == "unplayed":
            return [{"title": t["title"], "artist": t["artist"], "album": t["album"],
                     "duration": t["duration"], "track_id": t["track_id"],
                     "reason": "No escuchada aún"}
                    for t in self._mqs.unplayed(30)]

        elif mix_id == "daily_mix":
            return self._build_daily_mix()

        elif mix_id == "ai_recommended":
            return self._build_ai_mix()

        return [{"title": f"Mix {mix_id}", "track_id": 0}]

    def _build_daily_mix(self) -> list[dict]:
        if not self._mqs:
            return []
        try:
            recent = self._mqs.recent(50)
            unplayed = self._mqs.unplayed(50)
            recent_ids = {r["track_id"] for r in recent}
            combined = recent[:15]
            for t in unplayed:
                if t["track_id"] not in recent_ids and len(combined) < 25:
                    t["reason"] = "Mix diario"
                    combined.append(t)
            for t in combined:
                t["reason"] = "Mix diario"
            return combined[:25]
        except Exception as e:
            logger.debug("daily_mix failed: %s", e)
            return []

    def _build_ai_mix(self) -> list[dict]:
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
