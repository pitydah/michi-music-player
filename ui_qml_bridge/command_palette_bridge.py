"""CommandPaletteBridge — command palette using ActionRegistry."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot

from ui_qml_bridge.action_registry import ActionRegistry


class CommandPaletteBridge(QObject):
    commandsChanged = Signal()

    def __init__(self, action_registry: ActionRegistry | None = None,
                 navigation_bridge=None, nowplaying_bridge=None, parent=None):
        super().__init__(parent)
        self._registry = action_registry or ActionRegistry()
        self._nav = navigation_bridge
        self._np = nowplaying_bridge

    @Property("QVariantList", notify=commandsChanged)
    def commands(self):
        return self._registry.actions

    @Slot(str, result="QVariantList")
    def searchCommands(self, query: str):
        q = query.lower().strip()
        all_actions = self._registry.actions
        if not q:
            return all_actions
        return [a for a in all_actions
                if q in a.get("title", "").lower()
                or q in a.get("category", "").lower()]

    @Slot(str, result=dict)
    def executeCommand(self, command_id: str):
        return self._registry.execute(command_id)
