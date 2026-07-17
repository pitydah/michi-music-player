"""ActionRegistry — central registry of all user actions in the application.

Used by Command Palette, context menus, keyboard shortcuts, and toolbars.
Each action can optionally reference a service + method for contract validation.
"""
from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QObject, Signal, Property, Slot


class ActionDescriptor:
    def __init__(self, action_id: str, title: str, category: str,
                 icon_key: str = "", shortcut: str = "",
                 destructive: bool = False, requires_confirmation: bool = False,
                 handler: Callable | None = None,
                 service_name: str = "", method_name: str = "",
                 argument_schema: tuple[str, ...] = (),
                 capability: str | None = None):
        self.id = action_id
        self.title = title
        self.category = category
        self.icon_key = icon_key
        self.shortcut = shortcut
        self.destructive = destructive
        self.requires_confirmation = requires_confirmation
        self.handler = handler
        self.service_name = service_name
        self.method_name = method_name
        self.argument_schema = argument_schema
        self.capability = capability
        self.enabled = True
        self.visible = True


class ActionRegistry(QObject):
    registryChanged = Signal()

    def __init__(self, container: Any = None, parent=None):
        super().__init__(parent)
        self._container = container
        self._actions: dict[str, ActionDescriptor] = {}
        self._init_defaults()

    def set_container(self, container: Any):
        self._container = container

    def _make_nav_handler(self, route: str):
        return lambda: (
            self._container.navigation_bridge.navigate(route)
            if self._container and hasattr(self._container, 'navigation_bridge')
            and self._container.navigation_bridge
            else {"ok": False, "error": "NO_NAV"}
        )

    def _make_service_handler(self, service_attr: str, method: str, *args):
        return lambda: (
            getattr(getattr(self._container, service_attr, None), method, lambda: None)(*args)
            if self._container and hasattr(self._container, service_attr)
            else {"ok": False, "error": f"NO_{service_attr.upper()}"}
        )

    def bind_default_handlers(self):
        nav_actions = [
            "navigate_home", "navigate_library", "navigate_playlists",
            "navigate_radio", "navigate_lyrics", "navigate_settings",
            "navigate_eq", "navigate_library_sources", "navigate_jobs",
            "navigate_queue", "navigate_history", "navigate_home_audio",
            "navigate_diagnostics", "navigate_library_doctor", "navigate_mix",
        ]
        route_map = {
            "navigate_home": "home", "navigate_library": "library",
            "navigate_playlists": "playlists", "navigate_radio": "radio",
            "navigate_lyrics": "lyrics", "navigate_settings": "settings",
            "navigate_eq": "equalizer", "navigate_library_sources": "library.sources",
            "navigate_jobs": "jobs", "navigate_queue": "queue",
            "navigate_history": "history", "navigate_home_audio": "home_audio",
            "navigate_diagnostics": "diagnostics",
            "navigate_library_doctor": "library_doctor", "navigate_mix": "mix",
        }
        for aid in nav_actions:
            action = self._actions.get(aid)
            if action and aid in route_map:
                action.handler = self._make_nav_handler(route_map[aid])
                action.service_name = "navigation_bridge"

        playback_map = {
            "playback_playpause": ("playback_bridge", "togglePlay"),
            "playback_next": ("playback_bridge", "next"),
            "playback_prev": ("playback_bridge", "previous"),
            "playback_volume_up": ("playback_bridge", "volumeUp"),
            "playback_volume_down": ("playback_bridge", "volumeDown"),
            "playback_mute": ("playback_bridge", "toggleMute"),
            "playback_seek_forward": ("playback_bridge", "seekForward"),
            "playback_seek_back": ("playback_bridge", "seekBack"),
        }
        for aid, (svc, method) in playback_map.items():
            action = self._actions.get(aid)
            if action:
                action.handler = self._make_service_handler(svc, method)
                action.service_name = svc

        library_map = {
            "library_refresh": ("library_bridge", "refresh"),
            "library_scan": ("library_bridge", "scan"),
            "library_add_folder": ("library_bridge", "addFolder"),
        }
        for aid, (svc, method) in library_map.items():
            action = self._actions.get(aid)
            if action:
                action.handler = self._make_service_handler(svc, method)
                action.service_name = svc

        track_map = {
            "track_play_now": ("playback_bridge", "play"),
            "track_play_next": ("playback_bridge", "playNext"),
            "track_add_to_queue": ("queue_bridge", "add"),
            "track_favorite": ("library_bridge", "toggleFavorite"),
            "track_open_album": ("navigation_bridge", "navigateToAlbum"),
        }
        for aid, (svc, method) in track_map.items():
            action = self._actions.get(aid)
            if action:
                action.handler = self._make_service_handler(svc, method)
                action.service_name = svc

        album_map = {
            "album_play": ("playback_bridge", "playAlbum"),
            "album_shuffle": ("playback_bridge", "shuffleAlbum"),
            "album_queue": ("queue_bridge", "addAlbum"),
            "album_favorite": ("library_bridge", "toggleFavoriteAlbum"),
            "album_play_next": ("queue_bridge", "playNext"),
            "album_add_to_playlist": ("playlists_bridge", "addAlbum"),
        }
        for aid, (svc, method) in album_map.items():
            action = self._actions.get(aid)
            if action:
                action.handler = self._make_service_handler(svc, method)
                action.service_name = svc

        artist_map = {
            "artist_play": ("playback_bridge", "playArtist"),
            "artist_shuffle": ("playback_bridge", "shuffleArtist"),
            "artist_queue": ("queue_bridge", "addArtist"),
            "artist_radio": ("playback_bridge", "radioFromArtist"),
            "artist_add_to_playlist": ("playlists_bridge", "addArtist"),
        }
        for aid, (svc, method) in artist_map.items():
            action = self._actions.get(aid)
            if action:
                action.handler = self._make_service_handler(svc, method)
                action.service_name = svc

        folder_map = {
            "folder_play": ("playback_bridge", "playFolder"),
            "folder_queue": ("queue_bridge", "addFolder"),
        }
        for aid, (svc, method) in folder_map.items():
            action = self._actions.get(aid)
            if action:
                action.handler = self._make_service_handler(svc, method)
                action.service_name = svc

        track_extra_map = {
            "track_add_to_playlist": ("playlists_bridge", "addTrack"),
            "track_open_artist": ("navigation_bridge", "navigateToArtist"),
            "track_open_folder": ("navigation_bridge", "navigateToFolder"),
            "track_show_properties": ("navigation_bridge", "navigateToTrackProperties"),
            "track_edit_metadata": ("navigation_bridge", "navigateToMetadataEditor"),
            "track_radio": ("playback_bridge", "radioFromTrack"),
            "track_replace_queue": ("queue_bridge", "replace"),
            "track_unfavorite": ("library_bridge", "unfavorite"),
        }
        for aid, (svc, method) in track_extra_map.items():
            action = self._actions.get(aid)
            if action:
                action.handler = self._make_service_handler(svc, method)
                action.service_name = svc

        album_extra_map = {
            "album_open_folder": ("navigation_bridge", "navigateToAlbumFolder"),
            "album_edit_metadata": ("navigation_bridge", "navigateToAlbumMetadata"),
        }
        for aid, (svc, method) in album_extra_map.items():
            action = self._actions.get(aid)
            if action:
                action.handler = self._make_service_handler(svc, method)
                action.service_name = svc

        folder_extra_map = {
            "folder_open_filesystem": ("navigation_bridge", "navigateToFolder"),
            "folder_rescan": ("library_sources_bridge", "rescanFolder"),
        }
        for aid, (svc, method) in folder_extra_map.items():
            action = self._actions.get(aid)
            if action:
                action.handler = self._make_service_handler(svc, method)
                action.service_name = svc

        source_map = {
            "source_add": ("navigation_bridge", "navigateToSourceAdd"),
            "source_edit": ("navigation_bridge", "navigateToSourceEdit"),
            "source_scan": ("library_sources_bridge", "scan"),
            "source_cancel_scan": ("library_sources_bridge", "cancelScan"),
        }
        for aid, (svc, method) in source_map.items():
            action = self._actions.get(aid)
            if action:
                action.handler = self._make_service_handler(svc, method)
                action.service_name = svc

        meta_map = {
            "metadata_edit": ("navigation_bridge", "navigateToMetadataEditor"),
            "metadata_smart_tagging": ("navigation_bridge", "navigateToSmartTagging"),
        }
        for aid, (svc, method) in meta_map.items():
            action = self._actions.get(aid)
            if action:
                action.handler = self._make_service_handler(svc, method)
                action.service_name = svc

        other_map = {
            "playlist_create": ("playlists_bridge", "createPlaylist"),
            "radio_add_station": ("radio_bridge", "addStation"),
        }
        for aid, (svc, method) in other_map.items():
            action = self._actions.get(aid)
            if action:
                action.handler = self._make_service_handler(svc, method)
                action.service_name = svc

        system_map = {
            "app_quit": ("app_bridge", "quit"),
            "diagnostics_show": ("navigation_bridge", "navigate"),
        }
        for aid, (svc, method) in system_map.items():
            action = self._actions.get(aid)
            if action:
                if aid == "diagnostics_show":
                    action.handler = self._make_nav_handler("diagnostics")
                else:
                    action.handler = self._make_service_handler(svc, method)
                action.service_name = svc

    def _init_defaults(self):
        defaults = [
            ("navigate_home", "Ir a Inicio", "navigation", "home"),
            ("navigate_library", "Ir a Biblioteca", "navigation", "library"),
            ("navigate_playlists", "Ir a Playlists", "navigation", "playlists"),
            ("navigate_radio", "Ir a Radio", "navigation", "radio"),
            ("navigate_lyrics", "Ir a Letra", "navigation", "lyrics"),
            ("navigate_settings", "Ir a Ajustes", "navigation", "settings"),
            ("navigate_eq", "Abrir EQ", "navigation", "eq"),
            ("navigate_library_sources", "Fuentes de biblioteca", "navigation", "folder_add"),
            ("navigate_jobs", "Trabajos", "navigation", "tasks"),
            ("navigate_queue", "Cola", "navigation", "queue"),
            ("navigate_history", "Historial", "navigation", "history"),
            ("navigate_home_audio", "Home Audio", "navigation", "speaker"),
            ("navigate_diagnostics", "Diagnóstico", "navigation", "diagnostics"),
            ("navigate_library_doctor", "Library Doctor", "navigation", "stethoscope"),
            ("navigate_mix", "Mix", "navigation", "mix"),
            ("playback_playpause", "Reproducir / Pausar", "playback", "play"),
            ("playback_next", "Siguiente pista", "playback", "next"),
            ("playback_prev", "Pista anterior", "playback", "prev"),
            ("playback_volume_up", "Subir volumen", "playback", "volume_up"),
            ("playback_volume_down", "Bajar volumen", "playback", "volume_down"),
            ("playback_mute", "Silenciar", "playback", "mute"),
            ("playback_seek_forward", "Avanzar 10s", "playback", "seek_fwd"),
            ("playback_seek_back", "Retroceder 10s", "playback", "seek_back"),
            ("library_refresh", "Refrescar biblioteca", "library", "refresh"),
            ("library_scan", "Escanear biblioteca", "library", "scan"),
            ("library_add_folder", "Añadir carpeta", "library", "folder_add"),
            ("playlist_create", "Crear playlist", "playlist", "playlist"),
            ("metadata_edit", "Editar metadatos", "metadata", "tag"),
            ("metadata_smart_tagging", "Smart Tagging", "metadata", "magic", "", False, False, None, "", "", (), "smart_tagging"),
            ("radio_add_station", "Añadir emisora", "radio", "radio", "", False, False, None, "", "", (), "radio"),
            ("diagnostics_show", "Ver diagnóstico", "system", "diagnostics"),
            ("app_quit", "Salir", "system", "quit"),
            ("track_play_now", "Reproducir ahora", "track", "play"),
            ("track_play_next", "Reproducir siguiente", "track", "next"),
            ("track_add_to_queue", "Añadir a la cola", "track", "queue"),
            ("track_replace_queue", "Reemplazar cola", "track", "queue"),
            ("track_radio", "Radio desde tema", "track", "radio"),
            ("track_add_to_playlist", "Añadir a playlist", "track", "playlist"),
            ("track_favorite", "Marcar favorito", "track", "favorite"),
            ("track_unfavorite", "Quitar favorito", "track", "unfavorite"),
            ("track_open_album", "Abrir álbum", "track", "album"),
            ("track_open_artist", "Abrir artista", "track", "artist"),
            ("track_open_folder", "Abrir carpeta", "track", "folder"),
            ("track_show_properties", "Propiedades", "track", "info"),
            ("track_edit_metadata", "Editar metadatos", "track", "tag"),
            ("track_analyze_audio_lab", "Analizar en Audio Lab", "track", "lab"),
            ("track_convert", "Convertir formato", "track", "convert"),
            ("track_calculate_replaygain", "Calcular ReplayGain", "track", "replaygain"),
            ("track_check_integrity", "Verificar integridad", "track", "check"),
            ("track_find_duplicates", "Buscar duplicados", "track", "duplicate"),
            ("track_send_to_device", "Enviar a dispositivo", "track", "send"),
            ("track_exclude", "Excluir de biblioteca", "track", "exclude", True),
            ("track_relocate", "Reubicar archivo", "track", "relocate"),
            ("track_delete_from_library", "Eliminar de biblioteca", "track", "delete", True),
            ("track_delete_from_disk", "Eliminar del disco", "track", "delete_forever", True, True),
            ("album_play", "Reproducir álbum", "album", "play"),
            ("album_shuffle", "Mezclar álbum", "album", "shuffle"),
            ("album_queue", "Añadir álbum a cola", "album", "queue"),
            ("album_play_next", "Reproducir álbum después", "album", "next"),
            ("album_add_to_playlist", "Añadir álbum a playlist", "album", "playlist"),
            ("album_favorite", "Marcar álbum favorito", "album", "favorite"),
            ("album_edit_metadata", "Editar metadatos", "album", "tag"),
            ("album_change_artwork", "Cambiar carátula", "album", "artwork"),
            ("album_open_folder", "Abrir carpeta", "album", "folder"),
            ("album_analyze", "Analizar álbum", "album", "lab"),
            ("album_convert", "Convertir álbum", "album", "convert"),
            ("album_sync", "Sincronizar álbum", "album", "sync"),
            ("artist_play", "Reproducir artista", "artist", "play"),
            ("artist_shuffle", "Mezclar artista", "artist", "shuffle"),
            ("artist_queue", "Añadir artista a cola", "artist", "queue"),
            ("artist_add_to_playlist", "Añadir a playlist", "artist", "playlist"),
            ("artist_radio", "Radio desde artista", "artist", "radio"),
            ("folder_play", "Reproducir carpeta", "folder", "play"),
            ("folder_queue", "Añadir carpeta a cola", "folder", "queue"),
            ("folder_open_filesystem", "Abrir en gestor archivos", "folder", "folder"),
            ("folder_exclude", "Excluir carpeta", "folder", "exclude", True),
            ("folder_rescan", "Reescanear carpeta", "folder", "scan"),
            ("source_add", "Añadir fuente", "source", "add"),
            ("source_edit", "Editar fuente", "source", "edit"),
            ("source_remove", "Eliminar fuente", "source", "remove", True),
            ("source_enable", "Activar fuente", "source", "enable"),
            ("source_disable", "Desactivar fuente", "source", "disable"),
            ("source_scan", "Escanear fuente", "source", "scan"),
            ("source_cancel_scan", "Cancelar escaneo", "source", "cancel"),
        ]
        for entry in defaults:
            action_id, title, category, icon_key = entry[0], entry[1], entry[2], entry[3]
            shortcut = entry[4] if len(entry) > 4 and isinstance(entry[4], str) else ""
            destructive = entry[4] if len(entry) > 4 and isinstance(entry[4], bool) else (entry[5] if len(entry) > 5 and isinstance(entry[5], bool) else False)
            requires_confirmation = entry[5] if len(entry) > 5 and isinstance(entry[5], bool) else (entry[6] if len(entry) > 6 and isinstance(entry[6], bool) else False)
            handler = entry[6] if len(entry) > 6 and callable(entry[6]) else None
            service_name = entry[7] if len(entry) > 7 and isinstance(entry[7], str) else ""
            method_name = entry[8] if len(entry) > 8 and isinstance(entry[8], str) else ""
            argument_schema = entry[9] if len(entry) > 9 and isinstance(entry[9], tuple) else ()
            capability = entry[10] if len(entry) > 10 and isinstance(entry[10], str) else None
            self._actions[action_id] = ActionDescriptor(
                action_id=action_id, title=title, category=category, icon_key=icon_key,
                shortcut=shortcut, destructive=destructive,
                requires_confirmation=requires_confirmation, handler=handler,
                service_name=service_name, method_name=method_name,
                argument_schema=argument_schema, capability=capability,
            )

    def register(self, action: ActionDescriptor):
        if action.id in self._actions:
            raise ValueError(f"Duplicate action ID: {action.id}")
        self._actions[action.id] = action
        self.registryChanged.emit()

    def validate_all(self) -> list[dict]:
        issues = []
        for aid, action in self._actions.items():
            if action.handler is None and not action.service_name:
                continue
            if action.service_name and self._container:
                svc = getattr(self._container, action.service_name, None)
                if svc is None:
                    issues.append({
                        "action_id": aid, "issue": "service_not_found",
                        "service": action.service_name,
                    })
                elif action.method_name and not hasattr(svc, action.method_name):
                    issues.append({
                        "action_id": aid, "issue": "method_not_found",
                        "method": action.method_name,
                        "service": type(svc).__name__,
                    })
            if action.capability and self._container:
                cap_bridge = getattr(self._container, 'capability_bridge', None)
                if cap_bridge and not cap_bridge.has(action.capability):
                    issues.append({
                        "action_id": aid, "issue": "missing_capability",
                        "capability": action.capability,
                    })
        return issues

    def get(self, action_id: str) -> ActionDescriptor | None:
        return self._actions.get(action_id) if isinstance(self._actions.get(action_id), ActionDescriptor) else None

    @Slot(str, result=dict)
    def qmlGet(self, action_id: str) -> dict:
        action = self._actions.get(action_id)
        if isinstance(action, ActionDescriptor):
            return {"id": action.id, "title": action.title,
                    "category": action.category, "enabled": action.enabled,
                    "visible": action.visible, "handler_exists": action.handler is not None}
        return {}

    def find(self, action_id: str) -> ActionDescriptor | None:
        return self.get(action_id)

    @Property("QVariantList", notify=registryChanged)
    def actions(self):
        return [
            {"id": a.id, "title": a.title, "category": a.category,
             "icon": a.icon_key, "shortcut": a.shortcut,
             "destructive": a.destructive,
             "requires_confirmation": a.requires_confirmation,
             "enabled": a.enabled, "visible": a.visible}
            for a in self._actions.values() if a.visible
        ]

    def get_by_category(self, category: str) -> list[dict]:
        return [a for a in self.actions if a["category"] == category]

    @Slot(str, result=dict)
    def execute(self, action_id: str):
        action = self._actions.get(action_id)
        if not action or not action.enabled:
            return {"ok": False, "error": "NOT_FOUND"}
        if action.handler:
            try:
                result = action.handler()
                return result if isinstance(result, dict) else {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_HANDLER"}
