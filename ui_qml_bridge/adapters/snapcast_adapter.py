"""SnapcastAdapter — QML-friendly wrapper for Snapcast group management."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject

if TYPE_CHECKING:
    from integrations.snapcast.group_manager import GroupManager

logger = logging.getLogger("michi.qml.snapcast_adapter")


class SnapcastAdapter(QObject):
    """Lightweight adapter for Snapcast GroupManager."""

    def __init__(self, group_manager: GroupManager | None = None, parent=None):
        super().__init__(parent)
        self._group_mgr = group_manager
        self._is_available = group_manager is not None

    @property
    def is_available(self) -> bool:
        return self._is_available and self._group_mgr is not None

    def get_groups(self) -> list[dict]:
        """Return Snapcast groups from GroupManager."""
        if not self._group_mgr:
            return []
        try:
            return self._group_mgr.groups()
        except Exception as e:
            logger.debug("Snapcast get_groups failed: %s", e)
            return []

    def set_group_volume(self, zone_id: str, volume: float):
        """Set volume for a Snapcast zone."""
        if not self._group_mgr:
            return
        try:
            if hasattr(self._group_mgr, 'set_group_volume'):
                self._group_mgr.set_group_volume(zone_id, volume)
        except Exception as e:
            logger.debug("Snapcast set_group_volume failed: %s", e)

    def set_group_mute(self, zone_id: str, muted: bool):
        """Mute/unmute a Snapcast zone."""
        if not self._group_mgr:
            return
        try:
            if hasattr(self._group_mgr, 'set_group_mute'):
                self._group_mgr.set_group_mute(zone_id, muted)
        except Exception as e:
            logger.debug("Snapcast set_group_mute failed: %s", e)

    def assign_stream(self, stream_id: str):
        """Assign a stream to all Snapcast groups."""
        if not self._group_mgr:
            return
        try:
            if hasattr(self._group_mgr, 'assign_stream'):
                self._group_mgr.assign_stream(stream_id)
        except Exception as e:
            logger.debug("Snapcast assign_stream failed: %s", e)
