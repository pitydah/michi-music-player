"""CastController — unified cast menu combining Snapcast + Home Assistant."""
import logging

from PySide6.QtWidgets import QMenu

logger = logging.getLogger("astra.cast.controller")


class CastController:
    """Unified casting — delegates to SnapcastController or HomeAudioController."""

    def __init__(self, window):
        self._win = window

    def show_cast_menu(self):
        """Show the unified transmit/cast menu: local output + net devices + zones + HA."""
        from ui.premium_menus import premium_menu_qss
        menu = QMenu(self._win)
        menu.setStyleSheet(premium_menu_qss())

        # Local output
        local = menu.addAction("Salida local")
        local.setCheckable(True)
        active = self._win._ctx.transmit_mgr.get_active()
        local.setChecked(active is None)
        local.triggered.connect(lambda: self._win._activate_transmit_device(None))

        # TransmitManager network devices
        devices = self._win._ctx.transmit_mgr.get_devices()
        if devices:
            menu.addSeparator()
            for dev in devices:
                label = f"{dev.name} · {dev.stype.upper()}"
                action = menu.addAction(label)
                action.setCheckable(True)
                action.setChecked(active is not None and active.name == dev.name)
                action.triggered.connect(
                    lambda checked=False, d=dev: self._win._activate_transmit_device(d))
        else:
            menu.addSeparator()
            empty = menu.addAction("No hay dispositivos configurados")
            empty.setEnabled(False)

        # Snapcast zones
        snapcast_ctrl = getattr(self._win, '_snapcast_ctrl', None)
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
        ha_ctrl = getattr(self._win, '_ha_ctrl', None)
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
                       self._win._add_transmit_device)
        menu.addAction("Administrar dispositivos…",
                       self._win._manage_transmit_devices)

        btn = self._win._ctx.player_bar.transmit_button()
        menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))
