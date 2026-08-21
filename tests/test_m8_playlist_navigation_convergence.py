"""M8-R1F: playlist navigation convergence gates.

Covers:
- PlaylistNavigationCoordinator: validated open intent (recent + navigation),
  idempotence, fallback for empty/whitespace/unknown ids, open != play.
- mark_recent idempotence (no persist/notify when already MRU rank 0).
- Notification semantics: exactly one notification per changed authority.
- Architecture: coordinator is pure orchestration; no new authorities.
"""

from michi.application.navigation_service import NavigationService
from michi.application.playlist_navigation_coordinator import (
    PlaylistNavigationCoordinator,
)
from michi.application.playlist_service import PlaylistService
from michi.application.queue_service import QueueService
from michi.domain.navigation import AppRoute
from michi.domain.playlist import PlaylistNavigationState
from tests.conftest import FakeAudioPort
from tests.test_playlists import FakePlaylistsPort


def _build():
    from michi.application.playback_service import PlaybackService

    audio = FakeAudioPort()
    queue = QueueService(PlaybackService(audio))
    service = PlaylistService(queue, FakePlaylistsPort())
    nav = NavigationService()
    service.set_on_playlist_deleted(nav.forget_playlist)
    return service, nav, PlaylistNavigationCoordinator(service, nav), queue, audio


class TestOpenValid:
    def test_open_valid_playlist_marks_recent_and_navigates(self):
        service, nav, coord, _, _ = _build()
        a = service.create_playlist("Jazz")
        coord.open_playlist(a.playlist_id)
        assert nav.state.current_route == AppRoute.PLAYLISTS
        assert nav.state.playlist_id == a.playlist_id
        assert service.navigation.recent_ids == (a.playlist_id,)

    def test_open_a_then_b_updates_mru(self):
        service, nav, coord, _, _ = _build()
        a = service.create_playlist("A")
        b = service.create_playlist("B")
        coord.open_playlist(a.playlist_id)
        coord.open_playlist(b.playlist_id)
        assert service.navigation.recent_ids == (b.playlist_id, a.playlist_id)

    def test_open_b_then_a_reorders_mru(self):
        service, nav, coord, _, _ = _build()
        a = service.create_playlist("A")
        b = service.create_playlist("B")
        coord.open_playlist(a.playlist_id)
        coord.open_playlist(b.playlist_id)
        coord.open_playlist(a.playlist_id)
        assert service.navigation.recent_ids == (a.playlist_id, b.playlist_id)

    def test_open_same_playlist_twice_is_idempotent(self):
        service, nav, coord, _, _ = _build()
        a = service.create_playlist("A")
        coord.open_playlist(a.playlist_id)
        service_calls, nav_calls = [], []
        service.subscribe_changed(lambda: service_calls.append(1))
        nav.subscribe_changed(lambda: nav_calls.append(1))
        coord.open_playlist(a.playlist_id)
        assert service.navigation.recent_ids == (a.playlist_id,)
        assert service_calls == []  # MRU rank 0 already: no-op
        assert nav_calls == []  # same route/target: idempotent


class TestOpenInvalid:
    def test_open_unknown_playlist_falls_back_to_all(self):
        service, nav, coord, _, _ = _build()
        coord.open_playlist("ghost-id")
        assert nav.state.current_route == AppRoute.PLAYLISTS
        assert nav.state.playlist_id is None
        assert service.navigation.recent_ids == ()

    def test_open_empty_id_falls_back_safely(self):
        service, nav, coord, _, _ = _build()
        coord.open_playlist("")
        assert nav.state.current_route == AppRoute.PLAYLISTS
        assert nav.state.playlist_id is None
        assert service.navigation.recent_ids == ()

    def test_open_whitespace_id_falls_back_safely(self):
        service, nav, coord, _, _ = _build()
        coord.open_playlist("   ")
        assert nav.state.current_route == AppRoute.PLAYLISTS
        assert nav.state.playlist_id is None
        assert service.navigation.recent_ids == ()

    def test_open_unknown_never_notifies_playlist_service(self):
        service, nav, coord, _, _ = _build()
        calls = []
        service.subscribe_changed(lambda: calls.append(1))
        coord.open_playlist("ghost")
        assert calls == []


class TestOpenAll:
    def test_open_all_playlists_does_not_mark_recent(self):
        service, nav, coord, _, _ = _build()
        a = service.create_playlist("A")
        service.mark_recent(a.playlist_id)
        coord.open_all_playlists()
        assert nav.state.current_route == AppRoute.PLAYLISTS
        assert nav.state.playlist_id is None
        assert service.navigation.recent_ids == (a.playlist_id,)  # untouched


class TestNotificationSemantics:
    def test_open_valid_new_playlist_notifies_both_once(self):
        service, nav, coord, _, _ = _build()
        a = service.create_playlist("A")
        service_calls, nav_calls = [], []
        service.subscribe_changed(lambda: service_calls.append(1))
        nav.subscribe_changed(lambda: nav_calls.append(1))
        coord.open_playlist(a.playlist_id)
        assert service_calls == [1]
        assert nav_calls == [1]

    def test_open_unknown_falls_back_with_single_nav_notification(self):
        service, nav, coord, _, _ = _build()
        service_calls, nav_calls = [], []
        service.subscribe_changed(lambda: service_calls.append(1))
        nav.subscribe_changed(lambda: nav_calls.append(1))
        coord.open_playlist("ghost")
        assert service_calls == []
        assert nav_calls == [1]  # route changed to PLAYLISTS once


class TestOpenIsNotPlay:
    def test_open_does_not_touch_queue(self):
        service, nav, coord, queue, _ = _build()
        a = service.create_playlist("P")
        service.add_track(a.playlist_id, "/m/a.mp3")
        coord.open_playlist(a.playlist_id)
        assert queue.state.count == 0  # open ≠ play

    def test_play_playlist_still_fills_queue(self):
        service, nav, coord, queue, audio = _build()
        a = service.create_playlist("P")
        service.add_track(a.playlist_id, "/m/a.mp3")
        service.play_playlist(a.playlist_id)
        assert queue.state.count == 1
        audio.trigger_media_accepted(__import__("pathlib").Path("/m/a.mp3"))
        assert queue.state.current_index == 0


class TestGetPlaylistQuery:
    def test_get_playlist_valid_and_unknown(self):
        service, _, _, _, _ = _build()
        a = service.create_playlist("A")
        assert service.get_playlist(a.playlist_id) is not None
        assert service.get_playlist(a.playlist_id).playlist_id == a.playlist_id
        assert service.get_playlist("ghost") is None

    def test_get_playlist_no_mutation(self):
        service, _, _, _, _ = _build()
        a = service.create_playlist("A")
        calls = []
        service.subscribe_changed(lambda: calls.append(1))
        service.get_playlist(a.playlist_id)
        service.contains_playlist("ghost")
        assert calls == []
        assert service.navigation == PlaylistNavigationState()


class TestArchitecture:
    def test_coordinator_imports_no_qt_no_sqlite(self):
        import michi.application.playlist_navigation_coordinator as mod

        with open(mod.__file__) as fh:
            src = fh.read()
        assert "PySide6" not in src
        assert "sqlite3" not in src

    def test_navigation_service_has_no_playlist_dependency(self):
        import michi.application.navigation_service as mod

        with open(mod.__file__) as fh:
            src = fh.read()
        assert "PlaylistService" not in src

    def test_playlist_service_has_no_navigation_dependency(self):
        import michi.application.playlist_service as mod

        with open(mod.__file__) as fh:
            src = fh.read()
        assert "NavigationService" not in src
