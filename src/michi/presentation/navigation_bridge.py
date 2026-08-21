"""QML bridge for navigation — observes NavigationService.

M9-R1: the ONLY product-facing playlist intents are open_playlist /
open_all_playlists, routed through PlaylistNavigationCoordinator (validated
opens + automatic Recent). There is NO public navigate_to_playlist slot:
the low-level primitive exists only inside the coordinator."""

from PySide6.QtCore import Property, QObject, Signal, Slot

from michi.application.navigation_service import NavigationService
from michi.application.playlist_navigation_coordinator import (
    PlaylistNavigationCoordinator,
)


class NavigationBridge(QObject):
    """Thin adapter: NavigationService → QML properties, QML intent →
    coordinator → services."""

    route_changed = Signal()

    def __init__(
        self,
        service: NavigationService,
        parent: QObject | None = None,
        playlist_navigation: PlaylistNavigationCoordinator | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._coordinator = playlist_navigation
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
    def open_playlist(self, playlist_id: str) -> None:
        """PRODUCT INTENT: validated open — recent + navigation."""
        if self._coordinator is not None:
            self._coordinator.open_playlist(playlist_id)

    @Slot()
    def open_all_playlists(self) -> None:
        """PRODUCT INTENT: navigate to PLAYLISTS / All Playlists."""
        if self._coordinator is not None:
            self._coordinator.open_all_playlists()
