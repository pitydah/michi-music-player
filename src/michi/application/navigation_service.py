"""Navigation use case — sole authority over NavigationState."""

import logging
from collections.abc import Callable

from michi.domain.navigation import AppRoute, NavigationState

logger = logging.getLogger(__name__)


class NavigationService:
    """Owns NavigationState. Publishes changes."""

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
        for cb in self._subscribers:
            cb()

    def navigate(self, route_id: str) -> None:
        try:
            route = AppRoute(route_id)
        except ValueError:
            logger.warning("Invalid navigation route: %s", route_id)
            return

        if route == self._state.current_route:
            return

        self._state.current_route = route
        self._notify()
