"""Sidebar controller — rebuilds sidebar sections with hub-focused navigation."""

from PySide6.QtCore import QObject, Signal, QTimer

from library.library_db import get_mounted_devices


class SidebarController(QObject):
    navigation_requested = Signal(str)

    def __init__(self, sidebar_widget, db, parent=None):
        super().__init__(parent)
        self._sidebar = sidebar_widget
        self._db = db
        self._last_active = None
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(150)
        self._debounce_timer.timeout.connect(self._emit_navigation)
        self._pending_key = None
        sidebar_widget.item_clicked.connect(self._on_item_click)

    def _on_item_click(self, key: str):
        if key == self._last_active:
            return
        self._pending_key = key
        if self._debounce_timer.isActive():
            self._debounce_timer.stop()
        self._debounce_timer.start()

    def _emit_navigation(self):
        if self._pending_key is not None:
            self._last_active = self._pending_key
            self.navigation_requested.emit(self._pending_key)
            self._pending_key = None

    def rebuild(self, servers: list, sync_peers: list | None = None):
        """Rebuild sidebar sections.

        Note: `servers` parameter is reserved for future use.
        Servers are rendered inside ConnectionsHubPage, not as sidebar items.
        Sync peers (discovered Android devices) are shown under Dispositivos.
        """
        _ = servers  # kept for API compatibility; servers shown inside ConnectionsHubPage
        self._sidebar._clear()

        # ── Hubs principales ──
        self._sidebar.add_section("hub", "Michi Music", "sidebar_mix")
        self._sidebar.add_item("hub", "home", "Inicio", "sidebar_home")
        self._sidebar.add_item("hub", "library_hub", "Biblioteca", "sidebar_library")
        self._sidebar.add_item("hub", "mix_hub", "Mix", "sidebar_mix")
        self._sidebar.add_item("hub", "playback_hub", "Reproducción", "warm_play")
        self._sidebar.add_item("hub", "connections_hub", "Conexiones", "sidebar_servers")
        self._sidebar.add_item("hub", "ecosystem_hub", "Ecosistema Michi", "sidebar_servers")
        self._sidebar.add_item("hub", "home_audio", "Home Audio", "home_audio")
        self._sidebar.add_item("hub", "broadcast_hub", "Transmisiones", "sidebar_radio")
        self._sidebar.add_item("hub", "audio_lab", "Audio Lab", "sidebar_mix")
        self._sidebar.add_item("hub", "michi_ai", "Michi AI", "sidebar_assistant")

        # ── Playlists (hub principal + sección colapsable con Nueva playlist y playlists) ──
        self._sidebar.add_section("pl", "Playlists", "sidebar_playlists")
        self._sidebar.add_item("pl", "playlist_hub", "Playlists", "sidebar_playlists")
        self._sidebar.add_item("pl", "playlist:new", "+ Nueva playlist",
                                "sidebar_playlists")
        try:
            playlists = self._db.get_playlists()
            for pl in playlists[:20]:
                pid = pl.get("id", 0)
                name = pl.get("name", "Sin nombre")
                if len(name) > 24:
                    name = name[:23] + "…"
                self._sidebar.add_item("pl", f"playlist:{pid}", name,
                                        "sidebar_playlists")
        except Exception:
            pass

        # ── Dispositivos ──
        self._sidebar.add_section("dev", "Dispositivos", "sidebar_devices")
        self._sidebar.add_item("dev", "devices_page", "Michi Sync Suite",
                                "michi_sync")

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

        if self._last_active:
            self._sidebar.set_active(self._last_active)
        else:
            self._sidebar.set_active("home")

    def set_active(self, key: str):
        self._last_active = key
        self._sidebar.set_active(key)
