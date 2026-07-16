"""LEGACY - reemplazado por ui_qml_bridge correspondiente."""

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
        self._ctx = window._ctx
        self._svc = services

    def activate_zone(self, group: dict):
        """Activate a Snapcast zone — start snapserver + audio capture if needed."""
        snapserver = self._ctx.snapserver
        audio_capture = self._ctx.audio_capture
        group_mgr = self._ctx.group_mgr

        if snapserver and not snapserver.is_running and snapserver.is_binary_available() and audio_capture:
            audio_capture.create_sink()

        if group_mgr:
            zone_id = group.get("id", "")
            group_mgr.activate_group(zone_id)
            name = group.get("name", "Zona")
            if self._ctx.player_bar:
                self._ctx.player_bar.set_transmit_active(True, name)
            if self._ctx.toast:
                self._ctx.toast.show(f"Zona activada: {name}", "success")
            self.zone_activated.emit(zone_id, name)

    def get_zones(self) -> list[dict]:
        """Get list of Snapcast zones from GroupManager."""
        group_mgr = self._ctx.group_mgr
        if group_mgr:
            return group_mgr.groups()
        return []
