"""ActionRegistry — central registry of all user actions in the application.

Used by Command Palette, context menus, keyboard shortcuts, and toolbars.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, Signal, Property, Slot


class ActionDescriptor:
    def __init__(self, action_id: str, title: str, category: str,
                 icon_key: str = "", shortcut: str = "",
                 destructive: bool = False, requires_confirmation: bool = False,
                 handler: Callable | None = None):
        self.id = action_id
        self.title = title
        self.category = category
        self.icon_key = icon_key
        self.shortcut = shortcut
        self.destructive = destructive
        self.requires_confirmation = requires_confirmation
        self.handler = handler
        self.enabled = True
        self.visible = True


class ActionRegistry(QObject):
    registryChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._actions: dict[str, ActionDescriptor] = {}
        self._init_defaults()

    def _init_defaults(self):
        defaults = [
            ("navigate_home", "Ir a Inicio", "navigation", "home"),
            ("navigate_library", "Ir a Biblioteca", "navigation", "library"),
            ("navigate_playlists", "Ir a Playlists", "navigation", "playlists"),
            ("navigate_radio", "Ir a Radio", "navigation", "radio"),
            ("navigate_lyrics", "Ir a Letra", "navigation", "lyrics"),
            ("navigate_settings", "Ir a Ajustes", "navigation", "settings"),
            ("navigate_eq", "Abrir EQ", "navigation", "eq"),
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
            ("metadata_smart_tagging", "Smart Tagging", "metadata", "magic"),
            ("radio_add_station", "Añadir emisora", "radio", "radio"),
            ("diagnostics_show", "Ver diagnóstico", "system", "diagnostics"),
            ("app_quit", "Salir", "system", "quit"),
        ]
        for action_id, title, category, icon in defaults:
            self._actions[action_id] = ActionDescriptor(
                action_id=action_id, title=title, category=category, icon_key=icon,
            )

    def register(self, action: ActionDescriptor):
        self._actions[action.id] = action
        self.registryChanged.emit()

    def get(self, action_id: str) -> ActionDescriptor | None:
        return self._actions.get(action_id)

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
