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
    make_artist_key,
    merge_recently_added,
)
from michi.domain.library_index import (
    LibraryIndexEntry,
    ScanResult,
    classify_scan,
)
from michi.domain.search import (
    SearchQuery,
    build_search_corpus,
    build_search_projection,
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
        *,
        metadata_extractor: MetadataExtractorPort | None = None,
        artwork_provider: ArtworkProviderPort | None = None,
        artwork_cache: ArtworkCachePort | None = None,
        library_prefs: LibraryPrefsPort | None = None,
        library_index: LibraryIndexRepository | None = None,
        scan_pipeline: ScanPipelinePort | None = None,
    ) -> None:
        self._scanner = scanner
        self._metadata_extractor = metadata_extractor
        self._artwork_provider = artwork_provider
        self._artwork_cache = artwork_cache
        self._artwork_paths: dict[str, Path] = {}
        self._state = LibraryState()
        self._search_corpus = None  # M7: derived corpus, rebuilt structurally
        self._subscribers: list[Callable[[], None]] = []
        self._library_prefs = library_prefs
        self._library_index = library_index
        self._scan_pipeline = scan_pipeline
        if library_prefs is not None:
            prefs = library_prefs.load()
            self._state.favorite_paths = prefs.favorite_paths
            self._state.history_paths = prefs.history_paths
            self._state.recently_added_paths = prefs.recently_added_paths

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
        for cb in list(self._subscribers):
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
        # M7: the RAW query SURVIVES successful scans — the active search
        # projection is rebuilt against the new canonical library below.
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
        # M7: the active query follows the NEW canonical library (never
        # stale) — the caller owns the single notify.
        self._rebuild_search_corpus()

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
        for path_str, file_size, mtime_ns in discovered:
            path = Path(path_str)
            if path_str in added_ids or path_str in modified_ids:
                meta = self._extract_meta(path)
                ref = self._trackref_from_metadata(path, meta)
                upserts.append(LibraryIndexEntry(path_str, file_size, mtime_ns, meta))
            else:
                entry = known[path_str]
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
            for path_str, file_size, mtime_ns in discovered:
                if token.cancelled:
                    raise ScanCancelled()
                progress.current_path = path_str
                progress.processed += 1
                path = Path(path_str)
                if path_str in added_ids or path_str in modified_ids:
                    meta = self._extract_meta(path)
                    track_refs.append(self._trackref_from_metadata(path, meta))
                    upserts.append(
                        LibraryIndexEntry(path_str, file_size, mtime_ns, meta)
                    )
                else:
                    entry = known[path_str]
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

    def _trackref_from_metadata(
        self,
        file_path: Path,
        meta: TrackMetadata,
        *,
        track_id: str = "",
        media_file_id: str = "",
        library_source_id: str = "",
    ) -> TrackRef:
        """Project TrackMetadata onto a TrackRef with FULL carrier parity
        (M6-EXT-R4-E: totals/date/sort fields are never dropped) plus the
        stable catalog identities when the caller knows them."""
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
            track_total=meta.track_total,
            disc_number=meta.disc_number,
            disc_total=meta.disc_total,
            composer=meta.composer,
            date=meta.date,
            compilation=meta.compilation,
            sort_title=meta.sort_title,
            sort_artist=meta.sort_artist,
            sort_album=meta.sort_album,
            sort_album_artist=meta.sort_album_artist,
            codec=meta.codec,
            container=meta.container,
            sample_rate_hz=meta.sample_rate_hz,
            bit_depth=meta.bit_depth,
            channels=meta.channels,
            bitrate_bps=meta.bitrate_bps,
            file_size=meta.file_size,
            track_id=track_id,
            media_file_id=media_file_id,
            library_source_id=library_source_id,
        )

    def _enrich_albums(
        self, albums: tuple[AlbumRef, ...], *, offline: bool = False
    ) -> tuple[AlbumRef, ...]:
        """Mark albums with artwork (M6.5 + M6-PRODUCTION-INTEGRATION +
        M6-EXT-R4-M):
        PASS 0 — persisted cache lookup: PROVISIONAL cached cover renders
        immediately; PASS 1 — explicit FRONT cover from ANY album track;
        PASS 2 — first embedded fallback in canonical track order;
        PASS 3 — local artwork from the first track's parent directory;
        PASS 4 — none (has_artwork stays False; the Michi fallback asset is
        RECLASSIFIED to M9 — documented, not silently dropped).

        ONLINE (scan): the provider verdict wins — a healthy source whose
        artwork is corrupt/untagged drops the stale cached cover (golden
        degradation contract). OFFLINE (hydration): a valid cached cover is
        kept — never blank a cached cover because the source is unreachable.

        ``_artwork_paths`` is REBUILT from scratch (atomic replace after the
        loop) so stale mappings are pruned when albums or their artwork
        disappear."""
        if self._artwork_cache is None:
            return albums
        cache_lookup = getattr(self._artwork_cache, "lookup", None)
        next_artwork_paths: dict[str, Path] = {}
        enriched = []
        for album in albums:
            # PASS 0: provisional cached cover (renders instantly).
            cached = cache_lookup(album.key) if cache_lookup is not None else None
            if cached is not None:
                next_artwork_paths[album.key] = cached
            artwork = None
            # Provider passes only when the source is reachable; the
            # extractor never raises (returns None honestly on failure).
            if self._artwork_provider is not None:
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
                        artwork = self._artwork_provider.get_embedded_artwork(
                            track_path
                        )
                        if artwork is not None:
                            break
                # PASS 3: local artwork from the first track's parent dir.
                if artwork is None and album.track_paths:
                    artwork = self._artwork_provider.get_local_artwork(
                        album.track_paths[0].parent
                    )
            # PASS 4: fresh artwork wins. Online with no artwork found → the
            # stale cached cover is dropped (source speaks: corrupt/untagged).
            # Offline → the valid cached cover stays (never blank).
            has_artwork = cached is not None
            if artwork is not None:
                stored_path = self._artwork_cache.store(album.key, artwork)
                if stored_path is not None:
                    next_artwork_paths[album.key] = stored_path
                    has_artwork = True
            elif cached is not None and not offline:
                next_artwork_paths.pop(album.key, None)
                has_artwork = False
            enriched.append(replace(album, has_artwork=has_artwork))
        self._artwork_paths = next_artwork_paths  # atomic replace: stale pruned
        return tuple(enriched)

    def _rebuild_derived_library_state(self, *, offline: bool = False) -> None:
        """Recompute albums/artists/genres/folders from the canonical tracks
        and enrich albums with artwork. Called after ANY structural track
        mutation (successful scan, TRACK_MISSING removal, hydration).

        ``offline`` (M6-EXT-R4-M): hydration keeps valid cached covers;

        online scans honor the provider verdict (corrupt art drops)."""
        model = build_music_model(self._state.tracks)
        self._state.albums = self._enrich_albums(model.albums, offline=offline)
        self._state.artists = model.artists
        self._state.genres = model.genres
        self._state.composers = model.composers
        self._state.folders = build_folder_model(self._state.tracks)
        # M7: the search corpus + active projection follow the new canonical
        # model (structural mutation chokepoint).
        self._rebuild_search_corpus()

    def restore_directory_hint(self, directory: str) -> None:
        """Restore a persisted path as context. No scan. Idempotent."""
        if not directory:
            return
        if self._state.current_directory == directory:
            return
        self._state.current_directory = directory
        self._notify()

    def search(self, query: str) -> None:
        """M7: set the RAW query (presentation form preserved verbatim) and
        project the pre-normalized corpus. Never mutates the canonical
        model — search is a deterministic derived projection."""
        self._state.query = query or ""
        self._apply_query_projection()
        self._notify()

    def clear_search(self) -> None:
        """M7: deactivate search and restore the canonical collections."""
        self._state.query = ""
        self._state.search_projection = None
        self._notify()

    def _apply_query_projection(self) -> None:
        """Score the EXISTING corpus against the current query (cheap;
        the corpus is rebuilt only on structural change)."""
        if self._search_corpus is None:
            self._rebuild_search_corpus()
            return
        query = SearchQuery.from_raw(self._state.query)
        if query.active:
            self._state.search_projection = build_search_projection(
                query, self._search_corpus
            )
        else:
            self._state.search_projection = None

    def _rebuild_search_corpus(self) -> None:
        """Centralized search refresh (M7.5): rebuild the derived corpus
        from the canonical model and keep the active projection in sync.
        Called after EVERY structural mutation (scan commit, track
        removal) — an active query always follows the NEW canonical
        library; stale results are impossible."""
        self._search_corpus = build_search_corpus(
            self._state.tracks,
            self._state.albums,
            self._state.artists,
            self._state.genres,
            self._state.composers,
        )
        self._apply_query_projection()

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

    def record_history(self, path: Path) -> None:
        """Record a HISTORY entry for a path that was ACCEPTED as a new
        playback session commit. Owns history_paths, consecutive dedupe,
        HISTORY_CAP, persistence and notification. It does NOT decide WHEN
        playback happened (PlaybackHistoryCoordinator owns that).

        LEGACY path surface: new code prefers ``record_history_for_track``
        so History is keyed by stable TrackId (M6-EXT-R4-J)."""
        key = str(Path(path))
        if self._state.history_paths and self._state.history_paths[0] == key:
            return  # consecutive dedupe
        self._state.history_paths = (key, *self._state.history_paths)[:HISTORY_CAP]
        self._persist_prefs()
        self._notify()

    def record_history_for_track(self, track_id: str) -> None:
        """Record HISTORY by stable TrackId (M6-EXT-R4-J canonical).

        Resolves the current path projection; a track that is not in the
        library records nothing (no invented library history identity)."""
        ref = self.trackref_by_id(track_id)
        if ref is None:
            return
        self.record_history(ref.file_path)

    def trackref_by_id(self, track_id: str) -> TrackRef | None:
        """Canonical TrackRef by stable identity, or None (M6-EXT-R4-J)."""
        if not track_id:
            return None
        for ref in self._state.tracks:
            if ref.track_id == track_id:
                return ref
        return None

    def note_new_track_ids(self, track_ids: tuple[str, ...]) -> None:
        """M6-EXT-R4-K: recently-added semantics — ONLY new TrackId
        allocations enter Recently Added (never moves/relinks/modifies).
        Persists through the existing prefs surface (id-keyed upgrade lands
        with R4-G wiring)."""
        if not track_ids:
            return
        # The legacy prefs surface is path-keyed; new ids are recorded via
        # the recently-added path projection until the user-state
        # integration replaces it. Each new id maps to its current path.
        new_paths = []
        for track_id in track_ids:
            ref = self.trackref_by_id(track_id)
            if ref is not None:
                new_paths.append(str(ref.file_path))
        if not new_paths:
            return
        self._state.recently_added_paths = merge_recently_added(
            new_paths,
            self._state.recently_added_paths,
            current_library_paths={str(t.file_path) for t in self._state.tracks},
            cap=RECENT_CAP,
        )
        self._persist_prefs()
        self._notify()

    def apply_source_tracks(self, source_id: str, refs: list[TrackRef]) -> None:
        """M6-EXT-R4-K: replace ONLY this source's canonical TrackRefs and
        rebuild the derived model. Other sources survive untouched (a
        Source A scan can never remove Source B)."""
        kept = [t for t in self._state.tracks if t.library_source_id != source_id]
        self._state.tracks = kept + list(refs)
        self._rebuild_derived_library_state()
        self._notify()

    def resolve_trackref(self, file_path: Path) -> TrackRef | None:
        """Canonical TrackRef by current path, or None."""
        for ref in self._state.tracks:
            if ref.file_path == file_path:
                return ref
        return None

    def validate_track_for_playback(self, track: TrackRef) -> bool:
        """TD-013 filesystem validation (kept in LibraryService): TRACK_MISSING
        removes the exact stale reference / diagnostic; ACCESS/IO/UNKNOWN
        preserve the reference / diagnostic. Returns True only when the file
        is playable. The coordinator never becomes a filesystem service."""
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
            return False
        return True

    def visible_tracks(self) -> list[TrackRef]:
        """Current visible track list (generic lists projection)."""
        return list(self._state.visible_tracks)

    def album_by_key(self, album_key: str):
        """Canonical AlbumRef by key, or None."""
        for album in self._state.albums:
            if album.key == album_key:
                return album
        return None

    def artist_by_key(self, artist_key: str):
        """Canonical ArtistRef by key, or None (M6.9 Presentation reader)."""
        for artist in self._state.artists:
            if artist.key == artist_key:
                return artist
        return None

    def albums_for_artist(self, artist_key: str) -> tuple:
        """Canonical albums whose artist key matches (M6.9 Presentation reader)."""
        return tuple(
            album
            for album in self._state.albums
            if make_artist_key(album.artist) == artist_key
        )

    def tracks_for_artist(self, artist_key: str) -> tuple:
        """Canonical tracks whose TRACK ARTIST matches the artist key
        (M6.9 Presentation reader). The artist entity identity is the
        ``track.artist`` role — album_artist is a DIFFERENT semantic role
        (compilations keep their guest tracks under the track artist)."""
        return tuple(
            track
            for track in self._state.tracks
            if make_artist_key(track.artist.strip() or "Unknown Artist") == artist_key
        )

    def artwork_path_for(self, album_key: str) -> str | None:
        """Cached artwork path for an album key, or None when unavailable."""
        path = self._artwork_paths.get(album_key)
        return str(path) if path is not None else None
