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

    @Slot()
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
                    }
                    result.append(entry)
                    if entry["favorite"]:
                        favs.append(entry)
            except Exception:
                logger.debug("Radio refresh failed", exc_info=True)
        # No demo data — empty list is the correct state
        self._stations = result
        self._favorites = favs
        self.dataChanged.emit()

    @Slot(str, str, str, str)
    def addStation(self, name: str, url: str, codec: str, country: str):
        if self._radio_mgr and hasattr(self._radio_mgr, 'add_station'):
            try:
                self._radio_mgr.add_station(name, url, country=country, codec=codec)
                self.refresh()
            except Exception:
                logger.debug("Radio add station failed", exc_info=True)

    @Slot(str)
    def playStation(self, url: str):
        if self._player and hasattr(self._player, 'play_url'):
            try:
                self._player.play_url(url)
            except Exception:
                logger.debug("Radio play station failed", exc_info=True)

    @Slot(str)
    def deleteStation(self, url: str):
        if self._radio_mgr and hasattr(self._radio_mgr, 'remove_station'):
            try:
                self._radio_mgr.remove_station(url)
                self.refresh()
            except Exception:
                logger.debug("Radio delete station failed", exc_info=True)
