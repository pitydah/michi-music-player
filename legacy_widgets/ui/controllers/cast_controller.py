"""LEGACY - reemplazado por ui_qml_bridge correspondiente."""

"""CastController — unified cast menu combining Snapcast + Home Assistant."""
import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMenu

logger = logging.getLogger("michi.cast.controller")


class CastController(QObject):
    """Unified casting — delegates to SnapcastController or HomeAudioController."""

    transmit_device_selected = Signal(object)  # device or None for local
    add_transmit_requested = Signal()
    manage_transmit_requested = Signal()

    def __init__(self, window, services=None):
        super().__init__()
        self._win = window
        self._ctx = window._ctx
        self._svc = services

    def show_cast_menu(self):
        """Show the unified transmit/cast menu: local output + net devices + zones + HA."""
        if not self._ctx or not hasattr(self._ctx, 'transmit_mgr'):
            return

        from ui.premium_menus import premium_menu_qss
        menu = QMenu(self._win)
        menu.setStyleSheet(premium_menu_qss())

        # Local output
        local = menu.addAction("Salida local")
        local.setCheckable(True)
        active = self._ctx.transmit_mgr.get_active()
        local.setChecked(active is None)
        local.triggered.connect(lambda: self.transmit_device_selected.emit(None))

        # TransmitManager network devices
        devices = self._ctx.transmit_mgr.get_devices()
        if devices:
            menu.addSeparator()
            for dev in devices:
                label = f"{dev.name} · {dev.stype.upper()}"
                action = menu.addAction(label)
                action.setCheckable(True)
                action.setChecked(active is not None and active.name == dev.name)
                action.triggered.connect(
                    lambda checked=False, d=dev: self.transmit_device_selected.emit(d))
        else:
            menu.addSeparator()
            empty = menu.addAction("No hay dispositivos configurados")
            empty.setEnabled(False)

        # Snapcast zones
        snapcast_ctrl = self._ctx.snapcast_ctrl
        if snapcast_ctrl:
            zones = snapcast_ctrl.get_zones()
            if zones:
                menu.addSeparator()
                sc_section = menu.addAction("Snapcast / Zonas")
                sc_section.setEnabled(False)
                for g in zones:
                    label = f"  {g.get('name', 'Zona')}"
                    if g.get("active"):
                        label += " · activa"
                    action = menu.addAction(label)
                    action.triggered.connect(
                        lambda checked=False, gr=g: snapcast_ctrl.activate_zone(gr))

        # Home Assistant devices
        ha_ctrl = self._ctx.ha_ctrl
        if ha_ctrl:
            ha_devices = ha_ctrl.get_devices()
            if ha_devices:
                menu.addSeparator()
                ha_section = menu.addAction("Home Audio")
                ha_section.setEnabled(False)
                for dev in ha_devices:
                    label = f"  {dev.get('name', 'Dispositivo')}"
                    action = menu.addAction(label)
                    action.triggered.connect(
                        lambda checked=False, d=dev: ha_ctrl.cast_current(d))

        menu.addSeparator()
        menu.addAction("Añadir dispositivo…",
                       self.add_transmit_requested.emit)
        menu.addAction("Administrar dispositivos…",
                       self.manage_transmit_requested.emit)

        btn = None
        if self._ctx and hasattr(self._ctx, 'player_bar'):
            btn = self._ctx.player_bar.transmit_button()
        if btn:
            menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))
