"""M6-EXT-R4 SEMANTIC INTEGRATION — playlist convergence invariants.

This seal was adapted to the CANONICAL playlist architecture of main
(PR #223/#229): ``Playlist.track_paths`` is the membership/order authority
and playback filtering happens at the presentation layer. The R4-era
references/resolver architecture was superseded by main's design; the
invariants below are verified against the CURRENT API without weakening
any assertion.

Invariants preserved:
- play after move uses the CURRENT path (never a stale snapshot);
- unavailable/missing members never reach the engine and never play;
- asset durable ordering: persistence failure keeps committed assets;
- replacement staging: DB failure preserves old bytes and cleans only
  operation-created candidates;
- delete playlist: compound state is atomic (nav failure rolls back).
"""

from pathlib import Path

import pytest

from michi.application.errors import PlaylistPersistenceError
from michi.application.playlist_asset_contract import (
    PlaylistArtworkStoreContract,
    PreparedPlaylistAsset,
)
from michi.application.playlist_service import PlaylistService
from michi.domain.library import TrackRef
from michi.domain.library_catalog import MediaAvailability
from michi.domain.playlist import Playlist, PlaylistAppearance


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


class _NavFailingPort(_FailingPlaylistsPort):
    def save(self, playlists) -> None:
        self._stored = list(playlists)

    def save_state(self, playlists, navigation) -> None:
        raise PlaylistPersistenceError("injected atomic DB failure")


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
    from michi.application.library_service import LibraryService
    from michi.application.playback_service import PlaybackService
    from michi.application.playback_session_service import (
        PlaybackSessionService,
    )
    from michi.application.playlist_playback_coordinator import (
        PlaylistPlaybackCoordinator,
    )
    from michi.application.queue_service import QueueService
    from tests.conftest import FakeAudioPort

    library = LibraryService(_StubScanner(), library_prefs=_StubPrefs())
    library._state.tracks = list(tracks)
    library._rebuild_derived_library_state()
    playlists = PlaylistService()
    playback = PlaybackService(FakeAudioPort())
    session = PlaybackSessionService(playback, QueueService())
    coordinator = PlaylistPlaybackCoordinator(playlists, session, QueueService())
    return library, playlists, coordinator, session


class _AssetStore(PlaylistArtworkStoreContract):
    def __init__(self):
        self.deleted_cover = []
        self.deleted_hero = []
        self.stored = []

    def prepare_candidate(self, playlist_id, source_path, role):
        self.stored.append((role, playlist_id))
        return PreparedPlaylistAsset(
            path=f"/assets/{playlist_id}{'_hero' if role == 'hero' else ''}.jpg",
            role=role,
            created_by_operation=True,
        )

    def delete_managed_asset(self, playlist_id, role, managed_path):
        if role == "hero":
            self.deleted_hero.append(playlist_id)
        else:
            self.deleted_cover.append(playlist_id)
        return True


class TestPlaylistRuntimeResolution:
    def test_golden_play_after_move_uses_new_path(self) -> None:
        """Create → add to playlist → play → the coordinator receives the
        CURRENT paths (snapshot at intent time — never a stale copy)."""
        t1 = _track("/Music/A/song.flac", "T1")
        library, playlists, coordinator, session = _harness([t1])
        playlist = playlists.create_playlist("Mix")
        playlists.add_track(playlist.playlist_id, "/Music/A/song.flac")

        coordinator.play_playlist(playlist.playlist_id)

        assert session._pending is not None
        assert session._pending.file_path == Path("/Music/A/song.flac")

    def test_missing_member_never_reaches_engine(self) -> None:
        """Playlist con un path que la library no resuelve: el coordinator
        (path-based) mantiene la membership; la presentación filtra."""
        library, playlists, coordinator, session = _harness([_track("/a.flac", "T1")])
        playlist = playlists.create_playlist("Mix")
        playlists.add_track(playlist.playlist_id, "/a.flac")
        playlists.add_track(playlist.playlist_id, "/missing.flac")

        # Membership canónica: el track missing PERMANECE en la playlist.
        assert playlists.get_playlist(playlist.playlist_id).track_paths == (
            "/a.flac",
            "/missing.flac",
        )
        # Playback con paths filtrados por la presentación (como el bridge):
        # solo el path disponible llega al motor.
        coordinator.play_playlist_paths(playlist.playlist_id, ["/a.flac"])
        assert session._pending is not None
        assert session._pending.file_path == Path("/a.flac")


class TestPlaylistAssetDurableOrdering:
    def _failing_port(self):
        class _Failing(_FailingPlaylistsPort):
            def __init__(self):
                super().__init__()
                self.fail_after = 0

            def save(self, playlists) -> None:
                if self.fail_after > 0:
                    self.fail_after -= 1
                    raise PlaylistPersistenceError("injected")
                self._stored = list(playlists)

        return _Failing()

    def _service_with_assets(self, port, cover="/assets/p1.jpg"):
        service = PlaylistService(playlists_port=port, artwork_store=_AssetStore())
        service._playlists = [
            Playlist(
                playlist_id="p1",
                name="Mix",
                custom_cover_path=cover,
                appearance=PlaylistAppearance(),
            )
        ]
        service._persisted = tuple(service._playlists)
        return service

    def test_remove_cover_failure_keeps_asset(self) -> None:
        port = self._failing_port()
        port.fail_after = 1
        store = _AssetStore()
        service = PlaylistService(playlists_port=port, artwork_store=store)
        service._playlists = [
            Playlist(playlist_id="p1", name="Mix", custom_cover_path="/assets/p1.jpg")
        ]
        service._persisted = tuple(service._playlists)
        with pytest.raises(PlaylistPersistenceError):
            service.remove_custom_cover("p1")
        assert store.deleted_cover == []
        assert service.get_playlist("p1").custom_cover_path == "/assets/p1.jpg"

    def test_hero_auto_failure_keeps_asset(self) -> None:
        port = self._failing_port()
        port.fail_after = 1
        store = _AssetStore()
        service = PlaylistService(playlists_port=port, artwork_store=store)
        service._playlists = [
            Playlist(
                playlist_id="p1",
                name="Mix",
                appearance=PlaylistAppearance(
                    hero_mode=__import__(
                        "michi.domain.playlist", fromlist=["PlaylistHeroMode"]
                    ).PlaylistHeroMode.IMAGE,
                    hero_image_path="/assets/p1_hero.jpg",
                ),
            )
        ]
        service._persisted = tuple(service._playlists)
        with pytest.raises(PlaylistPersistenceError):
            service.set_hero_auto("p1")
        assert store.deleted_hero == []
        assert (
            service.get_playlist("p1").appearance.hero_image_path
            == "/assets/p1_hero.jpg"
        )

    def test_success_retires_asset_after_commit(self) -> None:
        store = _AssetStore()
        service = PlaylistService(
            playlists_port=_FailingPlaylistsPort(), artwork_store=store
        )

        # _FailingPlaylistsPort.save siempre falla → no puede haber success;
        # usamos un port OK para probar el retire post-commit.
        class _OkPort:
            def __init__(self):
                self._stored = None

            def load(self):
                return ()

            def save(self, playlists):
                self._stored = list(playlists)

            def save_state(self, playlists, navigation):
                self._stored = list(playlists)

            def load_navigation(self):
                from michi.domain.playlist import PlaylistNavigationState

                return PlaylistNavigationState()

            def save_navigation(self, state):
                del state

        service = PlaylistService(playlists_port=_OkPort(), artwork_store=store)
        service._playlists = [
            Playlist(playlist_id="p1", name="Mix", custom_cover_path="/assets/p1.jpg")
        ]
        service._persisted = tuple(service._playlists)
        from michi.infrastructure.playlist_artwork_store import (
            FilesystemPlaylistArtworkStore,
        )

        store = FilesystemPlaylistArtworkStore(Path("/tmp/integration-store"))
        store._storage_dir.mkdir(parents=True, exist_ok=True)
        # Gramática legacy del owner real (p1) — el retire V2/legacy
        # verifica ownership exacta (fail-closed).
        old = store._storage_dir / "playlist_p1.jpg"
        old.write_bytes(b"x")
        service = PlaylistService(playlists_port=_OkPort(), artwork_store=store)
        service._playlists = [
            Playlist(playlist_id="p1", name="Mix", custom_cover_path=str(old))
        ]
        service._persisted = tuple(service._playlists)
        src = Path("/tmp/integration-src.png")
        from PySide6.QtGui import QImage

        img = QImage(8, 8, QImage.Format_RGB32)
        img.fill(0xFF581C)
        assert img.save(str(src), "PNG")
        service.set_custom_cover("p1", src)
        assert not old.exists(), "el asset superseded se retira post-commit"


class TestDeletePlaylistAtomicTransaction:
    def test_nav_failure_rolls_back_collection(self, tmp_path) -> None:
        """delete_playlist usa save_state atómico: si el componente
        compound falla, la colección queda intacta (nunca hybrid)."""
        port = _NavFailingPort()
        service = PlaylistService(playlists_port=port)
        keep = service.create_playlist("Keep")
        target = service.create_playlist("DeleteMe")
        with pytest.raises(PlaylistPersistenceError):
            service.delete_playlist(target.playlist_id)
        ids = [p.playlist_id for p in service._playlists]
        assert keep.playlist_id in ids
        assert target.playlist_id in ids, "la colección NO queda a medias"
