"""M6.8 scale baseline — synthetic 10,000-track dataset (tests/test_m6_scale.py).

The SCALE gate runs the REAL incremental machinery (LibraryService +
SqliteLibraryIndexRepository) against a SYNTHETIC dataset: no real files, no
Mutagen. A SyntheticScanner returns 10,000 paths with canned fingerprints and
a synthetic extractor returns deterministic TrackMetadata derived from the
path. This pins (§58 of the master plan):

- the initial incremental scan of 10k tracks completes within a GENEROUS
  time bound (60 s — a correctness gate, NOT micro-perf; M12 owns tuning)
- the persistent index holds exactly 10,000 rows
- an unchanged rescan performs ZERO extractions (metadata reuse AT SCALE)
- the model construction is coherent at scale: the sum of album track counts
  equals the track total, and artists/genres/composers/folders counts are
  consistent
- determinism: two identical 10k scans produce the IDENTICAL model

Any failure here is a REAL gap in the scale behavior of the machinery.
"""

import time
from pathlib import Path

from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.playback_session_service import PlaybackSessionService
from michi.application.queue_service import QueueService
from michi.domain.library import TrackMetadata
from michi.infrastructure.library_index import SqliteLibraryIndexRepository
from tests.conftest import FakeAudioPort

SCALE_TRACKS = 10_000
TRACKS_PER_ALBUM = 10
_SYNTHETIC_ROOT = "/synthetic"


def _scale_specs(count: int = SCALE_TRACKS) -> dict:
    """Deterministic synthetic specs: path -> (file_size, mtime_ns, TrackMetadata).

    10 tracks per album -> 1000 albums; artists cycle over 100, genres over
    7, composers over 13, years over 30. Deterministic by construction, so
    two independently generated datasets are IDENTICAL (the test 15 gate).
    """
    specs = {}
    for i in range(count):
        album_idx = i // TRACKS_PER_ALBUM
        track_idx = i % TRACKS_PER_ALBUM + 1
        path = str(
            Path(f"{_SYNTHETIC_ROOT}/album_{album_idx:04d}/track_{track_idx:02d}.mp3")
        )
        artist = f"Artist {album_idx % 100:03d}"
        specs[path] = (
            1000 + i,
            1_000_000 + i * 1_000,
            TrackMetadata(
                title=f"Track {album_idx:04d}-{track_idx:02d}",
                artist=artist,
                album=f"Album {album_idx:04d}",
                album_artist=artist,
                genre=f"Genre {album_idx % 7}",
                composer=f"Composer {i % 13}",
                track_number=track_idx,
                disc_number=1,
                duration_ms=180_000,
                year=1990 + album_idx % 30,
            ),
        )
    return specs


class SyntheticScanner:
    """LibraryScannerPort over the synthetic spec: NO filesystem access."""

    def __init__(self, specs: dict) -> None:
        self._specs = specs

    def scan(self, root):
        return [Path(p) for p in sorted(self._specs)]

    def fingerprint(self, path):
        size, mtime_ns, _ = self._specs[str(path)]
        return size, mtime_ns

    def validate_file(self, path):
        return None


class SyntheticExtractor:
    """MetadataExtractorPort over the synthetic spec; records every call."""

    def __init__(self, specs: dict) -> None:
        self._specs = specs
        self.calls = []

    def extract(self, file_path):
        self.calls.append(file_path)
        _, _, meta = self._specs[str(file_path)]
        return meta


def _make_library(tmp_path, scanner, extractor):
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService()
    _session = PlaybackSessionService(playback, queue)
    repo = SqliteLibraryIndexRepository(tmp_path / "michi.db")
    library = LibraryService(scanner, metadata_extractor=extractor, library_index=repo)
    return library, repo


class TestScale10k:
    def test_scale_10k_incremental_scan(self, tmp_path):
        """Initial incremental scan of 10k tracks (real index) completes within
        a generous bound; the index holds 10k rows; an unchanged rescan
        performs ZERO extractions; the model is coherent at scale."""
        specs = _scale_specs()
        assert len(specs) == SCALE_TRACKS
        scanner = SyntheticScanner(specs)
        extractor = SyntheticExtractor(specs)
        library, repo = _make_library(tmp_path, scanner, extractor)

        started = time.monotonic()
        library.scan(_SYNTHETIC_ROOT)

        assert len(library.state.tracks) == SCALE_TRACKS
        assert len(extractor.calls) == SCALE_TRACKS  # initial full extraction
        assert len(repo.load_all()) == SCALE_TRACKS  # the index holds 10k rows
        # Model coherent at scale.
        assert len(library.state.albums) == 1_000
        assert sum(a.track_count for a in library.state.albums) == SCALE_TRACKS
        assert len(library.state.artists) == 100
        assert sum(ar.track_count for ar in library.state.artists) == SCALE_TRACKS
        assert len(library.state.genres) == 7
        assert sum(g.track_count for g in library.state.genres) == SCALE_TRACKS
        assert len(library.state.composers) == 13
        assert sum(c.track_count for c in library.state.composers) == SCALE_TRACKS
        assert len(library.state.folders) == 1_000
        assert sum(f.track_count for f in library.state.folders) == SCALE_TRACKS

        # Unchanged rescan: ZERO extractions — metadata reuse AT SCALE.
        extractor.calls.clear()
        library.scan(_SYNTHETIC_ROOT)
        assert extractor.calls == []
        assert len(library.state.tracks) == SCALE_TRACKS
        assert len(repo.load_all()) == SCALE_TRACKS

        # Generous correctness gate (60 s) — NOT micro-perf (M12 owns tuning).
        assert time.monotonic() - started < 60

    def test_scale_10k_model_deterministic(self, tmp_path):
        """Two identical 10k scans produce the IDENTICAL model — canonical
        determinism at scale."""
        specs_a = _scale_specs()
        specs_b = _scale_specs()
        assert specs_a == specs_b  # the datasets are identical by construction

        library_a, _ = _make_library(
            tmp_path, SyntheticScanner(specs_a), SyntheticExtractor(specs_a)
        )
        (tmp_path / "b").mkdir()
        library_b, _ = _make_library(
            tmp_path / "b", SyntheticScanner(specs_b), SyntheticExtractor(specs_b)
        )

        started = time.monotonic()
        library_a.scan(_SYNTHETIC_ROOT)
        library_b.scan(_SYNTHETIC_ROOT)

        assert library_a.state.tracks == library_b.state.tracks
        assert library_a.state.albums == library_b.state.albums
        assert library_a.state.artists == library_b.state.artists
        assert library_a.state.genres == library_b.state.genres
        assert library_a.state.composers == library_b.state.composers
        assert library_a.state.folders == library_b.state.folders
        assert (
            library_a.state.recently_added_paths == library_b.state.recently_added_paths
        )
        # Generous bound for the two full 10k scans.
        assert time.monotonic() - started < 120
