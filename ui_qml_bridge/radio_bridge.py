"""RadioBridge — connects QML Radio page to real RadioManager."""

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

    @Property("QVariantList", notify=dataChanged)
    def stations(self):
        return self._stations

    @Property("QVariantList", notify=dataChanged)
    def favorites(self):
        return self._favorites

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
                self._radio_mgr.add(name, url, country=country, codec=codec)
                self.refresh()
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_RADIO_MANAGER"}

    @Slot(str, result=dict)
    def playStation(self, url: str):
        if not url:
            return {"ok": False, "error": "EMPTY_URL"}
        if self._player and hasattr(self._player, 'play_url'):
            try:
                self._player.play_url(url)
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_PLAYER_SERVICE"}

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

    @Slot(result=str)
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

    @Slot(result=int)
    def getBitrate(self):
        return 0
