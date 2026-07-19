"""RouteRegistryBridge — exposes the route registry to QML."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Property, Slot

from .route_registry import (
    ROUTES,
    ROUTE_ALIASES,
    get_breadcrumb,
    get_parent_route,
    get_sidebar_sections,
    is_child_active,
    resolve_route,
)

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
        return resolve_route(route) in ROUTES

    @Slot(str, result=str)
    def getTitle(self, route: str):
        canonical = resolve_route(route)
        info = ROUTES.get(canonical)
        return info["title"] if info else "Sección en migración"

    @Slot(str, result=str)
    def getSource(self, route: str):
        canonical = resolve_route(route)
        info = ROUTES.get(canonical)
        return info["source"] if info else "../pages/PlaceholderPage.qml"

    @Slot(str, result=str)
    def getStatus(self, route: str):
        canonical = resolve_route(route)
        info = ROUTES.get(canonical)
        return info["status"] if info else "placeholder"

    @Slot(str, result=str)
    def getCategory(self, route: str):
        canonical = resolve_route(route)
        info = ROUTES.get(canonical)
        return info["category"] if info else "system"

    @Slot(str, result="QVariantMap")
    def getParams(self, route: str):
        canonical = resolve_route(route)
        info = ROUTES.get(canonical)
        return (info.get("params") or {}) if info else {}

    @Slot(str, result="QVariantList")
    def getRequiredParamKeys(self, route: str):
        canonical = resolve_route(route)
        info = ROUTES.get(canonical)
        params = (info.get("params") or {}) if info else {}
        return [k for k, v in params.items() if v.get("required")]

    @Slot(str, "QVariantMap", result=bool)
    def hasRequiredParams(self, route: str, params: dict):
        canonical = resolve_route(route)
        info = ROUTES.get(canonical)
        if not info:
            return False
        route_params = info.get("params") or {}
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
        return sections

    @Property("QVariantList", notify=registryChanged)
    def sidebarSections(self):
        sections, _ = get_sidebar_sections()
        return sections

    @Slot(result="QVariantList")
    def getSidebarFixedItems(self):
        _, fixed = get_sidebar_sections()
        return fixed

    @Property("QVariantList", notify=registryChanged)
    def sidebarFixedItems(self):
        _, fixed = get_sidebar_sections()
        return fixed

    @Slot(str, result=str)
    def getParentRoute(self, route: str):
        return get_parent_route(route) or ""

    @Slot(str, str, result=bool)
    def isChildActive(self, parent_route: str, current_route: str):
        return is_child_active(parent_route, current_route)

    @Slot(str, result="QVariant")
    def getIconPath(self, route: str):
        canonical = resolve_route(route)
        info = ROUTES.get(canonical)
        icon = info.get("icon", "") if info else ""
        if icon:
            return f"../../icons/sidebar/{icon}.svg"
        return ""

    @Slot(str, result=str)
    def getBreadcrumbTitle(self, route: str):
        canonical = resolve_route(route)
        info = ROUTES.get(canonical)
        return info.get("breadcrumb_title", info.get("title", "")) if info else ""
