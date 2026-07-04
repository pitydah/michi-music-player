"""CommandPaletteBridge — command palette for QML."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot

_COMMANDS = [
    {"id": "navigate_home", "label": "Ir a Inicio", "keywords": "home inicio"},
    {"id": "navigate_library", "label": "Ir a Biblioteca", "keywords": "library biblioteca"},
    {"id": "navigate_playlists", "label": "Ir a Playlists", "keywords": "playlists listas"},
    {"id": "navigate_radio", "label": "Ir a Radio", "keywords": "radio emisoras"},
    {"id": "navigate_audio_lab", "label": "Ir a Audio Lab", "keywords": "audio lab herramientas"},
    {"id": "navigate_settings", "label": "Ir a Ajustes", "keywords": "settings ajustes"},
    {"id": "navigate_diagnostics", "label": "Ir a Diagnóstico", "keywords": "diagnostics diagnóstico"},
    {"id": "navigate_eq", "label": "Abrir EQ", "keywords": "eq ecualizador"},
    {"id": "playback_toggle", "label": "Reproducir / Pausar", "keywords": "play pause toggle"},
    {"id": "refresh_library", "label": "Refrescar Biblioteca", "keywords": "refresh biblioteca"},
    {"id": "open_metadata", "label": "Abrir Metadata", "keywords": "metadata inspector"},
    {"id": "open_smart_tagging", "label": "Abrir Smart Tagging", "keywords": "smart tagging etiquetado"},
]


class CommandPaletteBridge(QObject):
    commandsChanged = Signal()

    def __init__(self, navigation_bridge=None, library_bridge=None, nowplaying_bridge=None, parent=None):
        super().__init__(parent)
        self._nav = navigation_bridge
        self._lib = library_bridge
        self._np = nowplaying_bridge

    @Property("QVariantList", notify=commandsChanged)
    def commands(self):
        return _COMMANDS

    @Slot(str, result="QVariantList")
    def searchCommands(self, query: str):
        q = query.lower().strip()
        if not q:
            return _COMMANDS
        return [c for c in _COMMANDS if q in c["label"].lower() or q in c["keywords"].lower()]

    @Slot(str, result=dict)
    def executeCommand(self, command_id: str):
        if command_id.startswith("navigate_") and self._nav:
            route = command_id.replace("navigate_", "")
            self._nav.navigate(route)
            return {"ok": True}
        if command_id == "playback_toggle":
            if self._np:
                self._np.togglePlay()
            elif self._nav:
                self._nav.navigate("playback")
            return {"ok": True}
        if command_id == "refresh_library":
            if self._lib and hasattr(self._lib, 'refresh'):
                self._lib.refresh()
            return {"ok": True}
        return {"ok": False, "error": "UNKNOWN_COMMAND"}
