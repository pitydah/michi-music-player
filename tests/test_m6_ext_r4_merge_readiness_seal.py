"""M6-EXT-R4 FINAL MERGE-READINESS SEAL.

P1  — commit_source_scan_if_current() bypasses the derived artwork
      firewall: a direct self._artwork_refresh.schedule() that throws
      would escape, SourceScanLifecycle._finish() never runs, and the
      lifecycle stalls (_active forever, scanActive stuck, Scan All
      stops) even though the Source/Catalog commit succeeded.

P2-01 — first-seen local artwork winner must be frozen by EXACT payload
P2-02 — case-insensitive local filename collisions must be deterministic
        (exact canonical case wins; folded matches sorted)
P2-03 — an unreadable primary local candidate must NOT hide a valid
        fallback (positive evidence is existential; uncertainty only
        poisons when no candidate is valid)

Governance: this is the ONLY new test file; existing tests are
read-only evidence.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from pathlib import Path

from michi.application.library_artwork_contracts import (
    ArtworkProbeObservation,
    ArtworkProbeVerdict,
)
from michi.application.library_service import LibraryService
from michi.application.ports import LibraryPrefsPort
from michi.application.source_scan_coordinator import SourceScanCoordinator
from michi.application.source_scan_lifecycle import SourceScanLifecycle
from michi.domain.library import LibraryPrefs
from michi.domain.library_catalog import (
    LibrarySource,
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


class ExplodingArtworkRefresh:
    def __init__(self):
        self.schedules = 0

    def schedule(self):
        self.schedules += 1
        raise RuntimeError("artwork boom")


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


def _source(tmp_path, name):
    return LibrarySource(
        library_source_id=new_library_source_id(),
        display_name=name,
        root_path=str(tmp_path / name),
    )


def _png(tmp_path, name, color, size=8):
    from PySide6.QtGui import QImage

    img = QImage(size, size, QImage.Format_RGB32)
    img.fill(color)
    path = tmp_path / name
    assert img.save(str(path), "PNG")
    return path


# ==========================================================================
# P1 — ASYNC SOURCE PATH USES THE DERIVED ARTWORK FIREWALL
# ==========================================================================


class TestAsyncArtworkFirewall:
    def _lifecycle_world(self, tmp_path, source_names=("a",)):
        from tests.test_m6_ext_r4_final_authority_seal import _ManualPipeline

        library, catalog, coordinator = _env(tmp_path)
        exploding = ExplodingArtworkRefresh()
        coordinator._artwork_refresh = exploding
        pipeline = _ManualPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        sources = []
        for name in source_names:
            source = _source(tmp_path, name)
            (tmp_path / name).mkdir(exist_ok=True)
            catalog.upsert_source(source)
            sources.append(source)
        return library, catalog, coordinator, exploding, pipeline, lifecycle, sources

    def test_async_success_artwork_failure_cannot_stall_source_lifecycle(
        self,
        tmp_path,
    ):
        """handle_done() con plan exitoso + artwork que explota: la
        excepción NO escapa, el lifecycle llega a _finish (terminal
        success), y la autoridad de Source queda commiteada."""
        library, catalog, coordinator, exploding, pipeline, lifecycle, (source,) = (
            self._lifecycle_world(tmp_path)
        )
        (tmp_path / "a" / "song.flac").write_bytes(b"x")

        lifecycle.request_scan_source(source.library_source_id)
        assert lifecycle._active is True
        pipeline.run(0)  # worker exitoso → on_done → commit → firewall

        assert lifecycle._active is False, "el lifecycle NO queda stall"
        assert lifecycle.state.active is False
        assert lifecycle.state.last_terminal_status is not None
        assert (
            coordinator._observations[source.library_source_id]
            is SourceAvailability.AVAILABLE
        )
        tracks = catalog.load_tracks()
        assert len(tracks) == 1, "catalog commiteado pese al fallo de artwork"
        assert exploding.schedules >= 1

    def test_scan_all_continues_to_next_source_when_artwork_schedule_fails(
        self,
        tmp_path,
    ):
        """Scan All con A y B: A commitea + artwork explota → B igual se
        somete automáticamente; al final ambos procesados y COMPLETED."""
        library, catalog, coordinator, exploding, pipeline, lifecycle, sources = (
            self._lifecycle_world(tmp_path, ("a", "b"))
        )
        (tmp_path / "a" / "one.flac").write_bytes(b"x")
        (tmp_path / "b" / "two.flac").write_bytes(b"x")

        lifecycle.request_scan_all()
        assert len(pipeline.submissions) == 1  # solo A arranca
        pipeline.run(0)  # A success + artwork boom → B se somete
        assert len(pipeline.submissions) == 2, "B se somete automáticamente"
        pipeline.run(1)  # B success

        assert lifecycle._active is False
        assert lifecycle.state.active is False
        assert lifecycle.state.last_terminal_status is not None
        assert (
            coordinator.observed_availability(sources[0].library_source_id)
            is SourceAvailability.AVAILABLE
        )
        assert (
            coordinator.observed_availability(sources[1].library_source_id)
            is SourceAvailability.AVAILABLE
        )
        assert exploding.schedules >= 2

    def test_commit_source_scan_if_current_never_propagates_artwork_schedule_failure(
        self,
        tmp_path,
    ):
        """La llamada directa al método de commit nunca propaga el fallo de
        artwork: outcome válido, observación AVAILABLE, catalog commiteado."""
        library, catalog, coordinator, exploding, pipeline, lifecycle, (source,) = (
            self._lifecycle_world(tmp_path)
        )
        (tmp_path / "a" / "song.flac").write_bytes(b"x")
        discovered = coordinator._scanner.discover(source)
        plan = coordinator.compute_source_reconciliation(source, discovered)

        outcome = coordinator.commit_source_scan_if_current(1, 1, plan, None)

        assert outcome is not None
        assert outcome.failed is False
        assert (
            coordinator._observations[source.library_source_id]
            is SourceAvailability.AVAILABLE
        )
        tracks = catalog.load_tracks()
        assert len(tracks) == 1, "catalog commiteado pese al fallo de artwork"


class _DiscoverScanner:
    def __init__(self, files=()):
        self._files = list(files)

    def discover(self, source):
        from michi.application.library_port import DiscoveredMediaFile

        discovered = []
        root = Path(source.root_path)
        for rel in self._files:
            if not isinstance(rel, Path):
                rel = Path(rel)
            absolute = root / rel.name if rel.parent == Path(".") else rel
            discovered.append(
                DiscoveredMediaFile(
                    relative_path=absolute.name,
                    absolute_path=absolute,
                    file_size=absolute.stat().st_size if absolute.exists() else 1,
                    mtime_ns=1,
                )
            )
        return tuple(discovered)


# ==========================================================================
# P2-01/02/03 — LOCAL ARTWORK DETERMINISM + FALLBACK
# ==========================================================================


class TestLocalArtworkHardening:
    def test_local_artwork_first_seen_directory_wins_with_distinct_payload(
        self,
        tmp_path,
        monkeypatch,
    ):
        """CD2/cover.png (payload B) con orden CD2→CD1: el ganador es el
        DIRECTORIO first-seen y su PAYLOAD exacto (no solo is not None)."""
        cd1 = tmp_path / "CD1"
        cd2 = tmp_path / "CD2"
        cd1.mkdir()
        cd2.mkdir()
        payload_a = _png(tmp_path, "payload_a.png", 0xFF581C)
        payload_b = _png(tmp_path, "payload_b.png", 0x22AA55)
        import shutil

        shutil.copy(payload_a, cd1 / "cover.png")
        shutil.copy(payload_b, cd2 / "cover.png")
        (cd1 / "t1.flac").write_bytes(b"x")
        (cd2 / "t2.flac").write_bytes(b"x")

        provider = MutagenArtworkProvider()
        monkeypatch.setattr(
            provider,
            "_probe_embedded",
            lambda path, *, front_only: ArtworkProbeObservation.absent(),
        )

        observation = provider.probe_album_artwork((cd2 / "t2.flac", cd1 / "t1.flac"))

        assert observation.verdict is ArtworkProbeVerdict.FOUND
        assert observation.artwork is not None
        assert observation.artwork.data == payload_b.read_bytes(), (
            "el payload del directorio first-seen (CD2) es el ganador exacto"
        )

    def test_local_artwork_exact_case_beats_case_insensitive_collision(
        self,
        tmp_path,
        monkeypatch,
    ):
        """cover.jpg y COVER.JPG coexisten con payloads distintos: la
        coincidencia EXACTA canónica (cover.jpg) gana — nunca el orden
        del iterdir."""
        cd = tmp_path / "CD"
        cd.mkdir()
        payload_exact = _png(tmp_path, "exact.png", 0xFF581C)
        payload_folded = _png(tmp_path, "folded.png", 0x22AA55)
        import shutil

        shutil.copy(payload_exact, cd / "cover.jpg")
        shutil.copy(payload_folded, cd / "COVER.JPG")
        (cd / "t.flac").write_bytes(b"x")

        provider = MutagenArtworkProvider()
        monkeypatch.setattr(
            provider,
            "_probe_embedded",
            lambda path, *, front_only: ArtworkProbeObservation.absent(),
        )

        observation = provider.probe_album_artwork((cd / "t.flac",))

        assert observation.verdict is ArtworkProbeVerdict.FOUND
        assert observation.artwork.data == payload_exact.read_bytes(), (
            "exact canonical cover.jpg gana la colisión"
        )

    def test_local_artwork_case_insensitive_fallback_remains_supported(
        self,
        tmp_path,
        monkeypatch,
    ):
        """Solo COVER.JPG → FOUND (compat case-insensitive preservada)."""
        cd = tmp_path / "CD"
        cd.mkdir()
        payload = _png(tmp_path, "p.png", 0x3366AA)
        import shutil

        shutil.copy(payload, cd / "COVER.JPG")
        (cd / "t.flac").write_bytes(b"x")

        provider = MutagenArtworkProvider()
        monkeypatch.setattr(
            provider,
            "_probe_embedded",
            lambda path, *, front_only: ArtworkProbeObservation.absent(),
        )

        observation = provider.probe_album_artwork((cd / "t.flac",))

        assert observation.verdict is ArtworkProbeVerdict.FOUND
        assert observation.artwork is not None

    def test_unreadable_primary_local_artwork_does_not_hide_valid_fallback(
        self,
        tmp_path,
        monkeypatch,
    ):
        """cover.jpg ilegible + folder.jpg válido → FOUND folder.jpg
        (positivo existencial; el candidato malo no esconde el fallback)."""
        cd = tmp_path / "CD"
        cd.mkdir()
        payload = _png(tmp_path, "fb.png", 0x22AA55)
        import shutil

        shutil.copy(payload, cd / "folder.jpg")
        (cd / "cover.jpg").write_bytes(b"not-an-image")
        (cd / "t.flac").write_bytes(b"x")

        provider = MutagenArtworkProvider()

        def _broken_read(self_):
            raise OSError("io error on primary")

        monkeypatch.setattr(
            provider,
            "_probe_embedded",
            lambda path, *, front_only: ArtworkProbeObservation.absent(),
        )
        # cover.jpg falla al leer; folder.jpg se lee bien.
        original_read_bytes = Path.read_bytes

        def _selective_read(self_):
            if self_.name == "cover.jpg":
                raise OSError("io error on primary")
            return original_read_bytes(self_)

        monkeypatch.setattr(Path, "read_bytes", _selective_read)

        observation = provider.probe_album_artwork((cd / "t.flac",))

        assert observation.verdict is ArtworkProbeVerdict.FOUND
        assert observation.artwork.data == payload.read_bytes(), (
            "folder.jpg es el fallback válido ganador"
        )

    def test_unreadable_local_candidate_without_valid_fallback_is_unavailable(
        self,
        tmp_path,
        monkeypatch,
    ):
        """cover.jpg con error de lectura y SIN fallback → UNAVAILABLE
        (incertidumbre), NUNCA ABSENT_CONFIRMED."""
        cd = tmp_path / "CD"
        cd.mkdir()
        (cd / "cover.jpg").write_bytes(b"x")
        (cd / "t.flac").write_bytes(b"x")

        provider = MutagenArtworkProvider()
        monkeypatch.setattr(
            provider,
            "_probe_embedded",
            lambda path, *, front_only: ArtworkProbeObservation.absent(),
        )

        def _broken_read(self_):
            raise OSError("io error")

        monkeypatch.setattr(Path, "read_bytes", _broken_read)

        observation = provider.probe_album_artwork((cd / "t.flac",))

        assert observation.verdict is ArtworkProbeVerdict.UNAVAILABLE
        assert observation.artwork is None
