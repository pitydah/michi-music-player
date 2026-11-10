"""Navigation domain — route identities and state. No Qt/infrastructure.

M8-R1: PLAYLISTS route with an optional playlist target. Invariant:
current_route != PLAYLISTS ⇒ playlist_id is None (no hidden stale targets).
Navigation targets reference playlist ids — never names."""

from dataclasses import dataclass
from enum import StrEnum


class AppRoute(StrEnum):
    NOW_PLAYING = "now_playing"
    LIBRARY = "library"
    QUEUE = "queue"
    SETTINGS = "settings"
    PLAYLISTS = "playlists"
    # E14: the Ecosystem surface is one Player route with an explicit
    # sub-route identity. The sub-route never becomes a second navigator.
    ECOSYSTEM = "ecosystem"


@dataclass
class NavigationState:
    current_route: AppRoute = AppRoute.LIBRARY
    playlist_id: str | None = None
    ecosystem_route: str = "ecosystem"
