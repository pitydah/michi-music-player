"""PageStateStore — preserves QML page state across navigation."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
from PySide6.QtQml import QJSValue


class PageStateStore(QObject):
    stateChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._states: dict[str, dict] = {}
        self._history: list[str] = []
        self._max_history = 20

    @Slot(str, "QVariant")
    def saveState(self, route: str, state: dict):
        if isinstance(state, QJSValue):
            state = state.toVariant()
        self._states[route] = dict(state) if isinstance(state, dict) else {}
        self._update_history(route)
        self.stateChanged.emit()

    @Slot(str, result="QVariant")
    def restoreState(self, route: str) -> dict:
        return dict(self._states.get(route, {}))

    @Slot(str, result=bool)
    def hasState(self, route: str) -> bool:
        return route in self._states

    def _update_history(self, route: str):
        if self._history and self._history[-1] == route:
            return
        self._history.append(route)
        if len(self._history) > self._max_history:
            self._history.pop(0)

    @Property("QVariantList", notify=stateChanged)
    def history(self):
        return list(self._history)

    @Slot(result=str)
    def previousRoute(self) -> str:
        if len(self._history) >= 2:
            return self._history[-2]
        return "home"

    @Slot()
    def clear(self):
        self._states.clear()
        self._history.clear()
        self.stateChanged.emit()
