"""Navigation use case — sole authority over NavigationState."""

import logging
from collections.abc import Callable

from michi.domain.navigation import AppRoute, NavigationState

logger = logging.getLogger(__name__)

# E12_STAGE_INTEGRATION: the Ecosystem sub-routes are identities inside the
# single AppRoute.ECOSYSTEM target. NavigationService remains the only owner
# of the active route; the pages are not a second navigator.
ECOSYSTEM_ROUTE_IDS = frozenset(
    {
        "ecosystem",
        "ecosystem/home",
        "ecosystem/diagnostics",
        "ecosystem/spaces",
        "ecosystem/devices",
        "ecosystem/discovery",
        "ecosystem/streams",
        "ecosystem/micro-server",
        "ecosystem/michi-link",
        "ecosystem/mobile",
        "ecosystem/account",
        "ecosystem/integrations",
        "ecosystem/integrations/home-assistant",
        "ecosystem/music-stream/create",
    }
)


class NavigationService:
    """Owns NavigationState. Publishes changes.

    M8-R1: PLAYLISTS route carries an optional playlist_id target (None =
    All Playlists). Invariant enforced here: leaving PLAYLISTS clears the
    playlist target; navigating to PLAYLISTS without a target clears it."""

    def __init__(self) -> None:
        self._state = NavigationState()
        self._subscribers: list[Callable[[], None]] = []

    @property
    def state(self) -> NavigationState:
        return self._state

    def subscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _notify(self) -> None:
        for cb in list(self._subscribers):
            cb()

    def navigate(self, route_id: str) -> None:
        """Navigate to a route; PLAYLISTS without an explicit target means
        All Playlists. Leaving PLAYLISTS clears the playlist target.

        E14: an Ecosystem sub-route selects AppRoute.ECOSYSTEM and stores the
        validated page identity in ecosystem_route. Leaving Ecosystem resets
        that sub-route to its root, so a later visit never resurrects a stale
        page target.
        """
        if route_id in ECOSYSTEM_ROUTE_IDS:
            if (
                self._state.current_route == AppRoute.ECOSYSTEM
                and self._state.ecosystem_route == route_id
            ):
                return
            self._state.current_route = AppRoute.ECOSYSTEM
            self._state.playlist_id = None
            self._state.ecosystem_route = route_id
            self._notify()
            return

        try:
            route = AppRoute(route_id)
        except ValueError:
            logger.warning("Invalid navigation route: %s", route_id)
            return

        if (
            route == self._state.current_route
            and self._state.playlist_id is None
            and self._state.ecosystem_route == "ecosystem"
        ):
            return

        self._state.current_route = route
        self._state.playlist_id = None
        self._state.ecosystem_route = "ecosystem"
        self._notify()

    def navigate_to_playlist(self, playlist_id: str) -> None:
        """Navigate to a specific playlist (PLAYLISTS / <id>). Empty or
        whitespace ids are rejected; the caller resolves existence."""
        if not playlist_id or not playlist_id.strip():
            logger.warning("Invalid playlist navigation target")
            return
        if (
            self._state.current_route == AppRoute.PLAYLISTS
            and self._state.playlist_id == playlist_id
        ):
            return  # idempotent
        self._state.current_route = AppRoute.PLAYLISTS
        self._state.playlist_id = playlist_id
        self._state.ecosystem_route = "ecosystem"
        self._notify()

    def forget_playlist(self, playlist_id: str) -> None:
        """Converge when a playlist disappears: if it is the active target,
        fall back to PLAYLISTS / All Playlists. No-op otherwise."""
        if (
            self._state.current_route == AppRoute.PLAYLISTS
            and self._state.playlist_id == playlist_id
        ):
            self._state.playlist_id = None
            self._notify()
