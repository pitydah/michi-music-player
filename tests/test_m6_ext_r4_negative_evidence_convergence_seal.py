"""M6-EXT-R4 ABSOLUTE FREEZE MICRO-SEAL — NEGATIVE-EVIDENCE COMPLETENESS.

P1-01  partial album observation can NEVER become destructive negative
       evidence (ABSENT_CONFIRMED requires EXHAUSTIVE coverage)
P1-02  source truth changes RESCHEDULE the current artwork world (healthy
       pending artwork is never starved by an unrelated source failure)
P2     strict tri-state provider tests (EXACT verdicts)
P2     UNKNOWN Source blocks probing; UNKNOWN media blocks completeness
P2     owner revalidates negative coverage before commit
P2     ApplicationContainer artwork lifecycle symmetry

Epistemic contract under test:
    positive evidence can be partial;
    negative evidence must be complete.

Prohibited: time.sleep / polling. Allowed: manual runners, captured
callbacks, deterministic generation delivery.
"""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")


import pytest

from michi.application.library_artwork_contracts import (
    ArtworkProbeObservation,
    ArtworkProbeVerdict,
    PreparedArtwork,
)
from michi.application.library_service import LibraryService
from michi.application.ports import LibraryPrefsPort, ScanCancelToken
from michi.application.source_scan_coordinator import SourceScanCoordinator
from michi.domain.library import LibraryPrefs
from michi.domain.library_catalog import (
    LibrarySource,
    MediaAvailability,
    SourceAvailability,
    new_library_source_id,
)
from michi.infrastructure.artwork import MutagenArtworkProvider
from michi.infrastructure.filesystem_source_scanner import (
    FilesystemLibrarySourceScanner,
)
from michi.infrastructure.library_catalog import SqliteLibraryCatalogRepository
from michi.infrastructure.library_media_cache import SqliteLibraryMediaCache


class _Prefs(LibraryPrefsPort):
    def load(self):
        return LibraryPrefs()

    def save(self, prefs):
        del prefs


class _Progress:
    def __init__(self, phase="", total=0, processed=0, current_path=""):
        self.phase = phase
        self.total = total
        self.processed = processed
        self.current_path = current_path


class _Artwork:
    def __init__(self, data=b"PNG", mime_type="image/png"):
        self.data = data
        self.mime_type = mime_type


class _ManualRunner:
    def __init__(self):
        self.submissions = []
        self.cancelled = []

    def submit(self, generation, work, on_progress, on_done):
        self.submissions.append((generation, work))

    def cancel(self, generation):
        self.cancelled.append(generation)

    def shutdown(self):
        pass

    def disconnect_relay(self):
        pass


class _RecordingCache:
    def __init__(self):
        self.store_calls = []
        self.invalidate_calls = []
        self.prepare_calls = []
        self.batch_calls = []
        self._mapping = {}

    def store(self, album_key, artwork):
        self.store_calls.append((album_key, artwork))
        return Path(f"/fake/{album_key}.png")

    def invalidate(self, album_key):
        self.invalidate_calls.append(album_key)

    def lookup(self, album_key):
        return self._mapping.get(album_key)

    def prepare_artwork(self, album_key, artwork):
        self.prepare_calls.append(album_key)
        return PreparedArtwork(
            album_key=album_key,
            filename=f"{album_key}.png",
            path=Path(f"/fake/{album_key}.png"),
        )

    def commit_manifest_batch(self, *, upserts, removals):
        self.batch_calls.append((len(upserts), tuple(removals)))
        published = {}
        for p in upserts:
            published[p.album_key] = p.path
            self._mapping[p.album_key] = p.path
        for key in removals:
            self._mapping.pop(key, None)
        return published


class _ProbeProvider:
    """Deterministic tri-state provider that records exactly WHICH paths
    were probed."""

    def __init__(self, verdict=ArtworkProbeVerdict.ABSENT_CONFIRMED):
        self.verdict = verdict
        self.calls = []

    def probe_album_artwork(self, track_paths, token=None):
        self.calls.append(tuple(str(p) for p in track_paths))
        if self.verdict is ArtworkProbeVerdict.FOUND:
            return ArtworkProbeObservation.found(_Artwork())
        if self.verdict is ArtworkProbeVerdict.ABSENT_CONFIRMED:
            return ArtworkProbeObservation.absent()
        return ArtworkProbeObservation.unavailable("injected")


def _ref(track_id, source_id, path, availability=MediaAvailability.AVAILABLE):
    from michi.domain.library import TrackRef

    return TrackRef(
        track_id=track_id,
        library_source_id=source_id,
        file_path=Path(path),
        display_name=track_id,
        title=track_id,
        availability=availability,
    )


def _album(library, key, track_ids, track_paths):
    from michi.domain.library import AlbumRef

    library.state.albums = tuple(a for a in library.state.albums if a.key != key) + (
        AlbumRef(
            key=key,
            title=f"Album {key}",
            artist="Artist",
            track_count=len(track_ids),
            duration_ms=0,
            track_ids=tuple(track_ids),
            track_paths=tuple(Path(p) for p in track_paths),
        ),
    )


def _set_library(library, tracks, albums):
    """Canonical state + derived indexes (trackref_by_id must resolve)."""
    library._state.tracks = tuple(tracks)
    library._track_refs_by_id = {ref.track_id: ref for ref in tracks if ref.track_id}
    library._track_refs_by_path = {ref.file_path: ref for ref in tracks}
    library._state.albums = tuple(albums)


def _env(tmp_path):
    db_path = tmp_path / "michi.db"
    catalog = SqliteLibraryCatalogRepository(db_path)
    library = LibraryService(FilesystemLibrarySourceScanner(), library_prefs=_Prefs())
    coordinator = SourceScanCoordinator(
        library,
        catalog,
        FilesystemLibrarySourceScanner(),
        media_cache=SqliteLibraryMediaCache(db_path),
    )
    return library, catalog, coordinator


def _refresh(library, provider, cache, coordinator):
    from michi.application.library_artwork_refresh import (
        LibraryArtworkRefresh,
    )

    runner = _ManualRunner()
    refresh = LibraryArtworkRefresh(
        library,
        provider,
        cache,
        runner=runner,
        album_probe=provider,
        prepared_cache=cache,
        source_availability_provider=coordinator.observed_availability,
    )
    return refresh, runner


def _source(tmp_path, name):
    return LibrarySource(
        library_source_id=new_library_source_id(),
        display_name=name,
        root_path=str(tmp_path / name),
    )


# ==========================================================================
# STRICT TRI-STATE (P2 hardening) — exact verdicts, no membership unions
# ==========================================================================


class TestStrictTriState:
    def test_tri_state_found_is_exact(self, monkeypatch, tmp_path):
        """Deterministic fake Mutagen audio with a front-cover APIC frame →
        verdict EXACTLY FOUND, artwork not None."""

        class _Frame:
            type = 3
            mime = "image/png"
            data = b"\x89PNG\r\n\x1a\n" + b"0" * 64

        class _Tags:
            def getall(self, key):
                return [_Frame()] if key == "APIC" else []

        class _FakeAudio:
            tags = _Tags()
            pictures = []

        monkeypatch.setattr(
            "michi.infrastructure.artwork.MutagenFile",
            lambda path: _FakeAudio(),
        )
        provider = MutagenArtworkProvider()
        observation = provider.probe_album_artwork((Path("/fake/track.mp3"),))
        assert observation.verdict is ArtworkProbeVerdict.FOUND
        assert observation.artwork is not None

    def test_tri_state_absent_is_exact_when_every_probe_is_readable(
        self, monkeypatch, tmp_path
    ):
        """Readable tags with NO artwork + empty album dir →
        verdict EXACTLY ABSENT_CONFIRMED, artwork None."""

        class _Tags:
            def getall(self, key):
                return []

        class _FakeAudio:
            tags = _Tags()
            pictures = []

        empty_dir = tmp_path / "album"
        empty_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(
            "michi.infrastructure.artwork.MutagenFile",
            lambda path: _FakeAudio(),
        )
        provider = MutagenArtworkProvider()
        observation = provider.probe_album_artwork((empty_dir / "track.flac",))
        assert observation.verdict is ArtworkProbeVerdict.ABSENT_CONFIRMED
        assert observation.artwork is None

    def test_tri_state_io_failure_is_exactly_unavailable(self, monkeypatch):
        def _raise(path):
            raise OSError("offline")

        monkeypatch.setattr("michi.infrastructure.artwork.MutagenFile", _raise)
        provider = MutagenArtworkProvider()
        observation = provider.probe_album_artwork((Path("/fake/track.mp3"),))
        assert observation.verdict is ArtworkProbeVerdict.UNAVAILABLE
        assert observation.artwork is None

    def test_tri_state_mutagen_failure_is_exactly_unavailable(self, monkeypatch):
        from mutagen import MutagenError

        def _raise(path):
            raise MutagenError("corrupt header")

        monkeypatch.setattr("michi.infrastructure.artwork.MutagenFile", _raise)
        provider = MutagenArtworkProvider()
        observation = provider.probe_album_artwork((Path("/fake/track.mp3"),))
        assert observation.verdict is ArtworkProbeVerdict.UNAVAILABLE
        assert observation.artwork is None


# ==========================================================================
# P1-01 — NEGATIVE EVIDENCE MUST BE EXHAUSTIVE
# ==========================================================================


class TestNegativeEvidenceCompleteness:
    def test_partial_album_negative_evidence_preserves_cached_artwork(self, tmp_path):
        """Album X: T1 (Source A AVAILABLE, no cover) + T2 (Source B
        OFFLINE). Provider on the observable T1 returns ABSENT_CONFIRMED.
        The partial observation must NOT remove the cached album cover."""
        library, catalog, coordinator = _env(tmp_path)
        source_a = _source(tmp_path, "a")
        source_b = _source(tmp_path, "b")
        catalog.upsert_source(source_a)
        catalog.upsert_source(source_b)
        coordinator._observations[source_a.library_source_id] = (
            SourceAvailability.AVAILABLE
        )
        coordinator._observations[source_b.library_source_id] = (
            SourceAvailability.OFFLINE
        )
        tracks = (
            _ref("TA1", source_a.library_source_id, "/a/T1.flac"),
            _ref("TB1", source_b.library_source_id, "/b/T2.flac"),
        )
        _album(library, "album-x", ("TA1", "TB1"), ("/a/T1.flac", "/b/T2.flac"))
        _set_library(library, tracks, library.state.albums)
        library._artwork_paths = {"album-x": "/fake/album-x.png"}
        library.state.albums = (
            tuple(
                a if a.key != "album-x" else a._replace(has_artwork=True)
                for a in library.state.albums
            )
            if hasattr(library.state.albums[0], "_replace")
            else library.state.albums
        )

        provider = _ProbeProvider(ArtworkProbeVerdict.ABSENT_CONFIRMED)
        cache = _RecordingCache()
        cache._mapping["album-x"] = "/fake/album-x.png"
        refresh, runner = _refresh(library, provider, cache, coordinator)
        coordinator._artwork_refresh = refresh

        refresh.schedule()
        assert len(runner.submissions) == 1
        gen1, work1 = runner.submissions[0]
        result1 = work1(_Progress(), ScanCancelToken(), lambda: None)
        refresh.handle_done(gen1, result1, None)

        # Source B path nunca fue probada.
        assert all("b/T2" not in call for call in provider.calls)
        # Cache preservada + has_artwork intacto + cero remociones.
        assert cache._mapping.get("album-x") == "/fake/album-x.png"
        assert library._artwork_paths.get("album-x") == "/fake/album-x.png"
        assert cache.batch_calls == []
        album = next(a for a in library.state.albums if a.key == "album-x")
        assert album.has_artwork is True

    def test_partial_album_positive_evidence_can_publish_artwork(self, tmp_path):
        """Same partial album, but T1 contains valid artwork: FOUND is
        valid even with partial coverage (existential positive)."""
        library, catalog, coordinator = _env(tmp_path)
        source_a = _source(tmp_path, "a")
        source_b = _source(tmp_path, "b")
        catalog.upsert_source(source_a)
        catalog.upsert_source(source_b)
        coordinator._observations[source_a.library_source_id] = (
            SourceAvailability.AVAILABLE
        )
        coordinator._observations[source_b.library_source_id] = (
            SourceAvailability.OFFLINE
        )
        tracks = (
            _ref("TA1", source_a.library_source_id, "/a/T1.flac"),
            _ref("TB1", source_b.library_source_id, "/b/T2.flac"),
        )
        _album(library, "album-x", ("TA1", "TB1"), ("/a/T1.flac", "/b/T2.flac"))
        _set_library(library, tracks, library.state.albums)

        provider = _ProbeProvider(ArtworkProbeVerdict.FOUND)
        cache = _RecordingCache()
        refresh, runner = _refresh(library, provider, cache, coordinator)

        refresh.schedule()
        gen1, work1 = runner.submissions[0]
        result1 = work1(_Progress(), ScanCancelToken(), lambda: None)
        refresh.handle_done(gen1, result1, None)

        assert all("b/T2" not in call for call in provider.calls), "T2 nunca probado"
        assert cache._mapping.get("album-x") == Path("/fake/album-x.png")
        album = next(a for a in library.state.albums if a.key == "album-x")
        assert album.has_artwork is True

    def test_complete_album_negative_evidence_invalidates_cache(self, tmp_path):
        """T1 + T2 both fully probeable, both inspected, no artwork:
        ABSENT_CONFIRMED is valid and removes the stale cached cover."""
        library, catalog, coordinator = _env(tmp_path)
        source_a = _source(tmp_path, "a")
        catalog.upsert_source(source_a)
        coordinator._observations[source_a.library_source_id] = (
            SourceAvailability.AVAILABLE
        )
        tracks = (
            _ref("TA1", source_a.library_source_id, "/a/T1.flac"),
            _ref("TA2", source_a.library_source_id, "/a/T2.flac"),
        )
        _album(library, "album-x", ("TA1", "TA2"), ("/a/T1.flac", "/a/T2.flac"))
        _set_library(library, tracks, library.state.albums)
        library._artwork_paths = {"album-x": "/fake/album-x.png"}

        provider = _ProbeProvider(ArtworkProbeVerdict.ABSENT_CONFIRMED)
        cache = _RecordingCache()
        cache._mapping["album-x"] = "/fake/album-x.png"
        refresh, runner = _refresh(library, provider, cache, coordinator)

        refresh.schedule()
        gen1, work1 = runner.submissions[0]
        result1 = work1(_Progress(), ScanCancelToken(), lambda: None)
        refresh.handle_done(gen1, result1, None)

        assert "album-x" not in cache._mapping
        assert "album-x" not in library._artwork_paths
        album = next(a for a in library.state.albums if a.key == "album-x")
        assert album.has_artwork is False

    def test_negative_result_is_rejected_if_coverage_becomes_partial_before_owner_commit(  # noqa: E501
        self, tmp_path
    ):
        """Worker saw COMPLETE coverage and returned ABSENT_CONFIRMED; the
        Source goes OFFLINE BEFORE the owner commits. The owner revalidates
        current coverage → refuses the negative invalidation."""
        library, catalog, coordinator = _env(tmp_path)
        source_a = _source(tmp_path, "a")
        source_b = _source(tmp_path, "b")
        catalog.upsert_source(source_a)
        catalog.upsert_source(source_b)
        coordinator._observations[source_a.library_source_id] = (
            SourceAvailability.AVAILABLE
        )
        coordinator._observations[source_b.library_source_id] = (
            SourceAvailability.AVAILABLE
        )
        tracks = (
            _ref("TA1", source_a.library_source_id, "/a/T1.flac"),
            _ref("TB1", source_b.library_source_id, "/b/T2.flac"),
        )
        _album(library, "album-x", ("TA1", "TB1"), ("/a/T1.flac", "/b/T2.flac"))
        _set_library(library, tracks, library.state.albums)
        library._artwork_paths = {"album-x": "/fake/album-x.png"}

        provider = _ProbeProvider(ArtworkProbeVerdict.ABSENT_CONFIRMED)
        cache = _RecordingCache()
        cache._mapping["album-x"] = "/fake/album-x.png"
        refresh, runner = _refresh(library, provider, cache, coordinator)

        refresh.schedule()
        gen1, work1 = runner.submissions[0]
        result1 = work1(_Progress(), ScanCancelToken(), lambda: None)

        # Source B se vuelve OFFLINE ANTES de la entrega del worker.
        coordinator._observations[source_b.library_source_id] = (
            SourceAvailability.OFFLINE
        )
        refresh.handle_done(gen1, result1, None)

        assert cache._mapping.get("album-x") == "/fake/album-x.png", (
            "negativo viejo NO invalida con cobertura actual parcial"
        )
        assert cache.batch_calls == []

    def test_unknown_source_is_never_probed_for_artwork(self, tmp_path):
        """ACTIVE + ENABLED source with observed availability UNKNOWN:
        schedule must NOT touch its filesystem; cached artwork preserved."""
        library, catalog, coordinator = _env(tmp_path)
        source_a = _source(tmp_path, "a")
        catalog.upsert_source(source_a)
        # Sin observación → observed_availability devuelve UNKNOWN.
        tracks = (_ref("TA1", source_a.library_source_id, "/a/T1.flac"),)
        _album(library, "album-x", ("TA1",), ("/a/T1.flac",))
        _set_library(library, tracks, library.state.albums)
        library._artwork_paths = {"album-x": "/fake/album-x.png"}

        provider = _ProbeProvider(ArtworkProbeVerdict.ABSENT_CONFIRMED)
        cache = _RecordingCache()
        cache._mapping["album-x"] = "/fake/album-x.png"
        refresh, runner = _refresh(library, provider, cache, coordinator)

        refresh.schedule()

        assert runner.submissions == [], "UNKNOWN no autoriza probing"
        assert provider.calls == []
        assert cache._mapping.get("album-x") == "/fake/album-x.png"

    def test_unknown_media_member_makes_album_coverage_partial(self, tmp_path):
        """Source AVAILABLE, T1 media AVAILABLE, T2 media UNKNOWN: the
        UNKNOWN member blocks negative completeness → cache preserved."""
        library, catalog, coordinator = _env(tmp_path)
        source_a = _source(tmp_path, "a")
        catalog.upsert_source(source_a)
        coordinator._observations[source_a.library_source_id] = (
            SourceAvailability.AVAILABLE
        )
        tracks = (
            _ref("TA1", source_a.library_source_id, "/a/T1.flac"),
            _ref(
                "TA2",
                source_a.library_source_id,
                "/a/T2.flac",
                availability=MediaAvailability.UNKNOWN,
            ),
        )
        _album(library, "album-x", ("TA1", "TA2"), ("/a/T1.flac", "/a/T2.flac"))
        _set_library(library, tracks, library.state.albums)
        library._artwork_paths = {"album-x": "/fake/album-x.png"}

        provider = _ProbeProvider(ArtworkProbeVerdict.ABSENT_CONFIRMED)
        cache = _RecordingCache()
        cache._mapping["album-x"] = "/fake/album-x.png"
        refresh, runner = _refresh(library, provider, cache, coordinator)

        refresh.schedule()
        assert len(runner.submissions) == 1
        gen1, work1 = runner.submissions[0]
        result1 = work1(_Progress(), ScanCancelToken(), lambda: None)
        refresh.handle_done(gen1, result1, None)

        assert all("T2.flac" not in call for call in provider.calls)
        assert cache._mapping.get("album-x") == "/fake/album-x.png"
        assert cache.batch_calls == []


# ==========================================================================
# P1-02 — SOURCE MUTATION CONVERGES (never starves healthy work)
# ==========================================================================


class TestSourceConvergence:
    def test_source_error_reschedules_healthy_artwork_instead_of_dropping_pending(
        self, tmp_path
    ):
        """gen1 active (album A), gen2 pending; an unrelated Source C
        failure must produce gen3 pending — never drop the healthy work."""
        library, catalog, coordinator = _env(tmp_path)
        source_a = _source(tmp_path, "a")
        source_c = _source(tmp_path, "c")
        catalog.upsert_source(source_a)
        catalog.upsert_source(source_c)
        coordinator._observations[source_a.library_source_id] = (
            SourceAvailability.AVAILABLE
        )
        tracks = (_ref("TA1", source_a.library_source_id, "/a/T1.flac"),)
        _album(library, "album-a", ("TA1",), ("/a/T1.flac",))
        _set_library(library, tracks, library.state.albums)

        provider = _ProbeProvider(ArtworkProbeVerdict.FOUND)
        cache = _RecordingCache()
        refresh, runner = _refresh(library, provider, cache, coordinator)
        coordinator._artwork_refresh = refresh

        refresh.schedule()  # gen1 active
        assert runner.submissions[0][0] == 1
        refresh.schedule()  # gen2 pending
        assert refresh._pending is not None
        assert refresh._pending[0] == 2

        # Falla una fuente NO relacionada (sin tracks en el album).
        from michi.application.library_port import LibraryFilesystemError
        from michi.domain.library import LibraryDiagnosticCode

        coordinator.record_source_scan_error(
            source_c.library_source_id,
            LibraryFilesystemError(
                LibraryDiagnosticCode.IO_FAILURE, Path("/c"), "boom"
            ),
        )

        assert refresh._pending is not None, "el error NO puede vaciar el pending"
        assert refresh._pending[0] == 3, "gen3 = último pending (fuente sana)"

        # gen1 termina → arranca SOLO gen3 (gen2 superseded).
        gen1, work1 = runner.submissions[0]
        result1 = work1(_Progress(), ScanCancelToken(), lambda: None)
        refresh.handle_done(gen1, result1, None)
        assert runner.submissions[-1][0] == 3
        gen3, work3 = runner.submissions[-1]
        assert refresh._pending is None  # pending consumed
        result3 = work3(_Progress(), ScanCancelToken(), lambda: None)
        assert len(result3) == 1
        assert result3[0].album_key == "album-a", "album sano sigue en el snapshot"

    def test_disabling_one_source_reschedules_artwork_for_remaining_sources(
        self, tmp_path
    ):
        """Source A + B AVAILABLE; disable B → replacement snapshot keeps
        album A and excludes album B (B never probed in the replacement)."""
        library, catalog, coordinator = _env(tmp_path)
        source_a = _source(tmp_path, "a")
        source_b = _source(tmp_path, "b")
        catalog.upsert_source(source_a)
        catalog.upsert_source(source_b)
        coordinator._observations[source_a.library_source_id] = (
            SourceAvailability.AVAILABLE
        )
        coordinator._observations[source_b.library_source_id] = (
            SourceAvailability.AVAILABLE
        )
        tracks = (
            _ref("TA1", source_a.library_source_id, "/a/T1.flac"),
            _ref("TB1", source_b.library_source_id, "/b/T1.flac"),
        )
        _album(library, "album-a", ("TA1",), ("/a/T1.flac",))
        _album(library, "album-b", ("TB1",), ("/b/T1.flac",))
        _set_library(library, tracks, library.state.albums)

        provider = _ProbeProvider(ArtworkProbeVerdict.FOUND)
        cache = _RecordingCache()
        refresh, runner = _refresh(library, provider, cache, coordinator)
        coordinator._artwork_refresh = refresh

        refresh.schedule()  # gen1 activo: album-a + album-b
        gen1, work1 = runner.submissions[0]
        provider.calls.clear()

        coordinator.set_source_enabled(source_b.library_source_id, False)

        assert refresh._pending is not None
        assert refresh._pending[0] == 2
        refresh.handle_done(
            gen1, work1(_Progress(), ScanCancelToken(), lambda: None), None
        )
        gen2, work2 = runner.submissions[-1]
        assert gen2 == 2
        result2 = work2(_Progress(), ScanCancelToken(), lambda: None)
        keys = [p.album_key for p in result2]
        assert "album-a" in keys, "source sano A sigue refrescando"
        assert "album-b" not in keys, "album del source deshabilitado excluido"
        assert all("b/" not in call for call in provider.calls), (
            "B nunca probado en el reemplazo"
        )

    def test_relocate_reschedules_artwork_without_old_root(self, tmp_path):
        """Relocate A /old → /new: A UNKNOWN → replacement snapshot has
        neither /old nor /new; healthy Source B remains; a late delivery of
        the old generation cannot publish."""
        library, catalog, coordinator = _env(tmp_path)
        source_a = _source(tmp_path, "old")
        source_b = _source(tmp_path, "b")
        (tmp_path / "new").mkdir(exist_ok=True)
        catalog.upsert_source(source_a)
        catalog.upsert_source(source_b)
        coordinator._observations[source_a.library_source_id] = (
            SourceAvailability.AVAILABLE
        )
        coordinator._observations[source_b.library_source_id] = (
            SourceAvailability.AVAILABLE
        )
        tracks = (
            _ref("TA1", source_a.library_source_id, "/old/T1.flac"),
            _ref("TB1", source_b.library_source_id, "/b/T1.flac"),
        )
        _album(library, "album-a", ("TA1",), ("/old/T1.flac",))
        _album(library, "album-b", ("TB1",), ("/b/T1.flac",))
        _set_library(library, tracks, library.state.albums)

        provider = _ProbeProvider(ArtworkProbeVerdict.FOUND)
        cache = _RecordingCache()
        refresh, runner = _refresh(library, provider, cache, coordinator)
        coordinator._artwork_refresh = refresh

        refresh.schedule()  # gen1 activo (contiene /old)
        gen1, work1 = runner.submissions[0]
        old_result = work1(_Progress(), ScanCancelToken(), lambda: None)
        provider.calls.clear()

        coordinator.relocate_source_root(
            source_a.library_source_id, str(tmp_path / "new")
        )

        assert refresh._pending is not None
        assert refresh._pending[0] == 2
        refresh.handle_done(gen1, old_result, None)
        gen2, work2 = runner.submissions[-1]
        assert gen2 == 2
        result2 = work2(_Progress(), ScanCancelToken(), lambda: None)
        keys = [p.album_key for p in result2]
        assert "album-b" in keys
        assert "album-a" not in keys, "A UNKNOWN tras relocate → no se proba"
        for call in provider.calls:
            assert "old" not in call, "nunca se toca /old"
            assert "new" not in call, "nunca se toca /new antes de AVAILABLE"
        # Entrega tardía del gen1 no publica (generation gate).
        assert cache.batch_calls == []


# ==========================================================================
# SYNC scan_source PARITY (async owner semantics)
# ==========================================================================


class _RaisingScanner:
    def __init__(self, error=None):
        self.error = error

    def discover(self, source):
        if self.error is not None:
            raise self.error
        return ()


class _ArtworkSpy:
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.schedule_calls = []
        self.invalidate_calls = []

    def schedule(self):
        self.schedule_calls.append(dict(self.coordinator._observations))

    def invalidate(self):
        self.invalidate_calls.append(1)


class TestSyncScanParity:
    def test_sync_source_scan_error_reschedules_current_artwork_world(self, tmp_path):
        from michi.application.library_port import LibraryFilesystemError
        from michi.domain.library import LibraryDiagnosticCode

        library, catalog, coordinator = _env(tmp_path)
        spy = _ArtworkSpy(coordinator)
        coordinator._artwork_refresh = spy
        scanner_error = LibraryFilesystemError(
            LibraryDiagnosticCode.DIRECTORY_MISSING, Path("/gone"), "missing root"
        )
        coordinator._scanner = _RaisingScanner(scanner_error)
        source = _source(tmp_path, "a")

        outcome = coordinator.scan_source(source)

        assert outcome.availability is SourceAvailability.MISSING_ROOT
        assert (
            coordinator._observations[source.library_source_id]
            is SourceAvailability.MISSING_ROOT
        )
        assert len(spy.schedule_calls) == 1, "error → UN schedule"
        assert spy.invalidate_calls == [], "cero invalidaciones hard"

    def test_sync_source_scan_success_publishes_observation_before_artwork_schedule(
        self, tmp_path
    ):
        class _ObservingSpy(_ArtworkSpy):
            def schedule(self):
                self.schedule_calls.append(
                    self.coordinator.observed_availability(self._target_source_id)
                )

            def set_target(self, source_id):
                self._target_source_id = source_id

        library, catalog, coordinator = _env(tmp_path)
        spy = _ObservingSpy(coordinator)
        coordinator._artwork_refresh = spy
        coordinator._scanner = _RaisingScanner()
        source = _source(tmp_path, "a")
        spy.set_target(source.library_source_id)

        outcome = coordinator.scan_source(source)

        assert not outcome.failed
        assert outcome.availability is SourceAvailability.AVAILABLE
        assert len(spy.schedule_calls) == 1, "éxito → UN schedule"
        observed = spy.schedule_calls[0]
        assert observed is SourceAvailability.AVAILABLE, (
            "la observación se publica ANTES del schedule"
        )


# ==========================================================================
# ApplicationContainer LIFECYCLE SYMMETRY (§40-44)
# ==========================================================================


class TestContainerLifecycleSymmetry:
    def test_container_artwork_shutdown_order_and_handle_release(self):
        from michi.bootstrap import ApplicationContainer

        calls = []

        class _Refresh:
            def shutdown(self):
                calls.append("refresh.shutdown")

        class _Dispatcher:
            def shutdown(self):
                calls.append("dispatcher.shutdown")

        class _Runner:
            def shutdown(self):
                calls.append("runner.shutdown")

            def disconnect_relay(self):
                calls.append("runner.disconnect_relay")

        container = ApplicationContainer()
        container._artwork_refresh = _Refresh()
        container._artwork_dispatcher = _Dispatcher()
        container._artwork_runner = _Runner()

        ApplicationContainer.shutdown(container)

        assert calls == [
            "refresh.shutdown",
            "dispatcher.shutdown",
            "runner.shutdown",
            "runner.disconnect_relay",
        ]
        assert container._artwork_refresh is None
        assert container._artwork_dispatcher is None
        assert container._artwork_runner is None

    def test_container_retains_artwork_handles_when_cleanup_is_not_proven(
        self,
    ):
        from michi.bootstrap import ApplicationContainer

        calls = []

        class _Refresh:
            def shutdown(self):
                calls.append("refresh.shutdown")

        class _Dispatcher:
            def shutdown(self):
                calls.append("dispatcher.shutdown")

        class _Runner:
            def shutdown(self):
                calls.append("runner.shutdown")
                raise RuntimeError("shutdown not proven")

            def disconnect_relay(self):
                calls.append("runner.disconnect_relay")

        container = ApplicationContainer()
        refresh = _Refresh()
        dispatcher = _Dispatcher()
        runner = _Runner()
        container._artwork_refresh = refresh
        container._artwork_dispatcher = dispatcher
        container._artwork_runner = runner

        with pytest.raises(RuntimeError):
            ApplicationContainer.shutdown(container)

        # El runner falló → cleanup NO probado → handles retenidos.
        assert container._artwork_runner is runner
        assert container._artwork_dispatcher is dispatcher
        assert container._artwork_refresh is refresh
        # El resto del cleanup seguro aún se intentó.
        assert calls == [
            "refresh.shutdown",
            "dispatcher.shutdown",
            "runner.shutdown",
            "runner.disconnect_relay",
        ]
