"""RadioBridge — thin adapter over the canonical radio service.

QML emits intention; the bridge validates and delegates. The bridge keeps no
parallel state: stations/favorites/history are read from the injected
``RadioService`` (``get_stations``/``get_favorites``/``get_history``), CRUD
delegates (``add_station``/``edit_station``/``delete_station``/``favorite_station``),
and ``isPlaying`` is only set when the player backend confirms playback
(state readback / ``state_changed`` signal), never optimistically.
"""
from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer

logger = logging.getLogger("michi.radio")

_CONNECT_TIMEOUT_MS = 15000
_CONFIRM_CHECK_MS = 1200
_HISTORY_LIMIT = 50


class RadioBridge(QObject):
    dataChanged = Signal()

    def __init__(self, radio_manager: Any = None,
                 player_service: Any = None,
                 parent=None):
        super().__init__(parent)
        self._radio_mgr = radio_manager
        self._player = player_service
        self._stations: list[dict] = []
        self._favorites: list[dict] = []
        self._current_station = ""
        self._current_station_name = ""
        self._reconnect_attempts = 0
        self._is_playing = False
        self._is_buffering = False
        self._metadata: dict = {}
        self._connect_timer: QTimer | None = None
        self._confirm_timer: QTimer | None = None
        self._pending_connect = False
        self._buffer_timeout_ms = _CONNECT_TIMEOUT_MS
        self._connect_player_signals()

    def _connect_player_signals(self):
        state_changed = getattr(self._player, "state_changed", None)
        if state_changed is not None and hasattr(state_changed, "connect"):
            try:
                state_changed.connect(self._on_player_state_changed)
            except Exception:
                logger.debug("Radio: could not subscribe to player state_changed", exc_info=True)

    @property
    def radio_manager(self) -> Any:
        return self._radio_mgr

    @radio_manager.setter
    def radio_manager(self, value: Any):
        self._radio_mgr = value

    @Property("QVariantList", notify=dataChanged)
    def stations(self):
        return self._stations

    @Property("QVariantList", notify=dataChanged)
    def favorites(self):
        return self._favorites

    @Property("QVariantList", notify=dataChanged)
    def history(self):
        if self._radio_mgr is None:
            return []
        get_history = getattr(self._radio_mgr, "get_history", None)
        if get_history is None:
            return []
        try:
            entries = get_history(_HISTORY_LIMIT) or []
        except Exception:
            logger.debug("Radio: history read failed", exc_info=True)
            return []
        return [self._history_entry(e) for e in entries[:_HISTORY_LIMIT]]

    @Property(str, notify=dataChanged)
    def currentStation(self):
        return self._current_station

    @Property(str, notify=dataChanged)
    def currentStationName(self):
        return self._current_station_name

    @Property(bool, notify=dataChanged)
    def isPlaying(self):
        return self._is_playing

    @Property(bool, notify=dataChanged)
    def isBuffering(self):
        return self._is_buffering

    @Property(int, notify=dataChanged)
    def reconnectAttempts(self):
        return self._reconnect_attempts

    @Property("QVariant", notify=dataChanged)
    def currentMetadata(self):
        return self._metadata

    def _find_station(self, station_id) -> dict | None:
        for s in self._stations:
            if str(s.get("id")) == str(station_id):
                return s
        return None

    @staticmethod
    def _history_entry(entry: dict) -> dict:
        return {
            "name": entry.get("station_name") or entry.get("name") or "",
            "url": entry.get("stream_url") or entry.get("url") or "",
            "played_at": entry.get("started_at") or entry.get("played_at")
            or entry.get("timestamp") or "",
        }

    @staticmethod
    def _station_entry(station: dict) -> dict:
        return {
            "id": station.get("id", 0),
            "name": station.get("name", "") or "",
            "url": station.get("url", "") or "",
            "codec": station.get("codec", "") or "",
            "country": station.get("country", "") or "",
            "tags": station.get("tags", []) or [],
            "favorite": bool(station.get("favorite", False)),
            "image_path": station.get("image_path", "") or "",
            "bitrate": station.get("bitrate", 0) or 0,
        }

    def _cancel_connect_timeout(self):
        if self._connect_timer:
            self._connect_timer.stop()
            self._connect_timer = None

    def _cancel_confirm_timer(self):
        if self._confirm_timer:
            self._confirm_timer.stop()
            self._confirm_timer = None

    #  Refresh

    @Slot(result=dict)
    def refresh(self):
        result = []
        favs = []
        if self._radio_mgr is None:
            self._stations = []
            self._favorites = []
            self.dataChanged.emit()
            return {"ok": True, "count": 0}
        try:
            get_stations = getattr(self._radio_mgr, "get_stations", None)
            if get_stations is None:
                logger.debug("Radio: injected service has no get_stations")
                return {"ok": True, "count": 0}
            stations = get_stations() or []
            for s in stations:
                entry = self._station_entry(s if isinstance(s, dict) else vars(s))
                result.append(entry)
                if entry["favorite"]:
                    favs.append(entry)
            self._stations = result
            self._favorites = favs
        except Exception:
            logger.debug("Radio refresh failed", exc_info=True)
        self.dataChanged.emit()
        return {"ok": True, "count": len(result)}

    #  CRUD

    @Slot(str, str, str, str, result=dict)
    def addStation(self, name: str, url: str, codec: str = "", country: str = ""):
        if not url:
            return {"ok": False, "error": "EMPTY_URL"}
        if not self._radio_mgr:
            return {"ok": False, "error": "NO_RADIO_MANAGER"}
        add_station = getattr(self._radio_mgr, "add_station", None)
        if add_station is None:
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        try:
            result = add_station(name, url, genre="", country=country, codec=codec)
            self.refresh()
            if result.get("ok"):
                return {"ok": True, "id": result.get("id", 0)}
            return {"ok": False, "error": result.get("error", "ADD_FAILED")}
        except Exception as e:
            logger.warning("Radio add failed: %s", e, exc_info=True)
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def deleteStation(self, url: str):
        if not self._radio_mgr:
            return {"ok": False, "error": "NO_RADIO_MANAGER"}
        delete_station = getattr(self._radio_mgr, "delete_station", None)
        if delete_station is None:
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        station = next((s for s in self._stations if s.get("url") == url), None)
        if station is None:
            return {"ok": False, "error": "NOT_FOUND"}
        try:
            result = delete_station(station["id"])
            self.refresh()
            return {"ok": bool(result.get("ok")), "error": result.get("error")} if not result.get("ok") else {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def removeStation(self, station_id: str):
        if not self._radio_mgr:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
        delete_station = getattr(self._radio_mgr, "delete_station", None)
        if delete_station is None:
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        result = delete_station(station_id)
        self.refresh()
        if result.get("ok"):
            return {"ok": True}
        return {"ok": False, "error": result.get("error", "DELETE_FAILED")}

    @Slot(int, str, str, str, str, result=dict)
    def editStation(self, station_id: int, name: str, url: str,
                    codec: str = "", country: str = ""):
        if not self._radio_mgr:
            return {"ok": False, "error": "NO_RADIO_MANAGER"}
        edit_station = getattr(self._radio_mgr, "edit_station", None)
        if edit_station is None:
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        try:
            result = edit_station(station_id, name=name, url=url,
                                  codec=codec, country=country)
            self.refresh()
            if result.get("ok"):
                return {"ok": True}
            return {"ok": False, "error": result.get("error", "EDIT_FAILED")}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    #  Favorites

    @Slot(int, result=dict)
    def toggleFavorite(self, station_id: int):
        if not self._radio_mgr:
            return {"ok": False, "error": "NO_RADIO_MANAGER"}
        favorite_station = getattr(self._radio_mgr, "favorite_station", None)
        if favorite_station is None:
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        try:
            result = favorite_station(station_id)
            self.refresh()
            if result.get("ok"):
                return {"ok": True, "favorite": bool(result.get("favorite", True))}
            return {"ok": False, "error": result.get("error", "FAVORITE_FAILED")}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    #  History

    @Slot(result=dict)
    def clearHistory(self):
        if self._radio_mgr is None:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
        clear_history = getattr(self._radio_mgr, "clear_history", None)
        if clear_history is None:
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        try:
            result = clear_history()
            self.dataChanged.emit()
            return {"ok": bool(result.get("ok", True))}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    #  Search

    @Slot(str, str, str, result=dict)
    def search(self, query: str = "", country: str = "", tag: str = ""):
        if not self._radio_mgr:
            return {"ok": False, "error": "NO_RADIO_MANAGER"}
        search_stations = getattr(self._radio_mgr, "search_stations", None)
        if search_stations is None:
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        try:
            result = search_stations(query or "")
            results = []
            for s in result.get("results", []) or []:
                entry = self._station_entry(s if isinstance(s, dict) else vars(s))
                country_s = entry["country"]
                tags = [t.lower() for t in entry["tags"]]
                if country and country.lower() != country_s.lower():
                    continue
                if tag and tag.lower() not in tags:
                    continue
                results.append(entry)
            return {"ok": True, "results": results, "count": len(results)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    #  Import / Export

    @Slot(str, result=dict)
    def importM3u(self, filepath: str):
        if not self._radio_mgr:
            return {"ok": False, "error": "NO_RADIO_MANAGER"}
        from pathlib import Path
        if not Path(filepath).is_file():
            return {"ok": False, "error": "FILE_NOT_FOUND"}
        try:
            count = 0
            with open(filepath, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and line.startswith("http"):
                        name = Path(line).stem or "Imported"
                        self._radio_mgr.add_station(name, line)
                        count += 1
            self.refresh()
            return {"ok": True, "count": count}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def exportM3u(self, filepath: str):
        if not self._stations:
            return {"ok": False, "error": "NO_STATIONS"}
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for s in self._stations:
                    f.write(f"#EXTINF:-1,{s['name']}\n{s['url']}\n")
            return {"ok": True, "count": len(self._stations)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def exportOpml(self, filepath: str):
        if not self._stations:
            return {"ok": False, "error": "NO_STATIONS"}
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write('<opml version="2.0"><body><outline text="Radio Stations">\n')
                for s in self._stations:
                    f.write(f'<outline type="rss" text="{s["name"]}" xmlUrl="{s["url"]}"/>\n')
                f.write('</outline></body></opml>\n')
            return {"ok": True, "count": len(self._stations)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    #  Connect / Buffer / Play

    def _start_connect_timeout(self):
        self._cancel_connect_timeout()
        self._connect_timer = QTimer(self)
        self._connect_timer.setSingleShot(True)
        self._connect_timer.setInterval(self._buffer_timeout_ms)
        self._connect_timer.timeout.connect(self._on_connect_timeout)
        self._connect_timer.start()

    def _start_confirm_check(self):
        self._cancel_confirm_timer()
        self._confirm_timer = QTimer(self)
        self._confirm_timer.setSingleShot(True)
        self._confirm_timer.setInterval(_CONFIRM_CHECK_MS)
        self._confirm_timer.timeout.connect(self._on_confirm_check)
        self._confirm_timer.start()

    def _on_confirm_check(self):
        self._confirm_timer = None
        state = getattr(self._player, "state", "")
        try:
            if callable(state):
                state = state()
        except Exception:
            state = ""
        if state == "playing" and self._pending_connect:
            self._on_station_connection_done()

    def _on_player_state_changed(self, state):
        if state == "playing" and self._pending_connect:
            self._on_station_connection_done()

    def _on_connect_timeout(self):
        self._pending_connect = False
        self._cancel_confirm_timer()
        self._is_buffering = False
        self._is_playing = False
        self._metadata = {"error": "TIMEOUT"}
        logger.debug("Radio connect timeout for %s", self._current_station)
        self.dataChanged.emit()

    @Slot(str, str, result=dict)
    def playStation(self, url: str, name: str = ""):
        if not url:
            return {"ok": False, "error": "EMPTY_URL"}
        if not self._player:
            return {"ok": False, "error": "NO_PLAYER_SERVICE"}
        try:
            self._cancel_connect_timeout()
            self._cancel_confirm_timer()
            self._is_buffering = True
            self._is_playing = False
            self._pending_connect = True
            self._current_station = url
            self._current_station_name = name
            self._reconnect_attempts = 0
            self._metadata = {}
            self.dataChanged.emit()

            if hasattr(self._player, 'play_url'):
                self._player.play_url(url)
            elif hasattr(self._player, 'play'):
                self._player.play(url)
            else:
                self._pending_connect = False
                self._is_buffering = False
                return {"ok": False, "error": "NO_PLAY_METHOD"}

            self._start_confirm_check()
            self._start_connect_timeout()
            self.dataChanged.emit()
            return {"ok": True}
        except Exception as e:
            self._pending_connect = False
            self._is_buffering = False
            self._is_playing = False
            self.dataChanged.emit()
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def reconnectLast(self):
        if self._current_station:
            return self.playStation(self._current_station, self._current_station_name)
        return {"ok": False, "error": "NO_LAST_STATION"}

    @Slot(result=dict)
    def retryCurrent(self):
        return self.reconnectLast()

    @Slot(result=dict)
    def stopStream(self):
        self._cancel_connect_timeout()
        self._cancel_confirm_timer()
        self._pending_connect = False
        self._is_playing = False
        self._is_buffering = False
        if self._player and hasattr(self._player, 'stop'):
            try:
                self._player.stop()
                self.dataChanged.emit()
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_PLAYER"}

    @Slot(result=dict)
    def cancelStream(self):
        return self.stopStream()

    #  Metadata

    @Slot(str, result=dict)
    def getMetadata(self, url: str = ""):
        # The canonical radio service owns metadata via probe/stream sessions;
        # the bridge does not keep a parallel metadata client.
        return {"ok": False, "error": "NO_METADATA"}

    #  Timeout / Cancel

    @Slot(int, result=dict)
    def setTimeoutMs(self, ms: int):
        self._buffer_timeout_ms = max(1000, min(120000, ms))
        return {"ok": True, "timeout_ms": self._buffer_timeout_ms}

    @Slot(result=dict)
    def cancel(self):
        self._cancel_connect_timeout()
        self._cancel_confirm_timer()
        self._pending_connect = False
        self._is_buffering = False
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(str, result="QVariantList")
    def parsePlaylistFile(self, content: str) -> list:
        import re
        stations = []
        if not content or not content.strip():
            return stations
        stripped = content.strip()
        if "<track" in stripped and "<location>" in stripped:
            track_re = re.compile(r"<track>([\s\S]*?)</track>", re.IGNORECASE)
            for match in track_re.finditer(stripped):
                track_body = match.group(1)
                title_m = re.search(r"<title>([^<]*)</title>", track_body, re.IGNORECASE)
                loc_m = re.search(r"<location>([^<]*)</location>", track_body, re.IGNORECASE)
                url = loc_m.group(1).strip() if loc_m else ""
                if url:
                    stations.append({
                        "name": title_m.group(1).strip() if title_m else "Imported",
                        "url": url, "selected": True,
                    })
            return stations
        if stripped.startswith("[playlist]") or re.search(r"^File\d+=", stripped, re.MULTILINE):
            name_map = {}
            file_map = {}
            for line in stripped.splitlines():
                line = line.strip()
                m = re.match(r"^File(\d+)=(.+)$", line)
                if m:
                    file_map[int(m.group(1))] = m.group(2).strip()
                m = re.match(r"^Title(\d+)=(.+)$", line)
                if m:
                    name_map[int(m.group(1))] = m.group(2).strip()
            for key in sorted(file_map):
                stations.append({
                    "name": name_map.get(key, "Imported"),
                    "url": file_map[key], "selected": True,
                })
            return stations
        current_name = ""
        for line in stripped.splitlines():
            line = line.strip()
            if not line:
                continue
            extinf_m = re.match(r"^#EXTINF:-1,(.+)$", line)
            if extinf_m:
                current_name = extinf_m.group(1).strip()
            elif not line.startswith("#") and re.match(r"^https?://", line):
                stations.append({
                    "name": current_name or "Imported",
                    "url": line, "selected": True,
                })
                current_name = ""
        return stations

    @Slot(result=str)
    def getCodec(self):
        return ""

    @Slot(result=int)
    def getBitrate(self):
        return 0

    def _record_play(self):
        """Tell the service a station actually started playing (confirmed)."""
        if not self._radio_mgr or not self._current_station:
            return
        try:
            stations = self._radio_mgr.get_stations() or []
            station = next(
                (s for s in stations if s.get("url") == self._current_station),
                None,
            )
            if station is None:
                return
            mark_played = getattr(self._radio_mgr, "mark_played", None)
            if mark_played is not None:
                mark_played(station.get("id"))
        except Exception:
            logger.debug("Radio: could not record play", exc_info=True)

    def _on_station_connection_done(self):
        self._cancel_connect_timeout()
        self._cancel_confirm_timer()
        self._pending_connect = False
        self._is_buffering = False
        self._is_playing = True
        self._record_play()
        self.dataChanged.emit()
