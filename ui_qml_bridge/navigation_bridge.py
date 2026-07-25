from __future__ import annotations

import json
import logging
import time
from typing import Any

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot
from PySide6.QtQml import QJSValue

from .route_registry import CAPABILITY_MAP, ROUTES, get_breadcrumb, resolve_route

logger = logging.getLogger(__name__)


class NavigationBridge(QObject):
    routeChanged = Signal(str)
    routeParamsChanged = Signal()
    backStackChanged = Signal()
    forwardStackChanged = Signal()
    routeRefreshRequested = Signal(str)
    invalidRouteError = Signal(str, str)
    breadcrumbChanged = Signal()
    navigationBlocked = Signal(str, str)
    pendingNavigationChanged = Signal()

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
        self._leave_guards: dict[str, QObject] = {}
        self._pending_navigation: dict | None = None
        self._resolving_guard = False
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
        if req is None:
            return
        route = req.get("route", "")
        params = req.get("params", {})
        action = req.get("action", "")
        if action == "back":
            self.back()
        elif action == "forward":
            self.forward()
        elif route:
            self.navigateWithParams(route, params)

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
            return canonical
        return "placeholder"

    @staticmethod
    def _params_from_qml(params: Any) -> dict:
        if isinstance(params, QJSValue):
            params = params.toVariant()
        return dict(params) if isinstance(params, dict) else {}

    def _validate_params(self, route: str, params: dict) -> str | None:
        info = ROUTES.get(route)
        if not info:
            return None
        route_params = info.get("params")
        if route_params is None:
            return None
        if not isinstance(route_params, dict):
            logger.warning("Route %s has invalid params spec (not a dict)", route)
            return None
        for key, spec in route_params.items():
            if not isinstance(spec, dict):
                logger.warning("Route %s param %s has invalid spec (not a dict)", route, key)
                continue
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

    @staticmethod
    def _route_in_prefix(route: str, prefix: str) -> bool:
        return route == prefix or route.startswith(prefix + ".")

    def _guard_for_route(self, route: str) -> tuple[str, QObject] | None:
        matches = [
            (prefix, guard)
            for prefix, guard in self._leave_guards.items()
            if self._route_in_prefix(route, prefix)
        ]
        if not matches:
            return None
        return max(matches, key=lambda item: len(item[0]))

    @staticmethod
    def _guard_has_pending_changes(guard: QObject) -> bool:
        try:
            value = getattr(guard, "hasPendingChanges", False)
            if callable(value):
                value = value()
            return bool(value)
        except Exception:
            logger.debug("Failed to evaluate navigation leave guard", exc_info=True)
            return False

    def _request_leave(
        self,
        action: str,
        target_route: str = "",
        params: dict | None = None,
    ) -> bool:
        if self._resolving_guard:
            return False
        if self._pending_navigation is not None:
            return True
        match = self._guard_for_route(self._current_route)
        if not match:
            return False
        prefix, guard = match
        if target_route and self._route_in_prefix(target_route, prefix):
            return False
        if not self._guard_has_pending_changes(guard):
            return False
        self._pending_navigation = {
            "action": action,
            "route": target_route,
            "params": dict(params or {}),
            "guard_prefix": prefix,
        }
        self.pendingNavigationChanged.emit()
        self.navigationBlocked.emit(target_route, "pending_changes")
        return True

    def _clear_pending_navigation(self):
        if self._pending_navigation is None:
            return
        self._pending_navigation = None
        self.pendingNavigationChanged.emit()

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
        return bool(self._back_stack)

    @Property(bool, notify=forwardStackChanged)
    def canGoForward(self):
        return bool(self._forward_stack)

    @Property("QVariantList", notify=backStackChanged)
    def history(self):
        return [
            {"route": route, "title": ROUTES.get(route, {}).get("title", "")}
            for route, _params in self._back_stack
        ]

    @Property(bool, notify=pendingNavigationChanged)
    def hasPendingNavigation(self):
        return self._pending_navigation is not None

    @Property(str, notify=pendingNavigationChanged)
    def pendingTarget(self):
        if not self._pending_navigation:
            return ""
        return self._pending_navigation.get("route", "")

    def _navigate_internal(self, route: str, params: dict | None = None):
        params = dict(params or {})
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

    def _replace_internal(self, route: str, params: dict | None = None):
        resolved = self._resolve(route)
        if resolved == self._current_route and dict(params or {}) == self._current_params:
            self.routeRefreshRequested.emit(resolved)
            return
        self._current_route = resolved
        self._current_params = dict(params or {})
        self.routeChanged.emit(resolved)
        self.routeParamsChanged.emit()
        self.breadcrumbChanged.emit()

    def _back_internal(self):
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
        self.breadcrumbChanged.emit()

    def _forward_internal(self):
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
        self.breadcrumbChanged.emit()

    @Slot(str, QObject)
    def registerLeaveGuard(self, route_prefix: str, guard: QObject):
        if route_prefix and guard is not None:
            self._leave_guards[route_prefix] = guard

    @Slot(str)
    def unregisterLeaveGuard(self, route_prefix: str):
        self._leave_guards.pop(route_prefix, None)

    @Slot(str, result=dict)
    def resolvePendingNavigation(self, decision: str):
        pending = self._pending_navigation
        if pending is None:
            return {"ok": False, "error": "NO_PENDING_NAVIGATION"}
        if decision not in {"apply", "discard", "cancel"}:
            return {"ok": False, "error": "INVALID_DECISION"}

        if decision == "cancel":
            self._clear_pending_navigation()
            return {"ok": True, "cancelled": True}

        guard_match = self._guard_for_route(self._current_route)
        guard = guard_match[1] if guard_match else None
        method_name = "commitAll" if decision == "apply" else "rollbackAll"
        if guard is None or not hasattr(guard, method_name):
            return {"ok": False, "error": "GUARD_ACTION_UNAVAILABLE"}

        result = getattr(guard, method_name)()
        if isinstance(result, dict) and not result.get("ok", False):
            return {"ok": False, "error": "GUARD_ACTION_FAILED", "result": result}

        self._clear_pending_navigation()
        self._resolving_guard = True
        try:
            action = pending.get("action")
            if action == "navigate":
                self._navigate_internal(pending.get("route", ""), pending.get("params", {}))
            elif action == "replace":
                self._replace_internal(pending.get("route", ""), pending.get("params", {}))
            elif action == "back":
                self._back_internal()
            elif action == "forward":
                self._forward_internal()
            else:
                return {"ok": False, "error": "UNKNOWN_PENDING_ACTION"}
        finally:
            self._resolving_guard = False
        return {"ok": True, "decision": decision}

    @Slot(str)
    def navigate(self, route: str):
        if route == self._current_route:
            self.routeRefreshRequested.emit(route)
            return
        resolved = self._resolve(route)
        if self._request_leave("navigate", resolved):
            return
        self._navigate_internal(route)

    @Slot(str, "QVariant")
    def navigateWithParams(self, route: str, params: dict):
        params = self._params_from_qml(params)
        resolved = self._resolve(route)
        if resolved == self._current_route:
            param_error = self._validate_params(resolved, params)
            if param_error:
                self.invalidRouteError.emit(route, param_error)
                return
            if params == self._current_params:
                self.routeRefreshRequested.emit(resolved)
                return
            self.updateCurrentParams(params)
            return
        if self._request_leave("navigate", resolved, params):
            return
        self._navigate_internal(route, params)

    @Slot("QVariant")
    def updateCurrentParams(self, params: dict):
        next_params = self._params_from_qml(params)
        if next_params == self._current_params:
            return
        self._current_params = next_params
        self.routeParamsChanged.emit()

    @Slot(str)
    def replace(self, route: str):
        resolved = self._resolve(route)
        if self._request_leave("replace", resolved):
            return
        self._replace_internal(route)

    @Slot()
    def back(self):
        if not self._back_stack:
            return
        target = self._back_stack[-1][0]
        if self._request_leave("back", target):
            return
        self._back_internal()

    @Slot()
    def forward(self):
        if not self._forward_stack:
            return
        target = self._forward_stack[-1][0]
        if self._request_leave("forward", target):
            return
        self._forward_internal()

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
                    key, value = pair.split("=", 1)
                    params[key] = value
        resolved = self._resolve(path)
        if self._request_leave("navigate", resolved, params):
            return {"ok": False, "blocked": True, "route": path, "params": params}
        self._navigate_internal(path, params)
        return {"ok": True, "route": path, "params": params}

    @Slot(result=dict)
    def saveState(self):
        return {
            "ok": True,
            "state": json.dumps(
                {
                    "version": 1,
                    "timestamp": time.time(),
                    "current_route": self._current_route,
                    "current_params": self._current_params,
                    "back_stack": self._back_stack,
                    "forward_stack": self._forward_stack,
                }
            ),
        }

    @Slot(str, result=dict)
    def restoreState(self, state_json: str):
        try:
            state = json.loads(state_json)
            if state.get("version") == 1:
                self._current_route = state.get("current_route", "home")
                self._current_params = state.get("current_params", {})
                self._back_stack = [tuple(item) for item in state.get("back_stack", [])]
                self._forward_stack = [tuple(item) for item in state.get("forward_stack", [])]
                self.routeChanged.emit(self._current_route)
                self.routeParamsChanged.emit()
                self.backStackChanged.emit()
                self.forwardStackChanged.emit()
                self.breadcrumbChanged.emit()
                return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": False, "error": "INVALID_STATE"}
