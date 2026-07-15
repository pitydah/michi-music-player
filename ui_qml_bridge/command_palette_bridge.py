from __future__ import annotations

import logging


from PySide6.QtCore import QObject, Signal, Property, Slot

from ui_qml_bridge.action_registry import ActionRegistry
from ui_qml_bridge.navigation_bridge import NavigationBridge
from ui_qml_bridge.capability_bridge import CapabilityBridge

logger = logging.getLogger("michi.command_palette")


class CommandPaletteBridge(QObject):
    commandsChanged = Signal()
    searchCompleted = Signal()

    def __init__(
        self,
        action_registry: ActionRegistry | None = None,
        navigation_bridge: NavigationBridge | None = None,
        nowplaying_bridge=None,
        capability_bridge: CapabilityBridge | None = None,
        confirmation_bridge=None,
        page_state_store=None,
        parent=None,
    ):
        super().__init__(parent)
        self._registry = action_registry or ActionRegistry()
        self._nav = navigation_bridge
        self._np = nowplaying_bridge
        self._cap = capability_bridge
        self._confirm = confirmation_bridge
        self._page_state = page_state_store
        self._search_results: list[dict] = []
        self._recent_commands: list[str] = []
        self._max_recent = 20
        self._sections: list[dict] = []
        self._build_sections()

    def _build_sections(self):
        self._sections = [
            {"id": "navigation", "title": "Navegacion", "icon": "navigation"},
            {"id": "playback", "title": "Reproduccion", "icon": "playback"},
            {"id": "library", "title": "Biblioteca", "icon": "library"},
            {"id": "track", "title": "Cancion", "icon": "track"},
            {"id": "album", "title": "Album", "icon": "album"},
            {"id": "playlist", "title": "Playlist", "icon": "playlist"},
            {"id": "system", "title": "Sistema", "icon": "system"},
        ]

    @Property("QVariantList", notify=commandsChanged)
    def commands(self):
        return self._registry.actions

    @Property("QVariantList", notify=commandsChanged)
    def sections(self):
        return self._sections

    @Property("QVariantList", notify=commandsChanged)
    def recentCommands(self):
        recent = []
        for cid in self._recent_commands:
            act = self._registry.get(cid)
            if act:
                recent.append({
                    "id": act.id, "title": act.title, "category": act.category,
                    "icon": act.icon_key, "shortcut": act.shortcut,
                })
        return recent

    @Property("QVariantList", notify=searchCompleted)
    def searchResults(self):
        return self._search_results

    def _check_capability(self, action: dict) -> tuple[bool, str]:
        if not self._cap:
            return True, ""
        category = action.get("category", "")
        cap_map = {
            "library": "library",
            "playback": "playback",
            "playlist": "playlists",
            "radio": "radio",
            "metadata": "metadata",
            "system": "diagnostics",
        }
        needed = cap_map.get(category)
        if needed and not self._cap.has(needed):
            return False, f"Funcionalidad '{needed}' no disponible"
        return True, ""

    def _filter_by_capability(self, actions: list[dict]) -> list[dict]:
        results = []
        for a in actions:
            ok, reason = self._check_capability(a)
            entry = dict(a)
            if not ok:
                entry["disabled"] = True
                entry["disabled_reason"] = reason
            else:
                entry["disabled"] = False
                entry["disabled_reason"] = ""
            results.append(entry)
        return results

    @Slot(str, result="QVariantList")
    def searchCommands(self, query: str):
        q = query.lower().strip()
        all_actions = self._registry.actions
        if not q:
            results = all_actions
        else:
            results = [
                a for a in all_actions
                if q in a.get("title", "").lower()
                or q in a.get("category", "").lower()
                or q in a.get("id", "").lower()
            ]
        results = self._filter_by_capability(results)
        self._search_results = results
        self.searchCompleted.emit()
        return results

    @Slot(str, result="QVariantList")
    def searchByCategory(self, category: str):
        results = self._registry.get_by_category(category)
        results = self._filter_by_capability(results)
        self._search_results = results
        self.searchCompleted.emit()
        return results

    @Slot(str, result=dict)
    def getActionDetail(self, command_id: str):
        action = self._registry.get(command_id)
        if not action:
            return {"ok": False, "error": "NOT_FOUND"}
        ok, reason = self._check_capability({
            "id": action.id, "category": action.category,
        })
        return {
            "ok": True,
            "id": action.id,
            "title": action.title,
            "category": action.category,
            "icon": action.icon_key,
            "shortcut": action.shortcut,
            "destructive": action.destructive,
            "requires_confirmation": action.requires_confirmation,
            "enabled": action.enabled,
            "visible": action.visible,
            "disabled": not ok,
            "disabled_reason": reason if not ok else "",
        }

    @Slot(str, result=dict)
    def executeCommand(self, command_id: str):
        action = self._registry.get(command_id)
        if not action:
            return {"ok": False, "error": "NOT_FOUND"}
        if not action.enabled:
            return {"ok": False, "error": "DISABLED"}
        ok, reason = self._check_capability({
            "id": action.id, "category": action.category,
        })
        if not ok:
            return {"ok": False, "error": "CAPABILITY_UNAVAILABLE", "reason": reason}
        self._add_recent(command_id)
        return self._registry.execute(command_id)

    def _add_recent(self, command_id: str):
        if command_id in self._recent_commands:
            self._recent_commands.remove(command_id)
        self._recent_commands.insert(0, command_id)
        if len(self._recent_commands) > self._max_recent:
            self._recent_commands = self._recent_commands[:self._max_recent]
        self.commandsChanged.emit()

    @Slot(str, result=dict)
    def executeNavigation(self, route: str):
        if not self._nav:
            return {"ok": False, "error": "NO_NAVIGATION"}
        self._nav.navigate(route)
        return {"ok": True, "route": route}

    @Slot(result=dict)
    def clearRecent(self):
        self._recent_commands.clear()
        self.commandsChanged.emit()
        return {"ok": True}

    @Slot(result="QVariantList")
    def keyboardShortcuts(self):
        shortcuts = []
        for a in self._registry.actions:
            if a.get("shortcut"):
                shortcuts.append({
                    "id": a["id"],
                    "title": a["title"],
                    "shortcut": a["shortcut"],
                    "category": a["category"],
                })
        return shortcuts

    @Slot(result=dict)
    def paletteScore(self) -> dict:
        score = 0
        if self._registry:
            score += 20
        if self._nav:
            score += 15
        if self._cap:
            score += 10
        if self._confirm:
            score += 10
        if self._page_state:
            score += 5
        if self._recent_commands:
            score += 5
        actions = self._registry.actions
        if actions:
            score += min(20, len(actions))
        return {
            "score": min(100, score),
            "total_commands": len(self._registry.actions),
            "recent_count": len(self._recent_commands),
            "has_nav": self._nav is not None,
            "has_capability": self._cap is not None,
            "has_confirmation": self._confirm is not None,
        }
