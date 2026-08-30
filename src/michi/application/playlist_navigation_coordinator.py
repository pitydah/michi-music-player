"""PlaylistNavigationCoordinator — application orchestration seam (M8-R1F).

Coordinates the EXISTING authorities for the product intent OPEN PLAYLIST:

    QML / Bridge
         │
         ▼
    PlaylistNavigationCoordinator.open_playlist(id)
         │
         ├── validate id against PlaylistService
         ├── mark Recent in PlaylistService
         └── navigate through NavigationService
                 ▼
            NavigationState

This class is NOT a state authority: it owns no state collection, no
persistence, no Qt, no threads. It only orchestrates PlaylistService and
NavigationService, which remain the sole owners of their respective states.

Ordering rule (observable result):
- VALID:   recent updated AND route targets the playlist.
- INVALID: recent unchanged AND route = PLAYLISTS / All Playlists.
"""

from michi.application.errors import PlaylistPersistenceError
from michi.application.navigation_service import NavigationService
from michi.application.playlist_service import PlaylistService
from michi.domain.navigation import AppRoute


class PlaylistOpenResult:
    """R3-03 application-level open outcome.

    OPEN PLAYLIST and PERSIST RECENT HISTORY are NOT one transaction:
    Recent is auxiliary navigation metadata. A Recent persistence failure
    must never block opening a valid playlist, and must never surface as
    a raw exception."""

    __slots__ = ("opened", "recent_persisted", "not_found")

    def __init__(self, opened: bool, recent_persisted: bool, not_found: bool):
        self.opened = opened
        self.recent_persisted = recent_persisted
        self.not_found = not_found

    @property
    def code(self) -> str:
        if not self.opened:
            return "not_found"
        return "opened" if self.recent_persisted else "opened_recent_unsaved"


class PlaylistNavigationCoordinator:
    def __init__(
        self,
        playlist_service: PlaylistService,
        navigation_service: NavigationService,
    ) -> None:
        self._playlists = playlist_service
        self._navigation = navigation_service

    def open_all_playlists(self) -> None:
        """Navigate to PLAYLISTS / All Playlists. Never mutates recent or
        pinned state; never writes persistence."""
        self._navigation.navigate(AppRoute.PLAYLISTS.value)

    def open_playlist(self, playlist_id: str) -> PlaylistOpenResult:
        """OPEN PLAYLIST product intent (R3-03): validate → mark recent
        (best-effort) → navigate.

        - Valid playlist: mark_recent is ATTEMPTED; if its persistence
          fails the playlist STILL OPENS and the result reports
          recent_persisted=False — opening content is the primary intent,
          Recent is secondary metadata.
        - Empty/whitespace/unknown id: fall back to PLAYLISTS / All
          Playlists (not_found). Recent is NOT touched.
        """
        if not playlist_id or not playlist_id.strip():
            self.open_all_playlists()
            return PlaylistOpenResult(False, False, True)
        if self._playlists.get_playlist(playlist_id) is None:
            self.open_all_playlists()
            return PlaylistOpenResult(False, False, True)
        recent_persisted = True
        try:
            self._playlists.mark_recent(playlist_id)
        except PlaylistPersistenceError:
            # Recent is auxiliary metadata: never block the primary intent.
            recent_persisted = False
        self._navigation.navigate_to_playlist(playlist_id)
        return PlaylistOpenResult(True, recent_persisted, False)
