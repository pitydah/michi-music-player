"""HomeAudioAdapter — QML-friendly wrapper for Home Assistant client."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject

if TYPE_CHECKING:
    from integrations.home_assistant.client import HomeAssistantClient

logger = logging.getLogger("michi.qml.ha_adapter")


class HomeAudioAdapter(QObject):
    """Lightweight adapter for HomeAssistantClient."""

    def __init__(self, ha_client: HomeAssistantClient | None = None, parent=None):
        super().__init__(parent)
        self._client = ha_client
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def get_devices(self) -> list[dict]:
        """Return available HA media_player devices."""
        if not self._client or not self._is_connected:
            return []
        try:
            self._client.get_media_players()
        except Exception as e:
            logger.debug("HA get_devices failed: %s", e)
        return []

    def configure(self, host: str = "", port: int = 0, access_token: str = ""):
        """Configure and test HA connection."""
        if not self._client:
            self._is_connected = False
            return
        base_url = f"http://{host}:{port}" if host else ""
        if base_url:
            try:
                self._client.configure(base_url=base_url, token=access_token)
                result = self._client.test_connection()
                self._is_connected = bool(result)
            except Exception:
                self._is_connected = False
        else:
            self._is_connected = False

    def test_connection(self) -> bool:
        """Test HA connection. Returns True if connected."""
        if not self._client:
            return False
        try:
            self._client.test_connection()
            return self._is_connected
        except Exception as e:
            logger.debug("HA test_connection failed: %s", e)
            return False
