"""HomeAudioController — Home Assistant device management and casting."""
import logging

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("michi.home_audio.controller")


class HomeAudioController(QObject):
    """Manages casting to Home Assistant media_player devices."""

    cast_started = Signal(str, str)        # entity_id, device_name
    cast_failed = Signal(str, str)         # entity_id, error
    error_occurred = Signal(str)

    def __init__(self, window, parent=None, services=None):
        super().__init__(parent)
        self._win = window
        self._ctx = window._ctx
        self._svc = services
    @property
    def is_connected(self) -> bool:
        if self._svc and self._svc.ha_connected:
            return self._svc.ha_connected()
        return self._ctx.ha_connected

    @property
    def ha_client(self):
        if self._svc and hasattr(self._svc, 'ha_client') and self._svc.ha_client:
            return self._svc.ha_client
        return self._ctx.ha_client

    def get_devices(self) -> list[dict]:
        """Return available Home Assistant media_player devices."""
        if not self.is_connected or not self.ha_client:
            return []
        view = self._ctx.home_audio_view
        if view and view._devices:
            return [d for d in view._devices if d.get("available")]
        return []

    def cast_current(self, device: dict):
        """Cast the currently playing track to an HA device."""
        if not self.is_connected or not self.ha_client:
            self.error_occurred.emit("Home Assistant no conectado")
            return

        if not hasattr(self._ctx, 'playback'):
            self.error_occurred.emit("Reproductor no disponible")
            return

        current = self._ctx.playback.current
        if not current:
            self._ctx.toast.show("No hay reproducción activa", "info")
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
        lms_ctrl = (self._svc.local_media_ctrl if self._svc and hasattr(self._svc, 'local_media_ctrl')
                    else self._ctx.local_media_ctrl)
        if not lms_ctrl:
            self.error_occurred.emit("Servidor local no disponible")
            return

        try:
            if self._svc and self._svc.local_ip:
                host = self._svc.local_ip()
            else:
                host = self._ctx.local_ip or 'localhost'
            url = lms_ctrl.register_file(filepath, host=host)
            self.ha_client.play_media(entity_id, url, "music")
            self._on_cast_success(entity_id, device_name)
        except ValueError as e:
            self._ctx.toast.show(
                f"No se pudo servir el archivo: {e}", "error")
            self.cast_failed.emit(entity_id, str(e))

    def _on_cast_success(self, entity_id: str, device_name: str):
        if hasattr(self._ctx, 'player_bar'):
            self._ctx.player_bar.set_transmit_active(True, device_name)
        if hasattr(self._ctx, 'toast'):
            self._ctx.toast.show(f"Enviando a {device_name}", "success")
        self.cast_started.emit(entity_id, device_name)

    def bind_view(self, view):
        """Connect all view signals to controller or window handlers — deprecated, use HomeAudioHandlers."""
        pass  # HomeAudioHandlers.wire_signals() handles all signal wiring now
