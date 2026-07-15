"""AudioOutputController — local audio output device selection.

Routes to the correct backend depending on which engine is active.
GStreamer: set_output_device_id on engine.
MPD: update mpd.conf and restart MPD with new device.
"""
import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMenu


class AudioOutputController(QObject):
    """Manages local audio output device selection."""

    preferences_requested = Signal()

    def __init__(self, window, services=None):
        super().__init__()
        self._win = window
        self._ctx = window._ctx
        self._svc = services

    def show_menu(self):
        """Show the audio output device selection menu."""
        from ui.premium_menus import premium_menu_qss
        menu = QMenu(self._win)
        menu.setStyleSheet(premium_menu_qss())

        backend_id = self._get_backend_id()

        action_system = menu.addAction("Predeterminada del sistema")
        action_system.setCheckable(True)
        current_id = self._ctx.playback.get_output_device_id()
        action_system.setChecked(current_id == "auto")
        action_system.triggered.connect(
            lambda: self._set_device(None))

        menu.addSeparator()

        devices = self._list_devices()
        if devices:
            for name, device_id in devices:
                action = menu.addAction(name)
                action.setCheckable(True)
                action.setChecked(current_id == device_id)
                action.triggered.connect(
                    lambda checked=False, did=device_id:
                    self._set_device(did))
        else:
            empty = menu.addAction("No se detectaron dispositivos")
            empty.setEnabled(False)

        menu.addSeparator()
        menu.addAction("PipeWire (sistema)",
                       lambda: self._set_device(None))
        menu.addAction("Actualizar dispositivos", self.show_menu)

        if backend_id == "mpd":
            mpd_info = menu.addAction("Backend: MPD — usar perfil GStreamer para cambiar salida")
            mpd_info.setEnabled(False)
        else:
            menu.addAction("Preferencias de audio…", self.preferences_requested.emit)

        btn = self._ctx.player_bar.audio_output_button()
        menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _get_backend_id(self) -> str:
        ctx = getattr(self, '_ctx', None)
        if ctx and hasattr(ctx, 'playback') and ctx.playback:
            try:
                return ctx.playback.get_active_backend_id()
            except Exception:
                pass
        return "gstreamer"

    def _set_device(self, device_id):
        """Set output device, routing to the correct backend."""
        backend_id = self._get_backend_id()
        if backend_id == "mpd":
            import logging as log
            log.getLogger("michi").info(
                "Device change ignored in MPD mode — use MPD config or switch profile")
            return
        self._ctx.playback.set_output_device_id(device_id)

    @staticmethod
    def _list_devices() -> list[tuple[str, str]]:
        """List hardware audio sinks via GStreamer DeviceMonitor."""
        try:
            import gi
            gi.require_version("Gst", "1.0")
            from gi.repository import Gst
            Gst.init(None)

            monitor = Gst.DeviceMonitor()
            monitor.add_filter("Audio/Sink", None)
            monitor.start()
            devs = monitor.get_devices()
            monitor.stop()
            devs = devs or []

            results = []
            for dev in devs:
                name = dev.get_display_name() or dev.get_device_class() or "Audio device"
                props = dev.get_properties()
                device_id = ""
                if props:
                    device_id = props.get_string("device.id") or props.get_string(
                        "api.alsa.path") or name
                results.append((name, device_id or name))
            return results
        except Exception:
            logging.getLogger("michi").debug("Audio device detection failed")
            return []
