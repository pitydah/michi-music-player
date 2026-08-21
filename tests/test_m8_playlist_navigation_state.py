"""M8-R1: playlist navigation metadata gates — pinned + recent (MRU).

Contracts:
- Pinned: pin appends deterministically; duplicate pin no-op; unknown pin
  no-op; rename preserves; delete prunes; restart restores exact order.
- Recent: MRU (most recent first), no duplicates, bounded
  MAX_RECENT_PLAYLISTS, unknown ids never enter, rename preserves identity,
  delete removes, restart preserves order.
- Notifications: exactly once per successful logical mutation; none for
  no-ops.
"""

from michi.application.playlist_service import PlaylistService
from michi.application.queue_service import QueueService
from michi.domain.playlist import (
    MAX_RECENT_PLAYLISTS,
    PlaylistNavigationState,
)
from tests.conftest import FakeAudioPort
from tests.test_playlists import FakePlaylistsPort


def _make(queue_audio=None):
    from michi.application.playback_service import PlaybackService

    audio = queue_audio or FakeAudioPort()
    queue = QueueService(PlaybackService(audio))
    return PlaylistService(queue, FakePlaylistsPort()), queue


def _seeded(n=3, prefix="P"):
    service, _ = _make()
    return service, [service.create_playlist(f"{prefix}{i}") for i in range(n)]


class TestPinned:
    def test_pin_appends_deterministically(self):
        service, [a, b] = _seeded(2)
        service.pin_playlist(a.playlist_id)
        service.pin_playlist(b.playlist_id)
        assert service.navigation.pinned_ids == (a.playlist_id, b.playlist_id)

    def test_pin_duplicate_is_noop(self):
        service, [a] = _seeded(1)
        service.pin_playlist(a.playlist_id)
        service.pin_playlist(a.playlist_id)
        assert service.navigation.pinned_ids == (a.playlist_id,)

    def test_pin_unknown_id_is_noop(self):
        service, _ = _seeded(1)
        calls = []
        service.subscribe_changed(lambda: calls.append(1))
        service.pin_playlist("ghost-id")
        assert service.navigation.pinned_ids == ()
        assert calls == []

    def test_unpin(self):
        service, [a, b] = _seeded(2)
        service.pin_playlist(a.playlist_id)
        service.pin_playlist(b.playlist_id)
        service.unpin_playlist(a.playlist_id)
        assert service.navigation.pinned_ids == (b.playlist_id,)

    def test_unpin_missing_id_is_noop(self):
        service, [a] = _seeded(1)
        calls = []
        service.subscribe_changed(lambda: calls.append(1))
        service.unpin_playlist("ghost-id")
        service.unpin_playlist(a.playlist_id)  # not pinned → no-op
        assert service.navigation.pinned_ids == ()
        assert calls == []

    def test_rename_preserves_pinned(self):
        service, [a] = _seeded(1)
        service.pin_playlist(a.playlist_id)
        service.rename_playlist(a.playlist_id, "Renamed")
        assert service.navigation.pinned_ids == (a.playlist_id,)

    def test_delete_prunes_pinned(self):
        service, [a, b] = _seeded(2)
        service.pin_playlist(a.playlist_id)
        service.pin_playlist(b.playlist_id)
        service.delete_playlist(a.playlist_id)
        assert service.navigation.pinned_ids == (b.playlist_id,)

    def test_restart_restores_pinned_order(self):
        port = FakePlaylistsPort()
        from michi.application.playback_service import PlaybackService

        audio = FakeAudioPort()
        queue = QueueService(PlaybackService(audio))
        service = PlaylistService(queue, port)
        a = service.create_playlist("A")
        b = service.create_playlist("B")
        service.pin_playlist(a.playlist_id)
        service.pin_playlist(b.playlist_id)
        service2 = PlaylistService(QueueService(PlaybackService(audio)), port)
        assert service2.navigation.pinned_ids == (a.playlist_id, b.playlist_id)

    def test_pinned_persisted_through_real_repo(self, tmp_path):
        from michi.infrastructure.playlists import SqlitePlaylistsRepository

        repo = SqlitePlaylistsRepository(tmp_path / "m.db")
        from michi.application.playback_service import PlaybackService

        audio = FakeAudioPort()
        service = PlaylistService(QueueService(PlaybackService(audio)), repo)
        a = service.create_playlist("A")
        service.pin_playlist(a.playlist_id)
        service2 = PlaylistService(QueueService(PlaybackService(audio)), repo)
        assert service2.navigation.pinned_ids == (a.playlist_id,)


class TestRecent:
    def test_mru_semantics(self):
        service, [a, b] = _seeded(2)
        service.mark_recent(a.playlist_id)
        assert service.navigation.recent_ids == (a.playlist_id,)
        service.mark_recent(b.playlist_id)
        assert service.navigation.recent_ids == (b.playlist_id, a.playlist_id)
        service.mark_recent(a.playlist_id)
        assert service.navigation.recent_ids == (a.playlist_id, b.playlist_id)

    def test_recent_no_duplicates(self):
        service, [a] = _seeded(1)
        service.mark_recent(a.playlist_id)
        service.mark_recent(a.playlist_id)
        service.mark_recent(a.playlist_id)
        assert service.navigation.recent_ids == (a.playlist_id,)

    def test_recent_bounded(self):
        service, created = _seeded(MAX_RECENT_PLAYLISTS + 3)
        for p in created:
            service.mark_recent(p.playlist_id)
        assert len(service.navigation.recent_ids) == MAX_RECENT_PLAYLISTS
        # most recent MAX first; oldest fall off
        assert service.navigation.recent_ids[0] == created[-1].playlist_id
        assert created[0].playlist_id not in service.navigation.recent_ids

    def test_unknown_id_never_enters_recent(self):
        service, _ = _seeded(1)
        calls = []
        service.subscribe_changed(lambda: calls.append(1))
        service.mark_recent("ghost-id")
        assert service.navigation.recent_ids == ()
        assert calls == []

    def test_rename_preserves_recent_identity(self):
        service, [a] = _seeded(1)
        service.mark_recent(a.playlist_id)
        service.rename_playlist(a.playlist_id, "Renamed")
        assert service.navigation.recent_ids == (a.playlist_id,)

    def test_delete_removes_from_recent(self):
        service, [a, b] = _seeded(2)
        service.mark_recent(a.playlist_id)
        service.mark_recent(b.playlist_id)
        service.delete_playlist(a.playlist_id)
        assert service.navigation.recent_ids == (b.playlist_id,)

    def test_restart_preserves_recent_order(self):
        port = FakePlaylistsPort()
        from michi.application.playback_service import PlaybackService

        audio = FakeAudioPort()
        service = PlaylistService(QueueService(PlaybackService(audio)), port)
        a = service.create_playlist("A")
        b = service.create_playlist("B")
        service.mark_recent(b.playlist_id)
        service.mark_recent(a.playlist_id)
        service2 = PlaylistService(QueueService(PlaybackService(audio)), port)
        assert service2.navigation.recent_ids == (a.playlist_id, b.playlist_id)


class TestNavigationStatePersistence:
    def test_navigation_roundtrip_through_real_repo(self, tmp_path):
        from michi.infrastructure.playlists import SqlitePlaylistsRepository

        repo = SqlitePlaylistsRepository(tmp_path / "m.db")
        state = PlaylistNavigationState(
            pinned_ids=("p1", "p2"), recent_ids=("r1", "r2", "r3")
        )
        repo.save_navigation(state)
        loaded = repo.load_navigation()
        assert loaded == state

    def test_navigation_absent_degrades_empty(self, tmp_path):
        from michi.infrastructure.playlists import SqlitePlaylistsRepository

        repo = SqlitePlaylistsRepository(tmp_path / "m.db")
        assert repo.load_navigation() == PlaylistNavigationState()

    def test_navigation_malformed_degrades_empty(self, tmp_path):
        import sqlite3

        from michi.infrastructure.playlists import SqlitePlaylistsRepository

        db = tmp_path / "m.db"
        conn = sqlite3.connect(str(db))
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS library_prefs ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.execute(
                "INSERT INTO library_prefs(key, value) "
                "VALUES('playlist_navigation', ?)",
                ('{"pinned_ids": "not-a-list", "recent_ids": [1, "ok", ""]}',),
            )
            conn.commit()
        finally:
            conn.close()
        state = SqlitePlaylistsRepository(db).load_navigation()
        assert state == PlaylistNavigationState(pinned_ids=(), recent_ids=("ok",))

    def test_delete_notifies_once_and_prunes(self):
        service, [a] = _seeded(1)
        service.pin_playlist(a.playlist_id)
        service.mark_recent(a.playlist_id)
        calls = []
        service.subscribe_changed(lambda: calls.append(1))
        deleted = []
        service.set_on_playlist_deleted(lambda pid: deleted.append(pid))
        service.delete_playlist(a.playlist_id)
        assert calls == [1]
        assert deleted == [a.playlist_id]
        assert service.navigation == PlaylistNavigationState()
