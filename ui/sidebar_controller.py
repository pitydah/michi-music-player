"""Sidebar Controller — manages sidebar sections and navigation dispatch."""

from PySide6.QtCore import QObject, Signal


class SidebarController(QObject):
    navigation_requested = Signal(str)

    def __init__(self, sidebar_widget, db, parent=None):
        super().__init__(parent)
        self._sidebar = sidebar_widget
        self._db = db
        sidebar_widget.item_clicked.connect(self._on_item_click)

    def _on_item_click(self, key: str):
        self.navigation_requested.emit(key)

    def rebuild(self, servers: list):
        self._sidebar._clear()

        # Biblioteca
        self._sidebar.add_section("lib", "Biblioteca", "sidebar_library")
        self._sidebar.add_item("lib", "library", "Todas las canciones",
                               "sidebar_library")
        self._sidebar.add_item("lib", "albums", "Álbumes", "sidebar_albums")
        self._sidebar.add_item("lib", "folders", "Carpetas", "sidebar_folders")

        # Playlists
        self._sidebar.add_section("pl", "Playlist", "sidebar_playlists")
        for p in self._db.get_playlists():
            self._sidebar.add_item("pl", f"pl:{p['id']}", p['name'],
                                   "sidebar_playlist_item")
        self._sidebar.add_item("pl", "new_playlist", "+ Nueva playlist",
                               "sidebar_add")

        # Descubrir
        self._sidebar.add_section("mix", "Descubrir", "sidebar_mix")
        self._sidebar.add_item("mix", "mix_daily", "Mix diario", "sidebar_mix")
        self._sidebar.add_item("mix", "mix_unplayed", "No escuchadas",
                               "sidebar_unplayed")
        self._sidebar.add_item("mix", "mix_popular", "Más escuchadas",
                               "sidebar_popular")
        self._sidebar.add_item("mix", "identifier", "Identificador",
                               "sidebar_identifier")

        # Radio
        self._sidebar.add_section("rad", "Radio", "sidebar_radio")
        self._sidebar.add_item("rad", "radio", "Emisoras", "sidebar_radio")

        # Servidores
        self._sidebar.add_section("srv", "Servidores", "sidebar_servers")
        for srv in servers:
            ico = "sidebar_navidrome" if srv.stype == "navidrome" else "sidebar_jellyfin"
            self._sidebar.add_item("srv", f"srv:{srv.name}", srv.name, ico)
        self._sidebar.add_item("srv", "add_server", "+ Añadir servidor",
                               "sidebar_add")

        # Dispositivos
        self._sidebar.add_section("dev", "Dispositivos", "sidebar_devices")
        from library.library_db import get_mounted_devices
        for d in get_mounted_devices():
            self._sidebar.add_item("dev", f"dev:{d['mount']}", d['name'],
                                   "sidebar_devices")

        self._sidebar.set_active("library")
