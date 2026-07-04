"""RouteRegistryBridge — exposes the route registry to QML."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
from .route_registry import ROUTES


class RouteRegistryBridge(QObject):
    registryChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

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
