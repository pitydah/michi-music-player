"""P1/PERF-LIB-12 R4 — bounded Application artwork-refresh lifecycle.

NOT a second Library authority. Structure (R4 FINAL RUNTIME TRUTH SEAL):

    owner schedule()
        ↓ immutable AlbumRef snapshot
        ↓ dedicated ThreadScanRunner + ScanRelay (own channel)
        ↓ WORKER: provider I/O ONLY → immutable {album_key: Artwork | None}
        ↓ owner handle_done(generation) gate
        ↓ cache.store/cache.invalidate (manifest mutation AFTER gate)
        ↓ library._artwork_paths + album.has_artwork + notify

The runner's per-submit callbacks are NOT the production completion
authority (ThreadScanRunner is relay-driven) — completion arrives through
the OWN relay connected to handle_done (P1-03). Cache manifest mutation
happens ONLY inside _apply after the generation gate (P1-04): a stale
worker can never alter manifest.json.
"""

import logging
from dataclasses import replace

from michi.application.ports import (
    ArtworkCachePort,
    ArtworkProviderPort,
    ScanCancelled,
)

logger = logging.getLogger(__name__)


class LibraryArtworkRefresh:
    """Generation-gated async artwork probing for the local Library."""

    def __init__(
        self,
        library,
        artwork_provider: ArtworkProviderPort | None,
        artwork_cache: ArtworkCachePort | None,
        runner=None,
    ) -> None:
        self._library = library
        self._provider = artwork_provider
        self._cache = artwork_cache
        self._runner = runner
        self._generation = 0

    # ------------------------------------------------------------- owner API

    def schedule(self) -> None:
        """Owner-thread entry: snapshot the CURRENT album set and probe on
        the worker. Supersedes any in-flight generation."""
        if self._provider is None or self._cache is None:
            return
        albums = tuple(self._library.state.albums)
        if not albums:
            return
        self._generation += 1
        generation = self._generation
        provider = self._provider

        def work(progress, token, report):
            del progress, report
            results: dict[str, object] = {}
            for album in albums:
                if token.cancelled:
                    raise ScanCancelled()
                artwork = None
                front_getter = getattr(provider, "get_embedded_front_artwork", None)
                if front_getter is not None:
                    for track_path in album.track_paths:
                        if token.cancelled:
                            raise ScanCancelled()
                        artwork = front_getter(track_path)
                        if artwork is not None:
                            break
                if artwork is None:
                    for track_path in album.track_paths:
                        if token.cancelled:
                            raise ScanCancelled()
                        artwork = provider.get_embedded_artwork(track_path)
                        if artwork is not None:
                            break
                if artwork is None and album.track_paths:
                    if token.cancelled:
                        raise ScanCancelled()
                    artwork = provider.get_local_artwork(album.track_paths[0].parent)
                # FACTS ONLY (P1-04): el worker NUNCA toca el manifest.
                results[album.key] = artwork
            return results

        # El runner es relay-driven: submit sin on_done; la completion llega
        # por el relay dedicado → handle_done (P1-03).
        self._runner.submit(generation, work, None, None)

    # --------------------------------------------------------- relay handler

    def handle_done(self, generation: int, result, error) -> None:
        """OWNER-thread completion (connected to the DEDICATED artwork
        relay, queued): the generation gate runs BEFORE any cache
        manifest mutation."""
        if generation != self._generation:
            return
        if error is not None or result is None:
            return
        self._apply(generation, result)

    # ------------------------------------------------------------- owner gate

    def _apply(self, generation: int, results: dict[str, object]) -> None:
        """OWNER gate: manifest mutation happens ONLY here, AFTER the
        generation check (P1-04). A stale generation is dropped before it
        can store/invalidate anything."""
        if generation != self._generation:
            return
        next_paths = dict(self._library._artwork_paths)
        for album_key, artwork in results.items():
            if artwork is None:
                # Veredicto negativo online confirmado → invalidación
                # persistente (solo aquí, tras el gate).
                invalidate = getattr(self._cache, "invalidate", None)
                if invalidate is not None:
                    invalidate(album_key)
                next_paths.pop(album_key, None)
                continue
            stored = self._cache.store(album_key, artwork)
            if stored is not None:
                next_paths[album_key] = stored
        # Solo keys presentes en la proyección ACTUAL (no resucitar albums).
        current_keys = {album.key for album in self._library.state.albums}
        next_paths = {
            key: value for key, value in next_paths.items() if key in current_keys
        }
        self._library._artwork_paths = next_paths
        updated = []
        for album in self._library.state.albums:
            updated.append(replace(album, has_artwork=album.key in next_paths))
        self._library.state.albums = tuple(updated)
        self._library._notify()
