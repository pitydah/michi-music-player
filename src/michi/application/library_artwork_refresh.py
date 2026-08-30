"""P1/PERF-LIB-12 — bounded Application artwork-refresh lifecycle.

NOT a second Library authority. Its ONLY responsibility:

    immutable AlbumRef snapshot
        ↓  WORKER: embedded/local artwork probing (cancellable, immutable)
        ↓  OWNER generation gate
        ↓  artwork cache/projection update + presentation notification

It NEVER writes TrackRecord / MediaFileRecord / LibrarySource / search
identity / user state. Generations coalesce: a stale artwork result can
never overwrite a newer Library projection.
"""

import logging
from dataclasses import replace
from pathlib import Path

from michi.application.ports import ArtworkCachePort, ArtworkProviderPort

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
        self._artwork_paths: dict[str, Path] = {}
        self._provider_calls: list[tuple[int, str]] = []

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
        cache = self._cache

        def work(progress, token, report):
            del progress, report
            results: dict[str, Path | None] = {}
            for album in albums:
                if token.cancelled:
                    from michi.application.ports import ScanCancelled

                    raise ScanCancelled()
                artwork = None
                front_getter = getattr(provider, "get_embedded_front_artwork", None)
                if front_getter is not None:
                    for track_path in album.track_paths:
                        artwork = front_getter(track_path)
                        if artwork is not None:
                            break
                if artwork is None:
                    for track_path in album.track_paths:
                        artwork = provider.get_embedded_artwork(track_path)
                        if artwork is not None:
                            break
                if artwork is None and album.track_paths:
                    artwork = provider.get_local_artwork(album.track_paths[0].parent)
                if artwork is not None:
                    stored = cache.store(album.key, artwork)
                    results[album.key] = stored
                else:
                    # ONLINE confirmed negative → persist invalidation.
                    invalidate = getattr(cache, "invalidate", None)
                    if invalidate is not None:
                        invalidate(album.key)
                    results[album.key] = None
            return results

        def on_done(generation_done, result, error) -> None:
            if generation_done != self._generation:
                return  # superseded: a stale artwork generation never wins
            if error is not None or result is None:
                return
            self._apply(generation_done, result)

        self._runner.submit(generation, work, None, on_done)

    # ------------------------------------------------------------- owner gate

    def _apply(self, generation: int, results: dict[str, Path | None]) -> None:
        """OWNER gate: merge confirmed artwork into the CURRENT projection
        (generation already checked by the caller)."""
        if generation != self._generation:
            return
        next_paths = dict(self._library._artwork_paths)
        for album_key, stored in results.items():
            if stored is not None:
                next_paths[album_key] = stored
            else:
                next_paths.pop(album_key, None)
        self._library._artwork_paths = next_paths
        # Re-project has_artwork on the CURRENT albums (cheap, no I/O).
        updated = []
        for album in self._library.state.albums:
            updated.append(replace(album, has_artwork=album.key in next_paths))
        self._library.state.albums = tuple(updated)
        self._library._notify()
