"""NavigationController — route dispatch, header config, breadcrumbs, nav history."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Callable

import logging

from PySide6.QtCore import QObject
from ui.icons import get_qicon

_log = logging.getLogger("michi.nav")

if TYPE_CHECKING:
    from ui.window import MainWindow

# ── Section config: title, subtitle, icon, views, search visibility ──
SECTION_CONFIG: dict[str, dict] = {
    "library":    {"title": "Biblioteca", "subtitle": "Música local, archivos disponibles y estadísticas de tu colección",
                   "icon": "sidebar_library", "views": ["list", "grid"],
                   "search": True, "default": "list"},
     "albums":     {"title": "Álbumes", "subtitle": "Carátulas y navegación visual",
                    "icon": "sidebar_albums", "views": ["grid", "coverflow"],
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
     "playlists":  {"title": "Playlists", "subtitle": "Colecciones personalizadas",
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
     "playlist_hub": {"title": "Playlists", "subtitle": "Organiza, mezcla e importa tus listas",
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
                         "subtitle": "Preserva, analiza y optimiza tu música",
                         "icon": "sidebar_mix", "views": [],
                         "search": False, "default": None},
    "audio_lab_diagnostics": {"title": "Diagnóstico",
                              "subtitle": "Analiza calidad, detecta formatos falsos y verifica tu biblioteca",
                              "icon": "sidebar_identifier", "views": [],
                              "search": False, "default": None},
    "audio_lab_identifier": {"title": "Identificador de Audios",
                             "subtitle": "Edita metadatos, identifica con MusicBrainz, gestiona carátulas y letras",
                             "icon": "metadata_editor", "views": [],
                             "search": False, "default": None},
    "audio_lab_backup": {"title": "Respaldar",
                         "subtitle": "Ripea CDs, digitaliza vinilos, convierte formatos y organiza archivos",
                         "icon": "sidebar_devices", "views": [],
                         "search": False, "default": None},
    "audio_lab_output": {"title": "Perfiles de Salida",
                         "subtitle": "Configura salida bit-perfect, upsampling, corrección de sala y perfiles DAC",
                         "icon": "home_audio", "views": [],
                         "search": False, "default": None},
    "audio_lab_vinyl_lab": {"title": "Vinyl Lab",
                            "subtitle": "Digitaliza vinilos desde tu ADC, separa pistas y exporta a FLAC",
                            "icon": "home_audio", "views": [],
                            "search": False, "default": None},
    "audio_lab_musicbrainz": {"title": "MusicBrainz",
                              "subtitle": "Busca álbumes, artistas y canciones en la base de datos MusicBrainz",
                              "icon": "sidebar_identifier", "views": [],
                              "search": False, "default": None},
    "audio_lab_organize": {"title": "Organizar Archivos",
                           "subtitle": "Renombra y reorganiza tu biblioteca con plantillas personalizadas",
                           "icon": "sidebar_folders", "views": [],
                           "search": False, "default": None},
    "audio_lab_conversion": {"title": "Convertir Formatos",
                             "subtitle": "Convierte archivos de audio entre formatos preservando metadatos",
                             "icon": "sidebar_mix", "views": [],
                             "search": False, "default": None},
    "audio_lab_intelligence": {"title": "Inteligencia Local",
                               "subtitle": "Extrae BPM, key y energía, genera radio local y recomendaciones",
                               "icon": "sidebar_mix", "views": [],
                               "search": False, "default": None},
    "michi_disc_lab": {"title": "Michi Disc Lab",
                       "subtitle": "Importación Hi-Fi y ripeo seguro de CDs",
                       "icon": "sidebar_mix", "views": [],
                       "search": False, "default": None},
     "home":           {"title": "Inicio",
                         "subtitle": "Estado general, continuidad y acciones rápidas",
                         "icon": "sidebar_home", "views": [],
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

# Ruta inicial de la aplicación — Inicio como landing page
INITIAL_ROUTE: str = "home"


def resolve_sidebar_active_key(key: str) -> str:
    """Mapea una clave de navegación a la clave del sidebar que debe quedar activa.

    Solo debe devolver claves que existan como ítems visibles en el sidebar.
    Subsecciones (playlists, servidores, dispositivos, etc.) se agrupan
    bajo el hub/section padre del sidebar.
    """
    # Hubs visibles
    if key in ("home", "library_hub", "mix_hub", "playlist_hub",
                "playback_hub", "connections_hub", "home_audio",
                "audio_lab", "assistant", "devices_page"):
        return key
    # Hijos de library_hub
    if key in ("library", "albums", "artists", "genres", "folders", "favs", "recent"):
        return "library_hub"
    # Hijos de mix_hub
    if key.startswith("mix_") and key != "mix_hub":
        return "mix_hub"
    # Hijos de playlist_hub
    if key.startswith("pl:") or key.startswith("playlist:"):
        return "playlist_hub"
    # Hijos de connections_hub
    if key.startswith("srv:") or key in ("add_server",):
        return "connections_hub"
    # Hijos de playback_hub
    if key == "radio":
        return "playback_hub"
    # Hijos de devices_page
    if key.startswith("dev:") or key in ("devices",):
        return "devices_page"
    # Hijos de audio_lab
    if key in ("metadata_editor", "metadata_review", "michi_disc_lab", "identifier",
               "audio_lab_diagnostics", "audio_lab_identifier",
               "audio_lab_backup", "audio_lab_output",
               "audio_lab_intelligence", "audio_lab_musicbrainz",
               "audio_lab_organize",
               "audio_lab_conversion",
               "audio_lab_vinyl_lab"):
        return "audio_lab"
    # Settings (ya no está en sidebar, pero la ruta sigue siendo válida)
    if key in ("settings_hub", "settings"):
        return "playback_hub"
    # Fallback: extraer prefijo antes de ":"
    prefix = key.split(":")[0] if ":" in key else key
    return prefix if prefix in (
        "home", "library_hub", "mix_hub", "playlist_hub",
        "playback_hub", "connections_hub", "home_audio",
        "audio_lab", "assistant", "devices_page",
    ) else "home"

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
    "audio_lab_diagnostics": "_show_audio_lab_diagnostics",
    "audio_lab_identifier": "_show_audio_lab_identifier",
    "audio_lab_backup": "_show_audio_lab_backup",
    "audio_lab_output": "_show_audio_lab_output",
    "audio_lab_intelligence": "_show_audio_lab_intelligence",
    "audio_lab_musicbrainz": "_show_audio_lab_musicbrainz",
    "audio_lab_organize": "_show_audio_lab_organize",
    "audio_lab_conversion": "_show_audio_lab_conversion",
    "audio_lab_vinyl_lab": "_show_audio_lab_vinyl_lab",
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
    "artists": "Buscar artistas...", "genres": "Buscar géneros...",
    "playlists": "Buscar en playlists...",
    "folders": "Buscar carpeta...", "radio": "Buscar emisoras...",
    "playlist_hub": "Buscar playlists...", "favs": "Buscar favoritos...",
    "recent": "Buscar recientes...",
    "mix_unplayed": "Buscar canciones...", "mix_favorites": "Buscar favoritos...",
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

    def push(self, key: str, search_text: str = "", force: bool = False):
        """Add a navigation entry, truncating forward history if not at tip.

        When force=True, always creates a new entry even if the key matches
        the current one (used for detail view checkpoints).
        """
        if not force and self._history and self._history[self._index][0] == key:
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

    def force_push(self, key: str, search_text: str = ""):
        """Push a history entry even if the key matches current route.

        Used before opening detail views so back/forward can restore the parent view.
        """
        self._history.push(key, search_text, force=True)
        self._update_buttons()

    def checkpoint(self):
        """Bookmark current route before showing a detail/sub-view.

        This creates a history restore point so navigate_back returns to the parent view.
        """
        w = self._win
        key = getattr(w, '_current_route_key', None) or "home"
        search = getattr(w, '_search_text', "")
        self.force_push(key, search)

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
        except Exception as e:
            _log.warning("Navigation restore failed for %s: %s", key, e)
        finally:
            self._history._restoring = False
            self._update_buttons()

    def _update_buttons(self):
        w = self._win
        can_back = self._history.can_go_back
        can_fwd = self._history.can_go_forward
        if hasattr(w, '_back_btn'):
            w._back_btn.setEnabled(can_back)
            w._back_btn.setToolTip("Atrás" if can_back else "Sin historial")
        if hasattr(w, '_forward_btn'):
            w._forward_btn.setEnabled(can_fwd)
            w._forward_btn.setToolTip("Adelante" if can_fwd else "Sin historial")

    # ── Header config ──
    def configure_header(self, section_key: str, route_key: str | None = None):
        w = self._win
        w._current_section_key = section_key
        w._current_route_key = route_key if route_key is not None else section_key
        w._current_sidebar_key = resolve_sidebar_active_key(route_key or section_key)
        config = resolve_section_config(section_key)
        title = config.get("title", "Todas las canciones")
        subtitle = config.get("subtitle", "")
        icon_name = config.get("icon", "sidebar_library")
        views = config.get("views", ["list", "grid"])
        search = config.get("search", True)
        default = config.get("default", "list")

        w._section_title.setText(title)
        w._section_subtitle.setText(self._build_breadcrumb(subtitle, section_key))

        icon_pix = get_qicon(icon_name, size=24).pixmap(24, 24)
        if not icon_pix.isNull():
            w._section_icon.setPixmap(icon_pix)
        else:
            _log.warning("Icon pixmap is null for key=%s icon=%s", section_key, icon_name)
            w._section_icon.clear()

        w._search.setPlaceholderText(_SEARCH_PLACEHOLDERS.get(section_key, "Buscar..."))
        w._search.setVisible(search)

        w._view_switcher.set_available_modes(views, default, context=section_key)
        w._view_switcher.update_for_width(w.width())

        if w._view_mode not in views and default:
            w._view_mode = default
            w._view_switcher.set_view(default, emit=False)

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
        self.configure_header(section_key, route_key=key)

        # Notify context service about navigation change
        ctx = getattr(w, '_context_svc', None)
        if ctx:
            ctx.update_navigation(key, extra={"section_key": section_key})

        # State explícito: ruta real, sidebar activo, sección funcional
        w._current_route_key = key
        w._current_sidebar_key = resolve_sidebar_active_key(key)
        w._current_section_key = section_key
        if hasattr(w, '_sidebar_controller'):
            w._sidebar_controller.set_active(w._current_sidebar_key)

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
                _log.warning("Navigation handler %s failed for key=%s: %s", method_name, key, e)
        elif not method_name and not any(key.startswith(p) for p in ("playlist:", "pl:", "srv:", "dev:", "mix_")):
            _log.warning("No navigation handler for key: %s", key)

    def _build_breadcrumb(self, subtitle: str, section_key: str) -> str:
        prev_key = self._history.current_key
        if prev_key is None:
            return subtitle
        hub_names = {
            "home": "Inicio", "library_hub": "Biblioteca", "mix_hub": "Mix",
            "playback_hub": "Reproducción", "connections_hub": "Conexiones",
            "radio": "Radio", "audio_lab": "Audio Lab",
            "audio_lab_diagnostics": "Audio Lab",
            "audio_lab_identifier": "Audio Lab",
            "audio_lab_backup": "Audio Lab",
            "audio_lab_output": "Audio Lab",
            "audio_lab_intelligence": "Audio Lab",
            "audio_lab_musicbrainz": "Audio Lab",
            "audio_lab_organize": "Audio Lab",
            "audio_lab_conversion": "Audio Lab",
            "audio_lab_vinyl_lab": "Audio Lab",
            "settings_hub": "Configuración", "home_audio": "Home Audio",
            "library": "Biblioteca", "albums": "Biblioteca",
            "artists": "Biblioteca", "genres": "Biblioteca",
            "folders": "Biblioteca",
        }
        hub = hub_names.get(prev_key, "")
        if hub and section_key not in ("home", "library_hub", "mix_hub",
                                         "playback_hub", "connections_hub",
                                         "settings_hub", "audio_lab",
                                         "audio_lab_diagnostics",
                                         "audio_lab_identifier",
                                         "audio_lab_backup",
                                         "audio_lab_output",
                                         "audio_lab_intelligence",
                                         "audio_lab_musicbrainz",
                                         "audio_lab_organize",
                                         "audio_lab_conversion",
                                         "audio_lab_vinyl_lab"):
            return f"{hub} / {subtitle}" if subtitle else hub
        return subtitle
