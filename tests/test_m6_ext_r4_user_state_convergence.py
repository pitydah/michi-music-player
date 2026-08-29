"""M6-EXT-R4 freeze gate — user state converges to TrackId authority."""

from pathlib import Path

from michi.application.library_port import LibraryUserStatePort
from michi.application.library_service import LibraryService
from michi.application.ports import LibraryPrefsPort
from michi.domain.library import LibraryPrefs, TrackRef
from michi.domain.library_catalog import MediaAvailability
from michi.infrastructure.library_user_state import SqliteLibraryUserStateRepository


class _StubPrefs(LibraryPrefsPort):
    def __init__(self) -> None:
        self.saved: list[LibraryPrefs] = []

    def load(self) -> LibraryPrefs:
        return LibraryPrefs()

    def save(self, prefs: LibraryPrefs) -> None:
        self.saved.append(prefs)


class _FailingUserState(LibraryUserStatePort):
    """Truthful failure injection: every write raises the typed storage error."""

    def __init__(self) -> None:
        from michi.application.library_port import LibraryCatalogStorageError

        self._error = LibraryCatalogStorageError("injected user-state failure")

    def load_favorites(self) -> tuple[str, ...]:
        return ()

    def load_history(self) -> tuple[str, ...]:
        return ()

    def load_recently_added(self) -> tuple[str, ...]:
        return ()

    def set_favorites(self, track_ids) -> None:
        raise self._error

    def set_history(self, track_ids) -> None:
        raise self._error

    def set_recently_added(self, track_ids) -> None:
        raise self._error


class _StubScanner:
    def validate_file(self, path: Path) -> None:
        return None

    def scan(self, root: Path):
        return []

    def fingerprint(self, path: Path):
        return (0, 0)


def _track(path: str, track_id: str) -> TrackRef:
    return TrackRef(
        Path(path),
        title=Path(path).stem,
        track_id=track_id,
        media_file_id=f"media-{track_id}",
        library_source_id="s1",
        availability=MediaAvailability.AVAILABLE,
    )


def _seed_catalog(tmp_path) -> None:
    """Authoritative catalog rows for T1/T2 (the user-state repo is
    FK-restricted against the catalog — honest production shape)."""
    from michi.domain.library_catalog import (
        LibrarySource,
        MediaFileRecord,
        TrackRecord,
        new_library_source_id,
        new_media_file_id,
    )
    from michi.infrastructure.library_catalog import SqliteLibraryCatalogRepository

    catalog = SqliteLibraryCatalogRepository(tmp_path / "michi.db")
    source = LibrarySource(
        library_source_id=new_library_source_id(),
        display_name="S",
        root_path="/",
    )
    catalog.upsert_source(source)
    media = [
        MediaFileRecord(
            media_file_id=new_media_file_id(),
            library_source_id=source.library_source_id,
            relative_path="a.flac",
            last_known_path="/a.flac",
            availability=MediaAvailability.AVAILABLE,
        ),
        MediaFileRecord(
            media_file_id=new_media_file_id(),
            library_source_id=source.library_source_id,
            relative_path="b.flac",
            last_known_path="/b.flac",
            availability=MediaAvailability.AVAILABLE,
        ),
    ]
    tracks = [
        TrackRecord(track_id="T1", media_file_id=media[0].media_file_id),
        TrackRecord(track_id="T2", media_file_id=media[1].media_file_id),
    ]
    catalog.apply_source_reconciliation(tuple(media), tuple(tracks))


def _service(tmp_path, user_state=None, prefs=None):
    if user_state is None:
        _seed_catalog(tmp_path)
    library = LibraryService(
        _StubScanner(),
        library_prefs=prefs or _StubPrefs(),
        user_state=user_state
        or SqliteLibraryUserStateRepository(tmp_path / "michi.db"),
    )
    library._state.tracks = [_track("/a.flac", "T1"), _track("/b.flac", "T2")]
    library._rebuild_derived_library_state()
    return library


class TestCanonicalFavorites:
    def test_toggle_by_id_persists_track_id(self, tmp_path) -> None:
        library = _service(tmp_path)
        user = SqliteLibraryUserStateRepository(tmp_path / "michi.db")
        library.toggle_favorite_by_id("T1")
        assert library.state.favorite_track_ids == ("T1",)
        assert library.state.favorite_paths == ("/a.flac",)  # derived
        assert user.load_favorites() == ("T1",)

    def test_path_wrapper_delegates_to_id(self, tmp_path) -> None:
        library = _service(tmp_path)
        library.toggle_favorite(Path("/b.flac"))
        assert library.state.favorite_track_ids == ("T2",)

    def test_move_updates_derived_path_identity_stays(self, tmp_path) -> None:
        from michi.presentation.library_bridge import LibraryBridge

        library = _service(tmp_path)
        bridge = LibraryBridge(library)
        library.toggle_favorite_by_id("T1")
        # The file moves: identity stays; the DERIVED path projection
        # resolves the CURRENT path through the live refs (bridge).
        library._state.tracks = [_track("/new/location.flac", "T1")]
        library._rebuild_derived_library_state()
        assert library.state.favorite_track_ids == ("T1",)
        assert bridge.property("favoritePaths") == ["/new/location.flac"]

    def test_storage_failure_never_publishes_success(self, tmp_path) -> None:
        library = _service(tmp_path, user_state=_FailingUserState())
        library.toggle_favorite_by_id("T1")
        # No false success: in-memory state unchanged.
        assert library.state.favorite_track_ids == ()
        assert library.state.favorite_paths == ()


class TestCanonicalHistory:
    def test_history_by_id_with_dedupe_and_cap(self, tmp_path) -> None:
        library = _service(tmp_path)
        user = SqliteLibraryUserStateRepository(tmp_path / "michi.db")
        library.record_history_for_track("T1")
        library.record_history_for_track("T1")  # consecutive dedupe
        library.record_history_for_track("T2")
        assert library.state.history_track_ids == ("T2", "T1")
        assert user.load_history() == ("T2", "T1")

    def test_unknown_id_records_nothing(self, tmp_path) -> None:
        library = _service(tmp_path)
        library.record_history_for_track("no-such")
        assert library.state.history_track_ids == ()

    def test_path_history_routes_library_tracks_to_ids(self, tmp_path) -> None:
        library = _service(tmp_path)
        library.record_history(Path("/a.flac"))
        assert library.state.history_track_ids == ("T1",)
        # Non-library path stays on the legacy surface.
        library.record_history(Path("/outside.flac"))
        assert library.state.history_track_ids == ("T1",)
        assert "/outside.flac" in library.state.history_paths

    def test_storage_failure_keeps_previous_state(self, tmp_path) -> None:
        library = _service(tmp_path, user_state=_FailingUserState())
        library.record_history_for_track("T1")
        assert library.state.history_track_ids == ()


class TestCanonicalRecentlyAdded:
    def test_new_ids_enter_by_identity(self, tmp_path) -> None:
        library = _service(tmp_path)
        user = SqliteLibraryUserStateRepository(tmp_path / "michi.db")
        library.note_new_track_ids(("T1",))
        assert library.state.recently_added_track_ids == ("T1",)
        assert user.load_recently_added() == ("T1",)

    def test_move_never_reenters(self, tmp_path) -> None:
        library = _service(tmp_path)
        library.note_new_track_ids(("T1",))
        library.note_new_track_ids(("T1",))  # relink/modify → NOT new
        assert library.state.recently_added_track_ids == ("T1",)


class TestBridgeIdProperties:
    def test_favorite_track_ids_property(self, tmp_path) -> None:
        from michi.presentation.library_bridge import LibraryBridge

        library = _service(tmp_path)
        bridge = LibraryBridge(library)
        library.toggle_favorite_by_id("T1")
        assert bridge.property("favoriteTrackIds") == ["T1"]
        assert bridge.property("favoritePaths") == ["/a.flac"]

    def test_search_within_favorites_uses_uuid(self, tmp_path) -> None:
        from michi.presentation.library_bridge import LibraryBridge

        library = _service(tmp_path)
        bridge = LibraryBridge(library)
        library.toggle_favorite_by_id("T1")  # "a" title from stem
        library.search("a")
        assert library.state.search_active
        assert bridge.property("favoriteTrackIds") == ["T1"]

    def test_legacy_fallback_still_filters_paths(self, tmp_path) -> None:
        from michi.presentation.library_bridge import LibraryBridge

        library = _service(tmp_path, user_state=None)
        library.toggle_favorite(Path("/a.flac"))  # legacy path surface
        bridge = LibraryBridge(library)
        library.search("a")
        assert bridge.property("favoritePaths") == ["/a.flac"]
