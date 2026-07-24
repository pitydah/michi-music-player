"""RadioRepository — persistence for radio stations, favorites, history."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("core.radio.repository")


@dataclass
class RadioStation:
    name: str
    url: str
    id: str = ""
    genre: str = ""
    country: str = ""
    language: str = ""
    bitrate: int = 0
    codec: str = ""
    favorite: bool = False
    last_played: float = 0.0
    play_count: int = 0
    tags: list[str] = field(default_factory=list)


class RadioRepository:
    def __init__(self, db=None, storage_path: str = ""):
        self._db = db
        self._stations: dict[str, RadioStation] = {}
        self._favorites: set[str] = set()
        self._history: list[dict] = []
        self._dirty = False

    def add_station(self, station: RadioStation) -> dict:
        sid = station.id or station.url
        self._stations[sid] = station
        self._dirty = True
        return {"ok": True, "id": sid}

    def remove_station(self, station_id: str) -> dict:
        if station_id in self._stations:
            del self._stations[station_id]
            self._favorites.discard(station_id)
            self._dirty = True
            return {"ok": True}
        return {"ok": False, "error": "NOT_FOUND"}

    def get_station(self, station_id: str) -> RadioStation | None:
        return self._stations.get(station_id)

    def get_all_stations(self) -> list[RadioStation]:
        return list(self._stations.values())

    def search(self, query: str) -> list[RadioStation]:
        q = query.lower().strip()
        if not q:
            return self.get_all_stations()
        results = []
        for s in self._stations.values():
            if q in s.name.lower() or q in s.url.lower() or q in s.genre.lower():
                results.append(s)
        return results

    def toggle_favorite(self, station_id: str) -> dict:
        if station_id not in self._stations:
            return {"ok": False, "error": "NOT_FOUND"}
        if station_id in self._favorites:
            self._favorites.discard(station_id)
            self._stations[station_id].favorite = False
        else:
            self._favorites.add(station_id)
            self._stations[station_id].favorite = True
        self._dirty = True
        return {"ok": True, "favorite": station_id in self._favorites}

    def get_favorites(self) -> list[RadioStation]:
        return [s for sid, s in self._stations.items() if sid in self._favorites]

    def record_play(self, station_id: str) -> dict:
        if station_id not in self._stations:
            return {"ok": False, "error": "NOT_FOUND"}
        import time
        s = self._stations[station_id]
        s.last_played = time.time()
        s.play_count += 1
        self._history.append({"station_id": station_id, "timestamp": s.last_played,
                              "name": s.name, "url": s.url})
        self._dirty = True
        return {"ok": True}

    def get_history(self, limit: int = 50) -> list[dict]:
        return sorted(self._history, key=lambda x: x.get("timestamp", 0), reverse=True)[:limit]

    def clear_history(self) -> dict:
        self._history = []
        self._dirty = True
        return {"ok": True}

    def import_stations(self, stations: list[dict]) -> dict:
        count = 0
        for s in stations:
            station = RadioStation(
                name=s.get("name", "Unknown"),
                url=s.get("url", ""),
                genre=s.get("genre", ""),
                country=s.get("country", ""),
                bitrate=s.get("bitrate", 0),
                codec=s.get("codec", ""),
            )
            result = self.add_station(station)
            if result.get("ok"):
                count += 1
        return {"ok": True, "imported": count}
