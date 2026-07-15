"""RadioService — thin adapter to radio manager logic."""
import logging

logger = logging.getLogger("core.radio.radio_service")


class RadioService:
    def __init__(self, radio_manager=None, db=None):
        self._radio_manager = radio_manager
        self._db = db

    @property
    def radio_manager(self):
        return self._radio_manager

    def get_stations(self, filter_text: str = "") -> list:
        if self._radio_manager:
            return self._radio_manager.get_stations(filter_text)
        return []

    def play_station(self, url: str, name: str) -> bool:
        if self._radio_manager:
            return self._radio_manager.play(url, name)
        return False

    def stop(self) -> dict:
        if self._radio_manager and hasattr(self._radio_manager, 'stop'):
            try:
                self._radio_manager.stop()
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
