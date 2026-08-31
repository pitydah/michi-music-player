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

from michi.application.library_artwork_contracts import (
    ArtworkProbeVerdict,
    PreparedArtwork,
)
from michi.application.ports import (
    ArtworkCachePort,
    ArtworkProviderPort,
    ScanCancelled,
)
from michi.domain.library_catalog import (
    SourceAvailability,
    effective_availability,
    media_playback_blocked,
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
    """Immutable worker fact: album_key + membership + tri-state verdict
    (+ prepared blob para FOUND)."""

    album_key: str
    membership_signature: tuple[str, ...]
    verdict: ArtworkProbeVerdict
    prepared: PreparedArtwork | None = None
    # legacy compatibility only
    artwork: object | None = None


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
        *,
        album_probe=None,
        prepared_cache=None,
        source_availability_provider=None,
    ) -> None:
        self._library = library
        self._provider = artwork_provider
        self._cache = artwork_cache
        self._runner = runner
        # R4 artwork authority: production capabilities explícitas.
        # Los test doubles legacy no las proveen (compat path).
        self._album_probe = album_probe
        self._prepared_cache = prepared_cache
        self._source_availability_provider = source_availability_provider
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

    def _eligible_track_paths(self, album) -> tuple[Path, ...]:
        """R4 artwork authority: solo se tocan tracks cuyo Source está
        POSITIVAMENTE AVAILABLE. Un source visible desde cache NO es
        permiso para tocar su filesystem."""
        if self._source_availability_provider is None:
            # Legacy compatibility only.
            return tuple(album.track_paths)
        track_ids = tuple(
            str(track_id)
            for track_id in getattr(album, "track_ids", ())
            if str(track_id)
        )
        if not track_ids:
            # Legacy carrier sin provenance estable.
            return tuple(album.track_paths)
        paths: list[Path] = []
        for track_id in track_ids:
            ref = self._library.trackref_by_id(track_id)
            if ref is None:
                continue
            source_id = ref.library_source_id or ""
            if source_id:
                source_availability = self._source_availability_provider(source_id)
                # Artwork I/O es MÁS estricto que playback fallback: solo
                # un source positivamente AVAILABLE se proba.
                if source_availability is not SourceAvailability.AVAILABLE:
                    continue
                availability = effective_availability(
                    ref.availability, source_availability
                )
            else:
                availability = ref.availability
            if media_playback_blocked(availability):
                continue
            paths.append(ref.file_path)
        return tuple(paths)

    def _snapshot_albums(self) -> tuple[_AlbumArtworkSnapshot, ...]:
        snapshots = []
        for album in self._library.state.albums:
            paths = self._eligible_track_paths(album)
            if not paths:
                # no probe != no artwork — preserve cached artwork.
                continue
            snapshots.append(
                _AlbumArtworkSnapshot(
                    album_key=album.key,
                    membership_signature=self._membership_signature(album),
                    track_paths=paths,
                )
            )
        return tuple(snapshots)

    # -------------------------------------------------------- invalidation

    def invalidate(self) -> None:
        """Supersede artwork work without requesting new probing (source
        config/truth became unsafe)."""
        if self._closed:
            return
        self._generation += 1
        self._pending = None
        active = self._active_generation
        if active is not None:
            cancel = getattr(self._runner, "cancel", None)
            if cancel is not None:
                cancel(active)

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
                if self._album_probe is not None and self._prepared_cache is not None:
                    # PRODUCTION: tri-state + blob preparado en worker.
                    observation = self._album_probe.probe_album_artwork(
                        snapshot.track_paths, token
                    )
                    verdict = observation.verdict
                    prepared = None
                    if verdict is ArtworkProbeVerdict.FOUND:
                        prepared = self._prepared_cache.prepare_artwork(
                            snapshot.album_key, observation.artwork
                        )
                        if prepared is None:
                            # Preparación fallida: NO invalidar cache viejo.
                            verdict = ArtworkProbeVerdict.UNAVAILABLE
                    probes.append(
                        _AlbumArtworkProbe(
                            album_key=snapshot.album_key,
                            membership_signature=snapshot.membership_signature,
                            verdict=verdict,
                            prepared=prepared,
                        )
                    )
                    continue
                # LEGACY TEST/COMPATIBILITY PATH ONLY. Production bootstrap
                # siempre provee album_probe + prepared_cache.
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
                verdict = (
                    ArtworkProbeVerdict.FOUND
                    if artwork is not None
                    else ArtworkProbeVerdict.ABSENT_CONFIRMED
                )
                probes.append(
                    _AlbumArtworkProbe(
                        album_key=snapshot.album_key,
                        membership_signature=snapshot.membership_signature,
                        verdict=verdict,
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
        probes: tuple,
    ) -> None:
        """Provenance order: generation → album existence → CURRENT
        membership → verdict interpretation → ONE batch manifest commit.
        UNAVAILABLE produce CERO mutación de manifest."""
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

        upserts = []
        removals = []

        if isinstance(probes, dict):
            # Legacy dict contract (seal previo): {key: artwork|None} sin
            # verdict — membership del album ACTUAL como evidencia.
            for key, artwork in probes.items():
                current = current_albums.get(key)
                if current is None:
                    continue
                if artwork is not None:
                    upserts.append(
                        _AlbumArtworkProbe(
                            album_key=key,
                            membership_signature=self._membership_signature(current),
                            verdict=ArtworkProbeVerdict.FOUND,
                            artwork=artwork,
                        )
                    )
                else:
                    removals.append(key)
            probes = tuple(upserts)
            upserts = []
            # legacy: artwork se publica via store per-item (compat)
            for probe in probes:
                if probe.artwork is not None and self._cache is not None:
                    stored = self._cache.store(probe.album_key, probe.artwork)
                    if stored is not None:
                        next_paths[probe.album_key] = stored
            for key in removals:
                next_paths.pop(key, None)
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
            return

        prepared_upserts = []
        for probe in probes:
            current = current_albums.get(probe.album_key)
            if current is None:
                continue
            if self._membership_signature(current) != probe.membership_signature:
                continue
            if probe.verdict is ArtworkProbeVerdict.UNAVAILABLE:
                # Preserva el artwork actual/último conocido.
                continue
            if probe.verdict is ArtworkProbeVerdict.ABSENT_CONFIRMED:
                removals.append(probe.album_key)
                continue
            if probe.verdict is ArtworkProbeVerdict.FOUND:
                if probe.prepared is not None:
                    prepared_upserts.append(probe.prepared)
                elif probe.artwork is not None and self._cache is not None:
                    # LEGACY TEST/COMPATIBILITY PATH ONLY: worker legacy
                    # sin prepared_cache → publication per-item vía store.
                    stored = self._cache.store(probe.album_key, probe.artwork)
                    if stored is not None:
                        next_paths[probe.album_key] = stored

        published = {}
        if self._prepared_cache is not None and (prepared_upserts or removals):
            published = self._prepared_cache.commit_manifest_batch(
                upserts=tuple(prepared_upserts),
                removals=tuple(removals),
            )

        for key in removals:
            next_paths.pop(key, None)
        for key, path in published.items():
            next_paths[key] = path

        current_keys = {album.key for album in self._library.state.albums}
        next_paths = {
            key: value for key, value in next_paths.items() if key in current_keys
        }
        changed = next_paths != self._library._artwork_paths
        self._library._artwork_paths = next_paths
        next_albums = tuple(
            replace(
                album,
                has_artwork=album.key in next_paths,
            )
            for album in self._library.state.albums
        )
        albums_changed = next_albums != self._library.state.albums
        self._library.state.albums = next_albums
        if changed or albums_changed:
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
