from PySide6.QtCore import QObject, Signal, Property, Slot
import logging

logger = logging.getLogger("michi.radio")


class RadioBridge(QObject):
    dataChanged = Signal()

    def __init__(self, radio_manager=None, player_service=None, parent=None):
        super().__init__(parent)
        self._radio_mgr = radio_manager
        self._player = player_service
        self._stations = []
        self._favorites = []
        self._history = []
        self._current_station = ""
        self._reconnect_attempts = 0

    @Property("QVariantList", notify=dataChanged)
    def stations(self):
        return self._stations

    @Property("QVariantList", notify=dataChanged)
    def favorites(self):
        return self._favorites

    @Property("QVariantList", notify=dataChanged)
    def history(self):
        return list(self._history)

    @Slot(result=dict)
    def refresh(self):
        result = []
        favs = []
        if self._radio_mgr and hasattr(self._radio_mgr, 'get_all'):
            try:
                all_stations = self._radio_mgr.get_all()
                for s in all_stations:
                    entry = {"id": getattr(s, 'id', 0), "name": getattr(s, 'name', '') or '', "url": getattr(s, 'url', '') or '', "codec": getattr(s, 'codec', '') or '', "country": getattr(s, 'country', '') or '', "tags": getattr(s, 'tags', []) or [], "favorite": getattr(s, 'favorite', False), "image_path": getattr(s, 'image_path', '') or ''}
                    result.append(entry)
                    if entry["favorite"]:
                        favs.append(entry)
            except Exception:
                logger.debug("Radio refresh failed", exc_info=True)
        self._stations = result
        self._favorites = favs
        self.dataChanged.emit()
        return {"ok": True, "count": len(result)}

    @Slot(str, str, str, str, result=dict)
    def addStation(self, name: str, url: str, codec: str, country: str):
        if not url:
            return {"ok": False, "error": "EMPTY_URL"}
        if self._radio_mgr and hasattr(self._radio_mgr, 'add'):
            try:
                station = self._radio_mgr.add(name, url, country=country, codec=codec)
                logger.info("Radio station added: id=%s, name=%s, url=%s",
                            getattr(station, 'id', '?'), name, url)
                self.refresh()
                return {"ok": True, "id": getattr(station, 'id', 0)}
            except Exception as e:
                logger.warning("Radio add failed: %s", e, exc_info=True)
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_RADIO_MANAGER"}

    @Slot(str, result=dict)
    def playStation(self, url: str, name: str = ""):
        if not url:
            return {"ok": False, "error": "EMPTY_URL"}
        if self._player and hasattr(self._player, 'play_url'):
            try:
                self._player.play_url(url)
                self._current_station = url
                if name:
                    self._history.insert(0, {"name": name, "url": url, "played_at": __import__("time").time()})
                    self._history = self._history[:50]
                    self.dataChanged.emit()
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_PLAYER_SERVICE"}

    @Slot(result=dict)
    def reconnectLast(self):
        if self._current_station:
            return self.playStation(self._current_station)
        return {"ok": False, "error": "NO_LAST_STATION"}

    @Slot(result=dict)
    def retryCurrent(self):
        return self.reconnectLast()

    @Slot(result=dict)
    def stopStream(self):
        if self._player and hasattr(self._player, 'stop'):
            try:
                self._player.stop()
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_PLAYER"}

    @Slot(result=dict)
    def cancelStream(self):
        return self.stopStream()

    @Slot(str, result=dict)
    def deleteStation(self, url: str):
        if self._radio_mgr and hasattr(self._radio_mgr, 'remove_station'):
            try:
                self._radio_mgr.remove_station(url)
                self.refresh()
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_RADIO_MANAGER"}

    @Slot(int, str, str, str, str, result=dict)
    def editStation(self, station_id: int, name: str, url: str, codec: str = "", country: str = ""):
        if not self._radio_mgr:
            return {"ok": False, "error": "NO_RADIO_MANAGER"}
        try:
            if hasattr(self._radio_mgr, 'update'):
                self._radio_mgr.update(station_id, name=name, url=url)
                self.refresh()
                return {"ok": True}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

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
                    })
            return {"ok": True, "results": results, "count": len(results)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def importM3u(self, filepath: str):
        if not self._radio_mgr:
            return {"ok": False, "error": "NO_RADIO_MANAGER"}
        from pathlib import Path
        if not Path(filepath).is_file():
            return {"ok": False, "error": "FILE_NOT_FOUND"}
        try:
            count = 0
            with open(filepath) as f:
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

    @Slot(str, result=dict)
    def getMetadata(self, url: str):
        if self._radio_mgr and hasattr(self._radio_mgr, 'get_metadata'):
            try:
                return self._radio_mgr.get_metadata(url)
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_METADATA"}

    @Slot(str, result=str)
    def getCodec(self):
        if self._radio_mgr and hasattr(self._radio_mgr, 'get_all'):
            try:
                stations = self._radio_mgr.get_all()
                for s in stations:
                    codec = getattr(s, 'codec', '') or ''
                    if codec:
                        return codec
            except Exception:
                pass
        return ""

    @Slot(str, result="QVariantList")
    def parsePlaylistFile(self, content: str) -> list:
        import re
        stations = []

        if not content or not content.strip():
            return stations

        stripped = content.strip()

        # XSPF detection: <track> elements with <location>
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
                        "url": url,
                        "selected": True,
                    })
            return stations

        # PLS detection: [playlist] or File1=/Title1= pattern
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
                    "url": file_map[key],
                    "selected": True,
                })
            return stations

        # Default: M3U / EXTINF parsing
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
                    "url": line,
                    "selected": True,
                })
                current_name = ""

        return stations

    @Slot(result=int)
    def getBitrate(self):
        return 0
