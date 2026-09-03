"""PLAYLISTS POST-MERGE IDENTITY RECOVERY (Iteración 2) — convergence
goldens: persistencia V3 + resolución TrackId-first en bridge/playback/
queue (relocation-safe).

Restores the M6-EXT-R4 invariants that the fcd6710 semantic integration
had emptied (the previous "play after move" golden did NOT move anything,
did NOT check TrackId and did NOT check relocation):

- play after move: catalog relocation T1 /A→/B → PLAY usa el path ACTUAL
  /B y transporta library_track_id == T1 (la playlist conserva T1 con su
  fallback /A — resolver ≠ reescribir el snapshot);
- queue after move: los tracks entran a la Queue con path actual + T1;
- legacy path-only members siguen reproduciendo (fallback por path);
- un miembro no resoluble conserva la membership y NUNCA llega al motor;
- Library → Playlist escribe references reales (track_id + path) en V3;
- el mismo TrackId con path nuevo no duplica;
- dos TrackIds distintos con el mismo path snapshot NO colapsan;
- restart (repo sqlite) preserva T1; el resave V3 preserva T1.
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
        """Legacy coordinator contract (path snapshot): la reproducción
        recibe los paths canónicos en el instante del intento."""
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


# ==========================================================================
# PLAYLISTS POST-MERGE IDENTITY RECOVERY (Iteración 2) — goldens reales de
# relocation a través del seam completo Bridge → Service → Persistence →
# Playback/Queue.
# ==========================================================================


def _identity_harness(tmp_path, tracks):
    """PlaylistsBridge completo: LibraryService (catálogo) + repo sqlite
    real (V3 durable) + PlaybackSession + Queue + coordinator."""
    from michi.application.library_service import LibraryService
    from michi.application.navigation_service import NavigationService
    from michi.application.playback_service import PlaybackService
    from michi.application.playback_session_service import (
        PlaybackSessionService,
    )
    from michi.application.playlist_navigation_coordinator import (
        PlaylistNavigationCoordinator,
    )
    from michi.application.playlist_playback_coordinator import (
        PlaylistPlaybackCoordinator,
    )
    from michi.application.queue_service import QueueService
    from michi.infrastructure.playlists import SqlitePlaylistsRepository
    from michi.presentation.playlists_bridge import PlaylistsBridge
    from tests.conftest import FakeAudioPort

    library = LibraryService(_StubScanner(), library_prefs=_StubPrefs())
    library._state.tracks = list(tracks)
    library._rebuild_derived_library_state()
    repo = SqlitePlaylistsRepository(tmp_path / "michi.db")
    playlists = PlaylistService(playlists_port=repo)
    nav = NavigationService()
    playlists.set_on_playlist_deleted(nav.forget_playlist)
    nav_coord = PlaylistNavigationCoordinator(playlists, nav)
    session = PlaybackSessionService(PlaybackService(FakeAudioPort()), QueueService())
    queue = QueueService()
    coordinator = PlaylistPlaybackCoordinator(playlists, session, queue)
    bridge = PlaylistsBridge(
        playlists,
        playlist_navigation=nav_coord,
        navigation_service=nav,
        library=library,
        playback_coordinator=coordinator,
    )
    return bridge, playlists, session, queue, library


def _relocate(library, track_id: str, new_path: str) -> None:
    """Relocación de catálogo con la notificación real del servicio:
    el mismo TrackRef estable ahora vive en new_path."""
    library._state.tracks = [
        _track(new_path, t.track_id) if t.track_id == track_id else t
        for t in library._state.tracks
    ]
    library._rebuild_derived_library_state()
    library._notify()


class TestIdentityRecoveryPlayback:
    def test_golden_play_after_move_uses_new_path_same_id(self, tmp_path) -> None:
        """El golden REAL: catalog T1 @/A → playlist (T1, fallback /A) →
        relocación T1 @/B → PLAY resuelve /B y transporta T1. El fallback
        persistido puede seguir siendo /A (resolver ≠ reescribir)."""
        bridge, playlists, session, _, library = _identity_harness(
            tmp_path, [_track("/A/song.flac", "T1")]
        )
        playlist = playlists.create_playlist("Mix")
        assert (
            bridge.add_track_to_playlist(playlist.playlist_id, "/A/song.flac")
            == "added"
        )
        assert playlists.get_playlist(playlist.playlist_id).track_ids == ("T1",)

        _relocate(library, "T1", "/B/song.flac")
        bridge.play_playlist(playlist.playlist_id)

        assert session._pending is not None
        assert session._pending.file_path == Path("/B/song.flac"), (
            "play usa la ubicación ACTUAL del TrackId"
        )
        assert session._pending.library_track_id == "T1", (
            "la identidad sobrevive hasta playback"
        )
        persisted = playlists.get_playlist(playlist.playlist_id)
        assert persisted.track_ids == ("T1",)
        assert persisted.track_paths == ("/A/song.flac",), (
            "el snapshot persistido puede quedar en la ubicación vieja"
        )

    def test_golden_queue_after_move_preserves_track_id(self, tmp_path) -> None:
        """QUEUE tras relocación: path actual + library_track_id en cada
        entrada de la Queue (nunca path-only cuando se conoce T1)."""
        bridge, playlists, _, queue, library = _identity_harness(
            tmp_path, [_track("/A/song.flac", "T1")]
        )
        playlist = playlists.create_playlist("Mix")
        bridge.add_track_to_playlist(playlist.playlist_id, "/A/song.flac")

        _relocate(library, "T1", "/B/song.flac")
        bridge.queue_playlist(playlist.playlist_id)

        assert len(queue.state.tracks) == 1
        assert queue.state.tracks[0].file_path == Path("/B/song.flac")
        assert queue.state.tracks[0].library_track_id == "T1"

    def test_legacy_path_only_playlist_still_plays(self, tmp_path) -> None:
        """Miembro legacy (sin TrackId, V2) resuelve por path y reproduce."""
        bridge, playlists, session, _, library = _identity_harness(
            tmp_path, [_track("/legacy.flac", "")]
        )
        playlist = playlists.create_playlist("Mix")
        playlists.add_track(playlist.playlist_id, "/legacy.flac")

        bridge.play_playlist(playlist.playlist_id)

        assert session._pending is not None
        assert session._pending.file_path == Path("/legacy.flac")
        assert session._pending.library_track_id in (None, "")

    def test_unresolved_member_retains_membership_and_never_plays(
        self, tmp_path
    ) -> None:
        """T1 no resoluble (ni id ni fallback en catálogo): la membership
        PERMANECE, nada llega al motor, y la proyección lo marca
        unavailable (nunca borrado silencioso)."""
        bridge, playlists, session, _, library = _identity_harness(
            tmp_path, [_track("/A/song.flac", "T1")]
        )
        playlist = playlists.create_playlist("Mix")
        bridge.add_track_to_playlist(playlist.playlist_id, "/A/song.flac")
        # El catálogo pierde el track: id desaparecido y path ausente.
        library._state.tracks = []
        library._rebuild_derived_library_state()
        library._notify()

        bridge.open_playlist(playlist.playlist_id)
        rows = bridge.property("playlistTrackRows")
        assert len(rows) == 1
        assert rows[0]["available"] is False
        assert rows[0]["trackId"] == "T1"
        assert bridge.property("playlistUnavailableCount") == 1

        bridge.play_playlist(playlist.playlist_id)
        assert session._pending is None, "unavailable nunca llega al motor"
        persisted = playlists.get_playlist(playlist.playlist_id)
        assert persisted.track_ids == ("T1",), "membership conservada"


class TestIdentityRecoveryMembership:
    def test_library_add_to_playlist_writes_track_id_and_path_v3(
        self, tmp_path
    ) -> None:
        """Library → Playlist (slot del picker, path factual) persiste una
        REFERENCIA real: track_id T1 + fallback en el payload V3 durable."""

        from michi.infrastructure.playlists import SqlitePlaylistsRepository

        bridge, playlists, _, _, _ = _identity_harness(
            tmp_path, [_track("/A/song.flac", "T1")]
        )
        playlist = playlists.create_playlist("Mix")
        assert bridge.add_track_to_playlist(playlist.playlist_id, "/A/song.flac")
        # Restart con repo real: el TrackId sobrevive.
        reloaded = PlaylistService(
            playlists_port=SqlitePlaylistsRepository(tmp_path / "michi.db")
        ).get_playlist(playlist.playlist_id)
        assert reloaded is not None
        assert reloaded.track_ids == ("T1",)
        raw = SqlitePlaylistsRepository(tmp_path / "michi.db")._load_raw("playlists")
        entry = raw[0]
        assert entry["version"] == 3
        assert entry["tracks"] == [{"track_id": "T1", "fallback_path": "/A/song.flac"}]

    def test_same_track_id_new_path_does_not_duplicate(self, tmp_path) -> None:
        """El mismo T1 ya en la playlist, re-agregado desde su NUEVA
        ubicación → 'already_present' (dedupe por TrackId), un solo
        miembro."""
        bridge, playlists, _, _, library = _identity_harness(
            tmp_path, [_track("/A/song.flac", "T1")]
        )
        playlist = playlists.create_playlist("Mix")
        bridge.add_track_to_playlist(playlist.playlist_id, "/A/song.flac")

        _relocate(library, "T1", "/B/song.flac")
        result = bridge.add_track_to_playlist(playlist.playlist_id, "/B/song.flac")

        assert result == "already_present"
        persisted = playlists.get_playlist(playlist.playlist_id)
        assert persisted.track_ids == ("T1",)
        assert persisted.track_paths == ("/A/song.flac",)

    def test_batch_add_preserves_order_and_identity(self, tmp_path) -> None:
        bridge, playlists, _, _, _ = _identity_harness(
            tmp_path,
            [
                _track("/a.flac", "T1"),
                _track("/b.flac", "T2"),
                _track("/c.flac", "T3"),
            ],
        )
        playlist = playlists.create_playlist("Mix")
        result = bridge.add_tracks(
            playlist.playlist_id, ["/a.flac", "/b.flac", "/c.flac"]
        )
        assert result["status"] == "updated"
        assert result["addedCount"] == 3
        persisted = playlists.get_playlist(playlist.playlist_id)
        assert persisted.track_ids == ("T1", "T2", "T3")
        assert persisted.track_paths == ("/a.flac", "/b.flac", "/c.flac")

    def test_distinct_track_ids_same_path_do_not_collapse(self, tmp_path) -> None:
        """Dos tracks estables distintos que comparten accidentalmente el
        mismo path snapshot (T1 y T2 con fallback /same.flac) NO colapsan:
        el TrackId decide la identidad; el path nunca es autoridad global.
        (Entrada por references — el catálogo real es path 1:1; este caso
        protege la membership ante datos históricos/snapshots compartidos.)"""
        from michi.domain.playlist import PlaylistTrackReference

        _, playlists, _, _, _ = _identity_harness(
            tmp_path, [_track("/same.flac", "T1"), _track("/same.flac", "T2")]
        )
        playlist = playlists.create_playlist_with_references(
            "Mix",
            [
                PlaylistTrackReference(track_id="T1", fallback_path="/same.flac"),
                PlaylistTrackReference(track_id="T2", fallback_path="/same.flac"),
            ],
        )
        persisted = playlists.get_playlist(playlist.playlist_id)
        assert persisted.track_ids == ("T1", "T2"), (
            "dos ids estables con el mismo snapshot NO colapsan"
        )
        assert len(persisted.references()) == 2
        # Y agregar el segundo después tampoco colapsa.
        second = playlists.create_playlist("Mix2")
        added = playlists.add_track_references(
            second.playlist_id,
            [
                PlaylistTrackReference(track_id="T1", fallback_path="/same.flac"),
                PlaylistTrackReference(track_id="T2", fallback_path="/same.flac"),
            ],
        )
        assert added == 2

    def test_playlist_rows_show_current_path_after_relocation(self, tmp_path) -> None:
        """La proyección del detalle tras relocación muestra la ubicación
        ACTUAL (path /B) con available True y trackId T1 — nunca el
        snapshot viejo."""
        bridge, playlists, _, _, library = _identity_harness(
            tmp_path, [_track("/A/song.flac", "T1")]
        )
        playlist = playlists.create_playlist("Mix")
        bridge.add_track_to_playlist(playlist.playlist_id, "/A/song.flac")
        _relocate(library, "T1", "/B/song.flac")

        bridge.open_playlist(playlist.playlist_id)
        rows = bridge.property("playlistTrackRows")
        assert len(rows) == 1
        assert rows[0]["path"] == "/B/song.flac"
        assert rows[0]["trackId"] == "T1"
        assert rows[0]["available"] is True
        assert bridge.property("playlistUnavailableCount") == 0


# ==========================================================================
# PLAYLISTS IDENTITY RECOVERY (2.1) — CONVERGENCE SEAL: LibraryTrackResolver
# como autoridad, effective availability, adversarial no-rebinding, undo
# identity-safe, batch remove relocation-safe, picker truth por TrackId,
# auto palette current, coordinator TrackId-native.
# ==========================================================================


def _state_track(
    path: str,
    track_id: str,
    *,
    title: str = "",
    artist: str = "Beta",
    album: str = "First Set",
    album_artist: str = "Beta",
    availability=MediaAvailability.AVAILABLE,
) -> TrackRef:
    return TrackRef(
        Path(path),
        title=title or Path(path).stem,
        artist=artist,
        album=album,
        album_artist=album_artist,
        track_id=track_id,
        media_file_id=f"media-{track_id}",
        library_source_id="s1" if track_id else "",
        availability=availability,
    )


def _library_with_albums(tmp_path, tracks):
    from michi.application.library_service import LibraryService

    library = LibraryService(_StubScanner(), library_prefs=_StubPrefs())
    library._state.tracks = list(tracks)
    library._rebuild_derived_library_state()
    return library


class TestConvergenceAvailability:
    def test_offline_track_retained_but_never_plays_or_queues(self, tmp_path) -> None:
        """T1 SOURCE_OFFLINE: la row sigue visible (membership retained)
        pero unavailable; play y queue son no-ops."""
        bridge, playlists, session, queue, library = _identity_harness(
            tmp_path,
            [
                _state_track(
                    "/A/song.flac", "T1", availability=MediaAvailability.SOURCE_OFFLINE
                )
            ],
        )
        playlist = playlists.create_playlist("Mix")
        bridge.add_track_to_playlist(playlist.playlist_id, "/A/song.flac")

        bridge.open_playlist(playlist.playlist_id)
        rows = bridge.property("playlistTrackRows")
        assert len(rows) == 1
        assert rows[0]["trackId"] == "T1"
        assert rows[0]["available"] is False, "offline → no reproducible"
        assert rows[0]["unavailableReason"] == "not_playable"
        assert bridge.property("playlistUnavailableCount") == 1

        bridge.play_playlist(playlist.playlist_id)
        assert session._pending is None, "offline nunca llega al motor"
        bridge.queue_playlist(playlist.playlist_id)
        assert len(queue.state.tracks) == 0, "offline nunca entra a Queue"

    def test_missing_track_retained_but_never_plays(self, tmp_path) -> None:
        bridge, playlists, session, queue, library = _identity_harness(
            tmp_path,
            [
                _state_track(
                    "/A/song.flac", "T1", availability=MediaAvailability.MISSING
                )
            ],
        )
        playlist = playlists.create_playlist("Mix")
        bridge.add_track_to_playlist(playlist.playlist_id, "/A/song.flac")

        bridge.open_playlist(playlist.playlist_id)
        rows = bridge.property("playlistTrackRows")
        assert rows[0]["available"] is False
        assert rows[0]["trackId"] == "T1"

        bridge.play_playlist(playlist.playlist_id)
        assert session._pending is None
        bridge.queue_playlist(playlist.playlist_id)
        assert len(queue.state.tracks) == 0
        # Membership durable intacta.
        assert playlists.get_playlist(playlist.playlist_id).track_ids == ("T1",)

    def test_member_track_id_never_rebinds_to_another_track(self, tmp_path) -> None:
        """ADVERSARIAL: T1 ya no existe en el catálogo y T2 ahora ocupa el
        viejo fallback /A — el miembro (T1, /A) NUNCA se presenta como T2:
        con TrackId estable, el fallback no reidentifica."""
        bridge, playlists, session, _, _ = _identity_harness(
            tmp_path, [_state_track("/A/song.flac", "T1")]
        )
        playlist = playlists.create_playlist("Mix")
        bridge.add_track_to_playlist(playlist.playlist_id, "/A/song.flac")
        # El catálogo cambia: T1 desaparece; T2 (otro track) ocupa /A.
        library = bridge._library
        library._state.tracks = [_state_track("/A/song.flac", "T2")]
        library._rebuild_derived_library_state()
        library._notify()

        bridge.open_playlist(playlist.playlist_id)
        rows = bridge.property("playlistTrackRows")
        assert len(rows) == 1
        assert rows[0]["trackId"] == "T1", "el miembro conserva su identidad"
        assert rows[0]["available"] is False, "T2 jamás se presenta como T1"
        bridge.play_playlist(playlist.playlist_id)
        assert session._pending is None


class TestConvergenceCoordinator:
    def _coordinator_harness(self, tmp_path, tracks):
        from michi.application.library_collection_coordinators import (
            LibraryPlaylistCoordinator,
        )
        from michi.infrastructure.playlists import SqlitePlaylistsRepository

        library = _library_with_albums(tmp_path, tracks)
        repo = SqlitePlaylistsRepository(tmp_path / "michi.db")
        playlists = PlaylistService(playlists_port=repo)
        coordinator = LibraryPlaylistCoordinator(library, playlists)
        return library, playlists, coordinator, repo

    def test_add_album_writes_durable_track_ids(self, tmp_path) -> None:
        from michi.infrastructure.playlists import SqlitePlaylistsRepository

        _, playlists, coordinator, _ = self._coordinator_harness(
            tmp_path,
            [
                _state_track("/a.flac", "T1", title="A"),
                _state_track("/b.flac", "T2", title="B"),
            ],
        )
        playlist = playlists.create_playlist("Mix")
        assert coordinator.add_album(playlist.playlist_id, "9::first set::beta") == 2
        persisted = playlists.get_playlist(playlist.playlist_id)
        assert persisted.track_ids == ("T1", "T2"), (
            "Add Album → references reales, no ids vacíos"
        )
        reloaded = PlaylistService(
            playlists_port=SqlitePlaylistsRepository(tmp_path / "michi.db")
        ).get_playlist(playlist.playlist_id)
        assert reloaded.track_ids == ("T1", "T2")

    def test_add_artist_writes_durable_track_ids(self, tmp_path) -> None:
        _, playlists, coordinator, _ = self._coordinator_harness(
            tmp_path,
            [
                _state_track("/a.flac", "T1", title="A"),
                _state_track("/b.flac", "T2", title="B"),
            ],
        )
        playlist = playlists.create_playlist("Mix")
        from michi.domain.library import make_artist_key

        assert (
            coordinator.add_artist(playlist.playlist_id, make_artist_key("Beta")) == 2
        )
        assert playlists.get_playlist(playlist.playlist_id).track_ids == ("T1", "T2")

    def test_create_from_album_first_durable_state_has_ids(self, tmp_path) -> None:
        from michi.infrastructure.playlists import SqlitePlaylistsRepository

        _, playlists, coordinator, _ = self._coordinator_harness(
            tmp_path,
            [
                _state_track("/a.flac", "T1", title="A"),
                _state_track("/b.flac", "T2", title="B"),
            ],
        )
        playlist = coordinator.create_from_album("New Mix", "9::first set::beta")
        assert playlist is not None
        assert playlist.track_ids == ("T1", "T2"), "IDs desde el primer estado durable"
        raw = SqlitePlaylistsRepository(tmp_path / "michi.db")._load_raw("playlists")
        assert raw[0]["version"] == 3
        assert raw[0]["tracks"][0]["track_id"] == "T1"


class TestConvergenceUndoAndBatch:
    def test_undo_after_relocation_restores_identity(self, tmp_path) -> None:
        """T1 /A → relocate /B → remove → undo → posición original con
        track_id T1 (restart incluido)."""
        from michi.infrastructure.playlists import SqlitePlaylistsRepository

        bridge, playlists, _, _, library = _identity_harness(
            tmp_path, [_state_track("/A/song.flac", "T1")]
        )
        playlist = playlists.create_playlist("Mix")
        bridge.add_track_to_playlist(playlist.playlist_id, "/A/song.flac")
        _relocate(library, "T1", "/B/song.flac")
        bridge.open_playlist(playlist.playlist_id)
        rows = bridge.property("playlistTrackRows")
        assert rows[0]["path"] == "/B/song.flac"

        # Remove (canonical index 0) + undo con la referencia congelada.
        assert bridge.remove_track(0) == "removed"
        assert playlists.get_playlist(playlist.playlist_id).references() == ()
        assert (
            bridge.insert_track_reference(
                playlist.playlist_id, 0, rows[0]["trackId"], rows[0]["path"]
            )
            == "restored"
        )
        restored = playlists.get_playlist(playlist.playlist_id)
        assert restored.track_ids == ("T1",), "el undo conserva la identidad"
        assert restored.track_paths == ("/B/song.flac",)
        reloaded = PlaylistService(
            playlists_port=SqlitePlaylistsRepository(tmp_path / "michi.db")
        ).get_playlist(playlist.playlist_id)
        assert reloaded.track_ids == ("T1",), "T1 sobrevive al restart"

    def test_batch_remove_by_current_path_after_relocation(self, tmp_path) -> None:
        """La selección multi llega con el path PROYECTADO (/B); el remove
        resuelve la membership canónica y remueve — no falla como missing
        contra el fallback persistido (/A)."""
        bridge, playlists, _, _, library = _identity_harness(
            tmp_path, [_state_track("/A/song.flac", "T1")]
        )
        playlist = playlists.create_playlist("Mix")
        bridge.add_track_to_playlist(playlist.playlist_id, "/A/song.flac")
        _relocate(library, "T1", "/B/song.flac")
        bridge.open_playlist(playlist.playlist_id)

        result = bridge.remove_tracks_by_paths(["/B/song.flac"])
        assert result["status"] == "removed"
        assert result["removedCount"] == 1
        assert playlists.get_playlist(playlist.playlist_id).references() == ()

    def test_picker_membership_truth_after_relocation(self, tmp_path) -> None:
        """Tras relocation el picker 'already present' decide por TrackId:
        selectedPlaylistTrackIds contiene T1 y la row candidata de T1 (con
        su path ACTUAL /B y trackId) está presente."""
        bridge, playlists, _, _, library = _identity_harness(
            tmp_path, [_state_track("/A/song.flac", "T1")]
        )
        playlist = playlists.create_playlist("Mix")
        bridge.add_track_to_playlist(playlist.playlist_id, "/A/song.flac")
        _relocate(library, "T1", "/B/song.flac")

        bridge.open_playlist(playlist.playlist_id)
        assert bridge.property("selectedPlaylistTrackIds") == ["T1"]
        candidates = bridge.property("addTrackCandidateRows")
        row = next(r for r in candidates if r.get("trackId") == "T1")
        assert row["path"] == "/B/song.flac"
        # El dedupe por TrackId del servicio coincide con la UI truth.
        assert (
            bridge.add_track_to_playlist(playlist.playlist_id, "/B/song.flac")
            == "already_present"
        )

    def test_auto_hero_palette_sources_use_current_paths(self, tmp_path) -> None:
        """La fuente de la paleta automática del hero son los paths ACTUALES
        de los miembros (relocation-safe), nunca los fallbacks persistidos."""
        bridge, playlists, _, _, library = _identity_harness(
            tmp_path, [_state_track("/A/song.flac", "T1")]
        )
        playlist = playlists.create_playlist("Mix")
        bridge.add_track_to_playlist(playlist.playlist_id, "/A/song.flac")
        _relocate(library, "T1", "/B/song.flac")
        bridge.open_playlist(playlist.playlist_id)

        captured = {}

        def _spy_mosaic(paths, index=None):
            captured["paths"] = tuple(paths)
            return []

        bridge._mosaic_for_paths = _spy_mosaic  # type: ignore[method-assign]
        bridge.property("selectedPlaylistAutoHeroColors")
        assert captured["paths"] == ("/B/song.flac",), (
            "la paleta automática usa el artwork ACTUAL, no el fallback /A"
        )
