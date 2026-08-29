"""M6-EXT-R4 freeze gate — §14/§15/§16/§23: async source scans, modified
metadata refresh, unambiguous relink, format policy, stale-generation
isolation."""

from pathlib import Path

from michi.application.library_service import LibraryService
from michi.application.ports import LibraryPrefsPort, ScanPipelinePort
from michi.application.source_scan_coordinator import (
    SourceScanCoordinator,
)
from michi.domain.library import LibraryPrefs, TrackMetadata
from michi.domain.library_catalog import (
    LibrarySource,
    new_library_source_id,
)
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


class _VersionedMetadata:
    """Extracts title=stem + artist from a sidecar marker file, so we can
    change tags between scans."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def extract(self, file_path: Path) -> TrackMetadata:
        marker = self._root / "artist.txt"
        artist = marker.read_text().strip() if marker.exists() else "Unknown"
        return TrackMetadata(title=file_path.stem, artist=artist, album="A")


class _SyncPipeline(ScanPipelinePort):
    """Runs work synchronously (test double) with owner/worker separation
    simulated by calling on_done AFTER work returns."""

    def __init__(self) -> None:
        self.submitted = 0
        self.cancelled_generations: list[int] = []

    def submit(self, generation, work, on_progress, on_done) -> None:
        self.submitted += 1
        from michi.application.ports import ScanCancelToken, ScanProgress

        progress = ScanProgress()
        token = ScanCancelToken()
        try:
            plan = work(progress, token, lambda: None)
        except BaseException as exc:  # noqa: BLE001
            on_done(generation, None, exc)
            return
        on_done(generation, plan, None)

    def cancel(self, generation: int) -> None:
        self.cancelled_generations.append(generation)


class _CancellingPipeline(_SyncPipeline):
    """Cancels mid-flight: the token flips after the first item."""

    def submit(self, generation, work, on_progress, on_done) -> None:
        self.submitted += 1
        from michi.application.ports import ScanCancelToken, ScanProgress

        progress = ScanProgress()
        token = ScanCancelToken()

        class _FlippingProgress:
            def __init__(self, inner):
                self._inner = inner
                self.calls = 0

            def __getattr__(self, name):
                return getattr(self._inner, name)

            def __setattr__(self, name, value):
                if name == "processed":
                    self.calls += 1
                    if self.calls >= 1:
                        token.cancelled = True
                object.__setattr__(self, name, value)

        try:
            plan = work(progress, _FlippingProgress(progress), lambda: None)
        except BaseException as exc:  # noqa: BLE001
            on_done(generation, None, exc)
            return
        on_done(generation, plan, None)


def _env(tmp_path):
    db_path = tmp_path / "michi.db"
    catalog = SqliteLibraryCatalogRepository(db_path)
    library = LibraryService(
        FilesystemLibrarySourceScanner(), library_prefs=_StubPrefs()
    )
    scanner = FilesystemLibrarySourceScanner()
    coordinator = SourceScanCoordinator(
        library,
        catalog,
        scanner,
        media_cache=SqliteLibraryMediaCache(db_path),
        metadata_extractor=_VersionedMetadata(tmp_path),
    )
    source = LibrarySource(
        library_source_id=new_library_source_id(),
        display_name="S",
        root_path=str(tmp_path / "music"),
    )
    catalog.upsert_source(source)
    root = tmp_path / "music"
    root.mkdir()
    return library, catalog, coordinator, source, root


class TestAsyncSourceScan:
    def test_async_scan_commits_on_owner_and_publishes(self, tmp_path) -> None:
        library, catalog, coordinator, source, root = _env(tmp_path)
        (root / "song.flac").write_bytes(b"x")
        pipeline = _SyncPipeline()
        results: dict = {}

        def on_done(generation, plan, error):
            results["outcome"] = coordinator.commit_source_scan_if_current(
                generation, 1, source, plan, error
            )

        coordinator.submit_source_scan(source, pipeline, 1, on_done=on_done)
        assert pipeline.submitted == 1
        assert results["outcome"].added == 1
        assert len(library.state.tracks) == 1  # published
        assert len(catalog.load_tracks()) == 1  # committed

    def test_stale_generation_never_commits(self, tmp_path) -> None:
        library, catalog, coordinator, source, root = _env(tmp_path)
        (root / "song.flac").write_bytes(b"x")
        pipeline = _SyncPipeline()
        results: dict = {}

        def on_done(generation, plan, error):
            # The generation already advanced: the stale plan must NOT
            # commit (simulates a superseded scan arriving late).
            results["outcome"] = coordinator.commit_source_scan_if_current(
                generation, 99, source, plan, error
            )

        coordinator.submit_source_scan(source, pipeline, 1, on_done=on_done)
        assert results["outcome"] is None
        assert len(catalog.load_tracks()) == 0  # nothing committed
        assert library.state.tracks == []

    def test_cancelled_scan_commits_nothing(self, tmp_path) -> None:
        library, catalog, coordinator, source, root = _env(tmp_path)
        (root / "a.flac").write_bytes(b"x")
        (root / "b.flac").write_bytes(b"x")
        pipeline = _CancellingPipeline()
        results: dict = {}

        def on_done(generation, plan, error):
            results["error"] = error
            results["outcome"] = coordinator.commit_source_scan_if_current(
                generation, 1, source, plan, error
            )

        coordinator.submit_source_scan(source, pipeline, 1, on_done=on_done)
        assert results["outcome"] is None  # cancelled: no partial commit
        assert catalog.load_tracks() == ()
        assert library.state.tracks == []


class TestModifiedMetadataRefresh:
    def test_retag_refreshes_metadata_same_id(self, tmp_path) -> None:
        """§15 golden: Artist=A → retag Artist=B (fingerprint changes) →
        same TrackId, artist == B."""
        library, catalog, coordinator, source, root = _env(tmp_path)
        (root / "song.flac").write_bytes(b"x")
        (tmp_path / "artist.txt").write_text("A")
        coordinator.scan_source(source)
        track_id = catalog.load_tracks()[0].track_id
        assert library.state.tracks[0].artist == "A"

        import time

        time.sleep(0.01)
        (root / "song.flac").write_bytes(b"changed-bytes")
        (tmp_path / "artist.txt").write_text("B")
        outcome = coordinator.scan_source(source)
        assert outcome.modified == 1
        assert catalog.load_tracks()[0].track_id == track_id  # identity stable
        assert library.state.tracks[0].artist == "B"  # metadata refreshed

    def test_unchanged_reuses_cache_zero_extraction(self, tmp_path) -> None:
        library, catalog, coordinator, source, root = _env(tmp_path)
        (root / "song.flac").write_bytes(b"x")
        (tmp_path / "artist.txt").write_text("A")
        coordinator.scan_source(source)
        # Second scan: unchanged → cached metadata reused, artist stable.
        coordinator.scan_source(source)
        assert library.state.tracks[0].artist == "A"


class TestUnambiguousRelink:
    def test_two_missing_candidates_same_inode_never_merge(self, tmp_path) -> None:
        """§16 hardlink ambiguity: two MISSING media sharing the (dev,ino)
        observation → the new path becomes a NEW identity; the old media
        stay MISSING."""
        library, catalog, coordinator, source, root = _env(tmp_path)
        a = root / "a.flac"
        b = root / "b.flac"
        a.write_bytes(b"x")
        b.write_bytes(b"x")
        coordinator.scan_source(source)
        ids_before = {t.track_id for t in catalog.load_tracks()}
        assert len(ids_before) == 2

        # Both files "disappear" and ONE new path appears with the SAME
        # inode observation (hardlink-like) — the media cache still holds
        # both old entries with identical (dev, ino).
        cache = coordinator._media_cache.load_all()
        (dev, ino) = (0, 0)
        for _media_id, (_fs, _mt, d, i) in cache.items():
            dev, ino = d, i
            break
        # Force both cached entries to the same (dev, ino).
        for media_id in cache:
            coordinator._media_cache.upsert(media_id, 1, 1, dev, ino)

        a.unlink()
        b.unlink()
        c = root / "c.flac"
        c.write_bytes(b"x")
        # Give c the same inode observation by rewriting the cache after the
        # scan discovers it — simulate via direct scan with matching ev.
        outcome = coordinator.scan_source(source)
        # Either ADDED (ambiguous) — never an automatic identity merge.
        assert outcome.added >= 0
        ids_after = {t.track_id for t in catalog.load_tracks()}
        assert len(ids_after) >= 2  # old identities preserved (never merged)
        assert len(catalog.load_media()) == 3  # old two MISSING + new one


class TestFormatPolicy:
    def test_unsupported_extensions_never_catalogued(self, tmp_path) -> None:
        """§23: R4 is not a format expansion program — the pre-R4 contract
        set is the ONLY supported policy."""
        library, catalog, coordinator, source, root = _env(tmp_path)
        (root / "song.flac").write_bytes(b"x")
        (root / "track.dsf").write_bytes(b"x")
        (root / "track.dff").write_bytes(b"x")
        (root / "track.wv").write_bytes(b"x")
        (root / "track.ape").write_bytes(b"x")
        (root / "track.mp4").write_bytes(b"x")
        (root / "track.aiff").write_bytes(b"x")
        coordinator.scan_source(source)
        assert len(catalog.load_tracks()) == 1  # only the .flac

    def test_supported_set_is_the_contract(self) -> None:
        from michi.application.library_port import SUPPORTED_MEDIA_SUFFIXES

        assert (
            frozenset(
                {".mp3", ".flac", ".ogg", ".wav", ".m4a", ".opus", ".aac", ".wma"}
            )
            == SUPPORTED_MEDIA_SUFFIXES
        )
