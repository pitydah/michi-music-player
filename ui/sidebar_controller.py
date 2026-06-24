"""Sidebar controller — rebuilds sidebar sections with hub-focused navigation."""

from PySide6.QtCore import QObject, Signal

from library.library_db import get_mounted_devices


class SidebarController(QObject):
    navigation_requested = Signal(str)

    def __init__(self, sidebar_widget, db, parent=None):
        super().__init__(parent)
        self._sidebar = sidebar_widget
        self._db = db
        self._last_active = None
        sidebar_widget.item_clicked.connect(self._on_item_click)

    def _on_item_click(self, key: str):
        self._last_active = key
        self.navigation_requested.emit(key)

    def rebuild(self, servers: list, sync_peers: list | None = None):
        self._sidebar._clear()

        # ── Hubs principales ──
        self._sidebar.add_section("hub", "Michi Music", "sidebar_mix")
        self._sidebar.add_item("hub", "home", "Inicio", "sidebar_library")
        self._sidebar.add_item("hub", "library_hub", "Biblioteca", "sidebar_library")
        self._sidebar.add_item("hub", "mix_hub", "Mix", "sidebar_mix")
        self._sidebar.add_item("hub", "playlist_hub", "Playlist", "sidebar_playlists")
        self._sidebar.add_item("hub", "playback_hub", "Reproducción", "warm_play")
        self._sidebar.add_item("hub", "connections_hub", "Conexiones", "sidebar_servers")
        self._sidebar.add_item("hub", "radio", "Radio", "sidebar_radio")
        self._sidebar.add_item("hub", "audio_lab", "Audio Lab", "sidebar_mix")
        self._sidebar.add_item("hub", "home_audio", "Home Audio", "home_audio")
        self._sidebar.add_item("hub", "identifier", "Identificador", "sidebar_identifier")
        self._sidebar.add_item("hub", "assistant", "Asistente", "sidebar_mix")
        self._sidebar.add_item("hub", "settings_hub", "Configuración", "sidebar_mix")

        # ── Dispositivos ──
        self._sidebar.add_section("dev", "Dispositivos", "sidebar_devices")
        self._sidebar.add_item("dev", "devices_page", "Michi Sync Suite",
                                "sidebar_devices")

        # Sync peers (discovered on network)
        if sync_peers:
            for peer in sync_peers:
                device_id = peer.get("device_id", "")
                alias = peer.get("alias", "Dispositivo")
                device_type = peer.get("device_type", "")
                label = alias
                if device_type:
                    label = f"{alias} · {device_type}"
                key = f"dev:sync:{device_id}" if device_id else f"dev:sync:{alias}"
                self._sidebar.add_item("dev", key, label, "sidebar_devices")

        # Mounted filesystem devices
        for d in get_mounted_devices():
            self._sidebar.add_item("dev", f"dev:{d['mount']}", d['name'],
                                    "sidebar_devices")

        # Restore last active or default to home
        if self._last_active:
            self._sidebar.set_active(self._last_active)
        else:
            self._sidebar.set_active("home")
