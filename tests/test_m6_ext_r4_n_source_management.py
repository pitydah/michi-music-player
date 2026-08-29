"""M6-EXT-R4-N — source management presentation (application half)."""

from pathlib import Path

from michi.application.library_service import LibraryService
from michi.application.ports import LibraryPrefsPort
from michi.application.source_scan_coordinator import (
    SourceOverlapError,
    SourceScanCoordinator,
)
from michi.domain.library import LibraryPrefs
from michi.domain.library_catalog import SourceLifecycle
from michi.infrastructure.filesystem_source_scanner import (
    FilesystemLibrarySourceScanner,
)
from michi.infrastructure.library_catalog import SqliteLibraryCatalogRepository
from michi.infrastructure.library_media_cache import SqliteLibraryMediaCache


class _StubPrefs(LibraryPrefsPort):
    def load(self) -> LibraryPrefs:
        return LibraryPrefs()

    def save(self, prefs: LibraryPrefs) -> None:
        del prefs


class _StubMetadata:
    def extract(self, file_path: Path):
        from michi.domain.library import TrackMetadata

        return TrackMetadata(title=file_path.stem, artist="A", album="B")


def _graph(tmp_path):
    db_path = tmp_path / "michi.db"
    catalog = SqliteLibraryCatalogRepository(db_path)
    library = LibraryService(
        FilesystemLibrarySourceScanner(),
        metadata_extractor=_StubMetadata(),
        library_prefs=_StubPrefs(),
    )
    coordinator = SourceScanCoordinator(
        library,
        catalog,
        FilesystemLibrarySourceScanner(),
        media_cache=SqliteLibraryMediaCache(db_path),
        metadata_extractor=_StubMetadata(),
    )
    from michi.presentation.library_bridge import LibraryBridge

    bridge = LibraryBridge(library, source_coordinator=coordinator)
    return bridge, catalog, coordinator, tmp_path


class TestSourceManagement:
    def test_bridge_projects_sources_with_counts(self, tmp_path) -> None:
        bridge, catalog, coordinator, tmp = _graph(tmp_path)
        root = tmp_path / "music"
        root.mkdir()
        source = coordinator.add_source("Local Music", str(root))
        (root / "song.flac").write_bytes(b"x")
        coordinator.scan_source(source)

        rows = bridge.property("musicSources")
        assert len(rows) == 1
        assert rows[0]["name"] == "Local Music"
        assert rows[0]["rootPath"] == str(root)
        assert rows[0]["trackCount"] == 1
        assert rows[0]["lifecycle"] == "active"
        assert rows[0]["enabled"] is True

    def test_add_source_detects_overlap_conflict(self, tmp_path) -> None:
        bridge, catalog, coordinator, tmp = _graph(tmp_path)
        root = tmp_path / "music"
        root.mkdir()
        coordinator.add_source("Music", str(root))
        # Nested root → typed conflict, never silently indexed.
        nested = root / "Classical"
        nested.mkdir()
        result = bridge.add_music_source("Classical", str(nested))
        assert "overlap" in result.lower()
        assert len(catalog.load_sources()) == 1
        # Parent-of-existing also rejected.
        parent = tmp_path
        result2 = bridge.add_music_source("Parent", str(parent))
        assert "overlap" in result2.lower()

    def test_retire_and_disable_via_bridge(self, tmp_path) -> None:
        bridge, catalog, coordinator, tmp = _graph(tmp_path)
        root = tmp_path / "music"
        root.mkdir()
        source = coordinator.add_source("Local", str(root))
        bridge.retire_source(source.library_source_id)
        assert catalog.load_sources()[0].lifecycle is SourceLifecycle.RETIRED
        bridge.disable_source(source.library_source_id, True)
        assert catalog.load_sources()[0].enabled is False
        # A retired source is never scanned.
        outcome = coordinator.scan_source(catalog.load_sources()[0])
        assert outcome.total == 0

    def test_scan_source_slot_reconciles_one_source(self, tmp_path) -> None:
        bridge, catalog, coordinator, tmp = _graph(tmp_path)
        root = tmp_path / "music"
        root.mkdir()
        source = coordinator.add_source("Local", str(root))
        (root / "song.flac").write_bytes(b"x")
        bridge.scan_source(source.library_source_id)
        rows = bridge.property("musicSources")
        assert rows[0]["trackCount"] == 1

    def test_source_overlap_error_is_typed(self, tmp_path) -> None:
        bridge, catalog, coordinator, tmp = _graph(tmp_path)
        root = tmp_path / "music"
        root.mkdir()
        coordinator.add_source("Music", str(root))
        nested = root / "Classical"
        nested.mkdir()
        try:
            coordinator.add_source("Classical", str(nested))
        except SourceOverlapError as exc:
            assert "overlap" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("SourceOverlapError not raised")
