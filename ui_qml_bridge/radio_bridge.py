"""RadioBridge — station CRUD, favorites, history, search, import, export,
connect, buffer, play, reconnect, stop, metadata, timeout, cancel.
No synchronous long operations.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer

logger = logging.getLogger("michi.radio")

_MAX_HISTORY = 50
_CONNECT_TIMEOUT_MS = 15000


class RadioBridge(QObject):
    dataChanged = Signal()

    def __init__(self, radio_manager: Any = None,
                 player_service: Any = None,
                 parent=None):
        super().__init__(parent)
        assert player_service is not None, "RadioBridge: player_service is REQUIRED"
        self._radio_mgr = radio_manager
        self._player = player_service
        self._stations: list[dict] = []
        self._favorites: list[dict] = []
        self._history: list[dict] = []
        self._current_station = ""
        self._current_station_name = ""
        self._reconnect_attempts = 0
        self._is_playing = False
        self._is_buffering = False
        self._metadata: dict = {}
        self._connect_timer: QTimer | None = None
        self._buffer_timeout_ms = _CONNECT_TIMEOUT_MS

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
        return list(self._history)

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

    def _find_station(self, station_id: int) -> dict | None:
        for s in self._stations:
            if s.get("id") == station_id:
                return s
        return None

    def _add_to_history(self, name: str, url: str):
        self._history.insert(0, {
            "name": name, "url": url, "played_at": time.time(),
        })
        self._history = self._history[:_MAX_HISTORY]

    def _cancel_connect_timeout(self):
        if self._connect_timer:
            self._connect_timer.stop()
            self._connect_timer = None

    #  Refresh

    @Slot(result=dict)
    def refresh(self):
        result = []
        favs = []
        if self._radio_mgr and hasattr(self._radio_mgr, 'get_all'):
            try:
                all_stations = self._radio_mgr.get_all()
                for s in all_stations:
                    entry = {
                        "id": getattr(s, 'id', 0),
                        "name": getattr(s, 'name', '') or '',
                        "url": getattr(s, 'url', '') or '',
                        "codec": getattr(s, 'codec', '') or '',
                        "country": getattr(s, 'country', '') or '',
                        "tags": getattr(s, 'tags', []) or [],
                        "favorite": getattr(s, 'favorite', False),
                        "image_path": getattr(s, 'image_path', '') or '',
                        "bitrate": getattr(s, 'bitrate', 0) or 0,
                    }
                    result.append(entry)
                    if entry["favorite"]:
                        favs.append(entry)
            except Exception:
                logger.debug("Radio refresh failed", exc_info=True)
        self._stations = result
        self._favorites = favs
        self.dataChanged.emit()
        return {"ok": True, "count": len(result)}

    #  CRUD

    @Slot(str, str, str, str, result=dict)
    def addStation(self, name: str, url: str, codec: str = "", country: str = ""):
        if not url:
            return {"ok": False, "error": "EMPTY_URL"}
        if not self._radio_mgr:
            return {"ok": False, "error": "NO_RADIO_MANAGER"}
        try:
            if hasattr(self._radio_mgr, 'add'):
                station = self._radio_mgr.add(name, url, country=country, codec=codec)
                self.refresh()
                return {"ok": True, "id": getattr(station, 'id', 0)}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            logger.warning("Radio add failed: %s", e, exc_info=True)
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def deleteStation(self, url: str):
        if not self._radio_mgr:
            return {"ok": False, "error": "NO_RADIO_MANAGER"}
        try:
            if hasattr(self._radio_mgr, 'remove_station'):
                self._radio_mgr.remove_station(url)
                self.refresh()
                return {"ok": True}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(int, str, str, str, str, result=dict)
    def editStation(self, station_id: int, name: str, url: str,
                    codec: str = "", country: str = ""):
        if not self._radio_mgr:
            return {"ok": False, "error": "NO_RADIO_MANAGER"}
        try:
            if hasattr(self._radio_mgr, 'update'):
                self._radio_mgr.update(station_id, name=name, url=url,
                                       codec=codec, country=country)
                self.refresh()
                return {"ok": True}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    #  Favorites

    @Slot(int, result=dict)
    def toggleFavorite(self, station_id: int):
        if not self._radio_mgr:
            return {"ok": False, "error": "NO_RADIO_MANAGER"}
        try:
            if hasattr(self._radio_mgr, 'toggle_favorite'):
                is_fav = self._radio_mgr.toggle_favorite(station_id)
                self.refresh()
                return {"ok": True, "favorite": is_fav}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    #  History

    @Slot(result=dict)
    def clearHistory(self):
        self._history = []
        self.dataChanged.emit()
        return {"ok": True}

    #  Search

    @Slot(str, str, str, result=dict)
    def search(self, query: str = "", country: str = "", tag: str = ""):
        if not self._radio_mgr:
            return {"ok": False, "error": "NO_RADIO_MANAGER"}
        try:
            all_stations = self._radio_mgr.get_all()
            results = []
            for s in all_stations:
                name = getattr(s, 'name', '') or ''
                country_s = getattr(s, 'country', '') or ''
                tags = getattr(s, 'tags', []) or []
                match = True
                if query and query.lower() not in name.lower():
                    match = False
                if country and country.lower() != country_s.lower():
                    match = False
                if tag and tag.lower() not in [t.lower() for t in tags]:
                    match = False
                if match:
                    results.append({
                        "id": getattr(s, 'id', 0), "name": name,
                        "url": getattr(s, 'url', '') or '',
                        "codec": getattr(s, 'codec', '') or '',
                        "country": country_s,
                        "tags": tags,
                        "favorite": getattr(s, 'favorite', False),
                        "bitrate": getattr(s, 'bitrate', 0) or 0,
                    })
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
                        self._radio_mgr.add(name, line)
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

    def _on_connect_timeout(self):
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
            self._is_buffering = True
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
                return {"ok": False, "error": "NO_PLAY_METHOD"}

            self._is_buffering = False
            self._is_playing = True
            if name:
                self._add_to_history(name, url)
            self._start_connect_timeout()
            self.dataChanged.emit()
            return {"ok": True}
        except Exception as e:
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
        target = url or self._current_station
        if not target:
            return {"ok": False, "error": "NO_URL"}
        if self._radio_mgr and hasattr(self._radio_mgr, 'get_metadata'):
            try:
                meta = self._radio_mgr.get_metadata(target)
                if isinstance(meta, dict):
                    self._metadata = meta
                else:
                    self._metadata = {"data": str(meta)}
                self.dataChanged.emit()
                return {"ok": True, "metadata": self._metadata}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_METADATA"}

    #  Timeout / Cancel

    @Slot(int, result=dict)
    def setTimeoutMs(self, ms: int):
        self._buffer_timeout_ms = max(1000, min(120000, ms))
        return {"ok": True, "timeout_ms": self._buffer_timeout_ms}

    @Slot(result=dict)
    def cancel(self):
        self._cancel_connect_timeout()
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

    @Slot(result=int)
    def getBitrate(self):
        return 0

    def _on_station_connection_done(self):
        self._cancel_connect_timeout()
        self._is_buffering = False
        self._is_playing = True
        self.dataChanged.emit()
