"""M6-EXT-R4 TRUE FINAL FREEZE — adversarial KILLCRITIC seal.

Owns the adversarial evidence for THIS seal:

    P1-01 source configuration ABA          (root / enabled / lifecycle / old error)
    P1-02 cancel-after-compute linearization (owner-side rejection)
    P1-03 Favorite TrackId bridge slot      (canonical identity intent)
    P1-04 disabled/retired never enter async worker
    P1-05 membership truth vs search-filtered view projection

Plus the bounded P2 hygiene:

    truthful plan immutability
    truthful progress (processed == reconciled, not enumerated)
    stale-without-replacement is never reported COMPLETED

No time.sleep() anywhere: every race is reproduced with a manual pipeline,
a held work result and delayed cancel acknowledgment — WORKER COMPUTATION
is always separated from OWNER COMPLETION.

New-Tests-Only governance: this file defines its OWN helpers; it never
imports private helpers from older test modules.
"""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from dataclasses import FrozenInstanceError

import pytest

from michi.application.library_port import LibraryFilesystemError
from michi.application.library_service import LibraryService
from michi.application.ports import LibraryPrefsPort, ScanCancelled, ScanCancelToken
from michi.application.source_scan_lifecycle import SourceScanLifecycle
from michi.domain.library import LibraryDiagnosticCode, LibraryPrefs
from michi.domain.library_catalog import (
    LibrarySource,
    SourceAvailability,
    new_library_source_id,
)
from michi.infrastructure.filesystem_source_scanner import (
    FilesystemLibrarySourceScanner,
)
from michi.infrastructure.library_catalog import SqliteLibraryCatalogRepository
from michi.infrastructure.library_media_cache import SqliteLibraryMediaCache
from michi.presentation.library_bridge import LibraryBridge


class _StubPrefs(LibraryPrefsPort):
    def load(self) -> LibraryPrefs:
        return LibraryPrefs()

    def save(self, prefs: LibraryPrefs) -> None:
        del prefs


class _Progress:
    def __init__(self, phase="", total=0, processed=0, current_path=""):
        self.phase = phase
        self.total = total
        self.processed = processed
        self.current_path = current_path


class _ManualPipeline:
    """Deterministic controlled pipeline (no threads). cancel() ACKS by
    delivering ScanCancelled — the safe (non-racing) path."""

    def __init__(self):
        self.submissions = []
        self.cancelled = []

    def submit(self, generation, work, on_progress, on_done):
        self.submissions.append((generation, work, on_progress, on_done))

    def cancel(self, generation):
        self.cancelled.append(generation)
        for submitted in self.submissions:
            if submitted[0] == generation:
                submitted[3](generation, None, ScanCancelled())
                return


class _DelayedCancelPipeline(_ManualPipeline):
    """Cancel is REQUESTED but NOT acknowledged: the racing completion may
    arrive before the acknowledgment — the dangerous owner-side window."""

    def cancel(self, generation):
        self.cancelled.append(generation)
        # Deliberately DO NOT invoke on_done.


class _CountingScanner(FilesystemLibrarySourceScanner):
    """Counts every filesystem discovery attempt."""

    def __init__(self):
        super().__init__()
        self.discover_calls = 0

    def discover(self, source):
        self.discover_calls += 1
        return super().discover(source)


class _ProbeExtractor:
    """Inspects the SAME worker-local progress object during extraction."""

    def __init__(self, progress):
        self._progress = progress
        self.seen = []  # (processed, phase) at extraction time

    def extract(self, file_path):
        self.seen.append((self._progress.processed, self._progress.phase))
        from michi.domain.library import TrackMetadata

        return TrackMetadata(title=Path(file_path).stem, duration_ms=1000)


def _source(tmp_path, name, enabled=True):
    root = tmp_path / name
    root.mkdir(exist_ok=True)
    return LibrarySource(
        library_source_id=new_library_source_id(),
        display_name=name,
        root_path=str(root),
        enabled=enabled,
    )


def _env(tmp_path, scanner=None, extractor=None):
    db_path = tmp_path / "michi.db"
    catalog = SqliteLibraryCatalogRepository(db_path)
    library = LibraryService(
        scanner or FilesystemLibrarySourceScanner(), library_prefs=_StubPrefs()
    )
    from michi.application.source_scan_coordinator import SourceScanCoordinator

    coordinator = SourceScanCoordinator(
        library,
        catalog,
        scanner or FilesystemLibrarySourceScanner(),
        media_cache=SqliteLibraryMediaCache(db_path),
        metadata_extractor=extractor,
    )
    return library, catalog, coordinator, db_path


def _seed_track(source, relative="song.flac"):
    """A real track file inside the source root (flac-agnostic: the fake
    fingerprint tolerates any bytes)."""
    track_path = Path(source.root_path) / relative
    track_path.write_bytes(b"x")
    return track_path


def _plan_after_worker(pipeline):
    """The DANGEROUS race pattern: worker computation FINISHES but the
    owner has NOT received the result. Returns (generation, plan, done)."""
    generation, work, _, done = pipeline.submissions[0]
    progress = _Progress()
    plan = work(progress, ScanCancelToken(), lambda: None)
    return generation, plan, done, progress


# ==========================================================================
# P1-01 — SOURCE CONFIGURATION ABA
# ==========================================================================


class TestSourceConfigAbA:
    def test_root_aba_rejects_old_plan_even_when_fields_match_again(
        self,
        tmp_path,
    ) -> None:
        """A₁ → B → A₂: the old plan's fields match the CURRENT source
        again, but the plan belongs to A₁. Epoch authority must drop it."""
        library, catalog, coordinator, _ = _env(tmp_path)
        source = _source(tmp_path, "a")
        stale = _seed_track(source, "stale.flac")
        catalog.upsert_source(source)
        coordinator.list_sources()  # refresh the in-memory source cache

        pipeline = _ManualPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_source(source.library_source_id)
        generation, plan, done, _ = _plan_after_worker(pipeline)
        assert plan is not None

        # A → B → A while the owner still holds the old plan.
        stale.unlink()  # A now represents a NEW filesystem truth
        b_root = tmp_path / "b"
        b_root.mkdir(exist_ok=True)
        coordinator.relocate_source_root(source.library_source_id, str(b_root))
        coordinator.relocate_source_root(source.library_source_id, str(tmp_path / "a"))

        done(generation, plan, None)

        assert catalog.load_tracks() == ()
        assert coordinator.source_config_epoch(source.library_source_id) == 2
        assert plan.source_config_epoch != coordinator.source_config_epoch(
            source.library_source_id
        )

    def test_enabled_aba_rejects_old_plan(self, tmp_path) -> None:
        """enabled True → False → True: structural values match again but
        the epoch differs — no commit, no observation from the old plan."""
        library, catalog, coordinator, _ = _env(tmp_path)
        source = _source(tmp_path, "a")
        _seed_track(source)
        catalog.upsert_source(source)
        coordinator.list_sources()

        pipeline = _ManualPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_source(source.library_source_id)
        generation, plan, done, _ = _plan_after_worker(pipeline)
        assert plan is not None

        coordinator.set_source_enabled(source.library_source_id, False)
        coordinator.set_source_enabled(source.library_source_id, True)

        done(generation, plan, None)

        assert catalog.load_tracks() == ()
        assert plan.source_config_epoch != coordinator.source_config_epoch(
            source.library_source_id
        )

    def test_lifecycle_aba_rejects_old_plan(self, tmp_path) -> None:
        """ACTIVE → RETIRED → ACTIVE: same root/enabled/lifecycle values
        again, but the old plan must not commit."""
        library, catalog, coordinator, _ = _env(tmp_path)
        source = _source(tmp_path, "a")
        _seed_track(source)
        catalog.upsert_source(source)
        coordinator.list_sources()

        pipeline = _ManualPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_source(source.library_source_id)
        generation, plan, done, _ = _plan_after_worker(pipeline)
        assert plan is not None

        coordinator.retire_source(source.library_source_id)
        coordinator.reactivate_source(source.library_source_id)

        done(generation, plan, None)

        assert catalog.load_tracks() == ()
        assert plan.source_config_epoch != coordinator.source_config_epoch(
            source.library_source_id
        )

    def test_old_error_cannot_poison_same_values_after_aba(self, tmp_path) -> None:
        """An old error describing config A₁ must NOT become the current
        availability when the values happen to match again after A→B→A."""
        library, catalog, coordinator, _ = _env(tmp_path)
        source = _source(tmp_path, "a")
        _seed_track(source)
        catalog.upsert_source(source)
        coordinator.list_sources()

        pipeline = _ManualPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_source(source.library_source_id)
        generation, _, _, _ = _plan_after_worker(pipeline)

        # A → B → A (both relocations refresh the in-memory records).
        b_root = tmp_path / "b"
        b_root.mkdir(exist_ok=True)
        coordinator.relocate_source_root(source.library_source_id, str(b_root))
        coordinator.relocate_source_root(source.library_source_id, str(tmp_path / "a"))

        old_error = LibraryFilesystemError(
            LibraryDiagnosticCode.DIRECTORY_MISSING,
            Path(source.root_path),
            "old observation",
        )
        pipeline.submissions[0][3](generation, None, old_error)

        assert (
            coordinator.observed_availability(source.library_source_id)
            is SourceAvailability.UNKNOWN
        )


# ==========================================================================
# P1-02 — CANCEL AFTER COMPUTE / BEFORE OWNER COMMIT
# ==========================================================================


class TestCancelLinearization:
    def test_cancel_after_worker_success_before_owner_done_never_commits(
        self,
        tmp_path,
    ) -> None:
        """Worker SUCCESS already exists; owner Cancel lands before
        done(). The owner-side rejection must make the generation
        non-committable."""
        library, catalog, coordinator, _ = _env(tmp_path)
        source = _source(tmp_path, "a")
        _seed_track(source)
        catalog.upsert_source(source)
        coordinator.list_sources()

        pipeline = _DelayedCancelPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_source(source.library_source_id)
        generation, plan, done, _ = _plan_after_worker(pipeline)
        assert plan is not None

        lifecycle.cancel()  # requested, NOT acknowledged by the pipeline

        done(generation, plan, None)

        assert catalog.load_tracks() == ()
        assert lifecycle.state.last_terminal_status == "CANCELLED"

    def test_stale_without_replacement_is_not_reported_completed(
        self,
        tmp_path,
    ) -> None:
        """A superseded scan (invalidate) with no replacement run must not
        report a false COMPLETED — stale terminal truth is CANCELLED."""
        library, catalog, coordinator, _ = _env(tmp_path)
        source = _source(tmp_path, "a")
        _seed_track(source)
        catalog.upsert_source(source)
        coordinator.list_sources()

        pipeline = _DelayedCancelPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_source(source.library_source_id)
        generation, plan, done, _ = _plan_after_worker(pipeline)
        assert plan is not None

        lifecycle.invalidate_source(source.library_source_id)

        done(generation, plan, None)

        assert catalog.load_tracks() == ()
        assert lifecycle.state.last_terminal_status == "CANCELLED"


# ==========================================================================
# P1-04 — DISABLED / RETIRED NEVER ENTER THE ASYNC WORKER
# ==========================================================================


class TestInactiveSourceNoWorker:
    def test_disabled_source_never_submits_worker(self, tmp_path) -> None:
        library, catalog, coordinator, _ = _env(tmp_path)
        scanner = _CountingScanner()
        library, catalog, coordinator, _ = _env(tmp_path, scanner=scanner)
        source = _source(tmp_path, "a", enabled=False)
        catalog.upsert_source(source)
        coordinator.list_sources()

        pipeline = _ManualPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_source(source.library_source_id)

        assert pipeline.submissions == []
        assert scanner.discover_calls == 0

    def test_retired_source_never_submits_worker(self, tmp_path) -> None:
        scanner = _CountingScanner()
        library, catalog, coordinator, _ = _env(tmp_path, scanner=scanner)
        source = _source(tmp_path, "a")
        catalog.upsert_source(source)
        coordinator.retire_source(source.library_source_id)

        pipeline = _ManualPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_source(source.library_source_id)

        assert pipeline.submissions == []
        assert scanner.discover_calls == 0

    def test_relocate_retired_updates_root_but_does_not_scan(self, tmp_path) -> None:
        """Relocating a RETIRED source updates its configured root but does
        NOT scan until Restore reactivates it."""
        scanner = _CountingScanner()
        library, catalog, coordinator, _ = _env(tmp_path, scanner=scanner)
        source = _source(tmp_path, "a")
        catalog.upsert_source(source)
        coordinator.retire_source(source.library_source_id)

        b_root = tmp_path / "b"
        b_root.mkdir(exist_ok=True)
        relocated = coordinator.relocate_source_root(
            source.library_source_id, str(b_root)
        )
        assert relocated.root_path == str(b_root)
        assert scanner.discover_calls == 0

        pipeline = _ManualPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_source(source.library_source_id)
        assert pipeline.submissions == []
        assert scanner.discover_calls == 0

        coordinator.reactivate_source(source.library_source_id)
        lifecycle.request_scan_source(source.library_source_id)
        assert len(pipeline.submissions) == 1
        assert scanner.discover_calls == 0  # worker not run yet — only submitted


# ==========================================================================
# P1-03 — FAVORITE TRACKID BRIDGE SLOT
# ==========================================================================


class TestFavoriteTrackIdBridge:
    def _env_with_track(self, tmp_path):
        library, catalog, coordinator, _ = _env(tmp_path)
        source = _source(tmp_path, "a")
        _seed_track(source)
        catalog.upsert_source(source)
        coordinator.scan_source(source)
        track = library.state.tracks[0]
        return library, track

    def test_bridge_favorite_by_id_is_real_and_canonical(self, tmp_path) -> None:
        library, track = self._env_with_track(tmp_path)
        bridge = LibraryBridge(service=library)

        assert hasattr(bridge, "toggle_favorite_by_id")

        bridge.toggle_favorite_by_id(track.track_id)
        assert track.track_id in library.state.favorite_track_ids

        bridge.toggle_favorite_by_id(track.track_id)
        assert track.track_id not in library.state.favorite_track_ids

    def test_favorite_membership_is_not_search_filtered(self, tmp_path) -> None:
        library, track = self._env_with_track(tmp_path)
        bridge = LibraryBridge(service=library)

        bridge.toggle_favorite_by_id(track.track_id)
        assert track.track_id in library.state.favorite_track_ids

        # Activate a search that matches NOTHING.
        library.search("zzzz-no-match-zzzz")

        # MEMBERSHIP truth: the favorite id survives the search filter.
        assert track.track_id in bridge.favoriteTrackIds

        # VIEW projection: rows are search-filtered and may be empty.
        assert bridge.favoriteTrackRows == []

    def test_michi_track_table_uses_normalized_identity(self) -> None:
        """The modern track table must send normalized TrackId (or an
        explicit legacy-path:: token) — never a raw path masquerading as
        a TrackId, and never an empty id."""
        table = Path("src/michi/presentation/qml/media/MichiTrackTable.qml").read_text()
        assert "property var favoriteTrackIds: []" in table
        assert '"legacy-path::" + String(modelData.path)' in table
        assert "? String(modelData.trackId)" in table
        assert "onFavoriteToggled: root.favoriteRequested(trackId)" in table
        assert "onQueueRequested: root.queueRequested(trackId)" in table
        assert "root.selectionToggleRequested(trackId)" in table
        assert "root.trackActivated(trackId, modelData.path, index)" in table
        assert "onAddToPlaylistRequested: root.addToPlaylistRequested(trackId)" in table


# ==========================================================================
# P2 — TRUTHFUL IMMUTABILITY / PROGRESS
# ==========================================================================


class TestTruthfulHygiene:
    def test_plan_dataclass_is_truthfully_frozen(self) -> None:
        from michi.application.source_scan_coordinator import (
            SourceReconciliationPlan,
            _IndexEntry,
        )

        assert SourceReconciliationPlan.__dataclass_params__.frozen is True

        entry = _IndexEntry(track_id="t1", file_size=1, mtime_ns=2, metadata=None)
        with pytest.raises(FrozenInstanceError):
            entry.metadata = object()

    def test_source_progress_does_not_count_item_before_metadata_finishes(
        self,
        tmp_path,
    ) -> None:
        library, catalog, coordinator, _ = _env(
            tmp_path, extractor=_ProbeExtractor(None)
        )
        source = _source(tmp_path, "a")
        _seed_track(source)
        catalog.upsert_source(source)
        coordinator.list_sources()

        pipeline = _ManualPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_source(source.library_source_id)

        generation, work, _, _ = pipeline.submissions[0]
        progress = _Progress()
        probe = _ProbeExtractor(progress)
        coordinator._metadata_extractor = probe
        work(progress, ScanCancelToken(), lambda: None)

        # DURING extraction of the first item the item is NOT counted yet.
        assert probe.seen and probe.seen[0][0] == 0
        # AFTER full reconciliation the item IS counted.
        assert progress.processed == 1


class TestArtworkSingleProtocol:
    """TRUE FINAL FREEZE P2 — one safe production artwork protocol."""

    def test_playlist_service_has_no_legacy_store_calls(self) -> None:
        service_source = Path("src/michi/application/playlist_service.py").read_text()
        assert "store_cover(" not in service_source
        assert "store_hero(" not in service_source

    def test_playlist_service_uses_prepare_protocol(self) -> None:
        service_source = Path("src/michi/application/playlist_service.py").read_text()
        assert "prepare_cover(" in service_source
        assert "prepare_hero(" in service_source
        assert "delete_managed_asset(" in service_source
