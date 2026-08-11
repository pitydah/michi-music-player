"""Navigation domain — route identities and state. No Qt/infrastructure."""

from dataclasses import dataclass
from enum import StrEnum


class AppRoute(StrEnum):
    NOW_PLAYING = "now_playing"
    LIBRARY = "library"
    QUEUE = "queue"


@dataclass
class NavigationState:
    current_route: AppRoute = AppRoute.LIBRARY
