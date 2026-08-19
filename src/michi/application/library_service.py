"""Library use case — owns LibraryState, coordinates scan and search."""

import logging
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from michi.application.library_port import (
    LibraryFilesystemError,
    LibraryScannerPort,
)
from michi.application.ports import (
    ArtworkCachePort,
    ArtworkProviderPort,
    LibraryIndexRepository,
    LibraryPrefsPort,
    MetadataExtractionError,
    MetadataExtractorPort,
    ScanCancelled,
    ScanCancelToken,
    ScanPipelinePort,
    ScanProgress,
)
from michi.application.queue_service import QueueService
from michi.domain.library import (
    HISTORY_CAP,
    RECENT_CAP,
    AlbumRef,
    LibraryDiagnostic,
    LibraryDiagnosticCode,
    LibraryPrefs,
    LibraryScanStatus,
    LibraryState,
    TrackMetadata,
    TrackRef,
    build_folder_model,
    build_music_model,
    merge_recently_added,
)
from michi.domain.library_index import (
    LibraryIndexEntry,
    ScanResult,
    classify_scan,
)

logger = logging.getLogger(__name__)


def _user_message(code, path=None, affected_count=0) -> str:
    """User-facing message for a library diagnostic code (spec §26)."""
    if code is LibraryDiagnosticCode.TRACK_MISSING:
        return f"File is no longer available: {path.name if path else ''}"
    if code is LibraryDiagnosticCode.DIRECTORY_MISSING:
        return f"Music directory is no longer available: {path}"
    if code is LibraryDiagnosticCode.ACCESS_FAILURE:
        return "Cannot access the library path."
    if code is LibraryDiagnosticCode.IO_FAILURE:
        return "The library filesystem reported an I/O error."
    if code is LibraryDiagnosticCode.UNKNOWN_FAILURE:
        return "The library path could not be validated."
    if code is LibraryDiagnosticCode.STALE_ENTRIES_REMOVED:
        return f"Removed {affected_count} unavailable file(s) from the library."
    return ""


class LibraryService:
    """Sole authority over LibraryState. Publishes changes."""

    def __init__(
        self,
        scanner: LibraryScannerPort,
        queue_service: QueueService,
        metadata_extractor: MetadataExtractorPort | None = None,
        artwork_provider: ArtworkProviderPort | None = None,
        artwork_cache: ArtworkCachePort | None = None,
        library_prefs: LibraryPrefsPort | None = None,
        library_index: LibraryIndexRepository | None = None,
        scan_pipeline: ScanPipelinePort | None = None,
    ) -> None:
        self._scanner = scanner
        self._queue = queue_service
        self._metadata_extractor = metadata_extractor
        self._artwork_provider = artwork_provider
        self._artwork_cache = artwork_cache
        self._artwork_paths: dict[str, Path] = {}
        self._state = LibraryState()
        self._subscribers: list[Callable[[], None]] = []
        self._library_prefs = library_prefs
        self._library_index = library_index
        self._scan_pipeline = scan_pipeline
        if library_prefs is not None:
            prefs = library_prefs.load()
            self._state.favorite_paths = prefs.favorite_paths
            self._state.history_paths = prefs.history_paths
            self._state.recently_added_paths = prefs.recently_added_paths
        queue_service.subscribe_changed(self._on_queue_changed)

    @property
    def state(self) -> LibraryState:
        return self._state

    def subscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _notify(self) -> None:
        for cb in self._subscribers:
            cb()

    def scan(self, directory: str) -> None:
        root = Path(directory)
        # Build the next state OUTSIDE the observable state (atomic commit):
        # any LibraryFilesystemError from scanner.scan OR scanner.fingerprint
        # lands on the SAME failure path — preserve state, set the
        # diagnostic, notify, return; nothing is assigned on failure.
        try:
            paths = self._scanner.scan(root)
            if self._library_index is not None:
                discovered = [(str(p), *self._scanner.fingerprint(p)) for p in paths]
                next_tracks, upserts, removed = self._incremental_tracks(
                    paths, discovered
                )
            else:
                next_tracks = [self._make_trackref(p) for p in paths]
                upserts, removed = (), ()
        except LibraryFilesystemError as exc:
            self._state.diagnostic = LibraryDiagnostic(
                code=exc.code,
                message=_user_message(exc.code, path=exc.path),
                path=exc.path,
            )
            self._notify()
            return
        # Durable index mutation on the OWNER thread (the sync path has no
        # generation race) inside a single transactional apply_delta, before
        # the atomic state commit.
        self._apply_index_delta(upserts, removed)
        # The commit block is shared with the async path (M6.4): the sync
        # scan() notifies once after the commit; the async _on_scan_done
        # notifies once with the terminal COMPLETED status.
        self._commit_scan_result(next_tracks, directory)
        self._notify()

    def _apply_index_delta(self, upserts, removed) -> None:
        """Durable index mutation (M6-PRODUCTION-INTEGRATION): ONLY called on
        the owner thread, ONLY after the generation gate (async path) and
        inside a single transactional apply_delta. The worker NEVER writes
        durable state — it only computes ScanResult deltas."""
        if self._library_index is None:
            return
        if upserts or removed:
            self._library_index.apply_delta(upserts, removed)

    def _commit_scan_result(self, next_tracks: list[TrackRef], directory: str) -> None:
        """Atomic commit of a successful scan result (M6.4): everything
        derived is computed BEFORE any state assignment; then a single
        assignment block. The caller owns the single notify."""
        previous_paths = {str(t.file_path) for t in self._state.tracks}
        removed = {t.file_path for t in self._state.tracks} - {
            t.file_path for t in next_tracks
        }
        same_dir = self._state.current_directory == directory
        model = build_music_model(next_tracks)
        next_albums = self._enrich_albums(model.albums)
        next_folders = build_folder_model(next_tracks)
        new_paths = [
            str(t.file_path)
            for t in next_tracks
            if str(t.file_path) not in previous_paths
        ]
        self._state.tracks = next_tracks
        self._state.query = ""
        self._state.current_directory = directory
        self._state.albums = next_albums
        self._state.artists = model.artists
        self._state.genres = model.genres
        self._state.composers = model.composers
        self._state.folders = next_folders
        previous_recent = self._state.recently_added_paths
        self._state.recently_added_paths = merge_recently_added(
            new_paths,
            previous_recent,
            current_library_paths={str(t.file_path) for t in next_tracks},
            cap=RECENT_CAP,
        )
        if same_dir and removed:
            self._state.diagnostic = LibraryDiagnostic(
                code=LibraryDiagnosticCode.STALE_ENTRIES_REMOVED,
                message=_user_message(
                    LibraryDiagnosticCode.STALE_ENTRIES_REMOVED,
                    affected_count=len(removed),
                ),
                affected_count=len(removed),
            )
        else:
            self._state.diagnostic = None
        self._persist_prefs()

    def _incremental_tracks(self, paths, discovered):
        """Incremental M6.3 path: fingerprint -> classify -> extract ONLY
        added/modified; reuse the index metadata for unchanged. The durable
        upsert/remove delta is RETURNED (never written here) — the caller
        applies it via apply_delta on the owner thread (M6-PRODUCTION-
        INTEGRATION: the worker must never mutate durable state)."""
        known = {e.track_id: e for e in self._library_index.load_all()}
        classification = classify_scan(known, discovered)
        added_ids = set(classification.added)
        modified_ids = set(classification.modified)
        track_refs: list[TrackRef] = []
        upserts: list[LibraryIndexEntry] = []
        for track_id, file_size, mtime_ns in discovered:
            path = Path(track_id)
            if track_id in added_ids or track_id in modified_ids:
                meta = self._extract_meta(path)
                ref = self._trackref_from_metadata(path, meta)
                upserts.append(LibraryIndexEntry(track_id, file_size, mtime_ns, meta))
            else:
                entry = known[track_id]
                ref = self._trackref_from_metadata(path, entry.metadata)
            track_refs.append(ref)
        return track_refs, tuple(upserts), classification.removed

    def start_scan(self, directory: str) -> None:
        """Async scan entry (M6.4): the heavy work runs off the UI thread via
        the scan pipeline; the commit happens on the owner thread. Without a
        pipeline this falls back to the synchronous scan() — and the sync
        path never touches the scan-state contract."""
        if self._scan_pipeline is None:
            self.scan(directory)
            return
        generation = self._state.scan_generation + 1
        self._state.scan_generation = generation
        self._state.scan_status = LibraryScanStatus.DISCOVERING
        self._state.scan_processed = 0
        self._state.scan_total = 0
        self._state.scan_progress = None
        self._state.scan_current_path = None
        self._notify()
        self._scan_pipeline.submit(
            generation,
            self._build_scan_work(directory),
            lambda progress: self._on_scan_progress(generation, progress),
            lambda gen, result, error: self._on_scan_done(gen, result, error),
        )

    def cancel_scan(self) -> None:
        if self._scan_pipeline is not None:
            self._scan_pipeline.cancel(self._state.scan_generation)

    def _build_scan_work(self, directory: str):
        return lambda progress, token, report: self._run_scan_work(
            directory, progress, token, report
        )

    def _run_scan_work(
        self,
        directory,
        progress: ScanProgress,
        token: ScanCancelToken,
        report,
    ) -> ScanResult:
        """The heavy scan work (runs on the worker thread). Discovering ->
        indexing (fingerprints + classify) -> extracting (per track: token
        check, extraction, progress report). The COMMIT phase happens on the
        owner thread."""
        progress.phase = "DISCOVERING"
        root = Path(directory)
        paths = self._scanner.scan(root)  # LibraryFilesystemError propagates
        if self._library_index is not None:
            progress.phase = "INDEXING"
            discovered = [(str(p), *self._scanner.fingerprint(p)) for p in paths]
            known = {e.track_id: e for e in self._library_index.load_all()}
            classification = classify_scan(known, discovered)
            added_ids = set(classification.added)
            modified_ids = set(classification.modified)
            progress.phase = "EXTRACTING"
            progress.total = len(discovered)
            progress.processed = 0
            track_refs = []
            upserts = []
            for track_id, file_size, mtime_ns in discovered:
                if token.cancelled:
                    raise ScanCancelled()
                progress.current_path = track_id
                progress.processed += 1
                path = Path(track_id)
                if track_id in added_ids or track_id in modified_ids:
                    meta = self._extract_meta(path)
                    track_refs.append(self._trackref_from_metadata(path, meta))
                    upserts.append(
                        LibraryIndexEntry(track_id, file_size, mtime_ns, meta)
                    )
                else:
                    entry = known[track_id]
                    track_refs.append(
                        self._trackref_from_metadata(path, entry.metadata)
                    )
                report()
            # M6-PRODUCTION-INTEGRATION: the worker ONLY computes — the
            # durable apply_delta happens on the owner thread AFTER the
            # generation gate in _on_scan_done.
            return ScanResult(
                tracks=tuple(track_refs),
                upserts=tuple(upserts),
                removed=classification.removed,
                directory=directory,
            )
        # No index: the full-scan extraction with the same discipline.
        progress.phase = "EXTRACTING"
        progress.total = len(paths)
        progress.processed = 0
        track_refs = []
        for p in paths:
            if token.cancelled:
                raise ScanCancelled()
            progress.current_path = str(p)
            progress.processed += 1
            track_refs.append(self._make_trackref(p))
            report()
        return ScanResult(tracks=tuple(track_refs), directory=directory)

    def _extract_meta(self, path: Path) -> TrackMetadata:
        if self._metadata_extractor is None:
            return TrackMetadata(title=path.stem)
        try:
            return self._metadata_extractor.extract(path)
        except MetadataExtractionError as exc:
            logger.warning("Metadata extraction failed for %s: %s", path, exc)
            return TrackMetadata(title=path.stem)

    def _on_scan_progress(self, generation: int, progress: ScanProgress) -> None:
        if generation != self._state.scan_generation:
            return  # stale generation: never touch the observable state
        phase = progress.phase
        if phase == "DISCOVERING":
            self._state.scan_status = LibraryScanStatus.DISCOVERING
        elif phase == "INDEXING":
            self._state.scan_status = LibraryScanStatus.INDEXING
        elif phase == "EXTRACTING":
            self._state.scan_status = LibraryScanStatus.EXTRACTING
        self._state.scan_processed = progress.processed
        self._state.scan_total = progress.total
        self._state.scan_progress = (
            progress.processed / progress.total if progress.total > 0 else None
        )
        self._state.scan_current_path = progress.current_path
        self._notify()

    def _on_scan_done(
        self,
        generation: int,
        result: ScanResult | None,
        error: BaseException | None,
    ) -> None:
        if generation != self._state.scan_generation:
            return  # stale generation NEVER commits
        if isinstance(error, ScanCancelled):
            self._state.scan_status = LibraryScanStatus.CANCELLED
            self._notify()
            return
        if isinstance(error, LibraryFilesystemError):
            self._state.scan_status = LibraryScanStatus.FAILED
            self._state.diagnostic = LibraryDiagnostic(
                code=error.code,
                message=_user_message(error.code, path=error.path),
                path=error.path,
            )
            self._notify()
            return
        if error is not None:
            self._state.scan_status = LibraryScanStatus.FAILED
            self._notify()
            return
        self._state.scan_status = LibraryScanStatus.COMMITTING
        # Durable index mutation ONLY after the generation gate (the worker
        # only computed; the commit path owns the durable state) — a stale
        # generation can never write SQLite.
        self._apply_index_delta(result.upserts, result.removed)
        self._commit_scan_result(list(result.tracks), result.directory)
        self._state.scan_status = LibraryScanStatus.COMPLETED
        self._notify()

    def handle_scan_progress(self, generation: int, progress: ScanProgress) -> None:
        """Owner-thread entry point (M6-PRODUCTION-INTEGRATION): called by
        the LibraryScanDispatcher from the GUI thread."""
        self._on_scan_progress(generation, progress)

    def handle_scan_done(
        self,
        generation: int,
        result: ScanResult | None,
        error: BaseException | None,
    ) -> None:
        """Owner-thread entry point (M6-PRODUCTION-INTEGRATION): called by
        the LibraryScanDispatcher from the GUI thread."""
        self._on_scan_done(generation, result, error)

    def _make_trackref(self, file_path: Path) -> TrackRef:
        if self._metadata_extractor is None:
            return TrackRef(file_path=file_path)
        try:
            meta: TrackMetadata = self._metadata_extractor.extract(file_path)
        except MetadataExtractionError as exc:
            logger.warning("Metadata extraction failed for %s: %s", file_path, exc)
            return TrackRef(file_path=file_path)
        return self._trackref_from_metadata(file_path, meta)

    def _trackref_from_metadata(self, file_path: Path, meta) -> TrackRef:
        return TrackRef(
            file_path=file_path,
            display_name=meta.title or file_path.stem,
            title=meta.title,
            artist=meta.artist,
            album=meta.album,
            duration_ms=meta.duration_ms,
            genre=meta.genre,
            year=meta.year,
            album_artist=meta.album_artist,
            track_number=meta.track_number,
            disc_number=meta.disc_number,
            composer=meta.composer,
            compilation=meta.compilation,
            sort_title=meta.sort_title,
            # M6-PRODUCTION-INTEGRATION: the canonical TrackRef retains the
            # technical carrier so runtime projections can show facts
            # (codec/container/sample rate/bit depth/channels/bitrate/size).
            codec=meta.codec,
            container=meta.container,
            sample_rate_hz=meta.sample_rate_hz,
            bit_depth=meta.bit_depth,
            channels=meta.channels,
            bitrate_bps=meta.bitrate_bps,
            file_size=meta.file_size,
        )

    def _enrich_albums(self, albums: tuple[AlbumRef, ...]) -> tuple[AlbumRef, ...]:
        """Mark albums with artwork (M6.5 + M6-PRODUCTION-INTEGRATION):
        PASS 1 — explicit FRONT cover from ANY album track (two-pass: a
        back cover on track 1 must never win over a front cover on track 2);
        PASS 2 — first embedded fallback in canonical track order;
        PASS 3 — local artwork from the first track's parent directory;
        PASS 4 — none (has_artwork stays False; the Michi fallback asset is
        RECLASSIFIED to M9 — documented, not silently dropped).

        ``_artwork_paths`` is REBUILT from scratch (atomic replace after the
        loop) so stale mappings are pruned when albums or their artwork
        disappear. The cache store + mapping happen exactly once, for
        whichever source resolved first. Without a provider or cache the
        albums are returned unchanged, i.e. has_artwork stays False
        (artwork absence is never an error)."""
        if self._artwork_provider is None or self._artwork_cache is None:
            return albums
        next_artwork_paths: dict[str, Path] = {}
        enriched = []
        for album in albums:
            artwork = None
            # PASS 1: explicit FRONT cover anywhere in the album.
            front_getter = getattr(
                self._artwork_provider, "get_embedded_front_artwork", None
            )
            if front_getter is not None:
                for track_path in album.track_paths:
                    artwork = front_getter(track_path)
                    if artwork is not None:
                        break
            # PASS 2: first embedded fallback in canonical track order.
            if artwork is None:
                for track_path in album.track_paths:
                    artwork = self._artwork_provider.get_embedded_artwork(track_path)
                    if artwork is not None:
                        break
            # PASS 3: local artwork from the first track's parent directory.
            if artwork is None and album.track_paths:
                artwork = self._artwork_provider.get_local_artwork(
                    album.track_paths[0].parent
                )
            # PASS 4: none (Michi fallback reclassified to M9).
            has_artwork = False
            if artwork is not None:
                stored_path = self._artwork_cache.store(album.key, artwork)
                if stored_path is not None:
                    next_artwork_paths[album.key] = stored_path
                    has_artwork = True
            enriched.append(replace(album, has_artwork=has_artwork))
        self._artwork_paths = next_artwork_paths  # atomic replace: stale pruned
        return tuple(enriched)

    def _rebuild_derived_library_state(self) -> None:
        """Recompute albums/artists/genres/folders from the canonical tracks
        and enrich albums with artwork. Called after ANY structural track
        mutation (successful scan, TRACK_MISSING removal, future mutations)."""
        model = build_music_model(self._state.tracks)
        self._state.albums = self._enrich_albums(model.albums)
        self._state.artists = model.artists
        self._state.genres = model.genres
        self._state.composers = model.composers
        self._state.folders = build_folder_model(self._state.tracks)

    def restore_directory_hint(self, directory: str) -> None:
        """Restore a persisted path as context. No scan. Idempotent."""
        if not directory:
            return
        if self._state.current_directory == directory:
            return
        self._state.current_directory = directory
        self._notify()

    def search(self, query: str) -> None:
        self._state.query = query.strip().lower()
        self._notify()

    def _persist_prefs(self) -> None:
        if self._library_prefs is not None:
            self._library_prefs.save(
                LibraryPrefs(
                    favorite_paths=self._state.favorite_paths,
                    history_paths=self._state.history_paths,
                    recently_added_paths=self._state.recently_added_paths,
                )
            )

    def toggle_favorite(self, file_path) -> None:
        key = str(Path(file_path))
        updated = set(self._state.favorite_paths)
        if key in updated:
            updated.discard(key)
        else:
            updated.add(key)
        new_tuple = tuple(sorted(updated))
        if new_tuple == self._state.favorite_paths:
            return
        self._state.favorite_paths = new_tuple
        self._persist_prefs()
        self._notify()

    def set_favorite(self, file_path, favorite: bool) -> None:
        key = str(Path(file_path))
        updated = set(self._state.favorite_paths)
        if favorite:
            updated.add(key)
        else:
            updated.discard(key)
        new_tuple = tuple(sorted(updated))
        if new_tuple == self._state.favorite_paths:
            return
        self._state.favorite_paths = new_tuple
        self._persist_prefs()
        self._notify()

    def _on_queue_changed(self) -> None:
        current = self._queue.state.current_track
        if current is None:
            return
        path = str(current.file_path)
        if self._state.history_paths and self._state.history_paths[0] == path:
            return  # consecutive dedupe
        self._state.history_paths = (path, *self._state.history_paths)[:HISTORY_CAP]
        self._persist_prefs()
        self._notify()

    def activate(self, visible_index: int) -> None:
        tracks = self._state.visible_tracks
        if not (0 <= visible_index < len(tracks)):
            return
        self.activate_track(tracks[visible_index])

    def activate_track(self, track: TrackRef) -> None:
        """TD-013 activation contract for an exact TrackRef: validate the
        filesystem through the port BEFORE any queue mutation; TRACK_MISSING
        removes the exact reference; ACCESS/IO/UNKNOWN preserve it; success
        keeps the existing queue behavior."""
        try:
            self._scanner.validate_file(track.file_path)
        except LibraryFilesystemError as exc:
            if exc.code is LibraryDiagnosticCode.TRACK_MISSING:
                self._state.tracks = [t for t in self._state.tracks if t is not track]
                self._rebuild_derived_library_state()
                self._state.diagnostic = LibraryDiagnostic(
                    code=LibraryDiagnosticCode.TRACK_MISSING,
                    message=_user_message(
                        LibraryDiagnosticCode.TRACK_MISSING, path=track.file_path
                    ),
                    path=track.file_path,
                )
            else:
                self._state.diagnostic = LibraryDiagnostic(
                    code=exc.code,
                    message=_user_message(exc.code, path=track.file_path),
                    path=track.file_path,
                )
            self._notify()
            return
        was_empty = self._queue.state.count == 0
        self._queue.add(track.file_path, title=track.title or "")
        if was_empty:
            self._queue.play_index(0)

    def artwork_path_for(self, album_key: str) -> str | None:
        """Cached artwork path for an album key, or None when unavailable."""
        path = self._artwork_paths.get(album_key)
        return str(path) if path is not None else None

    def resolve_trackref(self, file_path: Path) -> TrackRef | None:
        """First TrackRef whose file_path equals ``file_path``, else None."""
        for t in self._state.tracks:
            if t.file_path == file_path:
                return t
        return None
