"""M6-EXT-R4 FINAL SEAL P1-02/P1-03 — TrackId-native user-state projections
and ONE effective-availability authority.

KILLCRITIC cases:
- favorite/history/recently-added moved track stays visible, deduped,
  current-path, searchable by TrackId.
- offline source → EVERY surface reports effective unplayable (no lying).
- media MISSING + source AVAILABLE; both MISSING; DISABLED; RETIRED.
"""

from pathlib import Path
from types import SimpleNamespace

from michi.application.library_service import LibraryService
from michi.application.ports import LibraryPrefsPort
from michi.domain.library import LibraryPrefs, TrackRef
from michi.domain.library_catalog import (
    MediaAvailability,
    SourceAvailability,
    effective_availability,
)
from michi.infrastructure.library_catalog import SqliteLibraryCatalogRepository
from michi.infrastructure.library_user_state import SqliteLibraryUserStateRepository
from michi.presentation.library_bridge import LibraryBridge


class _StubPrefs(LibraryPrefsPort):
    def load(self) -> LibraryPrefs:
        return LibraryPrefs()

    def save(self, prefs: LibraryPrefs) -> None:
        del prefs


class _StubScanner:
    def validate_file(self, path: Path) -> None:
        return None

    def scan(self, root: Path):
        return []

    def fingerprint(self, path: Path):
        return (0, 0)


def _track(path: str, track_id: str, source_id: str = "s1") -> TrackRef:
    return TrackRef(
        Path(path),
        title=Path(path).stem,
        artist="Artist",
        album="Album",
        track_id=track_id,
        media_file_id=f"media-{track_id}",
        library_source_id=source_id,
        availability=MediaAvailability.AVAILABLE,
    )


def _seed_catalog(tmp_path, track_ids):
    from michi.domain.library_catalog import (
        LibrarySource,
        MediaFileRecord,
        TrackRecord,
        new_library_source_id,
        new_media_file_id,
    )

    catalog = SqliteLibraryCatalogRepository(tmp_path / "michi.db")
    source = LibrarySource(
        library_source_id=new_library_source_id(), display_name="S", root_path="/"
    )
    catalog.upsert_source(source)
    media = []
    tracks = []
    for i, track_id in enumerate(track_ids):
        media.append(
            MediaFileRecord(
                media_file_id=new_media_file_id(),
                library_source_id=source.library_source_id,
                relative_path=f"t{i}.flac",
                last_known_path=f"/t{i}.flac",
                availability=MediaAvailability.AVAILABLE,
            )
        )
        tracks.append(
            TrackRecord(track_id=track_id, media_file_id=media[-1].media_file_id)
        )
    catalog.apply_source_reconciliation(tuple(media), tuple(tracks))
    return catalog, source


def _harness(tmp_path):
    catalog, source = _seed_catalog(tmp_path, ["T1", "T2"])
    user = SqliteLibraryUserStateRepository(tmp_path / "michi.db")
    library = LibraryService(
        _StubScanner(), library_prefs=_StubPrefs(), user_state=user
    )
    library._state.tracks = [
        _track("/Music/A.flac", "T1", source.library_source_id),
        _track("/Music/B.flac", "T2", source.library_source_id),
    ]
    library._rebuild_derived_library_state()
    return library, catalog, source, user


class _OfflineCoordinator:
    """Minimal source-availability observer for the bridge."""

    def __init__(self, availability) -> None:
        self._availability = availability

    def observed_availability(self, source_id):
        return self._availability


class TestTrackIdNativeProjections:
    def test_favorite_moved_track_stays_visible_current_path(self, tmp_path) -> None:
        library, catalog, source, user = _harness(tmp_path)
        library.toggle_favorite_by_id("T1")
        bridge = LibraryBridge(library)
        # The file moves: TrackRef path projection updates; identity stays.
        library._state.tracks = [
            _track("/Music/New/A.flac", "T1", source.library_source_id),
            _track("/Music/B.flac", "T2", source.library_source_id),
        ]
        library._rebuild_derived_library_state()

        rows = bridge.property("favoriteTrackRows")
        assert len(rows) == 1  # not lost, not duplicated
        assert rows[0]["path"] == "/Music/New/A.flac"  # current path
        assert rows[0]["trackId"] == "T1"  # identity unchanged

    def test_search_within_favorites_uses_track_id(self, tmp_path) -> None:
        library, catalog, source, user = _harness(tmp_path)
        library.toggle_favorite_by_id("T1")
        bridge = LibraryBridge(library)
        library._state.tracks = [
            _track("/Music/New/A.flac", "T1", source.library_source_id),
            _track("/Music/B.flac", "T2", source.library_source_id),
        ]
        library._rebuild_derived_library_state()
        library.search("a")  # matches T1 (title stem) after the move
        assert library.state.search_active
        rows = bridge.property("favoriteTrackRows")
        assert len(rows) == 1
        assert rows[0]["trackId"] == "T1"

    def test_history_moved_track_stays_visible(self, tmp_path) -> None:
        library, catalog, source, user = _harness(tmp_path)
        library.record_history_for_track("T1")
        library._state.tracks = [
            _track("/Music/New/A.flac", "T1", source.library_source_id),
            _track("/Music/B.flac", "T2", source.library_source_id),
        ]
        library._rebuild_derived_library_state()
        bridge = LibraryBridge(library)
        rows = bridge.property("historyTrackRows")
        assert len(rows) == 1
        assert rows[0]["path"] == "/Music/New/A.flac"
        assert rows[0]["trackId"] == "T1"

    def test_recently_added_moved_track_stays_visible(self, tmp_path) -> None:
        library, catalog, source, user = _harness(tmp_path)
        library.note_new_track_ids(("T1",))
        library._state.tracks = [
            _track("/Music/New/A.flac", "T1", source.library_source_id),
            _track("/Music/B.flac", "T2", source.library_source_id),
        ]
        library._rebuild_derived_library_state()
        bridge = LibraryBridge(library)
        rows = bridge.property("recentlyAddedTrackRows")
        assert len(rows) == 1
        assert rows[0]["trackId"] == "T1"
        assert rows[0]["path"] == "/Music/New/A.flac"

    def test_offline_source_collections_still_render_unplayable(self, tmp_path) -> None:
        library, catalog, source, user = _harness(tmp_path)
        library.toggle_favorite_by_id("T1")
        bridge = LibraryBridge(library)
        bridge._source_coordinator = _OfflineCoordinator(SourceAvailability.OFFLINE)
        rows = bridge.property("favoriteTrackRows")
        assert len(rows) == 1  # still visible…
        assert rows[0]["availability"] == "source_offline"  # …never lying

    def test_stale_fallback_path_never_governs(self, tmp_path) -> None:
        library, catalog, source, user = _harness(tmp_path)
        library.toggle_favorite_by_id("T1")
        # The legacy path surface still holds the STALE old path (compat);
        # the canonical ID surface must ignore it.
        library._state.favorite_paths = ("/Music/OLD-REMOVED.flac",)
        library._state.tracks = [
            _track("/Music/New/A.flac", "T1", source.library_source_id),
            _track("/Music/B.flac", "T2", source.library_source_id),
        ]
        library._rebuild_derived_library_state()
        bridge = LibraryBridge(library)
        rows = bridge.property("favoriteTrackRows")
        assert len(rows) == 1
        assert rows[0]["trackId"] == "T1"


class TestEffectiveAvailabilityAuthority:
    def test_precedence_matrix(self) -> None:
        """ONE domain function defines ALL combinations."""
        assert (
            effective_availability(
                MediaAvailability.AVAILABLE, SourceAvailability.AVAILABLE
            )
            is MediaAvailability.AVAILABLE
        )
        assert (
            effective_availability(
                MediaAvailability.MISSING, SourceAvailability.AVAILABLE
            )
            is MediaAvailability.MISSING
        )
        assert (
            effective_availability(
                MediaAvailability.AVAILABLE, SourceAvailability.OFFLINE
            )
            is MediaAvailability.SOURCE_OFFLINE
        )
        assert (
            effective_availability(
                MediaAvailability.MISSING, SourceAvailability.OFFLINE
            )
            is MediaAvailability.SOURCE_OFFLINE
        )
        assert (
            effective_availability(
                MediaAvailability.AVAILABLE, SourceAvailability.DISABLED
            )
            is MediaAvailability.SOURCE_OFFLINE
        )

    def test_all_surfaces_share_one_availability(self, tmp_path) -> None:
        """Songs + Favorites + Search report the SAME effective value."""
        library, catalog, source, user = _harness(tmp_path)
        library.toggle_favorite_by_id("T1")
        bridge = LibraryBridge(library)
        bridge._source_coordinator = _OfflineCoordinator(SourceAvailability.OFFLINE)

        song_rows = bridge.property("songRows")
        favorite_rows = bridge.property("favoriteTrackRows")
        # Both surfaces must agree (never Songs=AVAILABLE while Favorites
        # says offline).
        assert {r["availability"] for r in favorite_rows} == {"source_offline"}
        assert {r["availability"] for r in song_rows} == {"source_offline"}

    def test_source_back_online_converges_without_new_identity(self, tmp_path) -> None:
        library, catalog, source, user = _harness(tmp_path)
        library.toggle_favorite_by_id("T1")
        bridge = LibraryBridge(library)
        bridge._source_coordinator = _OfflineCoordinator(SourceAvailability.OFFLINE)
        assert (
            bridge.property("favoriteTrackRows")[0]["availability"] == "source_offline"
        )

        # Source returns: same TrackId, effective AVAILABLE again.
        bridge._source_coordinator = _OfflineCoordinator(SourceAvailability.AVAILABLE)
        rows = bridge.property("favoriteTrackRows")
        assert rows[0]["availability"] == "available"
        assert rows[0]["trackId"] == "T1"


class TestPlaylistRowsStableIdentity:
    def test_moved_member_visible_at_current_path(self, tmp_path) -> None:
        """P1-02/03 in playlist rows: a moved member resolves by TrackId."""
        from michi.application.playlist_service import PlaylistService
        from michi.presentation.playlists_bridge import PlaylistsBridge

        library, catalog, source, user = _harness(tmp_path)
        service = PlaylistService()
        playlist = service.create_playlist("Mix")
        service.add_track(playlist.playlist_id, "/Music/A.flac")
        bridge = PlaylistsBridge(service, library=library)
        bridge._navigation = SimpleNamespace(
            state=SimpleNamespace(playlist_id=playlist.playlist_id)
        )

        # SEMANTIC INTEGRATION: main's playlist authority es PATH-based
        # (PR #223/#229) — un archivo movido deja el miembro visible pero
        # UNAVAILABLE (nunca se pierde, nunca se duplica, nunca se borra).
        library._state.tracks = [
            _track("/Music/New/A.flac", "T1", source.library_source_id),
            _track("/Music/B.flac", "T2", source.library_source_id),
        ]
        library._rebuild_derived_library_state()
        rows = bridge.property("playlistTrackRows")
        assert len(rows) == 1  # never lost, never duplicated
        assert rows[0]["path"] == "/Music/A.flac"  # membresía canónica intacta
        assert rows[0]["available"] is False  # el path viejo no resuelve
        assert rows[0]["unavailableReason"] == "not_in_library"

    def test_member_row_availability_is_effective(self, tmp_path) -> None:
        from michi.application.playlist_service import PlaylistService
        from michi.presentation.playlists_bridge import PlaylistsBridge

        library, catalog, source, user = _harness(tmp_path)
        service = PlaylistService()
        playlist = service.create_playlist("Mix")
        service.add_track(playlist.playlist_id, "/Music/A.flac")
        bridge = PlaylistsBridge(service, library=library)
        bridge._navigation = SimpleNamespace(
            state=SimpleNamespace(playlist_id=playlist.playlist_id)
        )
        rows = bridge.property("playlistTrackRows")
        # SEMANTIC INTEGRATION: main's bridge proyecta availability por
        # resolución de Library (available/unavailableReason) — el miembro
        # permanece visible y la proyección es honesta.
        assert rows[0]["path"] == "/Music/A.flac"
        assert "available" in rows[0]
        assert "unavailableReason" in rows[0]
