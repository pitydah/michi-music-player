"""Home Audio Handlers — extracted from window.py.

Plain class (not QObject, no signals) that receives the window reference
and delegates all attribute access through `self._win`.
"""

import socket
import logging

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QDialogButtonBox,
    QCheckBox,
    QInputDialog,
)

from core.settings_manager import get_bool, get_str, set_ as sset, get_int
from integrations.home_assistant.client import HomeAssistantClient, entity_to_device
from integrations.snapcast.receivers import ReceiverWizard

log = logging.getLogger(__name__)


class HomeAudioHandlers:
    """All Home Audio signal handler methods extracted from MainWindow."""

    def __init__(self, window):
        self._win = window

    # ── Signal wiring ──

    def wire_signals(self):
        v = self._win._home_audio_view
        if v is None:
            return
        v.connect_requested.connect(self.on_connect)
        v.refresh_requested.connect(self.on_refresh)
        v.enable_multiroom_requested.connect(self.on_multiroom)
        v.open_settings_requested.connect(self.on_settings)
        v.open_receiver_wizard_requested.connect(self.on_receiver_wizard)
        v.device_cast_current_requested.connect(self.on_cast)
        v.device_play_requested.connect(self.on_device_play)
        v.device_pause_requested.connect(self.on_device_pause)
        v.device_stop_requested.connect(self.on_device_stop)
        v.device_volume_changed.connect(self.on_device_volume)
        v.group_selected_requested.connect(self.on_group_selected)
        v.create_group_requested.connect(self.on_create_group)

    # ── Utilities ──

    @staticmethod
    def resolve_lan_ip() -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0)
            s.connect(("10.254.254.254", 1))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return ""

    # ── Home Assistant connection ──

    def on_connect(self):
        dlg = QDialog(self._win)
        dlg.setWindowTitle("Conectar Home Assistant")
        dlg.setMinimumWidth(440)
        layout = QFormLayout(dlg)
        layout.setSpacing(10)

        saved_url = get_str("home_audio/ha_base_url") or ""
        saved_token = get_str("home_audio/ha_token") or ""

        url_edit = QLineEdit(saved_url)
        url_edit.setPlaceholderText("http://homeassistant.local:8123")
        token_edit = QLineEdit(saved_token)
        token_edit.setEchoMode(QLineEdit.Password)
        token_edit.setPlaceholderText("Token de acceso de larga duracion")
        verify_cb = QCheckBox("Verificar SSL")
        verify_cb.setChecked(get_bool("home_audio/ha_verify_ssl"))
        verify_cb.setStyleSheet("color: rgba(255,255,255,0.72);")

        layout.addRow("URL:", url_edit)
        layout.addRow("Token:", token_edit)
        layout.addRow("", verify_cb)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(lambda: self.try_ha_connection(
            url_edit.text().strip(), token_edit.text().strip(), dlg, verify_cb.isChecked()))
        btns.rejected.connect(dlg.reject)
        layout.addRow(btns)
        dlg.exec()

    def try_ha_connection(self, url: str, token: str, dialog, verify_ssl: bool = True):
        sset("home_audio/ha_base_url", url)
        sset("home_audio/ha_token", token)
        sset("home_audio/ha_verify_ssl", verify_ssl)
        dialog.accept()

        if not hasattr(self._win, '_ha_client'):
            self._win._ha_client = HomeAssistantClient(self._win)
            self._win._ha_client.connection_tested.connect(
                self.on_ha_connection_result)
            self._win._ha_client.entities_loaded.connect(
                self.on_ha_entities_loaded)
            self._win._ha_client.error_occurred.connect(self.on_ha_error)

        self._win._toast_svc.show("Probando conexion con Home Assistant...", "info")
        self._win._ha_client.configure(
            url, token, get_bool("home_audio/ha_verify_ssl"))
        self._win._ha_client.test_connection()

    def on_ha_connection_result(self, ok: bool, msg: str):
        if ok:
            self._win._ha_connected = True
            self._win._home_audio_view.set_data(
                ha_connected=True, multiroom_active=False,
                snapserver_running=False, devices=[], groups=[])
            self._win._ha_client.get_media_players()
            self._win._toast_svc.show(f"Home Assistant: {msg}", "success")
        else:
            self._win._ha_connected = False
            self._win._toast_svc.show(f"Error: {msg}", "error")

    def on_ha_entities_loaded(self, entities: list):
        devices = [entity_to_device(e) for e in entities]
        self._win._home_audio_view.set_data(
            ha_connected=True, multiroom_active=False,
            snapserver_running=False, devices=devices, groups=[])
        n = len([d for d in devices if d.get("available")])
        self._win._toast_svc.show(
            f"Home Assistant: {n} media_player disponibles", "info")

    def on_ha_error(self, msg: str):
        self._win._toast_svc.show(f"Home Assistant: {msg}", "error")

    # ── Refresh ──

    def on_refresh(self):
        if hasattr(self._win, '_snap_discovery'):
            self._win._snap_discovery.refresh()
        if hasattr(self._win, '_ha_client') and getattr(self._win, '_ha_connected', False):
            self._win._ha_client.get_media_players()
        else:
            self.refresh_home_audio_state()

    # ── Multiroom toggle ──

    def on_multiroom(self, enable: bool):
        if enable:
            if not self._win._michi_api.is_running:
                self._win._michi_api.start()
            if not self._win._local_media.is_running:
                self._win._local_media.configure(get_int("home_audio/local_media_server_port"))
                self._win._local_media.start()
            if not self._win._mdns.is_running and self._win._mdns.is_available:
                self._win._mdns.configure(port=self._win._michi_api.port)
                self._win._mdns.start()

            if not self._win._snapserver.is_binary_available():
                self._win._toast_svc.show(
                    "snapserver no encontrado. Instala snapcast para usar multiroom.",
                    "error")
                self._win._home_audio_view.set_data(
                    ha_connected=getattr(self._win, '_ha_connected', False),
                    multiroom_active=False,
                    snapserver_running=False,
                    devices=self._win._home_audio_view._devices,
                    groups=self._win._group_mgr.groups())
                return
            self._win._snapserver.configure(
                tcp=get_int("home_audio/snapserver_tcp_port"),
                ctrl=get_int("home_audio/snapserver_control_port"),
                http=get_int("home_audio/snapserver_http_port"))
            self._win._audio_capture.create_sink()
        else:
            self._win._snapserver.stop()
            self._win._audio_capture.remove_sink()
            self._win._mdns.stop()
            self._win._michi_api.stop()
            self._win._local_media.stop()

    # ── Settings & Receiver Wizard ──

    def on_settings(self):
        self._win._show_preferences("home_audio")

    def on_receiver_wizard(self):
        dlg = ReceiverWizard(self._win)
        dlg.exec()

    # ── Device actions ──

    def on_cast(self, device: dict):
        if hasattr(self._win, '_ha_ctrl'):
            self._win._ha_ctrl.cast_current(device)
        else:
            self._win._toast_svc.show("Controlador Home Audio no disponible", "error")

    def on_device_play(self, device: dict):
        if not hasattr(self._win, '_ha_client'):
            self._win._toast_svc.show("No conectado a Home Assistant", "error")
            return
        self._win._ha_client.media_play(device.get("entity_id", ""))

    def on_device_pause(self, device: dict):
        if not hasattr(self._win, '_ha_client'):
            self._win._toast_svc.show("No conectado a Home Assistant", "error")
            return
        self._win._ha_client.media_pause(device.get("entity_id", ""))

    def on_device_stop(self, device: dict):
        if not hasattr(self._win, '_ha_client'):
            self._win._toast_svc.show("No conectado a Home Assistant", "error")
            return
        self._win._ha_client.media_stop(device.get("entity_id", ""))

    def on_device_volume(self, device: dict, volume: int):
        if not hasattr(self._win, '_ha_client'):
            self._win._toast_svc.show("No conectado a Home Assistant", "error")
            return
        self._win._ha_client.set_volume(device.get("entity_id", ""), volume / 100.0)

    # ── Group management ──

    def on_group_selected(self, group: dict):
        gid = group.get("id", "")
        if hasattr(self._win, '_group_mgr'):
            self._win._group_mgr.activate_group(gid)
            name = group.get("name", gid)
            self._win._ctx.player_bar.set_transmit_active(True, name)
            self._win._toast_svc.show(f"Zona activada: {name}", "success")
            self.refresh_home_audio_state()

    def on_create_group(self):
        name, ok = QInputDialog.getText(
            self._win, "Crear grupo", "Nombre del grupo o zona:")
        if ok and name.strip() and hasattr(self._win, '_group_mgr'):
            self._win._group_mgr.add_group(name.strip())
            self._win._toast_svc.show(f"Grupo creado: {name.strip()}", "success")
            self.refresh_home_audio_state()

    # ── Snapcast handlers ──

    def on_snapserver_started(self):
        self._win._toast_svc.show("Snapserver iniciado", "success")
        self._win._snap_discovery.refresh()
        self.refresh_home_audio_state()

    def on_snapserver_stopped(self):
        self._win._toast_svc.show("Snapserver detenido", "info")
        self.refresh_home_audio_state()

    def on_snapserver_error(self, msg: str):
        self._win._toast_svc.show(f"Snapcast: {msg}", "error")

    def on_audio_sink_ready(self, monitor: str):
        self._win._snapserver.configure(
            tcp=self._win._snapserver.tcp_port,
            ctrl=self._win._snapserver.control_port,
            http=self._win._snapserver.http_port)
        self._win._snapserver.start()

    def on_snap_clients_found(self, clients: list):
        self.refresh_home_audio_state()

    def on_groups_changed(self, groups: list):
        self.refresh_home_audio_state()

    # ── State refresh ──

    def refresh_home_audio_state(self):
        snap_clients = self._win._snap_discovery.clients() if hasattr(
            self._win, '_snap_discovery') else []
        snap_devices = [
            {"id": c["id"], "name": c.get("name", c.get("host", "")),
             "entity_id": c.get("id", ""), "state": "idle",
             "area": "", "device_type": "snapclient",
             "backend": c.get("backend", "snapcast"),
             "available": c.get("available", True)}
            for c in snap_clients]

        ha_devices = self._win._home_audio_view._devices if hasattr(
            self._win, '_home_audio_view') else []
        all_devices = ha_devices + snap_devices

        groups = self._win._group_mgr.groups() if hasattr(
            self._win, '_group_mgr') else []

        api_running = self._win._michi_api.is_running if hasattr(
            self._win, '_michi_api') else False
        mdns_running = self._win._mdns.is_running if hasattr(
            self._win, '_mdns') else False
        snap_running = self._win._snapserver.is_running if hasattr(
            self._win, '_snapserver') else False
        local_media_running = self._win._local_media.is_running if hasattr(
            self._win, '_local_media') else False

        tx_active = False
        tx_name = ""
        if hasattr(self._win, '_ctx') and hasattr(self._win._ctx, 'transmit_mgr'):
            tx_dev = self._win._ctx.transmit_mgr.get_active()
            if tx_dev:
                tx_active = True
                tx_name = tx_dev.name

        self._win._home_audio_view.set_data(
            ha_connected=getattr(self._win, '_ha_connected', False),
            multiroom_active=snap_running,
            snapserver_running=snap_running,
            devices=all_devices,
            groups=groups,
            transmit_active=tx_active,
            transmit_device_name=tx_name,
            snap_ctrl_port=self._win._snapserver.control_port if hasattr(self._win, '_snapserver') else 1705,
            api_running=api_running,
            mdns_running=mdns_running,
            local_media_running=local_media_running)

        self._win._home_audio_view.set_diagnostics({
            "Home Assistant": "Conectado" if getattr(self._win, '_ha_connected', False) else "No conectado",
            "API Michi": "Activa" if api_running else "No activa",
            "mDNS": "Activo" if mdns_running else (
                "No disponible" if not (hasattr(self._win, '_mdns') and self._win._mdns.is_available) else "No activo"),
            "Snapserver": "Activo" if snap_running else "Detenido",
            "Servidor local": "Activo" if local_media_running else "No activo",
            "Último error": (getattr(self._win._snapserver, 'last_error', "") or "—")[:40] if hasattr(self._win, '_snapserver') else "—",
            "IP local": getattr(self._win, '_local_ip', "—"),
            "Firewall": "Acepta tráfico local" if (api_running or local_media_running or mdns_running) else "—",
        })
