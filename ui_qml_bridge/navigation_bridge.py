from PySide6.QtCore import QObject, Signal, Property, Slot


VALID_ROUTES = {
    "home",
    "library",
    "mix",
    "playback",
    "connections",
    "radio",
    "playlists",
    "home_audio",
    "audio_lab",
    "assistant",
    "placeholder",
}


class NavigationBridge(QObject):
    routeChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_route = "home"

    @Property(str, notify=routeChanged)
    def currentRoute(self):
        return self._current_route

    @currentRoute.setter
    def currentRoute(self, route: str):
        if not route:
            route = "home"
        if route not in VALID_ROUTES:
            route = "placeholder"
        if route != self._current_route:
            self._current_route = route
            self.routeChanged.emit(route)

    @Slot(str)
    def navigate(self, route: str):
        self.currentRoute = route
