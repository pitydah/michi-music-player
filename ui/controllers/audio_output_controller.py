"""AudioOutputController — local audio output device selection."""
import logging

from PySide6.QtWidgets import QMenu


class AudioOutputController:
    """Manages local audio output device selection via GStreamer DeviceMonitor."""

    def __init__(self, window, services=None):
        self._win = window
        self._svc = services

    def show_menu(self):
        """Show the audio output device selection menu."""
        from ui.premium_menus import premium_menu_qss
        menu = QMenu(self._win)
        menu.setStyleSheet(premium_menu_qss())

        action_system = menu.addAction("Predeterminada del sistema")
        action_system.setCheckable(True)
        current_id = self._win._ctx.playback.get_output_device_id()
        action_system.setChecked(current_id == "auto")
        action_system.triggered.connect(
            lambda: self._win._ctx.playback.set_output_device_id(None))

        menu.addSeparator()

        devices = self._list_devices()
        if devices:
            for name, device_id in devices:
                action = menu.addAction(name)
                action.setCheckable(True)
                action.setChecked(current_id == device_id)
                action.triggered.connect(
                    lambda checked=False, did=device_id:
                    self._win._ctx.playback.set_output_device_id(did))
        else:
            empty = menu.addAction("No se detectaron dispositivos")
            empty.setEnabled(False)

        menu.addSeparator()
        menu.addAction("PipeWire (sistema)",
                       lambda: self._win._ctx.playback.set_output_device_id(None))
        menu.addAction("Actualizar dispositivos", self.show_menu)
        menu.addAction("Preferencias de audio…", self._win._show_preferences)

        btn = self._win._ctx.player_bar.audio_output_button()
        menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    @staticmethod
    def _list_devices() -> list[tuple[str, str]]:
        """List hardware audio sinks via GStreamer DeviceMonitor.

        Returns list of (display_name, device_id).
        """
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
            devs = devs or []  # guard against None

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
            logging.getLogger("astra").debug("Audio device detection failed")
            return []
