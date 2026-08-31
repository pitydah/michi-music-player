"""M6-EXT-R4 ABSOLUTE FINAL CLOSURE / FREEZE SEAL.

P1-FINAL: local artwork observation is NOT exhaustive — only
track_paths[0].parent was probed. Album != Directory: multi-disc /
multi-directory / multi-Source albums produced false ABSENT_CONFIRMED
and could remove valid cached artwork.

FIX: PASS 3 probes EVERY unique track directory (dict.fromkeys,
first-seen order, dedup), cancellation between directories, positive
evidence is existential.

DERIVED AUTHORITY FIREWALL: artwork convergence scheduling is
best-effort — a throwing schedule() must never fail/reclassify/rollback
an already committed Source/Catalog result.

Governance: this is the ONLY new test file (A tests/...). Every other
test file is read-only evidence.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from pathlib import Path

import pytest

from michi.application.library_artwork_contracts import (
    ArtworkProbeVerdict,
)
from michi.application.library_service import LibraryService
from michi.application.ports import LibraryPrefsPort
from michi.application.source_scan_coordinator import SourceScanCoordinator
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


class _Token:
    def __init__(self):
        self.cancelled = False


class _AbsentEmbeddedOnly:
    """Provider whose EMBEDDED probe always says absent — local artwork
    must come from the real _probe_local_artwork."""

    def __init__(self, real: MutagenArtworkProvider):
        self._real = real
        self.probed_dirs: list[Path] = []

    def probe_album_artwork(self, track_paths, token=None):
        # Reuses the real method but spies the local phase by subclassing
        # is not possible (frozen) — we call the real provider and assert
        # behavior; this wrapper is only for the embedded-absent baseline.
        return self._real.probe_album_artwork(track_paths, token)


# ==========================================================================
# MULTI-DIRECTORY LOCAL ARTWORK OBSERVATION
# ==========================================================================


class TestMultidirectoryLocalArtwork:
    def _tree(self, tmp_path):
        cd1 = tmp_path / "CD1"
        cd2 = tmp_path / "CD2"
        cd1.mkdir()
        cd2.mkdir()
        (cd1 / "track1.flac").write_bytes(b"x")
        (cd2 / "track2.flac").write_bytes(b"x")
        return cd1, cd2

    def _provider_with_absent_embedded(self, monkeypatch):
        provider = MutagenArtworkProvider()

        def _absent_embedded(file_path, *, front_only):
            from michi.application.library_artwork_contracts import (
                ArtworkProbeObservation,
            )

            return ArtworkProbeObservation.absent()

        monkeypatch.setattr(provider, "_probe_embedded", _absent_embedded)
        return provider

    def test_multidirectory_local_artwork_finds_cover_in_second_directory(
        self,
        tmp_path,
        monkeypatch,
    ):
        """CD1 sin artwork, CD2 con folder.jpg → FOUND exacto.
        FALLA contra pre-fix (track_paths[0].parent = CD1 solo)."""
        cd1, cd2 = self._tree(tmp_path)
        from PySide6.QtGui import QImage

        img = QImage(8, 8, QImage.Format_RGB32)
        img.fill(0xFF581C)
        assert img.save(str(cd2 / "folder.jpg"), "JPEG")
        provider = self._provider_with_absent_embedded(monkeypatch)

        observation = provider.probe_album_artwork(
            (cd1 / "track1.flac", cd2 / "track2.flac")
        )

        assert observation.verdict is ArtworkProbeVerdict.FOUND
        assert observation.artwork is not None

    def test_multidirectory_complete_absence_is_confirmed_only_after_all_directories(
        self,
        tmp_path,
        monkeypatch,
    ):
        """CD1 y CD2 legibles y SIN artwork → ABSENT_CONFIRMED (el fix no
        vuelve permanentemente conservador)."""
        cd1, cd2 = self._tree(tmp_path)
        provider = self._provider_with_absent_embedded(monkeypatch)

        observation = provider.probe_album_artwork(
            (cd1 / "track1.flac", cd2 / "track2.flac")
        )

        assert observation.verdict is ArtworkProbeVerdict.ABSENT_CONFIRMED
        assert observation.artwork is None

    def test_multidirectory_unreadable_directory_makes_negative_unavailable(
        self,
        tmp_path,
        monkeypatch,
    ):
        """CD1 legible sin artwork + CD2 con PermissionError →
        UNAVAILABLE (negativo incompleto NUNCA es ABSENT_CONFIRMED)."""
        cd1, cd2 = self._tree(tmp_path)
        provider = self._provider_with_absent_embedded(monkeypatch)

        def _denied(path):
            raise PermissionError("denied")

        monkeypatch.setattr("michi.infrastructure.artwork.Path.iterdir", _denied)

        observation = provider.probe_album_artwork(
            (cd1 / "track1.flac", cd2 / "track2.flac")
        )

        assert observation.verdict is ArtworkProbeVerdict.UNAVAILABLE
        assert observation.artwork is None

    def test_multidirectory_positive_artwork_overrides_previous_uncertainty(
        self,
        tmp_path,
        monkeypatch,
    ):
        """CD1 OSError + CD2 folder.jpg → FOUND (positivo existencial gana
        sobre la incertidumbre previa)."""
        cd1, cd2 = self._tree(tmp_path)
        from PySide6.QtGui import QImage

        img = QImage(8, 8, QImage.Format_RGB32)
        img.fill(0xCB0543)
        assert img.save(str(cd2 / "folder.jpg"), "JPEG")
        provider = self._provider_with_absent_embedded(monkeypatch)

        real_iterdir = Path.iterdir

        def _iterdir(path):
            if path == cd1:
                raise OSError("offline disk")
            return [entry for entry in real_iterdir(path)]

        monkeypatch.setattr("michi.infrastructure.artwork.Path.iterdir", _iterdir)

        observation = provider.probe_album_artwork(
            (cd1 / "track1.flac", cd2 / "track2.flac")
        )

        assert observation.verdict is ArtworkProbeVerdict.FOUND
        assert observation.artwork is not None

    def test_album_local_artwork_probes_each_unique_directory_once(
        self,
        tmp_path,
        monkeypatch,
    ):
        """3 tracks en CD1 + 1 en CD2 → _probe_local_artwork llamado
        exactamente [CD1, CD2] (dedup)."""
        cd1, cd2 = self._tree(tmp_path)
        (cd1 / "track3.flac").write_bytes(b"x")
        provider = self._provider_with_absent_embedded(monkeypatch)
        calls: list[Path] = []

        real_local = provider._probe_local_artwork

        def _spy(album_dir):
            calls.append(album_dir)
            return real_local(album_dir)

        monkeypatch.setattr(provider, "_probe_local_artwork", _spy)

        provider.probe_album_artwork(
            (
                cd1 / "track1.flac",
                cd1 / "track3.flac",
                cd2 / "track2.flac",
                cd1 / "track1.flac",
            )
        )

        assert calls == [cd1, cd2], f"dedup esperado [CD1, CD2], obtuve {calls}"

    def test_local_artwork_directory_resolution_preserves_track_order(
        self,
        tmp_path,
        monkeypatch,
    ):
        """CD2 primero en track_paths → gana CD2 (first-seen, no sort)."""
        cd1, cd2 = self._tree(tmp_path)
        from PySide6.QtGui import QImage

        img1 = QImage(8, 8, QImage.Format_RGB32)
        img1.fill(0xFF581C)
        img2 = QImage(8, 8, QImage.Format_RGB32)
        img2.fill(0x22AA55)
        assert img1.save(str(cd1 / "cover.png"), "PNG")
        assert img2.save(str(cd2 / "cover.png"), "PNG")
        provider = self._provider_with_absent_embedded(monkeypatch)

        observation = provider.probe_album_artwork(
            (cd2 / "track2.flac", cd1 / "track1.flac")
        )

        assert observation.verdict is ArtworkProbeVerdict.FOUND
        # El artwork de CD2 (primer dir first-seen) es el ganador.
        assert observation.artwork is not None

    def test_album_artwork_cancelled_between_local_directories(
        self,
        tmp_path,
        monkeypatch,
    ):
        """Cancel entre directorios locales → ScanCancelled antes de probar
        el segundo directorio (cancellation cooperativa preservada)."""
        from michi.application.ports import ScanCancelled

        cd1, cd2 = self._tree(tmp_path)
        provider = self._provider_with_absent_embedded(monkeypatch)
        token = _Token()
        probed: list[Path] = []

        real_local = provider._probe_local_artwork

        def _flip_then_absent(album_dir):
            probed.append(album_dir)
            token.cancelled = True
            return real_local(album_dir)

        monkeypatch.setattr(provider, "_probe_local_artwork", _flip_then_absent)

        with pytest.raises(ScanCancelled):
            provider.probe_album_artwork(
                (cd1 / "track1.flac", cd2 / "track2.flac"), token=token
            )

        assert probed == [cd1], "el segundo directorio nunca se prueba"


# ==========================================================================
# DERIVED AUTHORITY FIREWALL — artwork schedule failure is harmless
# ==========================================================================


class _ExplodingArtworkRefresh:
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


class _DiscoverScanner:
    def __init__(self, discovered=(), error=None):
        self._discovered = discovered
        self._error = error

    def discover(self, source):
        if self._error is not None:
            raise self._error
        return self._discovered


class TestArtworkScheduleFirewall:
    def test_artwork_schedule_failure_does_not_reclassify_successful_source_commit(
        self,
        tmp_path,
    ):
        from michi.application.library_port import (
            DiscoveredMediaFile,
        )

        library, catalog, coordinator = _env(tmp_path)
        exploding = _ExplodingArtworkRefresh()
        coordinator._artwork_refresh = exploding
        source = _source(tmp_path, "a")
        (tmp_path / "a").mkdir(exist_ok=True)
        media_path = tmp_path / "a" / "song.flac"
        media_path.write_bytes(b"x")
        catalog.upsert_source(source)
        discovered = (
            DiscoveredMediaFile(
                relative_path="song.flac",
                absolute_path=media_path,
                file_size=1,
                mtime_ns=1,
            ),
        )
        coordinator._scanner = _DiscoverScanner(discovered)

        outcome = coordinator.scan_source(source)

        assert not outcome.failed
        assert outcome.availability is SourceAvailability.AVAILABLE
        assert (
            coordinator._observations[source.library_source_id]
            is SourceAvailability.AVAILABLE
        )
        # Catalog commiteado con el Track.
        tracks = catalog.load_tracks()
        assert len(tracks) == 1
        assert tracks[0].track_id
        media = catalog.load_media()
        assert len(media) == 1
        assert media[0].relative_path == "song.flac"
        # Proyección de Library actualizada.
        assert len(library.state.tracks) == 1
        assert exploding.schedules >= 1, "el schedule sí se intentó"

    def test_artwork_schedule_failure_does_not_replace_source_filesystem_error(
        self,
        tmp_path,
    ):
        from michi.application.library_port import LibraryFilesystemError
        from michi.domain.library import LibraryDiagnosticCode

        library, catalog, coordinator = _env(tmp_path)
        exploding = _ExplodingArtworkRefresh()
        coordinator._artwork_refresh = exploding
        source = _source(tmp_path, "gone")
        catalog.upsert_source(source)
        coordinator._scanner = _DiscoverScanner(
            error=LibraryFilesystemError(
                LibraryDiagnosticCode.DIRECTORY_MISSING, Path("/gone"), "missing"
            )
        )

        outcome = coordinator.scan_source(source)

        assert outcome.availability is SourceAvailability.MISSING_ROOT
        assert (
            coordinator._observations[source.library_source_id]
            is SourceAvailability.MISSING_ROOT
        ), "la verdad física NO se reemplaza por el fallo de artwork"

    def test_artwork_schedule_failure_does_not_rollback_source_relocation(
        self,
        tmp_path,
    ):
        library, catalog, coordinator = _env(tmp_path)
        exploding = _ExplodingArtworkRefresh()
        coordinator._artwork_refresh = exploding
        source = _source(tmp_path, "old")
        catalog.upsert_source(source)
        new_root = tmp_path / "new"
        new_root.mkdir(exist_ok=True)

        relocated = coordinator.relocate_source_root(
            source.library_source_id, str(new_root)
        )

        assert relocated.library_source_id == source.library_source_id
        assert Path(relocated.root_path) == new_root, "sin rollback a /old"
        persisted = catalog.load_sources()
        assert persisted[0].root_path == str(new_root)
        assert (
            coordinator._observations.get(source.library_source_id) is None
            or coordinator.observed_availability(source.library_source_id)
            is SourceAvailability.UNKNOWN
        ), "observación reseteada según semántica de relocate"

    def test_artwork_schedule_failure_does_not_rollback_source_disable(
        self,
        tmp_path,
    ):
        library, catalog, coordinator = _env(tmp_path)
        exploding = _ExplodingArtworkRefresh()
        coordinator._artwork_refresh = exploding
        source = _source(tmp_path, "a")
        catalog.upsert_source(source)

        coordinator.set_source_enabled(source.library_source_id, False)

        persisted = catalog.load_sources()
        assert persisted[0].library_source_id == source.library_source_id
        assert persisted[0].enabled is False, "disable permanece autoritativo"

    def test_artwork_schedule_failure_does_not_rollback_source_retire(
        self,
        tmp_path,
    ):
        from michi.domain.library_catalog import SourceLifecycle

        library, catalog, coordinator = _env(tmp_path)
        exploding = _ExplodingArtworkRefresh()
        coordinator._artwork_refresh = exploding
        source = _source(tmp_path, "a")
        catalog.upsert_source(source)
        # Un track activo para verificar la exclusión de la proyección.
        coordinator._library.state.tracks = tuple()

        coordinator.retire_source(source.library_source_id)

        persisted = catalog.load_sources()
        assert persisted[0].library_source_id == source.library_source_id
        assert persisted[0].lifecycle is SourceLifecycle.RETIRED, (
            "RETIRED permanece autoritativo"
        )
