"""QML bridge for navigation — observes NavigationService."""

from PySide6.QtCore import Property, QObject, Signal, Slot

from michi.application.navigation_service import NavigationService


class NavigationBridge(QObject):
    """Thin adapter: NavigationService → QML properties, QML intent → service."""

    route_changed = Signal()

    def __init__(
        self, service: NavigationService, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._service = service
        service.subscribe_changed(self._on_service_changed)

    def dispose(self) -> None:
        self._service.unsubscribe_changed(self._on_service_changed)

    def _on_service_changed(self) -> None:
        self.route_changed.emit()

    def _get_current_route(self) -> str:
        return str(self._service.state.current_route.value)

    currentRoute = Property(str, _get_current_route, notify=route_changed)

    def _get_playlist_id(self) -> str:
        return self._service.state.playlist_id or ""

    playlistId = Property(str, _get_playlist_id, notify=route_changed)

    @Slot(str)
    def navigate(self, route_id: str) -> None:
        self._service.navigate(route_id)

    @Slot(str)
    def navigate_to_playlist(self, playlist_id: str) -> None:
        self._service.navigate_to_playlist(playlist_id)
