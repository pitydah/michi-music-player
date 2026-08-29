"""M6-EXT-R4 freeze gate — missing/offline preservation + effective
availability (§10, §11, goldens E/D/V)."""

from pathlib import Path

from michi.application.library_service import LibraryService
from michi.application.library_track_resolver import LibraryTrackResolver
from michi.application.source_scan_coordinator import SourceScanCoordinator
from michi.domain.library import LibraryPrefs, TrackRef
from michi.domain.library_catalog import (
    LibrarySource,
    MediaAvailability,
    SourceAvailability,
    effective_availability,
    new_library_source_id,
)
from michi.infrastructure.filesystem_source_scanner import (
    FilesystemLibrarySourceScanner,
)
from michi.infrastructure.library_catalog import SqliteLibraryCatalogRepository
from michi.infrastructure.library_media_cache import SqliteLibraryMediaCache


class _StubPrefs:
    def load(self) -> LibraryPrefs:
        return LibraryPrefs()

    def save(self, prefs: LibraryPrefs) -> None:
        del prefs


class _MissingScanner:
    """Filesystem gate that reports every file missing."""

    def validate_file(self, path: Path) -> None:
        from michi.application.library_port import LibraryFilesystemError
        from michi.domain.library import LibraryDiagnosticCode

        raise LibraryFilesystemError(LibraryDiagnosticCode.TRACK_MISSING, path)

    def scan(self, root: Path):
        return []

    def fingerprint(self, path: Path):
        return (0, 0)


def _ref(path: str, track_id: str, source_id: str) -> TrackRef:
    return TrackRef(
        Path(path),
        title=Path(path).stem,
        track_id=track_id,
        media_file_id=f"media-{track_id}",
        library_source_id=source_id,
        availability=MediaAvailability.AVAILABLE,
    )


class TestPlayMissingNeverDeletes:
    def test_golden_play_missing_preserves_everything(self, tmp_path) -> None:
        catalog = SqliteLibraryCatalogRepository(tmp_path / "michi.db")
        source = LibrarySource(
            library_source_id=new_library_source_id(),
            display_name="S",
            root_path="/Music",
        )
        catalog.upsert_source(source)
        library = LibraryService(
            _MissingScanner(),
            library_prefs=_StubPrefs(),
            catalog=catalog,
        )
        t1 = _ref("/Music/A/song.flac", "T1", source.library_source_id)
        library._state.tracks = [t1]
        library._rebuild_derived_library_state()

        playable = library.validate_track_for_playback(library.state.tracks[0])

        assert playable is False
        # Identity preserved: TrackRef still in the library, marked MISSING.
        assert len(library.state.tracks) == 1
        assert library.state.tracks[0].track_id == "T1"
        assert library.state.tracks[0].availability is MediaAvailability.MISSING
        assert library.state.diagnostic is not None
        # The catalog mark applies only when the media row exists; the
        # in-memory observation always stands (failure-safe).

    def test_missing_mark_writes_catalog_when_media_exists(self, tmp_path) -> None:
        from michi.domain.library_catalog import (
            MediaFileRecord,
            TrackRecord,
            new_media_file_id,
            new_track_id,
        )

        catalog = SqliteLibraryCatalogRepository(tmp_path / "michi.db")
        source = LibrarySource(
            library_source_id=new_library_source_id(),
            display_name="S",
            root_path="/Music",
        )
        catalog.upsert_source(source)
        media = MediaFileRecord(
            media_file_id=new_media_file_id(),
            library_source_id=source.library_source_id,
            relative_path="A/song.flac",
            last_known_path="/Music/A/song.flac",
            availability=MediaAvailability.AVAILABLE,
        )
        track = TrackRecord(track_id=new_track_id(), media_file_id=media.media_file_id)
        catalog.apply_source_reconciliation((media,), (track,))
        library = LibraryService(
            _MissingScanner(), library_prefs=_StubPrefs(), catalog=catalog
        )
        t1 = TrackRef(
            Path("/Music/A/song.flac"),
            title="song",
            track_id=track.track_id,
            media_file_id=media.media_file_id,
            library_source_id=source.library_source_id,
            availability=MediaAvailability.AVAILABLE,
        )
        library._state.tracks = [t1]
        library._rebuild_derived_library_state()

        assert library.validate_track_for_playback(t1) is False
        assert catalog.load_media()[0].availability is MediaAvailability.MISSING


class TestEffectiveAvailability:
    def test_offline_source_dominates_without_write_storm(self) -> None:
        assert (
            effective_availability(
                MediaAvailability.AVAILABLE, SourceAvailability.OFFLINE
            )
            is MediaAvailability.SOURCE_OFFLINE
        )
        assert (
            effective_availability(
                MediaAvailability.AVAILABLE, SourceAvailability.MISSING_ROOT
            )
            is MediaAvailability.SOURCE_OFFLINE
        )
        assert (
            effective_availability(
                MediaAvailability.AVAILABLE, SourceAvailability.ACCESS_DENIED
            )
            is MediaAvailability.ACCESS_DENIED
        )

    def test_available_source_defers_to_media(self) -> None:
        assert (
            effective_availability(
                MediaAvailability.MISSING, SourceAvailability.AVAILABLE
            )
            is MediaAvailability.MISSING
        )
        assert (
            effective_availability(
                MediaAvailability.AVAILABLE, SourceAvailability.AVAILABLE
            )
            is MediaAvailability.AVAILABLE
        )

    def test_resolver_unplayable_when_source_offline(self, tmp_path) -> None:
        catalog = SqliteLibraryCatalogRepository(tmp_path / "michi.db")
        source = LibrarySource(
            library_source_id=new_library_source_id(),
            display_name="NAS",
            root_path="/mnt/nas",
        )
        catalog.upsert_source(source)
        library = LibraryService(_MissingScanner(), library_prefs=_StubPrefs())
        t1 = _ref("/mnt/nas/song.flac", "T1", source.library_source_id)
        library._state.tracks = [t1]
        library._rebuild_derived_library_state()

        observations = {source.library_source_id: SourceAvailability.OFFLINE}
        resolver = LibraryTrackResolver(
            library,
            catalog=catalog,
            source_availability_provider=lambda sid: observations.get(
                sid, SourceAvailability.UNKNOWN
            ),
        )
        assert resolver.resolve_playable_path("T1") is None
        assert resolver.effective_availability(t1) is MediaAvailability.SOURCE_OFFLINE
        # Track identity fully preserved (no removal, no write storm).
        assert len(library.state.tracks) == 1

    def test_offline_scan_zero_child_missing_and_unplayable(self, tmp_path) -> None:
        # Golden D: source offline → zero child MISSING, tracks browsable,
        # unplayable via the resolver.
        catalog = SqliteLibraryCatalogRepository(tmp_path / "michi.db")
        library = LibraryService(
            FilesystemLibrarySourceScanner(), library_prefs=_StubPrefs()
        )
        coordinator = SourceScanCoordinator(
            library,
            catalog,
            FilesystemLibrarySourceScanner(),
            media_cache=SqliteLibraryMediaCache(tmp_path / "michi.db"),
        )
        source = LibrarySource(
            library_source_id=new_library_source_id(),
            display_name="NAS",
            root_path=str(tmp_path / "nas"),
        )
        catalog.upsert_source(source)
        root = Path(source.root_path)
        root.mkdir()
        (root / "song.flac").write_bytes(b"x")
        coordinator.scan_source(source)
        assert len(catalog.load_media()) == 1

        import shutil

        shutil.rmtree(root)
        outcome = coordinator.scan_source(source)
        assert outcome.missing == 0  # zero child write storm
        assert (
            coordinator.observed_availability(source.library_source_id)
            is SourceAvailability.MISSING_ROOT
        )
        assert len(catalog.load_media()) == 1  # children untouched
        assert len(library.state.tracks) == 1  # browsable

        resolver = LibraryTrackResolver(
            library,
            catalog=catalog,
            source_availability_provider=coordinator.observed_availability,
        )
        track = library.state.tracks[0]
        assert resolver.resolve_playable_path(track.track_id) is None
