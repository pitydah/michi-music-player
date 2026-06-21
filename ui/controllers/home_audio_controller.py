"""HomeAudioController — Home Assistant device management and casting."""
import logging

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("astra.home_audio.controller")


class HomeAudioController(QObject):
    """Manages casting to Home Assistant media_player devices."""

    cast_started = Signal(str, str)        # entity_id, device_name
    cast_failed = Signal(str, str)         # entity_id, error
    error_occurred = Signal(str)

    def __init__(self, window, parent=None):
        super().__init__(parent)
        self._win = window

    @property
    def is_connected(self) -> bool:
        return getattr(self._win, '_ha_connected', False)

    @property
    def ha_client(self):
        return getattr(self._win, '_ha_client', None)

    def get_devices(self) -> list[dict]:
        """Return available Home Assistant media_player devices."""
        if not self.is_connected or not self.ha_client:
            return []
        view = getattr(self._win, '_home_audio_view', None)
        if view and view._devices:
            return [d for d in view._devices if d.get("available")]
        return []

    def cast_current(self, device: dict):
        """Cast the currently playing track to an HA device."""
        if not self.is_connected or not self.ha_client:
            self.error_occurred.emit("Home Assistant no conectado")
            return

        current = self._win._ctx.playback.current
        if not current:
            self._win._ctx.toast.show("No hay reproducción activa", "info")
            return

        entity_id = device.get("entity_id", "")
        device_name = device.get("name", "Dispositivo")

        if current.startswith("http"):
            # Stream URL — send directly
            self.ha_client.play_media(entity_id, current, "music")
            self._on_cast_success(entity_id, device_name)
        else:
            # Local file — serve via LocalMediaServer
            self._stream_local_to_ha(entity_id, device_name, current)

    def _stream_local_to_ha(self, entity_id: str, device_name: str, filepath: str):
        """Stream a local file to an HA device via LocalMediaServerController."""
        lms_ctrl = getattr(self._win, '_local_media_ctrl', None)
        if not lms_ctrl:
            self.error_occurred.emit("Servidor local no disponible")
            return

        try:
            url = lms_ctrl.register_file(filepath)
            self.ha_client.play_media(entity_id, url, "music")
            self._on_cast_success(entity_id, device_name)
        except ValueError as e:
            self._win._ctx.toast.show(
                f"No se pudo servir el archivo: {e}", "error")
            self.cast_failed.emit(entity_id, str(e))

    def _on_cast_success(self, entity_id: str, device_name: str):
        self._win._ctx.player_bar.set_transmit_active(True, device_name)
        self._win._ctx.toast.show(f"Enviando a {device_name}", "success")
        self.cast_started.emit(entity_id, device_name)
