"""SnapcastController — Snapcast zone management and lifecycle."""
import logging

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("michi.snapcast.controller")


class SnapcastController(QObject):
    """Manages Snapcast zones, snapserver lifecycle, and audio capture."""

    zone_activated = Signal(str, str)      # zone_id, zone_name
    zone_deactivated = Signal(str)         # zone_id
    error_occurred = Signal(str)

    def __init__(self, window, parent=None, services=None):
        super().__init__(parent)
        self._win = window
        self._svc = services

    def activate_zone(self, group: dict):
        """Activate a Snapcast zone — start snapserver + audio capture if needed."""
        snapserver = getattr(self._win, '_snapserver', None)
        audio_capture = getattr(self._win, '_audio_capture', None)
        group_mgr = getattr(self._win, '_group_mgr', None)

        if snapserver and not snapserver.is_running and snapserver.is_binary_available() and audio_capture:
            audio_capture.create_sink()

        if group_mgr:
            zone_id = group.get("id", "")
            group_mgr.activate_group(zone_id)
            name = group.get("name", "Zona")
            ctx = getattr(self._win, '_ctx', None)
            if ctx and hasattr(ctx, 'player_bar'):
                ctx.player_bar.set_transmit_active(True, name)
            if ctx and hasattr(ctx, 'toast'):
                ctx.toast.show(f"Zona activada: {name}", "success")
            self.zone_activated.emit(zone_id, name)

    def get_zones(self) -> list[dict]:
        """Get list of Snapcast zones from GroupManager."""
        group_mgr = getattr(self._win, '_group_mgr', None)
        if group_mgr:
            return group_mgr.groups()
        return []
