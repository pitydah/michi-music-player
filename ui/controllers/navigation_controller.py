"""NavigationController — route dispatch, header config, breadcrumbs, nav history."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Callable

from PySide6.QtCore import QObject

if TYPE_CHECKING:
    from ui.window import MainWindow

# ── Section config: title, subtitle, icon, views, search visibility ──
SECTION_CONFIG: dict[str, dict] = {
    "library":    {"title": "Biblioteca", "subtitle": "Música local, archivos disponibles y estadísticas de tu colección",
                   "icon": "sidebar_library", "views": ["list", "grid"],
                   "search": True, "default": "list"},
    "albums":     {"title": "Álbumes", "subtitle": "Carátulas y navegación visual",
                   "icon": "sidebar_albums", "views": ["list", "grid", "coverflow"],
                   "search": True, "default": "grid"},
    "artists":    {"title": "Artistas", "subtitle": "Explora tu biblioteca por artista y álbumes",
                   "icon": "sidebar_artist", "views": ["grid", "list"],
                   "search": True, "default": "grid"},
    "genres":     {"title": "Géneros", "subtitle": "Atlas de estilos de tu biblioteca",
                    "icon": "sidebar_popular", "views": ["grid", "list"],
                    "search": True, "default": "grid"},
    "folders":    {"title": "Carpetas", "subtitle": "Explorador musical local",
                   "icon": "sidebar_folders", "views": ["tree"],
                   "search": True, "default": "tree"},
    "radio":      {"title": "Emisoras", "subtitle": "Radios por URL y mosaicos",
                   "icon": "sidebar_radio", "views": ["grid", "list"],
                   "search": True, "default": "grid"},
    "identifier": {"title": "Identificador", "subtitle": "Detección musical",
                   "icon": "sidebar_identifier", "views": [],
                   "search": False, "default": None},
    "playlists":  {"title": "Playlist", "subtitle": "Colecciones personalizadas",
                   "icon": "sidebar_playlists", "views": ["list", "grid"],
                   "search": True, "default": "list"},
    "favs":       {"title": "Favoritos", "subtitle": "Canciones marcadas como favoritas",
                   "icon": "sidebar_popular", "views": ["list", "grid"],
                   "search": True, "default": "list"},
    "recent":     {"title": "Recientes", "subtitle": "Reproducidas recientemente",
                   "icon": "sidebar_recent", "views": ["list", "grid"],
                   "search": True, "default": "list"},
    "discover":   {"title": "Descubrir", "subtitle": "Explora y redescubre tu música",
                   "icon": "sidebar_mix", "views": [],
                   "search": False, "default": None},
    "mix_daily":  {"title": "Mix diario", "subtitle": "Selección automática para hoy",
                   "icon": "sidebar_mix", "views": [],
                   "search": False, "default": None},
    "mix_unplayed": {"title": "No escuchadas", "subtitle": "Canciones por descubrir",
                     "icon": "sidebar_unplayed", "views": ["list", "grid"],
                     "search": True, "default": "list"},
    "mix_popular": {"title": "Más escuchadas", "subtitle": "Mayor número de reproducciones",
                    "icon": "sidebar_popular", "views": [],
                    "search": False, "default": None},
    "mix_favorites": {"title": "Favoritos recientes", "subtitle": "Canciones marcadas recientemente",
                      "icon": "sidebar_popular", "views": ["list", "grid"],
                      "search": True, "default": "list"},
    "add_server": {"title": "Añadir servidor", "subtitle": "Conecta Navidrome o Jellyfin",
                   "icon": "sidebar_add", "views": [],
                   "search": False, "default": None},
    "playlist_hub": {"title": "Playlist", "subtitle": "Organiza, mezcla e importa tus listas",
                     "icon": "sidebar_playlists", "views": ["grid"],
                     "search": False, "default": "grid"},
    "metadata_editor": {"title": "Editor de metadatos",
                         "subtitle": "Limpia, completa y normaliza la información de tus archivos",
                         "icon": "metadata_editor", "views": [],
                         "search": False, "default": None},
    "home_audio": {"title": "Home Audio",
                    "subtitle": "Audio multiroom, parlantes y Home Assistant",
                    "icon": "home_audio", "views": [],
                    "search": False, "default": None},
    "new_playlist": {"title": "Nueva playlist", "subtitle": "Crear una playlist vacía",
                     "icon": "sidebar_add", "views": [],
                     "search": False, "default": None},
    "assistant":  {"title": "Asistente",
                    "subtitle": "IA local para explorar tu biblioteca",
                    "icon": "sidebar_mix", "views": [],
                    "search": False, "default": None},
    "metadata_review": {"title": "Revisión de metadata",
                         "subtitle": "Compara y aprueba cambios sugeridos",
                         "icon": "metadata_editor", "views": [],
                         "search": False, "default": None},
    "audio_lab":      {"title": "Audio Lab",
                        "subtitle": "Importa, corrige y enriquece tu colección",
                        "icon": "sidebar_mix", "views": [],
                        "search": False, "default": None},
    "michi_disc_lab": {"title": "Michi Disc Lab",
                       "subtitle": "Importación Hi-Fi y ripeo seguro de CDs",
                       "icon": "sidebar_mix", "views": [],
                       "search": False, "default": None},
    "home":           {"title": "Inicio",
                        "subtitle": "Tu música en un solo lugar",
                        "icon": "sidebar_library", "views": [],
                        "search": False, "default": None},
    "library_hub":    {"title": "Biblioteca",
                        "subtitle": "Música local, servidores y archivos offline",
                        "icon": "sidebar_library", "views": [],
                        "search": False, "default": None},
    "mix_hub":        {"title": "Mix",
                        "subtitle": "Smart mixes, recomendaciones y playlists mixtas",
                        "icon": "sidebar_mix", "views": [],
                        "search": False, "default": None},
    "playback_hub":   {"title": "Reproducción",
                        "subtitle": "Cola, historial, favoritos y radio",
                        "icon": "warm_play", "views": [],
                        "search": False, "default": None},
    "connections_hub":{"title": "Conexiones",
                        "subtitle": "Servidores, Home Audio y dispositivos",
                        "icon": "sidebar_servers", "views": [],
                        "search": False, "default": None},
    "settings_hub":   {"title": "Configuración",
                        "subtitle": "Preferencias de la aplicación",
                        "icon": "warm_settings", "views": [],
                        "search": False, "default": None},
    "devices":        {"title": "Dispositivos",
                        "subtitle": "Unidades y discos externos",
                        "icon": "sidebar_devices", "views": [],
                        "search": False, "default": None},
    "devices_page":   {"title": "Michi Sync Suite",
                        "subtitle": "Sincroniza musica con tus dispositivos",
                        "icon": "sidebar_devices", "views": [],
                        "search": False, "default": None},
}

# Navigation routes — maps sidebar keys to window handler methods
NAV_ROUTES: dict[str, str] = {
    "library": "_show_library_hub_page", "albums": "_show_albums",
    "artists": "_show_artists", "genres": "_show_genres",
    "radio": "_show_radio", "home_audio": "_show_home_audio",
    "identifier": "_show_identifier", "discover": "_show_discover",
    "folders": "_show_folders", "playlist_hub": "_show_playlist_hub",
    "metadata_editor": "_show_metadata_editor",
    "favs": "_show_favs", "recent": "_show_recent",
    "new_playlist": "_show_new_playlist", "add_server": "_show_add_server",
    "assistant": "_show_assistant",
    "metadata_review": "_show_metadata_review",
    "audio_lab": "_show_audio_lab",
    "michi_disc_lab": "_show_michi_disc_lab",
    "home": "_show_home_page",
    "library_hub": "_show_library_hub_page",
    "mix_hub": "_show_mix_hub_page",
    "playback_hub": "_show_playback_hub_page",
    "connections_hub": "_show_connections_hub_page",
    "settings_hub": "_show_settings_hub_page",
    "devices": "_show_devices_page",
    "devices_page": "_show_devices_page",
}

# Search placeholders per section
_SEARCH_PLACEHOLDERS: dict[str, str] = {
    "library": "Buscar canciones...", "albums": "Buscar álbumes...",
    "artists": "Buscar artistas...", "playlists": "Buscar en playlist...",
    "folders": "Buscar carpeta...", "radio": "Buscar emisoras...",
    "playlist_hub": "Buscar playlists...", "favs": "Buscar favoritos...",
    "recent": "Buscar recientes...", "mix_unplayed": "Buscar canciones...",
}


def resolve_section_config(key: str, extra: dict | None = None) -> dict:
    """Resolve section config for static keys or dynamic prefixes (pl:, srv:, dev:)."""
    if key in SECTION_CONFIG:
        return SECTION_CONFIG[key]
    if key.startswith("pl:") and extra:
        name = extra.get("name", "Playlist")
        return {"title": name, "subtitle": "Playlist local",
                "icon": "sidebar_playlist_item", "views": ["list", "grid"],
                "search": True, "default": "list"}
    if key.startswith("srv:") and extra:
        name = extra.get("name", "Servidor")
        sv_type = extra.get("type", "")
        icon = "sidebar_navidrome" if sv_type == "navidrome" else "sidebar_jellyfin"
        return {"title": name, "subtitle": "Servidor remoto",
                "icon": icon, "views": [],
                "search": True, "default": None}
    if key.startswith("dev:") and extra:
        name = extra.get("name", os.path.basename(extra.get("mount", "")))
        return {"title": name, "subtitle": "Dispositivo externo",
                "icon": "sidebar_devices", "views": ["list"],
                "search": True, "default": "list"}
    return {"title": key.capitalize(), "subtitle": "",
            "icon": "sidebar_library", "views": ["list", "grid"],
            "search": True, "default": "list"}


class NavigationHistory:
    """Back/forward nav stack with button state updates.

    Stores search text alongside each navigation entry so that
    pressing back/forward restores the previous search state.
    """

    def __init__(self):
        self._history: list[tuple[str, str]] = []  # (key, search_text)
        self._index: int = -1
        self._restoring: bool = False

    @property
    def is_restoring(self) -> bool:
        return self._restoring

    @property
    def can_go_back(self) -> bool:
        return self._index > 0

    @property
    def can_go_forward(self) -> bool:
        return self._index < len(self._history) - 1

    @property
    def current_key(self) -> str | None:
        entry = self._history[self._index] if 0 <= self._index < len(self._history) else None
        return entry[0] if entry else None

    def push(self, key: str, search_text: str = ""):
        """Add a navigation entry, truncating forward history if not at tip."""
        if self._history and self._history[self._index][0] == key:
            return
        if self._index < len(self._history) - 1:
            self._history = self._history[:self._index + 1]
        self._history.append((key, search_text))
        self._index = len(self._history) - 1

    def back(self) -> tuple[str, str] | None:
        if not self.can_go_back:
            return None
        self._index -= 1
        return self._history[self._index]

    def forward(self) -> tuple[str, str] | None:
        if not self.can_go_forward:
            return None
        self._index += 1
        return self._history[self._index]

    def restore_call(self, key: str, navigate_fn: Callable):
        """Navigate while preserving the restoring flag."""
        self._restoring = True
        try:
            navigate_fn(key)
        finally:
            self._restoring = False


class NavigationController(QObject):
    """Centralizes section config, header rendering, and nav history."""

    def __init__(self, window: MainWindow):
        super().__init__(window)
        self._win = window
        self._history = NavigationHistory()

    # ── History delegates ──
    @property
    def is_restoring(self) -> bool:
        return self._history.is_restoring

    @property
    def can_go_back(self) -> bool:
        return self._history.can_go_back

    @property
    def can_go_forward(self) -> bool:
        return self._history.can_go_forward

    def push(self, key: str, search_text: str = ""):
        if not search_text:
            w = self._win
            search_text = getattr(w, '_search_text', "")
        self._history.push(key, search_text)

    def navigate_back(self):
        entry = self._history.back()
        if entry is not None:
            key, search_text = entry
            self._restore_call(key, self._win._on_sidebar_navigate, search_text)
        self._update_buttons()

    def navigate_forward(self):
        entry = self._history.forward()
        if entry is not None:
            key, search_text = entry
            self._restore_call(key, self._win._on_sidebar_navigate, search_text)
        self._update_buttons()

    def _restore_call(self, key: str, navigate_fn, search_text: str):
        self._history._restoring = True
        try:
            navigate_fn(key)
            w = self._win
            if search_text and hasattr(w, '_search') and w._search:
                w._search_text = search_text
                w._search.setText(search_text)
        finally:
            self._history._restoring = False

    def _update_buttons(self):
        w = self._win
        if hasattr(w, '_back_btn'):
            w._back_btn.setEnabled(self._history.can_go_back)
        if hasattr(w, '_forward_btn'):
            w._forward_btn.setEnabled(self._history.can_go_forward)

    # ── Header config ──
    def configure_header(self, section_key: str):
        w = self._win
        w._current_section_key = section_key
        config = resolve_section_config(section_key)
        title = config.get("title", "Todas las canciones")
        subtitle = config.get("subtitle", "")
        icon_name = config.get("icon", "sidebar_library")
        views = config.get("views", ["list", "grid"])
        search = config.get("search", True)
        default = config.get("default", "list")

        w._section_title.setText(title)
        w._section_subtitle.setText(self._build_breadcrumb(subtitle, section_key))

        from ui.icons import get_pixmap
        pix = get_pixmap(icon_name, size=26)
        if not pix.isNull():
            w._section_icon.setPixmap(pix)
        else:
            w._section_icon.clear()

        w._search.setPlaceholderText(_SEARCH_PLACEHOLDERS.get(section_key, "Buscar..."))
        w._search.setVisible(search)

        w._view_switcher.set_available_modes(views, default, context=section_key)
        w._view_switcher.update_for_width(w.width())

        if w._view_mode not in views and default:
            w._view_mode = default
            w._view_switcher.set_view(default, emit=False)

        if not search:
            w._search.hide()

        # Album-specific controls
        show_album_ctrl = (section_key == "albums")
        w._album_sort_btn.setVisible(show_album_ctrl)
        w._album_filter_btn.setVisible(show_album_ctrl)

    # ── Route dispatch ──
    def dispatch(self, key: str):
        """Dispatch a sidebar navigation key to the appropriate handler.

        Saves the current search text (from the section being left) before
        clearing it, so back/forward navigation can restore it.
        """
        w = self._win
        previous_search = getattr(w, '_search_text', "")
        if not previous_search and hasattr(w, '_search') and w._search:
            previous_search = w._search.text() or ""

        w._restore_central_opacity()
        w._current_playlist = None
        w._search_text = ""
        if hasattr(w, '_search') and w._search:
            w._search.clear()

        section_key = key.split(":")[0] if ":" in key else key
        if section_key == "srv":
            section_key = "servers"
        elif section_key == "dev":
            section_key = "devices"
        elif key.startswith("pl:") or key.startswith("playlist:"):
            section_key = "playlists"
        self.configure_header(section_key)

        if not self._history.is_restoring:
            self._history.push(key, previous_search)
            self._update_buttons()

        # Dynamic prefix routes
        if key.startswith("playlist:new"):
            w._create_playlist()
            return
        if key.startswith("playlist:") or key.startswith("pl:"):
            w._show_playlist_detail(key)
            return
        if key.startswith("srv:"):
            w._show_server(key)
            return
        if key.startswith("dev:sync:"):
            w._show_devices_page(key)
            return
        if key.startswith("dev:"):
            w._show_device(key)
            return
        if key.startswith("mix_") and key != "mix_hub":
            w._show_smart_mix(key)
            return

        # Static routes
        method_name = NAV_ROUTES.get(key)
        if method_name and hasattr(w, method_name):
            try:
                getattr(w, method_name)(key)
            except Exception as e:
                import logging
                logging.getLogger("michi.nav").warning(
                    "Navigation handler %s failed for key=%s: %s", method_name, key, e)
        elif not method_name and not any(key.startswith(p) for p in ("playlist:", "pl:", "srv:", "dev:", "mix_")):
            import logging
            logging.getLogger("michi.nav").warning(
                "No navigation handler for key: %s", key)

    def _build_breadcrumb(self, subtitle: str, section_key: str) -> str:
        prev_key = self._history.current_key
        if prev_key is None:
            return subtitle
        hub_names = {
            "home": "Inicio", "library_hub": "Biblioteca", "mix_hub": "Mix",
            "playback_hub": "Reproducción", "connections_hub": "Conexiones",
            "radio": "Radio", "audio_lab": "Audio Lab",
            "settings_hub": "Configuración", "home_audio": "Home Audio",
            "library": "Biblioteca", "albums": "Biblioteca",
            "artists": "Biblioteca", "genres": "Biblioteca",
            "folders": "Biblioteca",
        }
        hub = hub_names.get(prev_key, "")
        if hub and section_key not in ("home", "library_hub", "mix_hub",
                                         "playback_hub", "connections_hub",
                                         "settings_hub", "audio_lab"):
            return f"{hub} / {subtitle}" if subtitle else hub
        return subtitle
