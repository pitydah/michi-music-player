"""Shared canonical RadioService mocks for QML radio tests.

The RadioBridge delegates to the injected service API
(get_stations/add_station/edit_station/delete_station/favorite_station/
search_stations/get_history/clear_history/mark_played). These helpers build a
mock service with that API so bridge tests exercise the thin-adapter contract.
"""
from __future__ import annotations

from unittest.mock import MagicMock


def station_dicts() -> list[dict]:
    return [
        {"id": 1, "name": "Jazz FM", "url": "http://jazz.stream", "codec": "MP3",
         "country": "US", "tags": ["jazz", "cool"], "favorite": True,
         "image_path": "", "bitrate": 128},
        {"id": 2, "name": "Rock FM", "url": "http://rock.stream", "codec": "AAC",
         "country": "UK", "tags": ["rock", "classic"], "favorite": False,
         "image_path": "", "bitrate": 256},
    ]


def make_radio_service_mock(stations=None, history=None) -> MagicMock:
    """MagicMock exposing the canonical RadioService API.

    - ``search_stations`` filters by name/url substring (like the service).
    - ``mark_played`` appends to the history list; ``get_history`` reflects it.
    """
    stations = list(stations) if stations is not None else station_dicts()
    history: list[dict] = list(history) if history is not None else []

    def _search_stations(query: str = ""):
        q = (query or "").lower()
        if not q:
            results = list(stations)
        else:
            results = [s for s in stations
                       if q in s.get("name", "").lower()
                       or q in s.get("url", "").lower()]
        return {"ok": True, "results": results, "count": len(results)}

    def _mark_played(station_id):
        station = next(
            (s for s in stations if str(s.get("id")) == str(station_id)), None,
        )
        if station is None:
            return {"ok": False, "error": "NOT_FOUND"}
        history.insert(0, {
            "name": station.get("name", ""),
            "url": station.get("url", ""),
            "played_at": "now",
        })
        return {"ok": True}

    svc = MagicMock()
    svc.get_stations.return_value = list(stations)
    svc.get_favorites.return_value = [s for s in stations if s.get("favorite")]
    svc.get_history.side_effect = lambda limit=50: list(history)[:limit]
    svc.add_station.return_value = {"ok": True, "id": 99}
    svc.edit_station.return_value = {"ok": True}
    svc.delete_station.return_value = {"ok": True}
    svc.favorite_station.return_value = {"ok": True, "favorite": True}
    svc.search_stations.side_effect = _search_stations
    svc.mark_played.side_effect = _mark_played
    svc.clear_history.side_effect = lambda: history.clear() or {"ok": True}
    return svc
