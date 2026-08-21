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

from michi.application.navigation_service import NavigationService
from michi.application.playlist_service import PlaylistService
from michi.domain.navigation import AppRoute


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

    def open_playlist(self, playlist_id: str) -> None:
        """OPEN PLAYLIST product intent: validate → mark recent → navigate.

        - Valid playlist: mark_recent(playlist_id) then navigate to
          PLAYLISTS/<id>. Both states legitimately change (two authorities),
          so two notifications may occur — never merged, never duplicated
          per authority.
        - Empty/whitespace/unknown id: fall back to PLAYLISTS / All
          Playlists. Recent is NOT touched; no dangling target is created.
        """
        if not playlist_id or not playlist_id.strip():
            self.open_all_playlists()
            return
        if self._playlists.get_playlist(playlist_id) is None:
            self.open_all_playlists()
            return
        self._playlists.mark_recent(playlist_id)
        self._navigation.navigate_to_playlist(playlist_id)
