"""M6 library scan metadata enrichment — Phase-1 RED tests.

On the current baseline the module-level imports of the new symbols fail at
collection (ImportError) — that IS the expected Phase-1 red evidence. The
tests encode the target contract and must pass once the production changes
land (michi/domain/library.py TrackMetadata + TrackRef metadata fields,
michi/application/ports.py MetadataExtractionError, LibraryService optional
metadata_extractor wiring, QueueService.add title parameter).

Coverage:
- Scan enriches TrackRefs (title/artist/album/duration_ms, display_name)
- Untagged metadata -> display_name falls back to stem
- No extractor wired -> TrackRef defaults
- Per-file extraction failure -> fallback TrackRef, scan continues
- STALE_ENTRIES_REMOVED reconciliation survives extractor wiring (TD-013)
- QueueService.add(title=...) enrichment
- duration_ms flows from the extractor
"""

from pathlib import Path

from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.ports import MetadataExtractionError
from michi.application.queue_service import QueueService
from michi.domain.library import LibraryDiagnosticCode, TrackMetadata, TrackRef
from tests.conftest import FakeAudioPort


class FakeScanner:
    """Returns a fixed path list regardless of the scanned root."""

    def __init__(self, paths=None) -> None:
        self.paths = list(paths) if paths else []

    def scan(self, root):
        return list(self.paths)

    def validate_file(self, path):
        return None


class FakeExtractor:
    """Duck-typed port fake: canned metadata per path; raises for a set."""

    def __init__(self, failing=None, factory=None) -> None:
        self.failing = set(failing or [])
        self.factory = factory

    def extract(self, file_path):
        if file_path in self.failing:
            raise MetadataExtractionError(file_path)
        if self.factory is not None:
            return self.factory(file_path)
        return TrackMetadata(
            title="T " + file_path.stem, artist="A", album="B", duration_ms=1234
        )


def _make_library(scanner, extractor=None):
    """Build LibraryService with a real queue; extractor is optional."""
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService(playback)
    if extractor is None:
        library = LibraryService(scanner, queue)
    else:
        library = LibraryService(scanner, queue, extractor)
    return library, queue


class TestLibraryMetadataScan:
    def test_scan_enriches_trackrefs(self, tmp_path):
        p1 = tmp_path / "one.mp3"
        p2 = tmp_path / "two.flac"
        p1.write_bytes(b"x")
        p2.write_bytes(b"x")
        scanner = FakeScanner([p1, p2])
        library, _ = _make_library(scanner, FakeExtractor())
        library.scan(str(tmp_path))
        tracks = library.state.tracks
        assert [t.file_path for t in tracks] == [p1, p2]
        assert isinstance(tracks[0], TrackRef)
        assert tracks[0].title == "T one"
        assert tracks[0].artist == "A"
        assert tracks[0].album == "B"
        assert tracks[0].duration_ms == 1234
        assert tracks[0].display_name == tracks[0].title
        assert tracks[1].title == "T two"
        assert tracks[1].display_name == tracks[1].title

    def test_scan_untagged_uses_stem(self, tmp_path):
        p1 = tmp_path / "untitled.mp3"
        p1.write_bytes(b"x")
        scanner = FakeScanner([p1])
        extractor = FakeExtractor(
            factory=lambda p: TrackMetadata(
                title="", artist="", album="", duration_ms=0
            )
        )
        library, _ = _make_library(scanner, extractor)
        library.scan(str(tmp_path))
        track = library.state.tracks[0]
        assert track.title == ""
        assert track.display_name == p1.stem

    def test_scan_without_extractor_no_metadata(self, tmp_path):
        p1 = tmp_path / "plain.mp3"
        p1.write_bytes(b"x")
        scanner = FakeScanner([p1])
        library, _ = _make_library(scanner)  # 2-arg construction
        library.scan(str(tmp_path))
        track = library.state.tracks[0]
        assert isinstance(track, TrackRef)
        assert track.display_name == p1.stem
        assert track.title == ""
        assert track.artist == ""
        assert track.album == ""
        assert track.duration_ms == 0

    def test_scan_failed_extraction_falls_back_and_continues(self, tmp_path):
        p1 = tmp_path / "good.mp3"
        p2 = tmp_path / "broken.mp3"
        p1.write_bytes(b"x")
        p2.write_bytes(b"x")
        scanner = FakeScanner([p1, p2])
        extractor = FakeExtractor(failing={p2})
        library, _ = _make_library(scanner, extractor)
        library.scan(str(tmp_path))  # must not raise
        tracks = library.state.tracks
        assert len(tracks) == 2
        good = next(t for t in tracks if t.file_path == p1)
        broken = next(t for t in tracks if t.file_path == p2)
        assert good.title == "T good"
        assert good.duration_ms == 1234
        assert broken.title == ""
        assert broken.artist == ""
        assert broken.album == ""
        assert broken.duration_ms == 0
        assert broken.display_name == p2.stem

    def test_scan_extraction_failure_preserves_td013(self, tmp_path):
        p1 = tmp_path / "keep.mp3"
        p2 = tmp_path / "stale.mp3"
        p1.write_bytes(b"x")
        p2.write_bytes(b"x")
        scanner = FakeScanner([p1, p2])
        extractor = FakeExtractor()
        library, _ = _make_library(scanner, extractor)
        library.scan(str(tmp_path))
        assert library.state.diagnostic is None
        scanner.paths = [p1]
        extractor.failing = {p1}
        library.scan(str(tmp_path))
        assert [t.file_path for t in library.state.tracks] == [p1]
        assert library.state.diagnostic is not None
        assert (
            library.state.diagnostic.code is LibraryDiagnosticCode.STALE_ENTRIES_REMOVED
        )
        assert library.state.diagnostic.affected_count == 1
        assert library.state.tracks[0].title == ""  # failed extraction -> fallback

    def test_queue_add_with_title(self):
        library, queue = _make_library(FakeScanner())
        path = Path("/music/real.mp3")
        queue.add(path, title="Real Title")
        assert queue.state.tracks[0].title == "Real Title"
        queue.add(path)
        assert queue.state.tracks[1].title == "real"

    def test_scan_duration_flows(self, tmp_path):
        p1 = tmp_path / "song.mp3"
        p1.write_bytes(b"x")
        scanner = FakeScanner([p1])
        library, _ = _make_library(scanner, FakeExtractor())
        library.scan(str(tmp_path))
        assert library.state.tracks[0].duration_ms == 1234
