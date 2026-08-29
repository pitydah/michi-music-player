"""M6-EXT-R4 freeze gate — playlist runtime resolution by stable TrackId +
truthful persistence (goldens §7 and §19)."""

from pathlib import Path

import pytest

from michi.application.library_service import LibraryService
from michi.application.library_track_resolver import LibraryTrackResolver
from michi.application.playback_session_service import PlaybackSessionService
from michi.application.playlist_playback_coordinator import (
    PlaylistPlaybackCoordinator,
)
from michi.application.playlist_service import PlaylistService
from michi.application.queue_service import QueueService
from michi.domain.library import TrackRef
from michi.domain.library_catalog import MediaAvailability
from michi.domain.playlist import (
    Playlist,
    PlaylistAppearance,
    PlaylistPersistenceError,
    PlaylistTrackReference,
)


class _StubScanner:
    def validate_file(self, path: Path) -> None:
        return None

    def scan(self, root: Path):
        return []

    def fingerprint(self, path: Path):
        return (0, 0)


class _StubPrefs:
    def load(self):
        from michi.domain.library import LibraryPrefs

        return LibraryPrefs()

    def save(self, prefs):
        del prefs


class _FailingPlaylistsPort:
    """Truthful failure injection: save always raises."""

    def __init__(self) -> None:
        self.loaded: tuple = ()

    def load(self):
        return self.loaded

    def save(self, playlists) -> None:
        raise PlaylistPersistenceError("injected playlist write failure")

    def load_navigation(self):
        from michi.domain.playlist import PlaylistNavigationState

        return PlaylistNavigationState()

    def save_navigation(self, state) -> None:
        del state


def _track(path: str, track_id: str) -> TrackRef:
    return TrackRef(
        Path(path),
        title=Path(path).stem,
        track_id=track_id,
        media_file_id=f"media-{track_id}",
        library_source_id="s1",
        availability=MediaAvailability.AVAILABLE,
    )


def _harness(tracks):
    from michi.application.playback_service import PlaybackService

    library = LibraryService(_StubScanner(), library_prefs=_StubPrefs())
    library._state.tracks = list(tracks)
    library._rebuild_derived_library_state()
    resolver = LibraryTrackResolver(library)
    playlists = PlaylistService()
    playback = PlaybackService(_FakeBackend())
    session = PlaybackSessionService(playback, QueueService())
    coordinator = PlaylistPlaybackCoordinator(
        playlists, session, QueueService(), resolver
    )
    return library, playlists, coordinator, resolver


class TestPlaylistRuntimeResolution:
    def test_golden_play_after_move_uses_new_path_same_id(self) -> None:
        """Create → add to playlist → move file → play → backend receives
        NEW path; library_track_id unchanged."""
        t1 = _track("/Music/A/song.flac", "T1")
        library, playlists, coordinator, resolver = _harness([t1])
        playlist = playlists.create_playlist_with_references(
            "Mix",
            [PlaylistTrackReference(track_id="T1", fallback_path="/Music/A/song.flac")],
        )

        # The file moves; the TrackRef path projection updates.
        library._state.tracks = [_track("/Music/B/song.flac", "T1")]
        library._rebuild_derived_library_state()

        coordinator.play_playlist(playlist.playlist_id)
        pending = coordinator._session._pending
        assert pending is not None
        assert pending.file_path == Path("/Music/B/song.flac")  # NEW path
        assert pending.library_track_id == "T1"  # identity unchanged
        # Playlist membership still holds the stable id.
        assert playlists.get_playlist(playlist.playlist_id).track_ids == ("T1",)

    def test_unresolved_legacy_falls_back_to_path(self) -> None:
        library, playlists, coordinator, resolver = _harness([])
        playlist = playlists.create_playlist_with_references(
            "Legacy", [PlaylistTrackReference(track_id="", fallback_path="/old/x.flac")]
        )
        coordinator.play_playlist(playlist.playlist_id)
        pending = coordinator._session._pending
        assert pending.file_path == Path("/old/x.flac")
        assert pending.library_track_id is None

    def test_missing_track_keeps_membership(self) -> None:
        t1 = _track("/Music/A/song.flac", "T1")
        library, playlists, coordinator, resolver = _harness([t1])
        playlist = playlists.create_playlist_with_references(
            "Mix",
            [PlaylistTrackReference(track_id="T1", fallback_path="/Music/A/song.flac")],
        )
        # Track becomes MISSING: unplayable → skipped at play time, but the
        # playlist membership is never removed.
        missing = TrackRef(
            Path("/Music/A/song.flac"),
            title="song",
            track_id="T1",
            availability=MediaAvailability.MISSING,
        )
        library._state.tracks = [missing]
        library._rebuild_derived_library_state()
        coordinator.play_playlist(playlist.playlist_id)
        assert coordinator._session._pending is None  # nothing playable
        assert playlists.get_playlist(playlist.playlist_id).track_ids == ("T1",)

    def test_queue_playlist_carries_identity(self) -> None:
        t1 = _track("/a.flac", "T1")
        library, playlists, coordinator, resolver = _harness([t1])
        playlist = playlists.create_playlist_with_references(
            "Mix", [PlaylistTrackReference(track_id="T1", fallback_path="/a.flac")]
        )
        queue = QueueService()
        coordinator._queue = queue
        coordinator.queue_playlist(playlist.playlist_id)
        assert queue.state.tracks[0].library_track_id == "T1"


class TestPlaylistTruthfulPersistence:
    def test_create_failure_never_publishes(self) -> None:
        port = _FailingPlaylistsPort()
        service = PlaylistService(playlists_port=port)
        with pytest.raises(PlaylistPersistenceError):
            service.create_playlist("Mix")
        assert service.playlists == ()

    def test_mutation_failure_rolls_back(self) -> None:
        class _OkThenFail:
            """First save succeeds (create), then failures."""

            def __init__(self) -> None:
                self.saved = 0

            def load(self):
                return ()

            def save(self, playlists) -> None:
                self.saved += 1
                if self.saved > 1:
                    raise PlaylistPersistenceError("injected failure")

            def load_navigation(self):
                from michi.domain.playlist import PlaylistNavigationState

                return PlaylistNavigationState()

            def save_navigation(self, state) -> None:
                del state

        service = PlaylistService(playlists_port=_OkThenFail())
        playlist = service.create_playlist("Mix")
        with pytest.raises(PlaylistPersistenceError):
            service.rename_playlist(playlist.playlist_id, "Renamed")
        # In-memory state rolled back to the last persisted snapshot.
        assert service.playlists[0].name == "Mix"


class _FakeBackend:
    """Minimal AudioPort fake (play request only, no acceptance)."""

    def load(self, file_path): ...

    def play(self): ...

    def pause(self): ...

    def resume(self): ...

    def stop(self): ...

    def set_volume(self, value): ...

    def set_muted(self, muted): ...

    def seek(self, position_ms): ...

    def position(self):
        return 0

    def duration(self):
        return 0

    def subscribe_end_of_media(self, cb): ...

    def unsubscribe_end_of_media(self, cb): ...

    def subscribe_position_changed(self, cb): ...

    def unsubscribe_position_changed(self, cb): ...

    def subscribe_duration_changed(self, cb): ...

    def unsubscribe_duration_changed(self, cb): ...

    def subscribe_media_accepted(self, cb): ...

    def unsubscribe_media_accepted(self, cb): ...

    def subscribe_media_rejected(self, cb): ...

    def unsubscribe_media_rejected(self, cb): ...

    def subscribe_playback_state_changed(self, cb): ...

    def unsubscribe_playback_state_changed(self, cb): ...


class TestPlaylistMembershipIdentityMapping:
    """P1-04 golden: membership index → playback entry BY IDENTITY."""

    def _harness_with_unavailable(self, library, playlists, coordinator, resolver):
        """[A available, B missing, C available] playlist."""
        t1 = _track("/a.flac", "T1")
        t3 = _track("/c.flac", "T3")
        missing = TrackRef(
            Path("/b.flac"),
            title="b",
            track_id="T2",
            availability=MediaAvailability.MISSING,
        )
        library._state.tracks = [t1, missing, t3]
        library._rebuild_derived_library_state()
        playlist = playlists.create_playlist_with_references(
            "Mix",
            [
                PlaylistTrackReference(track_id="T1", fallback_path="/a.flac"),
                PlaylistTrackReference(track_id="T2", fallback_path="/b.flac"),
                PlaylistTrackReference(track_id="T3", fallback_path="/c.flac"),
            ],
        )
        return playlist

    def test_click_c_after_filtered_b_reproduces_c(self) -> None:
        """[A ✓, B ✗, C ✓] — click membership index 2 → backend C, never A."""
        t1 = _track("/a.flac", "T1")
        library, playlists, coordinator, resolver = _harness([t1])
        playlist = self._harness_with_unavailable(
            library, playlists, coordinator, resolver
        )

        coordinator.play_playlist_track(playlist.playlist_id, 2)
        pending = coordinator._session._pending
        assert pending is not None
        assert pending.file_path == Path("/c.flac")
        assert pending.library_track_id == "T3"

    def test_click_unavailable_member_plays_nothing(self) -> None:
        """Click B (unavailable): explicit no-play — NOT A, NOT C."""
        t1 = _track("/a.flac", "T1")
        library, playlists, coordinator, resolver = _harness([t1])
        playlist = self._harness_with_unavailable(
            library, playlists, coordinator, resolver
        )

        coordinator.play_playlist_track(playlist.playlist_id, 1)
        assert coordinator._session._pending is None  # nothing started

    def test_first_unavailable_click_last_member(self) -> None:
        """[A ✗, B ✓, C ✓] — click index 2 → C (not shifted to B)."""
        t2 = _track("/b.flac", "T2")
        library, playlists, coordinator, resolver = _harness([t2])
        missing = TrackRef(
            Path("/a.flac"),
            title="a",
            track_id="T1",
            availability=MediaAvailability.MISSING,
        )
        library._state.tracks = [missing, t2, _track("/c.flac", "T3")]
        library._rebuild_derived_library_state()
        playlist = playlists.create_playlist_with_references(
            "Mix",
            [
                PlaylistTrackReference(track_id="T1", fallback_path="/a.flac"),
                PlaylistTrackReference(track_id="T2", fallback_path="/b.flac"),
                PlaylistTrackReference(track_id="T3", fallback_path="/c.flac"),
            ],
        )
        coordinator.play_playlist_track(playlist.playlist_id, 2)
        assert coordinator._session._pending.library_track_id == "T3"

    def test_legacy_path_only_member_maps_by_path(self) -> None:
        library, playlists, coordinator, resolver = _harness([])
        playlist = playlists.create_playlist_with_references(
            "Legacy",
            [
                PlaylistTrackReference(track_id="", fallback_path="/x.flac"),
                PlaylistTrackReference(track_id="", fallback_path="/y.flac"),
            ],
        )
        coordinator.play_playlist_track(playlist.playlist_id, 1)
        assert coordinator._session._pending.file_path == Path("/y.flac")

    def test_moved_track_id_maps_by_identity_not_path(self) -> None:
        t1 = _track("/old/A.flac", "T1")
        library, playlists, coordinator, resolver = _harness([t1])
        playlist = playlists.create_playlist_with_references(
            "Mix", [PlaylistTrackReference(track_id="T1", fallback_path="/old/A.flac")]
        )
        # Move: resolved current path is NEW; identity T1 maps the click.
        library._state.tracks = [_track("/new/B.flac", "T1")]
        library._rebuild_derived_library_state()
        coordinator.play_playlist_track(playlist.playlist_id, 0)
        assert coordinator._session._pending.file_path == Path("/new/B.flac")
        assert coordinator._session._pending.library_track_id == "T1"


class TestPlaylistAssetDurableOrdering:
    """P1-06: irreversible asset destruction happens ONLY after the durable
    authority commit succeeded."""

    def _failing_port(self):
        class _Failing:
            def load(self):
                return ()

            def load_navigation(self):
                from michi.domain.playlist import PlaylistNavigationState

                return PlaylistNavigationState()

            def save(self, playlists):
                raise PlaylistPersistenceError("injected DB failure")

            def save_navigation(self, state):
                del state

        return _Failing()

    class _AssetStore:
        def __init__(self):
            self.deleted_cover = []
            self.deleted_hero = []
            self.stored = []

        def store_cover(self, playlist_id, source):
            self.stored.append(("cover", playlist_id))
            return f"/assets/{playlist_id}.jpg"

        def store_hero(self, playlist_id, source):
            self.stored.append(("hero", playlist_id))
            return f"/assets/{playlist_id}_hero.jpg"

        def delete_cover(self, playlist_id):
            self.deleted_cover.append(playlist_id)

        def delete_hero(self, playlist_id):
            self.deleted_hero.append(playlist_id)

    def test_delete_failure_keeps_assets(self) -> None:
        store = self._AssetStore()
        service = PlaylistService(
            playlists_port=self._failing_port(),
            artwork_store=store,  # type: ignore[arg-type]
        )
        # Simulate an existing playlist with managed assets.
        service._playlists = [
            Playlist(
                playlist_id="p1",
                name="Mix",
                custom_cover_path="/assets/p1.jpg",
            )
        ]
        service._persisted = tuple(service._playlists)
        with pytest.raises(PlaylistPersistenceError):
            service.delete_playlist("p1")
        # Assets were NEVER deleted (no commit happened).
        assert store.deleted_cover == []
        assert store.deleted_hero == []
        # Logical state rolled back: the playlist still exists.
        assert service.get_playlist("p1") is not None

    def test_hero_solid_failure_keeps_asset(self) -> None:
        store = self._AssetStore()
        service = PlaylistService(
            playlists_port=self._failing_port(),
            artwork_store=store,  # type: ignore[arg-type]
        )
        from michi.domain.playlist import PlaylistHeroMode

        service._playlists = [
            Playlist(
                playlist_id="p1",
                name="Mix",
                appearance=PlaylistAppearance(
                    hero_mode=PlaylistHeroMode.IMAGE,
                    hero_image_path="/assets/p1_hero.jpg",
                ),
            )
        ]
        service._persisted = tuple(service._playlists)
        with pytest.raises(PlaylistPersistenceError):
            service.set_hero_solid("p1", "#112233")
        # The old hero asset survived the failed commit.
        assert store.deleted_hero == []
        assert (
            service.get_playlist("p1").appearance.hero_image_path
            == "/assets/p1_hero.jpg"
        )

    def test_remove_cover_failure_keeps_asset(self) -> None:
        store = self._AssetStore()
        service = PlaylistService(
            playlists_port=self._failing_port(),
            artwork_store=store,  # type: ignore[arg-type]
        )
        service._playlists = [
            Playlist(playlist_id="p1", name="Mix", custom_cover_path="/assets/p1.jpg")
        ]
        service._persisted = tuple(service._playlists)
        with pytest.raises(PlaylistPersistenceError):
            service.remove_custom_cover("p1")
        assert store.deleted_cover == []
        assert service.get_playlist("p1").custom_cover_path == "/assets/p1.jpg"

    def test_hero_auto_failure_keeps_asset(self) -> None:
        store = self._AssetStore()
        service = PlaylistService(
            playlists_port=self._failing_port(),
            artwork_store=store,  # type: ignore[arg-type]
        )
        from michi.domain.playlist import PlaylistHeroMode

        service._playlists = [
            Playlist(
                playlist_id="p1",
                name="Mix",
                appearance=PlaylistAppearance(
                    hero_mode=PlaylistHeroMode.IMAGE,
                    hero_image_path="/assets/p1_hero.jpg",
                ),
            )
        ]
        service._persisted = tuple(service._playlists)
        with pytest.raises(PlaylistPersistenceError):
            service.set_hero_auto("p1")
        assert store.deleted_hero == []

    def test_success_deletes_asset_after_commit(self) -> None:
        class _OkPort:
            def __init__(self):
                self.saved = 0

            def load(self):
                return ()

            def load_navigation(self):
                from michi.domain.playlist import PlaylistNavigationState

                return PlaylistNavigationState()

            def save(self, playlists):
                self.saved += 1

            def save_navigation(self, state):
                del state

        store = self._AssetStore()
        service = PlaylistService(playlists_port=_OkPort(), artwork_store=store)  # type: ignore[arg-type]
        from michi.domain.playlist import PlaylistHeroMode

        service._playlists = [
            Playlist(
                playlist_id="p1",
                name="Mix",
                appearance=PlaylistAppearance(
                    hero_mode=PlaylistHeroMode.IMAGE,
                    hero_image_path="/assets/p1_hero.jpg",
                ),
            )
        ]
        service._persisted = tuple(service._playlists)
        assert service.set_hero_solid("p1", "#112233") is True
        # Commit succeeded → the superseded hero asset is cleaned up.
        assert store.deleted_hero == ["p1"]
        assert service.get_playlist("p1").appearance.hero_image_path == ""


class TestReplacementStagingProtocol:
    """CORRECTIVE SEAL §9 — byte level: a DB failure after staging must
    preserve the previously committed image byte-for-byte."""

    def _store_env(self, tmp_path):
        from michi.infrastructure.playlist_artwork_store import (
            FilesystemPlaylistArtworkStore,
        )

        store = FilesystemPlaylistArtworkStore(tmp_path / "covers")
        return store

    class _FailingPort:
        def __init__(self, *, fail_after=0):
            self.saved = 0
            self.fail_after = fail_after

        def load(self):
            return ()

        def load_navigation(self):
            from michi.domain.playlist import PlaylistNavigationState

            return PlaylistNavigationState()

        def save(self, playlists):
            self.saved += 1
            if self.saved > self.fail_after:
                raise PlaylistPersistenceError("injected DB failure")

        def save_navigation(self, state):
            del state

    def test_cover_db_failure_preserves_old_bytes(self, tmp_path) -> None:

        store = self._store_env(tmp_path)
        service = PlaylistService(
            playlists_port=self._FailingPort(fail_after=1), artwork_store=store
        )  # type: ignore[arg-type]
        service._playlists = [Playlist(playlist_id="p1", name="Mix")]
        service._persisted = tuple(service._playlists)
        # Commit an initial cover (via the successful first save).
        old_src = tmp_path / "old.jpg"
        old_src.write_bytes(b"OLD_BYTES")
        assert service.set_custom_cover("p1", old_src) is not None
        committed_path = service.get_playlist("p1").custom_cover_path
        assert Path(committed_path).read_bytes() == b"OLD_BYTES"

        # Replace with NEW bytes; the authoritative persist FAILS.
        new_src = tmp_path / "new.jpg"
        new_src.write_bytes(b"NEW_BYTES")
        with pytest.raises(PlaylistPersistenceError):
            service.set_custom_cover("p1", new_src)

        # Old committed image byte-for-byte intact; metadata rolled back.
        assert Path(committed_path).read_bytes() == b"OLD_BYTES"
        assert service.get_playlist("p1").custom_cover_path == committed_path
        # No NEW bytes anywhere in the committed asset.
        assert b"NEW_BYTES" not in Path(committed_path).read_bytes()

    def test_hero_db_failure_preserves_old_bytes(self, tmp_path) -> None:
        from michi.domain.playlist import PlaylistHeroMode

        store = self._store_env(tmp_path)
        service = PlaylistService(
            playlists_port=self._FailingPort(fail_after=1), artwork_store=store
        )  # type: ignore[arg-type]
        service._playlists = [
            Playlist(
                playlist_id="p1",
                name="Mix",
                appearance=PlaylistAppearance(hero_mode=PlaylistHeroMode.AUTO),
            )
        ]
        service._persisted = tuple(service._playlists)
        old_src = tmp_path / "old_hero.png"
        old_src.write_bytes(b"OLD_HERO_BYTES")
        assert service.set_custom_hero_image("p1", old_src) is not None
        committed = service.get_playlist("p1").appearance.hero_image_path
        assert Path(committed).read_bytes() == b"OLD_HERO_BYTES"

        new_src = tmp_path / "new_hero.png"
        new_src.write_bytes(b"NEW_HERO_BYTES")
        with pytest.raises(PlaylistPersistenceError):
            service.set_custom_hero_image("p1", new_src)
        assert Path(committed).read_bytes() == b"OLD_HERO_BYTES"
        assert service.get_playlist("p1").appearance.hero_image_path == committed

    def test_extension_change_failure_preserves_old(self, tmp_path) -> None:

        store = self._store_env(tmp_path)
        service = PlaylistService(
            playlists_port=self._FailingPort(fail_after=1), artwork_store=store
        )  # type: ignore[arg-type]
        service._playlists = [Playlist(playlist_id="p1", name="Mix")]
        service._persisted = tuple(service._playlists)
        old_src = tmp_path / "old.jpg"
        old_src.write_bytes(b"OLD_BYTES")
        assert service.set_custom_cover("p1", old_src) is not None
        old_committed = Path(service.get_playlist("p1").custom_cover_path)

        # Extension change .jpg → .png fails at persist: the .jpg survives.
        new_src = tmp_path / "new.png"
        new_src.write_bytes(b"NEW_BYTES")
        with pytest.raises(PlaylistPersistenceError):
            service.set_custom_cover("p1", new_src)
        assert old_committed.read_bytes() == b"OLD_BYTES"
        assert service.get_playlist("p1").custom_cover_path == str(old_committed)

    def test_success_promotes_and_retires_old_extension(self, tmp_path) -> None:
        store = self._store_env(tmp_path)
        service = PlaylistService(
            playlists_port=self._FailingPort(fail_after=999), artwork_store=store
        )  # type: ignore[arg-type]
        service._playlists = [Playlist(playlist_id="p1", name="Mix")]
        service._persisted = tuple(service._playlists)
        old_src = tmp_path / "old.jpg"
        old_src.write_bytes(b"OLD_BYTES")
        assert service.set_custom_cover("p1", old_src) is not None
        old_path = Path(service.get_playlist("p1").custom_cover_path)

        new_src = tmp_path / "new.png"
        new_src.write_bytes(b"NEW_BYTES")
        assert service.set_custom_cover("p1", new_src) is not None
        final_path = Path(service.get_playlist("p1").custom_cover_path)
        assert final_path.read_bytes() == b"NEW_BYTES"
        # Superseded .jpg variant retired post-commit.
        assert not old_path.exists()


class TestDeletePlaylistAtomicTransaction:
    def test_nav_failure_rolls_back_collection(self, tmp_path) -> None:
        """§10: collection write succeeds, nav write fails → BOTH roll back
        durably; a restart sees the old coherent state."""

        class _NavFailingPort:
            def __init__(self):
                self.saved_collections = []

            def load(self):
                return tuple(
                    self.saved_collections[-1] if self.saved_collections else ()
                )

            def load_navigation(self):
                from michi.domain.playlist import PlaylistNavigationState

                return PlaylistNavigationState()

            def save(self, playlists):
                self.saved_collections.append(tuple(playlists))

            def save_navigation(self, state):
                raise PlaylistPersistenceError("injected nav failure")

            def save_playlists_with_navigation(self, playlists, navigation):
                # ONE atomic logical operation that FAILS: both must roll
                # back (the service never half-commits).
                raise PlaylistPersistenceError("injected atomic failure")

        from michi.application.playlist_service import PlaylistService

        port = _NavFailingPort()
        service = PlaylistService(playlists_port=port)  # type: ignore[arg-type]
        keep = service.create_playlist("Keep")
        target = service.create_playlist("DeleteMe")
        with pytest.raises(PlaylistPersistenceError):
            service.delete_playlist(target.playlist_id)
        # In-memory rolled back to the pre-delete coherent state.
        assert service.get_playlist(target.playlist_id) is not None
        assert service.get_playlist(keep.playlist_id) is not None
        # Restart (new service over the SAME port) sees the coherent state.
        restarted = PlaylistService(playlists_port=port)  # type: ignore[arg-type]
        assert restarted.get_playlist(target.playlist_id) is not None
        assert restarted.get_playlist(keep.playlist_id) is not None
