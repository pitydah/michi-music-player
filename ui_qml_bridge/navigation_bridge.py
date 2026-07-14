"""NavigationBridge — QML route navigation with back stack and params."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
from .route_registry import ROUTES


class NavigationBridge(QObject):
    routeChanged = Signal(str)
    routeParamsChanged = Signal()
    backStackChanged = Signal()
    routeRefreshRequested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_route = "home"
        self._current_params: dict = {}
        self._history: list[tuple[str, dict]] = []
        self._max_history = 50

    def _resolve(self, route: str) -> str:
        if not route:
            return "home"
        from ui_qml_bridge.route_registry import ALIASES
        if route in ALIASES:
            return ALIASES[route]["alias_of"]
        if route in ROUTES:
            return route
        return "placeholder"

    @Property(str, notify=routeChanged)
    def currentRoute(self):
        return self._current_route

    @Property(str, notify=routeChanged)
    def currentTitle(self):
        info = ROUTES.get(self._current_route)
        return info["title"] if info else "Sección en migración"

    @Property("QVariant", notify=routeParamsChanged)
    def currentParams(self):
        return self._current_params

    @Property(bool, notify=backStackChanged)
    def canGoBack(self):
        return len(self._history) > 0

    @Property("QVariantList", notify=backStackChanged)
    def history(self):
        return [{"route": r, "title": ROUTES.get(r, {}).get("title", "")} for r, p in self._history]

    @Slot(str)
    def navigate(self, route: str):
        resolved = self._resolve(route)
        if resolved == self._current_route:
            return
        self._history.append((self._current_route, dict(self._current_params)))
        if len(self._history) > self._max_history:
            self._history.pop(0)
        self._current_route = resolved
        self._current_params = {}
        self.routeChanged.emit(resolved)
        self.backStackChanged.emit()

    def _has_required_params(self, route: str, params: dict) -> bool:
        info = ROUTES.get(route)
        if not info:
            return True
        route_params = info.get("params", {})
        for key, spec in route_params.items():
            if spec.get("required") and key not in params:
                return False
        return True

    @Slot(str, "QVariant")
    def navigateWithParams(self, route: str, params: dict):
        if params is None:
            params = {}
        resolved = self._resolve(route)
        if not self._has_required_params(resolved, params):
            return
        self._history.append((self._current_route, dict(self._current_params)))
        if len(self._history) > self._max_history:
            self._history.pop(0)
        self._current_route = resolved
        self._current_params = params
        self.routeChanged.emit(resolved)
        self.routeParamsChanged.emit()
        self.backStackChanged.emit()

    @Slot(str)
    def replace(self, route: str):
        resolved = self._resolve(route)
        if resolved == self._current_route:
            return
        self._current_route = resolved
        self._current_params = {}
        self.routeChanged.emit(resolved)

    @Slot()
    def back(self):
        if not self._history:
            return
        prev_route, prev_params = self._history.pop()
        self._current_route = prev_route
        self._current_params = prev_params
        self.routeChanged.emit(prev_route)
        self.routeParamsChanged.emit()
        self.backStackChanged.emit()

    @Slot()
    def clearHistory(self):
        self._history.clear()
        self.backStackChanged.emit()

    @Slot()
    def refreshCurrent(self):
        self.routeRefreshRequested.emit(self._current_route)
