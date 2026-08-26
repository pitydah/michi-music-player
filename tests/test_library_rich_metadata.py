"""LOCAL-META-02.2a rich canonical metadata — Phase-1 RED tests.

The target contract (mega-WP section 7.1/7.2, DoD 52) is NOT implemented on
the current baseline: ``TrackMetadata`` only carries title/artist/album/
duration_ms/genre/year and ``TrackRef`` only carries the basic projection, so
constructing with the rich keyword arguments raises ``TypeError``
(``unexpected keyword argument 'album_artist'`` / ``'codec'``) and accessing
the new fields raises ``AttributeError``. That IS the expected Phase-1 red
evidence. These tests encode the target contract and must pass once the
production changes land (michi/domain/library.py TrackMetadata rich fields +
TrackRef projection fields, LibraryService._make_trackref projection copy).

Contract being encoded:
- TrackMetadata gains, after ``year``: musical fields album_artist,
  track_number, track_total, disc_number, disc_total, composer, date,
  compilation, sort_title, sort_artist, sort_album, sort_album_artist; then
  technical fields codec, container, sample_rate_hz, bit_depth, channels,
  bitrate_bps, file_size. 0/"" represent UNKNOWN honestly, never fabricated.
- TrackRef gains ONLY the model projection: album_artist, track_number,
  disc_number, composer, compilation (12 fields total — technical fields stay
  in TrackMetadata only).
- LibraryService._make_trackref copies the projection fields into TrackRef.
"""

from pathlib import Path

from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.playback_session_service import PlaybackSessionService
from michi.application.queue_service import QueueService
from michi.domain.library import TrackMetadata, TrackRef
from tests.conftest import FakeAudioPort
from tests.test_library_metadata import FakeExtractor, FakeScanner


def _make_library(scanner, extractor=None):
    """Build LibraryService with a real queue; extractor is optional."""
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService()
    _session = PlaybackSessionService(playback, queue)
    if extractor is None:
        library = LibraryService(scanner)
    else:
        library = LibraryService(scanner, metadata_extractor=extractor)
    return library, queue


def _full_metadata(path: Path) -> TrackMetadata:
    """Factory canned metadata exercising every rich musical + technical field."""
    return TrackMetadata(
        title="T " + path.stem,
        artist="Artist",
        album_artist="Album Artist",
        album="Album",
        duration_ms=60000,
        genre="Rock",
        year=1999,
        track_number=3,
        track_total=12,
        disc_number=2,
        disc_total=2,
        composer="Composer",
        date="1999-11-23",
        compilation=True,
        sort_title="Sort Title",
        sort_artist="Sort Artist",
        sort_album="Sort Album",
        sort_album_artist="Sort Album Artist",
        codec="FLAC",
        container="flac",
        sample_rate_hz=96000,
        bit_depth=24,
        channels=2,
        bitrate_bps=0,
        file_size=12345,
    )


class TestTrackMetadataFields:
    def test_full_musical_fields_constructible(self):
        m = TrackMetadata(
            title="T",
            artist="A",
            album_artist="AA",
            album="AL",
            track_number=3,
            track_total=12,
            disc_number=2,
            disc_total=3,
            genre="Rock",
            composer="C",
            date="1999-11-23",
            year=1999,
            compilation=True,
            sort_title="ST",
            sort_artist="SA",
            sort_album="SAL",
            sort_album_artist="SAA",
        )
        assert m.title == "T"
        assert m.artist == "A"
        assert m.album_artist == "AA"
        assert m.album == "AL"
        assert m.track_number == 3
        assert m.track_total == 12
        assert m.disc_number == 2
        assert m.disc_total == 3
        assert m.genre == "Rock"
        assert m.composer == "C"
        assert m.date == "1999-11-23"
        assert m.year == 1999
        assert m.compilation is True
        assert m.sort_title == "ST"
        assert m.sort_artist == "SA"
        assert m.sort_album == "SAL"
        assert m.sort_album_artist == "SAA"

    def test_full_technical_fields_constructible(self):
        m = TrackMetadata(
            codec="FLAC",
            container="flac",
            sample_rate_hz=96000,
            bit_depth=24,
            channels=2,
            bitrate_bps=0,
            file_size=12345,
            duration_ms=60000,
        )
        assert m.codec == "FLAC"
        assert m.container == "flac"
        assert m.sample_rate_hz == 96000
        assert m.bit_depth == 24
        assert m.channels == 2
        assert m.bitrate_bps == 0
        assert m.file_size == 12345
        assert m.duration_ms == 60000

    def test_unknown_defaults_honest(self):
        m = TrackMetadata()
        # Musical fields default to 0/""/False — never fabricated values.
        assert m.album_artist == ""
        assert m.track_number == 0
        assert m.track_total == 0
        assert m.disc_number == 0
        assert m.disc_total == 0
        assert m.composer == ""
        assert m.date == ""
        assert m.compilation is False
        assert m.sort_title == ""
        assert m.sort_artist == ""
        assert m.sort_album == ""
        assert m.sort_album_artist == ""
        # Technical fields default to 0/"" — UNKNOWN is honest.
        assert m.codec == ""
        assert m.container == ""
        assert m.sample_rate_hz == 0
        assert m.bit_depth == 0
        assert m.channels == 0
        assert m.bitrate_bps == 0
        assert m.file_size == 0


class TestTrackRefProjection:
    def test_projection_fields_constructible(self):
        t = TrackRef(
            file_path=Path("/m/a.flac"),
            title="T",
            album_artist="AA",
            track_number=3,
            disc_number=1,
            composer="C",
            compilation=True,
        )
        assert t.file_path == Path("/m/a.flac")
        assert t.title == "T"
        assert t.album_artist == "AA"
        assert t.track_number == 3
        assert t.disc_number == 1
        assert t.composer == "C"
        assert t.compilation is True

    def test_projection_defaults(self):
        t = TrackRef(file_path=Path("/m/a.flac"))
        assert t.album_artist == ""
        assert t.track_number == 0
        assert t.disc_number == 0
        assert t.composer == ""
        assert t.compilation is False

    def test_scan_carries_projection(self, tmp_path):
        p1 = tmp_path / "rich.flac"
        p1.write_bytes(b"x")
        scanner = FakeScanner([p1])
        library, _ = _make_library(scanner, FakeExtractor(factory=_full_metadata))
        library.scan(str(tmp_path))
        track = library.state.tracks[0]
        assert isinstance(track, TrackRef)
        # Projection fields carried from TrackMetadata.
        assert track.album_artist == "Album Artist"
        assert track.track_number == 3
        assert track.disc_number == 2
        assert track.composer == "Composer"
        assert track.compilation is True
        # M6-PRODUCTION-INTEGRATION (spec §39-40): the canonical TrackRef
        # RETAINS the technical carrier so runtime projections can show
        # facts — the old "technical fields stay in TrackMetadata only"
        # contract is retired.
        assert track.codec == "FLAC"
        assert track.container == "flac"
        assert track.sample_rate_hz == 96000
        assert track.bit_depth == 24
        assert track.channels == 2
        assert track.bitrate_bps == 0
        assert track.file_size == 12345

    def test_scan_without_extractor_defaults(self, tmp_path):
        p1 = tmp_path / "plain.flac"
        p1.write_bytes(b"x")
        scanner = FakeScanner([p1])
        library, _ = _make_library(scanner)  # 2-arg construction, no extractor
        library.scan(str(tmp_path))
        track = library.state.tracks[0]
        assert isinstance(track, TrackRef)
        assert track.album_artist == ""
        assert track.track_number == 0
        assert track.disc_number == 0
        assert track.composer == ""
        assert track.compilation is False
