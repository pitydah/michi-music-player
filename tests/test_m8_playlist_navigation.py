"""M8-R1: first-class PLAYLISTS navigation gates.

AppRoute.PLAYLISTS + playlist target semantics:
- navigate(PLAYLISTS) → All Playlists (target None)
- navigate_to_playlist(id) → PLAYLISTS / id
- leaving PLAYLISTS clears the target (invariant: target only on PLAYLISTS)
- rename never resets the target (identity-based)
- deleting the selected playlist converges to PLAYLISTS / All Playlists
- unknown ids fail safe (All Playlists)
- deterministic notifications; idempotent same-target navigation
"""

from michi.application.navigation_service import NavigationService
from michi.application.playlist_service import PlaylistService
from michi.application.queue_service import QueueService
from michi.domain.navigation import AppRoute
from tests.test_playlists import FakePlaylistsPort


def _nav():
    return NavigationService()


def _service_and_nav():

    _queue = QueueService()
    service = PlaylistService(playlists_port=FakePlaylistsPort())
    nav = NavigationService()
    service.set_on_playlist_deleted(nav.forget_playlist)
    return service, nav


class TestAppRoute:
    def test_playlists_route_exists(self):
        assert AppRoute.PLAYLISTS == "playlists"
        assert "playlists" in {r.value for r in AppRoute}

    def test_existing_routes_unchanged(self):
        assert AppRoute.NOW_PLAYING == "now_playing"
        assert AppRoute.LIBRARY == "library"
        assert AppRoute.QUEUE == "queue"
        assert AppRoute.SETTINGS == "settings"


class TestNavigate:
    def test_navigate_playlists_is_all_playlists(self):
        nav = _nav()
        nav.navigate(AppRoute.PLAYLISTS.value)
        assert nav.state.current_route == AppRoute.PLAYLISTS
        assert nav.state.playlist_id is None

    def test_navigate_to_playlist_sets_target(self):
        nav = _nav()
        nav.navigate_to_playlist("id-1")
        assert nav.state.current_route == AppRoute.PLAYLISTS
        assert nav.state.playlist_id == "id-1"

    def test_invariant_target_only_on_playlists(self):
        nav = _nav()
        nav.navigate_to_playlist("id-1")
        nav.navigate(AppRoute.LIBRARY.value)
        assert nav.state.playlist_id is None
        nav.navigate_to_playlist("id-2")
        nav.navigate(AppRoute.SETTINGS.value)
        assert nav.state.playlist_id is None

    def test_navigate_playlists_clears_stale_target(self):
        nav = _nav()
        nav.navigate_to_playlist("id-1")
        nav.navigate(AppRoute.PLAYLISTS.value)  # back to All Playlists
        assert nav.state.playlist_id is None

    def test_invalid_route_ignored(self):
        nav = _nav()
        nav.navigate("ghost")
        assert nav.state.current_route == AppRoute.LIBRARY

    def test_empty_playlist_target_rejected(self):
        nav = _nav()
        nav.navigate_to_playlist("")
        assert nav.state.playlist_id is None
        nav.navigate_to_playlist("   ")
        assert nav.state.playlist_id is None

    def test_same_target_idempotent(self):
        nav = _nav()
        calls = []
        nav.subscribe_changed(lambda: calls.append(1))
        nav.navigate_to_playlist("id-1")
        nav.navigate_to_playlist("id-1")
        assert calls == [1]


class TestDeleteConvergence:
    def test_delete_selected_converges_to_all_playlists(self):
        service, nav = _service_and_nav()
        created = service.create_playlist("Jazz")
        nav.navigate_to_playlist(created.playlist_id)
        service.delete_playlist(created.playlist_id)
        assert nav.state.current_route == AppRoute.PLAYLISTS
        assert nav.state.playlist_id is None

    def test_delete_non_selected_leaves_target(self):
        service, nav = _service_and_nav()
        a = service.create_playlist("A")
        b = service.create_playlist("B")
        nav.navigate_to_playlist(a.playlist_id)
        service.delete_playlist(b.playlist_id)
        assert nav.state.playlist_id == a.playlist_id

    def test_rename_keeps_navigation_target(self):
        service, nav = _service_and_nav()
        created = service.create_playlist("Jazz")
        nav.navigate_to_playlist(created.playlist_id)
        service.rename_playlist(created.playlist_id, "Jazz Nocturno")
        assert nav.state.current_route == AppRoute.PLAYLISTS
        assert nav.state.playlist_id == created.playlist_id

    def test_unknown_playlist_never_navigated_by_service(self):
        """open/navigate is caller-side; the service never invents targets."""
        service, nav = _service_and_nav()
        calls = []
        nav.subscribe_changed(lambda: calls.append(1))
        nav.forget_playlist("ghost-id")
        assert calls == []
        assert nav.state.playlist_id is None

    def test_forget_clears_only_matching_target(self):
        nav = _nav()
        nav.navigate_to_playlist("x")
        nav.forget_playlist("y")
        assert nav.state.playlist_id == "x"
        nav.forget_playlist("x")
        assert nav.state.playlist_id is None


class TestNotifications:
    def test_subscriber_gets_state_changes(self):
        nav = _nav()
        seen = []
        nav.subscribe_changed(lambda: seen.append(nav.state.current_route))
        nav.navigate(AppRoute.PLAYLISTS.value)
        nav.navigate_to_playlist("id-9")
        nav.navigate(AppRoute.QUEUE.value)
        assert seen == [
            AppRoute.PLAYLISTS,
            AppRoute.PLAYLISTS,
            AppRoute.QUEUE,
        ]

    def test_no_notify_on_invalid_route(self):
        nav = _nav()
        calls = []
        nav.subscribe_changed(lambda: calls.append(1))
        nav.navigate("nope")
        assert calls == []

    def test_navigate_same_route_idempotent(self):
        nav = _nav()
        calls = []
        nav.subscribe_changed(lambda: calls.append(1))
        nav.navigate(AppRoute.QUEUE.value)
        nav.navigate(AppRoute.QUEUE.value)
        assert calls == [1]
