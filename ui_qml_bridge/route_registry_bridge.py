"""RouteRegistryBridge — exposes the route registry to QML."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Property, Slot

from .route_registry import ROUTES, ROUTE_ALIASES, resolve_route, get_breadcrumb, get_sidebar_sections, is_child_active, get_parent_route

logger = logging.getLogger(__name__)


class RouteRegistryBridge(QObject):
    registryChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        logger.debug("RouteRegistryBridge.__init__ called")

    @Property("QVariantList", notify=registryChanged)
    def routes(self):
        result = []
        for key, info in ROUTES.items():
            entry = {"id": key}
            entry.update(info)
            result.append(entry)
        return result

    @Property("QVariantList", notify=registryChanged)
    def routeIds(self):
        return list(ROUTES.keys())

    @Slot(str, result=bool)
    def isValidRoute(self, route: str):
        return route in ROUTES

    @Slot(str, result=str)
    def getTitle(self, route: str):
        info = ROUTES.get(route)
        return info["title"] if info else "Sección en migración"

    @Slot(str, result=str)
    def getSource(self, route: str):
        info = ROUTES.get(route)
        return info["source"] if info else "../pages/PlaceholderPage.qml"

    @Slot(str, result=str)
    def getStatus(self, route: str):
        info = ROUTES.get(route)
        return info["status"] if info else "placeholder"

    @Slot(str, result=str)
    def getCategory(self, route: str):
        info = ROUTES.get(route)
        return info["category"] if info else "system"

    @Slot(str, result="QVariantMap")
    def getParams(self, route: str):
        info = ROUTES.get(route)
        return info.get("params", {}) if info else {}

    @Slot(str, result="QVariantList")
    def getRequiredParamKeys(self, route: str):
        info = ROUTES.get(route)
        params = info.get("params", {}) if info else {}
        return [k for k, v in params.items() if v.get("required")]

    @Slot(str, "QVariantMap", result=bool)
    def hasRequiredParams(self, route: str, params: dict):
        info = ROUTES.get(route)
        if not info:
            return False
        route_params = info.get("params", {})
        for key, spec in route_params.items():
            if spec.get("required") and key not in params:
                return False
        return True

    @Slot(str, result=str)
    def resolveRoute(self, route: str):
        return resolve_route(route)

    @Slot(str, result=str)
    def resolveAlias(self, route: str):
        return ROUTE_ALIASES.get(route, route)

    @Slot(str, result="QVariantList")
    def getBreadcrumb(self, route: str):
        return get_breadcrumb(route)

    @Slot(result="QVariantList")
    def getSidebarSections(self):
        sections, fixed = get_sidebar_sections()
        result = []
        for s in sections:
            result.append(s)
        for f in fixed:
            result.append(f)
        return result

    @Slot(str, result=str)
    def getParentRoute(self, route: str):
        return get_parent_route(route) or ""

    @Slot(str, str, result=bool)
    def isChildActive(self, parent_route: str, current_route: str):
        return is_child_active(parent_route, current_route)

    @Slot(str, result="QVariant")
    def getIconPath(self, route: str):
        info = ROUTES.get(route)
        icon = info.get("icon", "") if info else ""
        if icon:
            return f"../../icons/sidebar/{icon}.svg"
        return ""

    @Slot(str, result=str)
    def getBreadcrumbTitle(self, route: str):
        info = ROUTES.get(route)
        return info.get("breadcrumb_title", info.get("title", "")) if info else ""
