"""M6-EXT-R4-K/L — source-aware scans, multi-source isolation, offline and
missing semantics (golden scenarios A–J from prompt §90)."""

import time
from pathlib import Path

import pytest

from michi.application.library_service import LibraryService
from michi.application.ports import LibraryPrefsPort
from michi.application.source_scan_coordinator import (
    SourceScanCoordinator,
)
from michi.domain.library import LibraryPrefs
from michi.domain.library_catalog import (
    LibrarySource,
    MediaAvailability,
    SourceAvailability,
    SourceLifecycle,
    new_library_source_id,
)
from michi.infrastructure.filesystem_source_scanner import (
    FilesystemLibrarySourceScanner,
)
from michi.infrastructure.library_catalog import SqliteLibraryCatalogRepository
from michi.infrastructure.library_media_cache import SqliteLibraryMediaCache


class _StubPrefs(LibraryPrefsPort):
    def __init__(self) -> None:
        self.saved: list[LibraryPrefs] = []

    def load(self) -> LibraryPrefs:
        return LibraryPrefs()

    def save(self, prefs: LibraryPrefs) -> None:
        self.saved.append(prefs)


class _StubMetadata:
    """Extracts (title=stem, artist=parent name) so files are distinguishable."""

    def extract(self, file_path: Path):
        from michi.domain.library import TrackMetadata

        return TrackMetadata(
            title=file_path.stem,
            artist=file_path.parent.name,
            album="Album",
            duration_ms=1000,
        )


@pytest.fixture
def env(tmp_path):
    db_path = tmp_path / "michi.db"
    catalog = SqliteLibraryCatalogRepository(db_path)
    media_cache = SqliteLibraryMediaCache(db_path)
    scanner = FilesystemLibrarySourceScanner()
    library = LibraryService(
        scanner, metadata_extractor=_StubMetadata(), library_prefs=_StubPrefs()
    )
    coordinator = SourceScanCoordinator(
        library,
        catalog,
        scanner,
        media_cache=media_cache,
        metadata_extractor=_StubMetadata(),
    )
    return library, catalog, coordinator, scanner, tmp_path


def _source(tmp_path, name: str) -> LibrarySource:
    root = tmp_path / name
    root.mkdir()
    source = LibrarySource(
        library_source_id=new_library_source_id(),
        display_name=name,
        root_path=str(root),
    )
    return source


def _write(root: Path, relative: str, content: bytes = b"x") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


class TestSingleSource:
    def test_a_first_scan_adds_all_tracks(self, env) -> None:
        library, catalog, coordinator, scanner, tmp_path = env
        source = _source(tmp_path, "music")
        catalog.upsert_source(source)
        _write(Path(source.root_path), "A/song1.flac")
        _write(Path(source.root_path), "B/song2.flac")

        outcome = coordinator.scan_source(source)

        assert outcome.added == 2
        assert outcome.unchanged == 0
        assert outcome.availability is SourceAvailability.AVAILABLE
        assert outcome.failed is False
        # Catalog committed authoritative identities.
        media = catalog.media_for_source(source.library_source_id)
        assert len(media) == 2
        tracks = catalog.load_tracks()
        assert len(tracks) == 2
        # Library state carries stable ids + availability.
        assert len(library.state.tracks) == 2
        assert all(t.track_id for t in library.state.tracks)
        assert all(
            t.library_source_id == source.library_source_id
            for t in library.state.tracks
        )
        assert all(
            t.availability is MediaAvailability.AVAILABLE for t in library.state.tracks
        )

    def test_unchanged_rescan_is_zero_extraction_and_zero_new_ids(self, env) -> None:
        library, catalog, coordinator, scanner, tmp_path = env
        source = _source(tmp_path, "music")
        catalog.upsert_source(source)
        _write(Path(source.root_path), "A/song1.flac")
        coordinator.scan_source(source)
        ids_before = {t.track_id for t in catalog.load_tracks()}

        outcome = coordinator.scan_source(source)

        assert outcome.unchanged == 1
        assert outcome.added == 0
        assert {t.track_id for t in catalog.load_tracks()} == ids_before

    def test_i_modified_tags_keeps_identity(self, env) -> None:
        library, catalog, coordinator, scanner, tmp_path = env
        source = _source(tmp_path, "music")
        catalog.upsert_source(source)
        path = _write(Path(source.root_path), "A/song1.flac", b"old")
        coordinator.scan_source(source)
        track_id_before = catalog.load_tracks()[0].track_id
        media_id_before = catalog.load_media()[0].media_file_id

        time.sleep(0.01)  # ensure distinct mtime
        path.write_bytes(b"new-bytes")
        outcome = coordinator.scan_source(source)

        assert outcome.modified == 1
        tracks = catalog.load_tracks()
        assert tracks[0].track_id == track_id_before  # identity preserved
        assert catalog.load_media()[0].media_file_id == media_id_before

    def test_e_missing_file_is_marked_not_deleted(self, env) -> None:
        library, catalog, coordinator, scanner, tmp_path = env
        source = _source(tmp_path, "music")
        catalog.upsert_source(source)
        path = _write(Path(source.root_path), "A/song1.flac")
        coordinator.scan_source(source)
        track_id_before = catalog.load_tracks()[0].track_id

        path.unlink()
        outcome = coordinator.scan_source(source)

        assert outcome.missing == 1
        assert outcome.added == 0
        media = catalog.load_media()[0]
        assert media.availability is MediaAvailability.MISSING
        assert catalog.load_tracks()[0].track_id == track_id_before
        # Library still shows the track (cached, unavailable).
        assert len(library.state.tracks) == 1
        assert library.state.tracks[0].availability is MediaAvailability.MISSING

    def test_f_renamed_file_relinks_uniquely(self, env) -> None:
        library, catalog, coordinator, scanner, tmp_path = env
        source = _source(tmp_path, "music")
        catalog.upsert_source(source)
        path = _write(Path(source.root_path), "A/song1.flac")
        coordinator.scan_source(source)
        track_id_before = catalog.load_tracks()[0].track_id

        target_dir = Path(source.root_path) / "B"
        target_dir.mkdir()
        path.rename(target_dir / "song1.flac")
        outcome = coordinator.scan_source(source)

        assert outcome.relinked == 1
        assert outcome.added == 0
        assert outcome.missing == 0
        media = catalog.media_for_source(source.library_source_id)
        assert len(media) == 1
        assert media[0].relative_path == "B/song1.flac"
        assert media[0].availability is MediaAvailability.AVAILABLE
        assert catalog.load_tracks()[0].track_id == track_id_before


class TestMultiSource:
    def test_b_two_independent_sources_union(self, env) -> None:
        library, catalog, coordinator, scanner, tmp_path = env
        source_a = _source(tmp_path, "a")
        source_b = _source(tmp_path, "b")
        catalog.upsert_source(source_a)
        catalog.upsert_source(source_b)
        _write(Path(source_a.root_path), "song1.flac")
        _write(Path(source_b.root_path), "song2.flac")

        coordinator.scan_source(source_a)
        coordinator.scan_source(source_b)

        assert len(library.state.tracks) == 2
        ids_a = {
            t.track_id
            for t in library.state.tracks
            if t.library_source_id == source_a.library_source_id
        }
        assert len(ids_a) == 1

    def test_c_same_filename_in_two_sources_is_two_identities(self, env) -> None:
        library, catalog, coordinator, scanner, tmp_path = env
        source_a = _source(tmp_path, "a")
        source_b = _source(tmp_path, "b")
        catalog.upsert_source(source_a)
        catalog.upsert_source(source_b)
        _write(Path(source_a.root_path), "song.flac")
        _write(Path(source_b.root_path), "song.flac")

        coordinator.scan_source(source_a)
        coordinator.scan_source(source_b)

        tracks = library.state.tracks
        assert len(tracks) == 2
        assert len({t.track_id for t in tracks}) == 2  # distinct identities
        assert len({t.media_file_id for t in tracks}) == 2

    def test_source_a_rescan_cannot_remove_source_b(self, env) -> None:
        library, catalog, coordinator, scanner, tmp_path = env
        source_a = _source(tmp_path, "a")
        source_b = _source(tmp_path, "b")
        catalog.upsert_source(source_a)
        catalog.upsert_source(source_b)
        _write(Path(source_a.root_path), "a1.flac")
        _write(Path(source_b.root_path), "b1.flac")
        coordinator.scan_source(source_a)
        coordinator.scan_source(source_b)
        b_ids = {
            t.track_id
            for t in library.state.tracks
            if t.library_source_id == source_b.library_source_id
        }

        # Rescan A only — B survives untouched.
        coordinator.scan_source(source_a)
        remaining_b = {
            t.track_id
            for t in library.state.tracks
            if t.library_source_id == source_b.library_source_id
        }
        assert remaining_b == b_ids

    def test_d_offline_source_marks_zero_children(self, env) -> None:
        library, catalog, coordinator, scanner, tmp_path = env
        source = _source(tmp_path, "nas")
        catalog.upsert_source(source)
        _write(Path(source.root_path), "song1.flac")
        coordinator.scan_source(source)
        assert len(catalog.load_media()) == 1

        # The root vanishes (offline NAS).
        import shutil

        shutil.rmtree(source.root_path)
        outcome = coordinator.scan_source(source)

        assert outcome.availability is SourceAvailability.MISSING_ROOT
        assert outcome.missing == 0  # ZERO child MISSING rows
        assert outcome.total == 0
        media = catalog.load_media()
        assert len(media) == 1
        # Cached track still browsable (identity + metadata preserved).
        assert len(library.state.tracks) == 1
        assert (
            coordinator.observed_availability(source.library_source_id)
            is SourceAvailability.MISSING_ROOT
        )

    def test_retired_source_is_skipped(self, env) -> None:
        library, catalog, coordinator, scanner, tmp_path = env
        source = LibrarySource(
            library_source_id=new_library_source_id(),
            display_name="gone",
            root_path=str(tmp_path / "gone"),
            lifecycle=SourceLifecycle.RETIRED,
        )
        catalog.upsert_source(source)
        outcome = coordinator.scan_source(source)
        assert outcome.availability is SourceAvailability.DISABLED
        assert outcome.total == 0


class TestCatalogCommitFailure:
    def test_catalog_failure_never_publishes_state(self, env, monkeypatch) -> None:
        library, catalog, coordinator, scanner, tmp_path = env
        source = _source(tmp_path, "music")
        catalog.upsert_source(source)
        _write(Path(source.root_path), "song1.flac")
        coordinator.scan_source(source)
        state_snapshot = list(library.state.tracks)

        def boom(records, tracks):
            from michi.application.library_port import LibraryCatalogStorageError

            raise LibraryCatalogStorageError("injected storage failure")

        monkeypatch.setattr(catalog, "apply_source_reconciliation", boom)
        outcome = coordinator.scan_source(source)

        assert outcome.failed is True
        # No state mutation after a failed authoritative commit.
        assert [t.track_id for t in library.state.tracks] == [
            t.track_id for t in state_snapshot
        ]
