"""M6.8 golden dataset — REAL-pipeline pins on a real directory tree.

This file encodes the M6.8 golden contract (§53-57 of the master plan): a
builder produces a REAL directory tree (real files, REAL Mutagen tags, REAL
artwork bytes) and the gates run the REAL pipeline end-to-end —
FilesystemLibraryScanner + InfrastructureMetadataExtractor +
SqliteLibraryIndexRepository — plus the FakeScanPipeline async drive for the
M6.4 supersession pin and the LibraryBridge for the M6.6/M6.7 selection pins.

The golden dataset exercises every identity, ordering and degradation rule:

- a single-disc album (3 tracks, track numbers)
- a multi-disc album (2 FLAC discs — canonical (disc, track) ordering; the
  file names are deliberately track-major so the SCAN order differs from the
  canonical order)
- a compilation (Various Artists with explicit album_artist)
- an explicit-album_artist album
- a missing-album_artist album (falls back to the track artist)
- a composer-tagged track
- an untagged file (stem fallback)
- the same album title with different artists (2 albums)
- the same artist with case variations (ONE artist identity)
- duplicate track titles (different paths)
- unknown track/disc numbers (M6.1 UNKNOWN-last determinism)
- different years (canonical timeline decades)
- MP3 + FLAC formats (per AUDIO_EXTENSIONS)
- embedded artwork (front), folder artwork (cover.jpg), no artwork, and
  modified artwork (the second scan — M6.5 digest-aware cache invalidation)
- the mutation set (added file, modified audio file, removed audio file)

The machinery exists (full suite 949 passed at HEAD 5ddb206) — these pins
should be GREEN. Any failure is a REAL gap in the production machinery, not
a harness artifact, and must be reported with its evidence.
"""

import gc
from dataclasses import dataclass
from pathlib import Path

from mutagen.flac import FLAC
from mutagen.id3 import APIC
from mutagen.mp3 import MP3, EasyMP3

from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.playback_session_service import PlaybackSessionService
from michi.application.ports import (
    MetadataExtractionError,
    ScanCancelToken,
    ScanProgress,
)
from michi.application.queue_service import QueueService
from michi.domain.library import (
    LibraryDiagnosticCode,
    LibraryScanStatus,
    build_timeline_projection,
)
from michi.infrastructure.artwork import ArtworkCache, MutagenArtworkProvider
from michi.infrastructure.filesystem_scanner import FilesystemLibraryScanner
from michi.infrastructure.library_index import SqliteLibraryIndexRepository
from michi.infrastructure.metadata_extractor import InfrastructureMetadataExtractor
from michi.presentation.library_bridge import LibraryBridge
from tests.conftest import FakeAudioPort
from tests.test_library_async import FakeScanPipeline
from tests.test_library_incremental import _bump_mtime
from tests.test_metadata_extractor import MP3_FRAME, _flac_streaminfo

# ---------------------------------------------------------------------------
# Golden dataset builder — a REAL directory tree with REAL tags/artwork.
# ---------------------------------------------------------------------------

# Minimal 1x1 PNG / JPEG payloads (content is irrelevant, only bytes matter).
PNG_1x1 = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
PNG_1x1_ALT = b"\x89PNG\r\n\x1a\n" + b"\xff" * 20
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 16

_GOLDEN_TRACK_COUNT = 29


def _make_mp3(path: Path, tags: dict | None = None) -> Path:
    """Minimal tagged MP3 (easy-style rich tags through EasyMP3)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(MP3_FRAME * 4)
    if tags:
        audio = EasyMP3(str(path))
        for key, value in tags.items():
            audio[key] = value
        audio.save()
    return path


def _make_flac(path: Path, tags: dict | None = None) -> Path:
    """Minimal tagged FLAC (native Vorbis-comment dict)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"fLaC" + bytes([0x80]) + (34).to_bytes(3, "big") + _flac_streaminfo()
    )
    if tags:
        audio = FLAC(str(path))
        for key, value in tags.items():
            audio[key] = value
        audio.save()
    return path


def _tag_mp3_artwork(
    path: Path, data: bytes, mime: str = "image/png", type_: int = 3
) -> None:
    """Replace the embedded artwork of an MP3 with ``data`` (APIC frame).

    The file may already carry an ID3 tag (from _make_mp3's EasyMP3 tagging):
    ``add_tags()`` raises when tags already exist, so it must be guarded.
    """
    audio = MP3(str(path))
    if audio.tags is None:
        audio.add_tags()
    audio.tags.delall("APIC")
    audio.tags.add(APIC(encoding=3, mime=mime, type=type_, desc="", data=data))
    audio.save()


def _multi_tags(track: int, disc: int) -> dict:
    """Multi-disc track tags: title encodes (track, disc); canonical numbers."""
    return {
        "title": f"T{track}D{disc}",
        "artist": "Multi Artist",
        "album": "Multi Disc",
        "albumartist": "Multi Artist",
        "tracknumber": str(track),
        "discnumber": str(disc),
        "genre": "Electronic",
        "composer": "M. Composer",
        "date": "1999-01-01",
    }


@dataclass(frozen=True)
class GoldenDataset:
    root: Path
    single: tuple[Path, ...]
    multi: tuple[Path, ...]
    compilation: tuple[Path, ...]
    explicit_aa: tuple[Path, ...]
    missing_aa: tuple[Path, ...]
    composer: tuple[Path, ...]
    untagged: tuple[Path, ...]
    same_title: tuple[Path, ...]
    case_variations: tuple[Path, ...]
    duplicates: tuple[Path, ...]
    unknown_numbers: tuple[Path, ...]
    years: tuple[Path, ...]
    embedded_art: tuple[Path, ...]
    folder_art: tuple[Path, ...]
    no_art: tuple[Path, ...]
    all_paths: tuple[Path, ...]
    scan_order: tuple[Path, ...]


def build_golden(tmp_path: Path) -> GoldenDataset:
    """Build the golden directory tree; return the structured dataset.

    ``scan_order`` is the REAL scanner's discovery order (self-verifying: the
    builder proves every produced file is recognized by AUDIO_EXTENSIONS).
    """
    root = tmp_path / "golden"

    # 1. Single-disc album: 3 MP3 tracks, track numbers, genre, composer.
    single = (
        _make_mp3(
            root / "single" / "01 Intro.mp3",
            {
                "title": "Intro",
                "artist": "Single Artist",
                "album": "Single Disc",
                "tracknumber": "1",
                "genre": "Rock",
                "composer": "S. Composer",
                "date": "2005-03-01",
            },
        ),
        _make_mp3(
            root / "single" / "02 Middle.mp3",
            {
                "title": "Middle",
                "artist": "Single Artist",
                "album": "Single Disc",
                "tracknumber": "2",
                "genre": "Rock",
                "composer": "S. Composer",
                "date": "2005-03-01",
            },
        ),
        _make_mp3(
            root / "single" / "03 Outro.mp3",
            {
                "title": "Outro",
                "artist": "Single Artist",
                "album": "Single Disc",
                "tracknumber": "3",
                "genre": "Rock",
                "composer": "S. Composer",
                "date": "2005-03-01",
            },
        ),
    )

    # 2. Multi-disc album: 2 FLAC discs, declared in CANONICAL (disc, track)
    # order. The file names are track-major ("t1-d1", "t1-d2", "t2-d1",
    # "t2-d2") so the lexicographic SCAN order differs from the canonical
    # order — the model must canonicalize, never follow the scan.
    multi = (
        _make_flac(root / "multi" / "t1-d1.flac", _multi_tags(1, 1)),
        _make_flac(root / "multi" / "t2-d1.flac", _multi_tags(2, 1)),
        _make_flac(root / "multi" / "t1-d2.flac", _multi_tags(1, 2)),
        _make_flac(root / "multi" / "t2-d2.flac", _multi_tags(2, 2)),
    )

    # 3. Compilation: ONE album, explicit album_artist "Various Artists",
    # per-track artists preserved.
    compilation = (
        _make_mp3(
            root / "compilation" / "va-one.mp3",
            {
                "title": "Compilation One",
                "artist": "Performer One",
                "album": "Compilation Album",
                "albumartist": "Various Artists",
                "tracknumber": "1",
                "genre": "Pop",
                "date": "2015-05-05",
            },
        ),
        _make_mp3(
            root / "compilation" / "va-two.mp3",
            {
                "title": "Compilation Two",
                "artist": "Performer Two",
                "album": "Compilation Album",
                "albumartist": "Various Artists",
                "tracknumber": "2",
                "genre": "Pop",
                "date": "2015-05-05",
            },
        ),
    )

    # 4. Explicit album_artist album.
    explicit_aa = (
        _make_mp3(
            root / "explicit" / "one.mp3",
            {
                "title": "Explicit One",
                "artist": "Solo Performer",
                "album": "Explicit AA Album",
                "albumartist": "The Band",
                "tracknumber": "1",
                "genre": "Rock",
                "date": "2010-10-10",
            },
        ),
    )

    # 5. Missing album_artist album: falls back to the track artist.
    missing_aa = (
        _make_mp3(
            root / "missing-aa" / "two.mp3",
            {
                "title": "No AA Two",
                "artist": "Track Singer",
                "album": "No AA Album",
                "tracknumber": "1",
                "date": "2012-12-12",
            },
        ),
    )

    # 6. Composer-tagged track.
    composer = (
        _make_mp3(
            root / "composer" / "one.mp3",
            {
                "title": "Composer Piece",
                "artist": "Composer Artist",
                "album": "Composer Album",
                "tracknumber": "1",
                "composer": "C. Composer",
                "genre": "Classical",
                "date": "2008-08-08",
            },
        ),
    )

    # 7. Untagged file: missing metadata -> stem fallback (Unknown Album).
    untagged = (_make_mp3(root / "untagged" / "UntaggedTrack.mp3"),)

    # 8. Same album title, different artists -> TWO albums.
    same_title = (
        _make_mp3(
            root / "same-title" / "a.mp3",
            {
                "title": "A Side",
                "artist": "Band A",
                "album": "Best Of",
                "tracknumber": "1",
                "genre": "Pop",
                "date": "2000-01-01",
            },
        ),
        _make_mp3(
            root / "same-title" / "b.mp3",
            {
                "title": "B Side",
                "artist": "Band B",
                "album": "Best Of",
                "tracknumber": "1",
                "genre": "Jazz",
                "composer": "B. Composer",
                "date": "2000-01-01",
            },
        ),
    )

    # 9. Same artist, case variations -> ONE artist identity.
    case_variations = (
        _make_mp3(
            root / "case-variation" / "one.mp3",
            {
                "title": "Case One",
                "artist": "The Artist",
                "album": "Case Album",
                "tracknumber": "1",
            },
        ),
        _make_mp3(
            root / "case-variation" / "two.mp3",
            {
                "title": "Case Two",
                "artist": "THE ARTIST",
                "album": "Case Album",
                "tracknumber": "2",
            },
        ),
    )

    # 10. Duplicate track titles, different paths.
    duplicates = (
        _make_mp3(
            root / "duplicates" / "a.mp3",
            {
                "title": "Chorus",
                "artist": "Dup Artist",
                "album": "Duplicates",
                "tracknumber": "1",
                "genre": "Rock",
                "date": "1990-01-01",
            },
        ),
        _make_mp3(
            root / "duplicates" / "b.mp3",
            {
                "title": "Chorus",
                "artist": "Dup Artist",
                "album": "Duplicates",
                "tracknumber": "2",
                "genre": "Rock",
                "date": "1990-01-01",
            },
        ),
    )

    # 11. Unknown track/disc numbers: the 00-* files SCAN FIRST (lexicographic)
    # but must sort LAST deterministically (M6.1 UNKNOWN-last rule).
    unknown_numbers = (
        _make_mp3(
            root / "unknown" / "00-Zulu.mp3",
            {
                "title": "Zulu",
                "artist": "Order Artist",
                "album": "Ordered",
            },
        ),
        _make_mp3(
            root / "unknown" / "00-Alpha.mp3",
            {
                "title": "Alpha",
                "artist": "Order Artist",
                "album": "Ordered",
            },
        ),
        _make_mp3(
            root / "unknown" / "01 Known.mp3",
            {
                "title": "Known",
                "artist": "Order Artist",
                "album": "Ordered",
                "tracknumber": "1",
            },
        ),
        _make_mp3(
            root / "unknown" / "02 Known2.mp3",
            {
                "title": "Known2",
                "artist": "Order Artist",
                "album": "Ordered",
                "tracknumber": "2",
            },
        ),
    )

    # 12. Different years -> canonical timeline decades.
    years = (
        _make_mp3(
            root / "years" / "1985-retro.mp3",
            {
                "title": "Retro Track",
                "artist": "Year Artist",
                "album": "Retro",
                "genre": "Rock",
                "date": "1985-06-01",
            },
        ),
        _make_mp3(
            root / "years" / "2001-millennium.mp3",
            {
                "title": "Millennium Track",
                "artist": "Year Artist",
                "album": "Millennium",
                "genre": "Electronic",
                "date": "2001-01-15",
            },
        ),
        _make_mp3(
            root / "years" / "2019-modern.mp3",
            {
                "title": "Modern Track",
                "artist": "Year Artist",
                "album": "Modern",
                "genre": "Pop",
                "date": "2019-12-31",
            },
        ),
    )

    # 13. Artwork: embedded front, folder cover.jpg, none.
    embedded_art = (
        _make_mp3(
            root / "art-embedded" / "one.mp3",
            {
                "title": "Embedded One",
                "artist": "Art Artist",
                "album": "Embedded Art",
                "tracknumber": "1",
                "date": "2018-01-01",
            },
        ),
    )
    _tag_mp3_artwork(embedded_art[0], PNG_1x1)  # APIC front cover (type 3)
    folder_art = (
        _make_mp3(
            root / "art-folder" / "one.mp3",
            {
                "title": "Folder One",
                "artist": "Art Artist",
                "album": "Folder Art",
                "tracknumber": "1",
                "date": "2018-01-01",
            },
        ),
    )
    (root / "art-folder" / "cover.jpg").write_bytes(JPEG_BYTES)
    no_art = (
        _make_mp3(
            root / "art-none" / "one.mp3",
            {
                "title": "None One",
                "artist": "Art Artist",
                "album": "No Art",
                "tracknumber": "1",
                "date": "2018-01-01",
            },
        ),
    )

    # Self-verification via the REAL scanner: every file is recognized and the
    # discovery order is the machine's own (sorted rglob).
    scanner = FilesystemLibraryScanner()
    scan_order = tuple(scanner.scan(root))
    assert len(scan_order) == _GOLDEN_TRACK_COUNT, (
        f"golden builder drift: expected {_GOLDEN_TRACK_COUNT} tracks, "
        f"scanner found {len(scan_order)}"
    )
    return GoldenDataset(
        root=root,
        single=single,
        multi=multi,
        compilation=compilation,
        explicit_aa=explicit_aa,
        missing_aa=missing_aa,
        composer=composer,
        untagged=untagged,
        same_title=same_title,
        case_variations=case_variations,
        duplicates=duplicates,
        unknown_numbers=unknown_numbers,
        years=years,
        embedded_art=embedded_art,
        folder_art=folder_art,
        no_art=no_art,
        all_paths=scan_order,
        scan_order=scan_order,
    )


# ---------------------------------------------------------------------------
# Harness helpers — the extraction is ALWAYS the real Mutagen extractor.
# ---------------------------------------------------------------------------


class SpyExtractor:
    """Wraps the real InfrastructureMetadataExtractor: records every extract()
    call and may raise MetadataExtractionError for a designated failing set
    (the M6.8 malformed-file gate). Extraction RESULTS are never faked."""

    def __init__(self, inner=None, failing=()):
        self.inner = inner if inner is not None else InfrastructureMetadataExtractor()
        self.failing = set(failing)
        self.calls = []

    def extract(self, file_path):
        self.calls.append(file_path)
        if file_path in self.failing:
            raise MetadataExtractionError(file_path, "malformed audio file")
        return self.inner.extract(file_path)


def _make_library(
    tmp_path,
    scanner,
    extractor,
    *,
    artwork_provider=None,
    artwork_cache=None,
    pipeline=None,
):
    """Build LibraryService with a real queue, index and optional pipeline."""
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService()
    _session = PlaybackSessionService(playback, queue)
    repo = SqliteLibraryIndexRepository(tmp_path / "michi.db")
    library = LibraryService(
        scanner,
        metadata_extractor=extractor,
        artwork_provider=artwork_provider,
        artwork_cache=artwork_cache,
        library_index=repo,
        scan_pipeline=pipeline,
    )
    return library, repo


# ---------------------------------------------------------------------------
# The gates.
# ---------------------------------------------------------------------------


class TestGoldenRestart:
    def test_golden_restart_reuses_index(self, tmp_path):
        """Initial scan -> DESTROY the graph -> NEW graph on the SAME db ->
        zero extractions; the model matches graph 1 exactly."""
        golden = build_golden(tmp_path)

        scanner1 = FilesystemLibraryScanner()
        extractor1 = SpyExtractor()
        library1, repo1 = _make_library(tmp_path, scanner1, extractor1)
        library1.scan(str(golden.root))

        assert extractor1.calls == list(golden.all_paths)  # full extraction
        assert len(repo1.load_all()) == _GOLDEN_TRACK_COUNT
        before = (
            list(library1.state.tracks),
            library1.state.albums,
            library1.state.artists,
            library1.state.genres,
            library1.state.composers,
            library1.state.folders,
        )

        # DESTROY the graph; the database file survives.
        del library1, repo1, scanner1, extractor1
        gc.collect()

        # NEW graph on the SAME database.
        scanner2 = FilesystemLibraryScanner()
        extractor2 = SpyExtractor()
        library2, repo2 = _make_library(tmp_path, scanner2, extractor2)
        library2.scan(str(golden.root))

        # THE gate: an unchanged restart performs ZERO extractions — the index
        # metadata is reused.
        assert extractor2.calls == []
        after = (
            list(library2.state.tracks),
            library2.state.albums,
            library2.state.artists,
            library2.state.genres,
            library2.state.composers,
            library2.state.folders,
        )
        # tracks/albums/artists/genres/composers/folders coherent
        assert after == before
        assert len(repo2.load_all()) == _GOLDEN_TRACK_COUNT


class TestGoldenIncremental:
    def test_golden_incremental_delta(self, tmp_path):
        """Initial scan -> mutate (+A tagged, -B, modify C: bump mtime + re-tag)
        -> rescan: extraction for {A, C} ONLY; B absent everywhere; the index
        rows match the final file set."""
        golden = build_golden(tmp_path)
        scanner = FilesystemLibraryScanner()
        extractor = SpyExtractor()
        library, repo = _make_library(tmp_path, scanner, extractor)

        library.scan(str(golden.root))
        assert len(extractor.calls) == _GOLDEN_TRACK_COUNT

        # The mutation set.
        encore = golden.root / "single" / "04 Encore.mp3"  # +A: new tagged file
        _make_mp3(
            encore,
            {
                "title": "Encore",
                "artist": "Single Artist",
                "album": "Single Disc",
                "tracknumber": "4",
                "genre": "Rock",
                "composer": "S. Composer",
                "date": "2005-03-01",
            },
        )
        removed_b = golden.same_title[1]  # -B: "Best Of" / Band B
        removed_b.unlink()
        modified_c = golden.duplicates[1]  # modify C: bump mtime + re-tag
        audio = EasyMP3(str(modified_c))
        audio["title"] = "Chorus (Live)"
        audio.save()
        _bump_mtime(modified_c)

        extractor.calls.clear()
        library.scan(str(golden.root))

        # The golden delta: extraction ONLY for added A and modified C.
        assert set(extractor.calls) == {encore, modified_c}
        final_paths = set(golden.all_paths) - {removed_b} | {encore}
        assert {t.file_path for t in library.state.tracks} == final_paths
        assert len(library.state.tracks) == _GOLDEN_TRACK_COUNT

        # B absent from the model: no album/artist/genre/composer/folder refs.
        assert removed_b not in {
            tp for al in library.state.albums for tp in al.track_paths
        }
        assert "Band B" not in [a.artist for a in library.state.albums]
        assert "Band B" not in [ar.name for ar in library.state.artists]
        assert "Jazz" not in [g.name for g in library.state.genres]
        assert "B. Composer" not in [c.name for c in library.state.composers]
        assert removed_b.name not in str(library.state.folders)
        # The Best Of title survives via Band A (the B album is gone).
        best_of = [a for a in library.state.albums if a.title == "Best Of"]
        assert len(best_of) == 1
        assert best_of[0].artist == "Band A"
        # Modified C is in the model with its FRESH metadata.
        c_ref = next(t for t in library.state.tracks if t.file_path == modified_c)
        assert c_ref.title == "Chorus (Live)"
        # Index rows == the final file set.
        assert {e.track_id for e in repo.load_all()} == {str(p) for p in final_paths}
        assert len(repo.load_all()) == _GOLDEN_TRACK_COUNT
        # Coherence + recently-added delta semantics.
        assert (
            sum(al.track_count for al in library.state.albums)
            == len(library.state.tracks)
            == _GOLDEN_TRACK_COUNT
        )
        assert str(encore) in library.state.recently_added_paths
        assert str(removed_b) not in library.state.recently_added_paths


class TestGoldenOrderingPins:
    def test_golden_multi_disc_canonical_ordering(self, tmp_path):
        golden = build_golden(tmp_path)
        library, _ = _make_library(tmp_path, FilesystemLibraryScanner(), SpyExtractor())
        library.scan(str(golden.root))

        album = next(a for a in library.state.albums if a.title == "Multi Disc")
        assert album.disc_count == 2
        assert album.track_count == 4
        # The scan order is deliberately NOT canonical (track-major names).
        multi_paths = {str(p) for p in golden.multi}
        scan_order = [p for p in golden.scan_order if str(p) in multi_paths]
        assert [p.name for p in scan_order] == [
            "t1-d1.flac",
            "t1-d2.flac",
            "t2-d1.flac",
            "t2-d2.flac",
        ]
        # The model follows the canonical (disc, track) order, NOT the scan.
        assert list(album.track_paths) == list(golden.multi)
        refs = {t.file_path: t for t in library.state.tracks}
        assert [
            (refs[p].disc_number, refs[p].track_number) for p in album.track_paths
        ] == [
            (1, 1),
            (1, 2),
            (2, 1),
            (2, 2),
        ]
        # FLAC format proof: the real FLAC extraction reads a 60 s stream.
        assert album.duration_ms == 4 * 60_000

    def test_golden_compilation_various_artists(self, tmp_path):
        golden = build_golden(tmp_path)
        library, _ = _make_library(tmp_path, FilesystemLibraryScanner(), SpyExtractor())
        library.scan(str(golden.root))

        albums = [a for a in library.state.albums if a.title == "Compilation Album"]
        assert len(albums) == 1  # ONE album
        assert albums[0].artist == "Various Artists"
        assert albums[0].track_count == 2
        assert set(albums[0].track_paths) == set(golden.compilation)
        # The per-track artists are preserved in the model.
        artist_names = {ar.name for ar in library.state.artists}
        assert {"Performer One", "Performer Two"} <= artist_names
        track_artists = {
            t.artist for t in library.state.tracks if t.album == "Compilation Album"
        }
        assert track_artists == {"Performer One", "Performer Two"}

    def test_golden_artist_case_variations_one_identity(self, tmp_path):
        golden = build_golden(tmp_path)
        library, _ = _make_library(tmp_path, FilesystemLibraryScanner(), SpyExtractor())
        library.scan(str(golden.root))

        matches = [ar for ar in library.state.artists if ar.key == "the artist"]
        assert len(matches) == 1  # ONE identity across the case variations
        assert matches[0].track_count == 2
        assert matches[0].album_count == 1
        album = next(a for a in library.state.albums if a.title == "Case Album")
        assert album.track_count == 2
        assert set(album.track_paths) == set(golden.case_variations)

    def test_golden_duplicate_titles_distinct_paths(self, tmp_path):
        golden = build_golden(tmp_path)
        library, _ = _make_library(tmp_path, FilesystemLibraryScanner(), SpyExtractor())
        library.scan(str(golden.root))

        chorus = [t for t in library.state.tracks if t.title == "Chorus"]
        assert len(chorus) == 2  # two DISTINCT tracks with the same title
        assert {t.file_path for t in chorus} == set(golden.duplicates)
        album = next(a for a in library.state.albums if a.title == "Duplicates")
        assert album.track_count == 2
        assert set(album.track_paths) == set(golden.duplicates)

    def test_golden_unknown_numbers_deterministic(self, tmp_path):
        golden = build_golden(tmp_path)
        library, _ = _make_library(tmp_path, FilesystemLibraryScanner(), SpyExtractor())
        library.scan(str(golden.root))

        album = next(a for a in library.state.albums if a.title == "Ordered")
        # 00-* files scan FIRST (lexicographic) but sort LAST (UNKNOWN-last):
        # known numbered tracks first, then Alpha before Zulu (title order).
        assert list(album.track_paths) == [
            golden.unknown_numbers[2],  # 01 Known
            golden.unknown_numbers[3],  # 02 Known2
            golden.unknown_numbers[1],  # 00-Alpha
            golden.unknown_numbers[0],  # 00-Zulu
        ]
        unknown_dir = golden.unknown_numbers[0].parent
        scanned_here = [p for p in golden.scan_order if p.parent == unknown_dir]
        assert scanned_here[0] == golden.unknown_numbers[1]  # 00-Alpha scans FIRST
        assert album.track_paths[-1] == golden.unknown_numbers[0]  # ...sorts LAST
        # Deterministic across an unchanged rescan.
        library.scan(str(golden.root))
        album2 = next(a for a in library.state.albums if a.title == "Ordered")
        assert album2.track_paths == album.track_paths

    def test_golden_timeline_years(self, tmp_path):
        golden = build_golden(tmp_path)
        library, _ = _make_library(tmp_path, FilesystemLibraryScanner(), SpyExtractor())
        library.scan(str(golden.root))

        timeline = build_timeline_projection(library.state.albums)
        by_title = {p.title: p for p in timeline}
        assert by_title["Modern"].year == 2019
        assert by_title["Modern"].decade == "2010s"
        assert by_title["Millennium"].year == 2001
        assert by_title["Millennium"].decade == "2000s"
        assert by_title["Retro"].year == 1985
        assert by_title["Retro"].decade == "1980s"
        # Canonical order: (-year, key) — newest album first.
        assert [p.year for p in timeline] == sorted(
            [p.year for p in timeline], reverse=True
        )
        # Year-0 albums land LAST with "Unknown era" (M6.1): the untagged
        # file's album plus any album without a date tag. Every year-0 row
        # sorts AFTER every year>0 row, in ascending album-key order.
        unknown = next(p for p in timeline if p.title == "Unknown Album")
        assert unknown.decade == "Unknown era"
        year0 = [p for p in timeline if p.year == 0]
        positive = [p for p in timeline if p.year > 0]
        assert positive  # the different-year albums are in the timeline
        assert all(p.decade == "Unknown era" for p in year0)
        assert all(timeline[i] in year0 for i in range(len(positive), len(timeline))), (
            "every year-0 album must sort after every year>0 album"
        )
        assert [p.album_key for p in timeline[-len(year0) :]] == sorted(
            p.album_key for p in year0
        )


class TestGoldenAsync:
    def test_golden_async_supersession(self, tmp_path):
        """FakeScanPipeline drive: gen 100 -> gen 101 supersedes -> 101 commits
        -> 100's LATE work+done is ignored (the library reflects 101 only)."""
        golden = build_golden(tmp_path)
        scanner = FilesystemLibraryScanner()
        extractor = SpyExtractor()
        pipeline = FakeScanPipeline()
        library, _ = _make_library(tmp_path, scanner, extractor, pipeline=pipeline)
        directory = str(golden.root)

        # Arm generations 1..99 (each start_scan arms + submits, runs nothing).
        for _ in range(99):
            library.start_scan(directory)
        assert library.state.scan_generation == 99

        library.start_scan(directory)  # gen 100
        library.start_scan(directory)  # gen 101 supersedes
        assert library.state.scan_generation == 101
        gen100, work100, _, on_done100 = pipeline.submits[99]
        gen101, work101, _, on_done101 = pipeline.submits[100]
        assert (gen100, gen101) == (100, 101)

        # Drive 101's work + done: committed, the REAL pipeline extracted all.
        result101 = work101(ScanProgress(), ScanCancelToken(), lambda: None)
        assert len(result101.tracks) == _GOLDEN_TRACK_COUNT
        on_done101(gen101, result101, None)
        assert len(library.state.tracks) == _GOLDEN_TRACK_COUNT
        assert library.state.scan_status is LibraryScanStatus.COMPLETED

        # The world moves on: B removed, C modified on disk.
        golden.same_title[1].unlink()
        _bump_mtime(golden.duplicates[1])

        # gen 100's LATE work differs from the committed world (B is gone)...
        result100 = work100(ScanProgress(), ScanCancelToken(), lambda: None)
        assert len(result100.tracks) == _GOLDEN_TRACK_COUNT - 1
        # ...but its done NEVER commits: the library reflects 101 only.
        notifies = []
        library.subscribe_changed(lambda: notifies.append(1))
        on_done100(gen100, result100, None)

        assert len(library.state.tracks) == _GOLDEN_TRACK_COUNT  # 101 intact
        assert library.state.scan_status is LibraryScanStatus.COMPLETED
        assert len(notifies) == 0  # NO second commit notify


_VIEWS_DIR = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "michi"
    / "presentation"
    / "qml"
    / "views"
)


def _aggregated_views_qml() -> str:
    """Concatenated text of every QML file under views/ (sorted determinism)."""
    return "\n".join(p.read_text() for p in sorted(_VIEWS_DIR.glob("*.qml")))


class TestGoldenSixViews:
    def test_golden_six_views_same_selection(self, tmp_path):
        """Select an album on the GOLDEN dataset: the six mode bindings carry
        the SAME album keys (the albums property is ONE model); switching
        modes keeps selectedAlbumKey == X (the M6.7 structural pin)."""
        golden = build_golden(tmp_path)
        library, _ = _make_library(tmp_path, FilesystemLibraryScanner(), SpyExtractor())
        library.scan(str(golden.root))
        bridge = LibraryBridge(library)

        album_x = next(a for a in library.state.albums if a.title == "Multi Disc")
        bridge.select_album(album_x.key)
        assert bridge.property("selectedAlbumKey") == album_x.key

        # ONE model: every mode's binding consumes the same album key set.
        albums = bridge.property("albums")
        keys = {row["key"] for row in albums}
        assert keys == {a.key for a in library.state.albums}
        assert album_x.key in keys
        timeline_keys = {row["key"] for row in bridge.property("timelineAlbums")}
        # timeline = the same album set, canonically projected
        assert timeline_keys == keys
        # The selected album's detail rows follow the canonical track order.
        rows = bridge.property("albumTracks")
        assert [r["path"] for r in rows] == [str(p) for p in album_x.track_paths]

        # Mode switching is presentation state — the selection never moves
        # or resets. The header emits a mode request; it never mutates Library.
        assert bridge.property("selectedAlbumKey") == album_x.key
        albums_view_qml = (_VIEWS_DIR / "AlbumsView.qml").read_text()
        header_qml = (_VIEWS_DIR / "LibraryHeader.qml").read_text()
        assert "property string albumMode" in albums_view_qml
        selector = header_qml.split("MichiSegmentedControl", 1)[1]
        assert "library." not in selector, (
            "the mode switcher must not touch the bridge — albumMode is local"
        )
        for mode in ("grid", "cover", "vinyl", "timeline", "magazine", "list"):
            assert f'value: "{mode}"' in header_qml

        # An unchanged rescan keeps the selection and the shared model.
        library.scan(str(golden.root))
        assert bridge.property("selectedAlbumKey") == album_x.key
        assert {row["key"] for row in bridge.property("albums")} == keys

        # Structural (M6.7): the six projections consume ONE shared model.
        qml = _aggregated_views_qml()
        for name in (
            "albumGridView",
            "albumCoverView",
            "albumVinylView",
            "albumTimelineView",
            "albumMagazineView",
            "albumListView",
        ):
            assert f'objectName: "{name}"' in qml, f"{name} missing"
        assert qml.count("property var albumModel: library.albums") == 5
        assert qml.count("property var albumModel: library.timelineAlbums") == 1
        assert qml.count("albumModel: root.presentationAlbums") == 4
        assert qml.count("albumModel: root.editorialAlbums") == 1
        assert qml.count("albumModel: root.presentationTimelineAlbums") == 1
        for ident in (
            "gridAlbums",
            "vinylAlbums",
            "magazineAlbums",
            "pathAlbums",
            "listAlbums",
        ):
            assert ident not in qml, (
                f"view-specific album model {ident!r} must not exist"
            )
        bridge.dispose()


class TestGoldenDegradation:
    def test_golden_degradation_broken_artwork(self, tmp_path):
        """Corrupt artwork bytes do NOT remove the album: the corrupt frame is
        skipped (has_artwork False), the scan completes, the rest is intact.
        A later VALID modification becomes active (M6.5 digest invalidation)."""
        golden = build_golden(tmp_path)
        scanner = FilesystemLibraryScanner()
        # 27-byte PNGs fit; the 100-byte corrupt garbage does not (skipped).
        provider = MutagenArtworkProvider(max_bytes=64)
        cache = ArtworkCache(tmp_path / "art-cache")
        library, _ = _make_library(
            tmp_path,
            scanner,
            SpyExtractor(),
            artwork_provider=provider,
            artwork_cache=cache,
        )
        library.scan(str(golden.root))
        assert library.state.diagnostic is None

        albums = {a.title: a for a in library.state.albums}
        assert albums["Embedded Art"].has_artwork is True
        assert albums["Folder Art"].has_artwork is True  # cover.jpg fallback
        assert albums["No Art"].has_artwork is False
        album_key = albums["Embedded Art"].key
        path_phase1 = library.artwork_path_for(album_key)
        assert path_phase1 is not None

        # BREAK the artwork: replace the embedded front cover with garbage
        # bytes (> max_bytes) + bump mtime. The corrupt artwork must be
        # skipped — never crash the scan, never remove the album.
        track = golden.embedded_art[0]
        _tag_mp3_artwork(track, b"\x99" * 100, mime="image/png", type_=3)
        _bump_mtime(track)
        library.scan(str(golden.root))

        assert library.state.diagnostic is None  # the scan COMPLETED
        albums = {a.title: a for a in library.state.albums}
        assert "Embedded Art" in albums  # the album STAYS
        assert albums["Embedded Art"].track_count == 1
        assert albums["Embedded Art"].has_artwork is False  # corrupt art skipped
        assert albums["Folder Art"].has_artwork is True  # the rest intact
        assert albums["No Art"].has_artwork is False
        # The corrupt-artwork track's MUSICAL metadata is intact.
        ref = next(t for t in library.state.tracks if t.file_path == track)
        assert ref.title == "Embedded One"
        assert ref.album == "Embedded Art"

        # MODIFIED artwork (the second scan): valid DIFFERENT bytes become
        # active — the digest-aware cache yields a NEW path.
        _tag_mp3_artwork(track, PNG_1x1_ALT, mime="image/png", type_=3)
        _bump_mtime(track)
        library.scan(str(golden.root))

        albums = {a.title: a for a in library.state.albums}
        assert albums["Embedded Art"].has_artwork is True
        path_phase3 = library.artwork_path_for(album_key)
        assert path_phase3 is not None
        assert path_phase3 != path_phase1  # changed content -> NEW cache entry

    def test_golden_degradation_malformed_file(self, tmp_path):
        """One track whose extractor raises MetadataExtractionError does NOT
        abort the scan: stem-title fallback, the rest intact."""
        golden = build_golden(tmp_path)
        middle = golden.single[1]  # "02 Middle.mp3" — the malformed track
        extractor = SpyExtractor(failing={middle})
        library, _ = _make_library(tmp_path, FilesystemLibraryScanner(), extractor)

        library.scan(str(golden.root))

        assert library.state.diagnostic is None  # the scan COMPLETED
        assert {t.file_path for t in library.state.tracks} == set(golden.all_paths)
        ref = next(t for t in library.state.tracks if t.file_path == middle)
        assert ref.title == "02 Middle"  # stem-title fallback
        # The rest is intact: the Single Disc album keeps its healthy tracks.
        album = next(a for a in library.state.albums if a.title == "Single Disc")
        assert [p.name for p in album.track_paths] == ["01 Intro.mp3", "03 Outro.mp3"]
        assert (
            sum(al.track_count for al in library.state.albums)
            == len(library.state.tracks)
            == _GOLDEN_TRACK_COUNT
        )

    def test_golden_degradation_missing_file_and_dir(self, tmp_path):
        """TD-013 TRACK_MISSING activation preserves the library; a
        missing-directory scan preserves the last valid Library + diagnostic."""
        golden = build_golden(tmp_path)
        scanner = FilesystemLibraryScanner()
        library, repo = _make_library(tmp_path, scanner, SpyExtractor())
        library.scan(str(golden.root))
        assert len(library.state.tracks) == _GOLDEN_TRACK_COUNT

        # TD-013 TRACK_MISSING activation: the file vanishes; activation
        # removes the EXACT ref and preserves the rest of the library.
        missing_path = golden.no_art[0]
        ref = next(t for t in library.state.tracks if t.file_path == missing_path)
        missing_path.unlink()
        library.validate_track_for_playback(ref)

        assert library.state.diagnostic is not None
        assert library.state.diagnostic.code is LibraryDiagnosticCode.TRACK_MISSING
        assert library.state.diagnostic.path == missing_path
        # M6-EXT-R4 freeze gate §10: play/scan-missing NEVER removes
        # identity — the ref is PRESERVED and marked MISSING.
        assert missing_path in {t.file_path for t in library.state.tracks}
        assert len(library.state.tracks) == _GOLDEN_TRACK_COUNT
        missing_ref = next(
            t for t in library.state.tracks if t.file_path == missing_path
        )
        assert missing_ref.availability.value == "missing"
        # the No Art album survives (identity preserved).
        assert any(a.title == "No Art" for a in library.state.albums)
        # rest preserved
        assert any(a.title == "Multi Disc" for a in library.state.albums)
        rows_before = repo.load_all()

        # A MISSING DIRECTORY scan preserves the last valid library + sets the
        # diagnostic (the REAL scanner raises DIRECTORY_MISSING).
        library.scan(str(golden.root / "no-such-dir"))

        assert library.state.diagnostic is not None
        assert library.state.diagnostic.code is LibraryDiagnosticCode.DIRECTORY_MISSING
        assert len(library.state.tracks) == _GOLDEN_TRACK_COUNT  # preserved
        assert any(a.title == "Multi Disc" for a in library.state.albums)
        assert repo.load_all() == rows_before  # no partial index writes
