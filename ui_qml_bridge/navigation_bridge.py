from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal, Property, Slot

from .route_registry import ROUTES, CAPABILITY_MAP, resolve_route, get_breadcrumb

logger = logging.getLogger(__name__)


class NavigationBridge(QObject):
    routeChanged = Signal(str)
    routeParamsChanged = Signal()
    backStackChanged = Signal()
    forwardStackChanged = Signal()
    routeRefreshRequested = Signal(str)
    invalidRouteError = Signal(str, str)
    breadcrumbChanged = Signal()

    def __init__(self, navigation_service: Any = None, parent=None):
        super().__init__(parent)
        logger.debug("NavigationBridge.__init__ called")
        self._nav_service = navigation_service
        self._current_route = "home"
        self._current_params: dict = {}
        self._back_stack: list[tuple[str, dict]] = []
        self._forward_stack: list[tuple[str, dict]] = []
        self._max_history = 50
        self._capabilities: set[str] = set()
        self._poll_timer: QTimer | None = None
        if navigation_service is not None:
            self._poll_timer = QTimer(self)
            self._poll_timer.setInterval(100)
            self._poll_timer.timeout.connect(self._poll_navigation_service)
            self._poll_timer.start()

    def set_capabilities(self, caps: set[str]):
        self._capabilities = caps

    def _poll_navigation_service(self):
        if self._nav_service is None:
            return
        req = self._nav_service.pop_last_request()
        if req is not None:
            route = req.get("route", "")
            params = req.get("params", {})
            action = req.get("action", "")
            if action == "back":
                self.back()
            elif action == "forward":
                self.forward()
            elif route:
                self._navigate_internal(route, params)

    def _route_matches_capability(self, route: str) -> bool:
        if not self._capabilities:
            return True
        for pattern, cap in CAPABILITY_MAP.items():
            if pattern.endswith(".*"):
                prefix = pattern[:-2]
                if route.startswith(prefix):
                    return cap in self._capabilities
            elif route == pattern:
                return cap in self._capabilities
        return True

    def _resolve(self, route: str) -> str:
        if not route:
            return "home"
        canonical = resolve_route(route)
        if canonical in ROUTES:
            if not self._route_matches_capability(canonical):
                return "home"
            return canonical
        return "placeholder"

    def _validate_params(self, route: str, params: dict) -> str | None:
        info = ROUTES.get(route)
        if not info:
            return None
        route_params = info.get("params", {})
        for key, spec in route_params.items():
            if spec.get("required") and key not in params:
                return f"Missing required parameter: {key}"
            if key in params:
                expected_type = spec.get("type", "string")
                val = params[key]
                if expected_type == "int":
                    try:
                        params[key] = int(val)
                    except (ValueError, TypeError):
                        return f"Parameter {key} must be {expected_type}"
        return None

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

    @Property("QVariantList", notify=breadcrumbChanged)
    def currentBreadcrumb(self):
        return get_breadcrumb(self._current_route)

    @Property(bool, notify=backStackChanged)
    def canGoBack(self):
        return len(self._back_stack) > 0

    @Property(bool, notify=forwardStackChanged)
    def canGoForward(self):
        return len(self._forward_stack) > 0

    @Property("QVariantList", notify=backStackChanged)
    def history(self):
        return [{"route": r, "title": ROUTES.get(r, {}).get("title", "")} for r, p in self._back_stack]

    def _navigate_internal(self, route: str, params: dict | None = None):
        if params is None:
            params = {}
        resolved = self._resolve(route)
        if resolved == "placeholder":
            self.invalidRouteError.emit(route, f"Route '{route}' not found")
        param_error = self._validate_params(resolved, params)
        if param_error:
            self.invalidRouteError.emit(route, param_error)
            return
        self._back_stack.append((self._current_route, dict(self._current_params)))
        if len(self._back_stack) > self._max_history:
            self._back_stack.pop(0)
        self._forward_stack.clear()
        self._current_route = resolved
        self._current_params = params
        self.routeChanged.emit(resolved)
        self.routeParamsChanged.emit()
        self.backStackChanged.emit()
        self.forwardStackChanged.emit()
        self.breadcrumbChanged.emit()

    @Slot(str)
    def navigate(self, route: str):
        if route == self._current_route:
            self.routeRefreshRequested.emit(route)
            return
        self._navigate_internal(route)

    @Slot(str, "QVariant")
    def navigateWithParams(self, route: str, params: dict):
        if params is None:
            params = {}
        self._navigate_internal(route, params)

    @Slot(str)
    def replace(self, route: str):
        resolved = self._resolve(route)
        if resolved == self._current_route:
            self.routeRefreshRequested.emit(resolved)
            return
        self._current_route = resolved
        self._current_params = {}
        self.routeChanged.emit(resolved)
        self.routeParamsChanged.emit()

    @Slot()
    def back(self):
        if not self._back_stack:
            return
        self._forward_stack.append((self._current_route, dict(self._current_params)))
        prev_route, prev_params = self._back_stack.pop()
        self._current_route = prev_route
        self._current_params = prev_params
        self.routeChanged.emit(prev_route)
        self.routeParamsChanged.emit()
        self.backStackChanged.emit()
        self.forwardStackChanged.emit()

    @Slot()
    def forward(self):
        if not self._forward_stack:
            return
        self._back_stack.append((self._current_route, dict(self._current_params)))
        next_route, next_params = self._forward_stack.pop()
        self._current_route = next_route
        self._current_params = next_params
        self.routeChanged.emit(next_route)
        self.routeParamsChanged.emit()
        self.backStackChanged.emit()
        self.forwardStackChanged.emit()

    @Slot()
    def clearHistory(self):
        self._back_stack.clear()
        self._forward_stack.clear()
        self.backStackChanged.emit()
        self.forwardStackChanged.emit()

    @Slot()
    def refreshCurrent(self):
        self.routeRefreshRequested.emit(self._current_route)

    @Slot(str, result=dict)
    def deepLink(self, route: str):
        parts = route.lstrip("/").split("?")
        path = parts[0]
        params = {}
        if len(parts) > 1:
            for pair in parts[1].split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    params[k] = v
        self._navigate_internal(path, params)
        return {"ok": True, "route": path, "params": params}

    @Slot(result=dict)
    def saveState(self):
        import json
        import time
        return {
            "ok": True,
            "state": json.dumps({
                "version": 1,
                "timestamp": time.time(),
                "current_route": self._current_route,
                "current_params": self._current_params,
                "back_stack": self._back_stack,
                "forward_stack": self._forward_stack,
            }),
        }

    @Slot(str, result=dict)
    def restoreState(self, state_json: str):
        import json
        try:
            state = json.loads(state_json)
            if state.get("version") == 1:
                self._current_route = state.get("current_route", "home")
                self._current_params = state.get("current_params", {})
                self._back_stack = [tuple(x) for x in state.get("back_stack", [])]
                self._forward_stack = [tuple(x) for x in state.get("forward_stack", [])]
                self.routeChanged.emit(self._current_route)
                self.routeParamsChanged.emit()
                self.backStackChanged.emit()
                self.forwardStackChanged.emit()
                return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "INVALID_STATE"}
