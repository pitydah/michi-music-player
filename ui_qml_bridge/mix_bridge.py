"""MixBridge — connects QML Mix page to real library data."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging

logger = logging.getLogger("michi.mix")

MIX_CATEGORIES = [
    {"id": "daily_mix", "title": "Mix diario", "icon": "MX", "desc": "Recomendaciones basadas en tu historial reciente"},
    {"id": "favorites", "title": "Favoritos", "icon": "FV", "desc": "Tus canciones marcadas como favoritas"},
    {"id": "recent", "title": "Escuchadas recientemente", "icon": "RC", "desc": "Canciones que has reproducido"},
    {"id": "most_played", "title": "Más escuchadas", "icon": "MP", "desc": "Tus canciones con más reproducciones"},
    {"id": "discover", "title": "Hallazgos", "icon": "DI", "desc": "Canciones que no has escuchado en tu biblioteca"},
    {"id": "ai_recommended", "title": "Recomendaciones IA", "icon": "AI", "desc": "Sugerencias inteligentes basadas en patrones"},
]


class MixBridge(QObject):
    dataChanged = Signal()

    def __init__(self, db=None, playback_ctrl=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._player = playback_ctrl
        self._current_mix_id = ""
        self._current_mix_title = ""
        self._current_songs = []
        self._error_message = ""

    @Property("QVariantList", notify=dataChanged)
    def categories(self):
        return MIX_CATEGORIES

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
            items = self._db.fetch_all() if self._db and hasattr(self._db, 'fetch_all') else []
            songs = self._filter_mix_items(items, mix_id)
            self._current_songs = [self._to_dict(s) for s in songs]
        except Exception as e:
            logger.debug("Mix load failed", exc_info=True)
            self._error_message = str(e)
            self._current_songs = []
        self.dataChanged.emit()
        return {"ok": True, "count": len(self._current_songs)}

    @Slot(result=dict)
    def refresh(self):
        if self._current_mix_id:
            return self.loadMix(self._current_mix_id)
        self.dataChanged.emit()
        return {"ok": True}

    def _filter_mix_items(self, items, mix_id):
        if not items:
            return []
        if mix_id == "favorites":
            return sorted(items, key=lambda x: getattr(x, 'play_count', 0) or 0, reverse=True)[:20]
        elif mix_id == "recent":
            return sorted(items, key=lambda x: getattr(x, 'added_at', 0) or 0, reverse=True)[:15]
        elif mix_id == "most_played":
            return sorted(items, key=lambda x: getattr(x, 'play_count', 0) or 0, reverse=True)[:20]
        elif mix_id == "discover":
            played = sorted(items, key=lambda x: getattr(x, 'play_count', 0) or 0)[:30]
            return played
        else:
            return items[:25]

    @staticmethod
    def _to_dict(s):
        return {
            "title": getattr(s, 'title', '') or '',
            "artist": getattr(s, 'artist', '') or '',
            "album": getattr(s, 'album', '') or '',
            "duration": getattr(s, 'duration', 0) or 0,
            "filepath": getattr(s, 'filepath', '') or '',
            "track_id": getattr(s, 'id', 0) or 0,
        }
