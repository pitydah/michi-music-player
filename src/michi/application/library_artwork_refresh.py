"""P1/PERF-LIB-12 R4 — bounded single-flight Application artwork lifecycle.

ABSOLUTE FINAL RUNTIME SEAL structure:

    owner schedule()  (every structural event = new authority epoch,
                       INCLUDING zero-album transitions)
        ↓ immutable _AlbumArtworkSnapshot (album_key + membership signature
          + track_paths) — NEVER mutable library state
        ↓ dedicated ThreadScanRunner + ScanRelay + LibraryArtworkDispatcher
        ↓ WORKER: provider I/O ONLY → immutable _AlbumArtworkProbe facts
        ↓ owner handle_done(generation) gate
        ↓ _apply: generation → current album existence → CURRENT membership
          signature → ONLY THEN cache.store/cache.invalidate
        ↓ library._artwork_paths + album.has_artwork + notify

Single-flight: at most ONE active provider worker. New requests supersede
the active generation; ONLY the latest pending snapshot starts after the
active worker ends. shutdown() closes the lifecycle: late worker results
are inert (zero publication).
"""

import logging
from dataclasses import dataclass, replace
from pathlib import Path

from michi.application.ports import (
    ArtworkCachePort,
    ArtworkProviderPort,
    ScanCancelled,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _AlbumArtworkSnapshot:
    """Immutable evidence of what a worker generation observed."""

    album_key: str
    membership_signature: tuple[str, ...]
    track_paths: tuple[Path, ...]


@dataclass(frozen=True)
class _AlbumArtworkProbe:
    """Immutable worker fact: album_key + membership + probed artwork."""

    album_key: str
    membership_signature: tuple[str, ...]
    artwork: object | None


class LibraryArtworkRefresh:
    """Single-flight owner-gated async artwork probing for the local Library.

    NOT a second Library authority. Worker facts only; manifest mutation
    ONLY inside _apply after generation + membership gates.
    """

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
        # Lifecycle state (R4 ABSOLUTE FINAL SEAL):
        self._generation = 0  # latest REQUEST epoch
        self._active_generation: int | None = None  # worker submitted
        self._pending: tuple[int, tuple[_AlbumArtworkSnapshot, ...]] | None = (
            None  # latest superseding request
        )
        self._closed = False  # terminal lifecycle state

    # -------------------------------------------------------- membership

    @staticmethod
    def _membership_signature(album) -> tuple[str, ...]:
        """Canonical membership evidence: TrackIds first; path fallback ONLY
        for genuinely legacy AlbumRef carriers. Never Path(track_id)."""
        track_ids = tuple(
            str(track_id)
            for track_id in getattr(album, "track_ids", ())
            if str(track_id)
        )
        if track_ids:
            return track_ids
        return tuple(f"legacy-path::{path}" for path in album.track_paths)

    # -------------------------------------------------------- snapshots

    def _snapshot_albums(self) -> tuple[_AlbumArtworkSnapshot, ...]:
        return tuple(
            _AlbumArtworkSnapshot(
                album_key=album.key,
                membership_signature=self._membership_signature(album),
                track_paths=tuple(album.track_paths),
            )
            for album in self._library.state.albums
        )

    # -------------------------------------------------------- owner API

    def schedule(self) -> None:
        """Every structural refresh request gets a NEW authority epoch —
        INCLUDING a transition to ZERO albums (which invalidates old work)."""
        if self._closed:
            return
        if self._provider is None or self._cache is None or self._runner is None:
            return

        self._generation += 1
        generation = self._generation
        snapshots = self._snapshot_albums()

        # Latest-wins pending request (zero albums → no pending worker but
        # the epoch bump already invalidates any in-flight generation).
        self._pending = (generation, snapshots) if snapshots else None

        if self._active_generation is not None:
            # Cooperative optimization; correctness from generation gates.
            cancel = getattr(self._runner, "cancel", None)
            if cancel is not None:
                cancel(self._active_generation)
            return

        self._start_pending()

    def _start_pending(self) -> None:
        if self._closed:
            self._pending = None
            return
        if self._active_generation is not None:
            return
        if self._pending is None:
            return

        generation, snapshots = self._pending
        self._pending = None
        self._active_generation = generation

        provider = self._provider

        def work(progress, token, report):
            del progress, report
            probes: list[_AlbumArtworkProbe] = []
            for snapshot in snapshots:
                if token.cancelled:
                    raise ScanCancelled()
                artwork = None
                front_getter = getattr(provider, "get_embedded_front_artwork", None)
                if front_getter is not None:
                    for track_path in snapshot.track_paths:
                        if token.cancelled:
                            raise ScanCancelled()
                        artwork = front_getter(track_path)
                        if artwork is not None:
                            break
                if artwork is None:
                    for track_path in snapshot.track_paths:
                        if token.cancelled:
                            raise ScanCancelled()
                        artwork = provider.get_embedded_artwork(track_path)
                        if artwork is not None:
                            break
                if artwork is None and snapshot.track_paths:
                    if token.cancelled:
                        raise ScanCancelled()
                    artwork = provider.get_local_artwork(snapshot.track_paths[0].parent)
                probes.append(
                    _AlbumArtworkProbe(
                        album_key=snapshot.album_key,
                        membership_signature=snapshot.membership_signature,
                        artwork=artwork,
                    )
                )
            return tuple(probes)

        self._runner.submit(generation, work, None, None)

    # -------------------------------------------------------- completion

    def handle_done(self, generation: int, result, error) -> None:
        """OWNER completion. Late results after shutdown are inert."""
        if self._closed:
            return
        # Only the worker we currently own may complete the active slot.
        if generation != self._active_generation:
            return
        self._active_generation = None
        # Apply only if this active worker is STILL the latest authority.
        if generation == self._generation and error is None and result is not None:
            self._apply(generation, result)
        # If schedule() happened while running, start ONLY the latest
        # pending snapshot (coalescing: gen 6/7 → only 7 ever starts).
        self._start_pending()

    # ------------------------------------------------------------- owner gate

    def _apply(
        self,
        generation: int,
        probes: tuple[_AlbumArtworkProbe, ...],
    ) -> None:
        """Provenance order is NON-NEGOTIABLE:

        generation gate → current album existence → CURRENT membership
        signature → ONLY THEN cache.store/cache.invalidate.
        """
        if self._closed:
            return
        if generation != self._generation:
            return

        current_albums = {album.key: album for album in self._library.state.albums}
        current_keys = set(current_albums)
        next_paths = {
            key: value
            for key, value in self._library._artwork_paths.items()
            if key in current_keys
        }

        if isinstance(probes, dict):
            # Compatibilidad legacy (seal previo): {album_key: artwork} sin
            # membership — la membership del album ACTUAL es la evidencia
            # (el dict no transporta signature, el gate de generación ya
            # filtró lo estale).
            probes = tuple(
                _AlbumArtworkProbe(
                    album_key=key,
                    membership_signature=self._membership_signature(current_albums[key])
                    if key in current_albums
                    else (),
                    artwork=artwork,
                )
                for key, artwork in probes.items()
            )

        for probe in probes:
            current = current_albums.get(probe.album_key)
            # Album no longer exists — old evidence is void.
            if current is None:
                continue
            # Same key but DIFFERENT canonical membership — the old worker
            # observed a DIFFERENT album instance. AlbumKey alone is NOT
            # sufficient provenance.
            if self._membership_signature(current) != probe.membership_signature:
                continue
            if probe.artwork is None:
                invalidate = getattr(self._cache, "invalidate", None)
                if invalidate is not None:
                    invalidate(probe.album_key)
                next_paths.pop(probe.album_key, None)
                continue
            stored = self._cache.store(probe.album_key, probe.artwork)
            if stored is not None:
                next_paths[probe.album_key] = stored

        # One last structural prune.
        current_keys = {album.key for album in self._library.state.albums}
        next_paths = {
            key: value for key, value in next_paths.items() if key in current_keys
        }
        self._library._artwork_paths = next_paths
        self._library.state.albums = tuple(
            replace(
                album,
                has_artwork=album.key in next_paths,
            )
            for album in self._library.state.albums
        )
        self._library._notify()

    # ------------------------------------------------------------- shutdown

    def shutdown(self) -> None:
        """Close the lifecycle: invalidate every outstanding result. A late
        worker result after shutdown is harmless even if the provider was
        mid-I/O (handle_done sees _closed and publishes ZERO)."""
        if self._closed:
            return
        self._closed = True
        self._generation += 1
        self._pending = None
        active = self._active_generation
        self._active_generation = None
        if active is not None and self._runner is not None:
            cancel = getattr(self._runner, "cancel", None)
            if cancel is not None:
                cancel(active)
