"""M6 metadata extraction — Phase-1 RED tests for TrackMetadata + extractor.

On the current baseline the module-level imports of the new symbols fail at
collection (ImportError) — that IS the expected Phase-1 red evidence. The
tests encode the target contract and must pass once the production changes
land (michi/domain/library.py TrackMetadata, michi/application/ports.py
MetadataExtractorPort + MetadataExtractionError, michi/infrastructure/
metadata_extractor.py InfrastructureMetadataExtractor).

Coverage:
- Tagged MP3/FLAC extraction (title/artist/album/duration_ms)
- Untagged fallback (title -> stem, empty artist/album)
- Corrupt tags -> fallback, never raise
- Missing title/artist/album tag combinations
- Unicode + long titles round-trip exactly
- Missing/disappearing file -> typed MetadataExtractionError (.path)
- Unknown extension -> fallback (mutagen returns None)
"""

from pathlib import Path

import pytest
from mutagen.flac import FLAC
from mutagen.id3 import TALB, TIT2, TPE1
from mutagen.mp3 import MP3, EasyMP3

from michi.application.ports import MetadataExtractionError
from michi.domain.library import TrackMetadata
from michi.infrastructure.metadata_extractor import (
    InfrastructureMetadataExtractor,
)

# Minimal silent MPEG-1 Layer III frame: 128 kbps (bitrate index 9), 44.1 kHz,
# no CRC. Frame length = 144 * 128000 / 44100 = 417 bytes. mutagen only accepts
# a sync candidate after 4 consecutive valid frames, so we repeat it 4x.
MP3_FRAME = b"\xff\xfb\x90\x00" + b"\x00" * 413

# FLAC STREAMINFO parameters: 60 s @ 44.1 kHz, stereo, 16 bit.
_FLAC_SAMPLE_RATE = 44100
_FLAC_CHANNELS = 2
_FLAC_BITS = 16
_FLAC_TOTAL_SAMPLES = 2646000


def _flac_streaminfo() -> bytes:
    """34-byte FLAC STREAMINFO metadata block payload."""
    return (
        (4096).to_bytes(2, "big")  # min block size
        + (4096).to_bytes(2, "big")  # max block size
        + b"\x00\x00\x00"  # min frame size
        + b"\x00\x00\x00"  # max frame size
        + (
            _FLAC_SAMPLE_RATE << 44
            | (_FLAC_CHANNELS - 1) << 41
            | (_FLAC_BITS - 1) << 36
            | _FLAC_TOTAL_SAMPLES
        ).to_bytes(8, "big")
        + bytes(16)  # MD5 (zeroed)
    )


def _build_media(tmp_path, kind, tags=None, corrupt=False) -> Path:
    """Build a minimal MP3 or FLAC file; optionally apply tags / corrupt it.

    ``tags`` is an optional mapping with any of "title"/"artist"/"album".
    ``corrupt`` overwrites the first 30 bytes (the tag region) with garbage.
    """
    path = tmp_path / f"track_{len(list(tmp_path.iterdir()))}.{kind}"
    if kind == "mp3":
        path.write_bytes(MP3_FRAME * 4)
        if tags is not None:
            audio = MP3(str(path))
            audio.add_tags()
            if tags.get("title"):
                audio.tags.add(TIT2(encoding=3, text=tags["title"]))
            if tags.get("artist"):
                audio.tags.add(TPE1(encoding=3, text=tags["artist"]))
            if tags.get("album"):
                audio.tags.add(TALB(encoding=3, text=tags["album"]))
            audio.save()
    elif kind == "flac":
        path.write_bytes(
            b"fLaC" + bytes([0x80]) + (34).to_bytes(3, "big") + _flac_streaminfo()
        )
        if tags is not None:
            audio = FLAC(str(path))
            for key in ("title", "artist", "album"):
                if tags.get(key):
                    audio[key] = tags[key]
            audio.save()
    else:
        raise ValueError(f"unsupported kind: {kind!r}")
    if corrupt:
        raw = path.read_bytes()
        path.write_bytes(b"\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99" * 3 + raw[30:])
    return path


def _tag_rich(path: Path, kind: str, tags) -> None:
    """Apply easy-style musical tags (albumartist, tracknumber, discnumber,
    composer, date, compilation, sort_*) to a fixture built by _build_media.

    Mirrors the extractor's easy read path: EasyMP3 for MP3, the native
    Vorbis-comment dict for FLAC. ``tags`` maps easy key -> raw string value.
    """
    if kind == "mp3":
        audio = EasyMP3(str(path))
    elif kind == "flac":
        audio = FLAC(str(path))
    else:
        raise ValueError(f"unsupported kind: {kind!r}")
    for key, value in tags.items():
        audio[key] = value
    audio.save()


class TestInfrastructureMetadataExtractor:
    def test_mp3_title_artist_album_duration(self, tmp_path):
        path = _build_media(
            tmp_path,
            "mp3",
            tags={
                "title": "Canción de prueba",
                "artist": "Artista Uno",
                "album": "Álbum Á",
            },
        )
        result = InfrastructureMetadataExtractor().extract(path)
        assert isinstance(result, TrackMetadata)
        assert result.title == "Canción de prueba"
        assert result.artist == "Artista Uno"
        assert result.album == "Álbum Á"
        assert result.duration_ms > 0

    def test_flac_title_artist_album_duration(self, tmp_path):
        path = _build_media(
            tmp_path,
            "flac",
            tags={
                "title": "Canción de prueba",
                "artist": "Artista Uno",
                "album": "Álbum Á",
            },
        )
        result = InfrastructureMetadataExtractor().extract(path)
        assert isinstance(result, TrackMetadata)
        assert result.title == "Canción de prueba"
        assert result.artist == "Artista Uno"
        assert result.album == "Álbum Á"
        assert result.duration_ms == 60000  # 2646000 / 44100 * 1000

    def test_untagged_mp3_falls_back(self, tmp_path):
        path = _build_media(tmp_path, "mp3")
        result = InfrastructureMetadataExtractor().extract(path)
        assert isinstance(result, TrackMetadata)
        assert result.title == path.stem
        assert result.artist == ""
        assert result.album == ""
        assert result.duration_ms > 0

    def test_untagged_flac_falls_back(self, tmp_path):
        path = _build_media(tmp_path, "flac")
        result = InfrastructureMetadataExtractor().extract(path)
        assert isinstance(result, TrackMetadata)
        assert result.title == path.stem
        assert result.artist == ""
        assert result.album == ""
        assert result.duration_ms == 60000  # info still readable

    def test_corrupt_tags_fall_back(self, tmp_path):
        path = _build_media(tmp_path, "mp3", tags={"title": "Doomed"}, corrupt=True)
        result = InfrastructureMetadataExtractor().extract(path)
        assert isinstance(result, TrackMetadata)
        assert result.title == path.stem

    def test_missing_title_tag_falls_back_to_stem(self, tmp_path):
        path = _build_media(
            tmp_path,
            "mp3",
            tags={"artist": "Artista Uno", "album": "Álbum Á"},
        )
        result = InfrastructureMetadataExtractor().extract(path)
        assert isinstance(result, TrackMetadata)
        assert result.title == path.stem
        assert result.artist == "Artista Uno"
        assert result.album == "Álbum Á"

    def test_missing_artist_album_tags(self, tmp_path):
        path = _build_media(tmp_path, "mp3", tags={"title": "Solo Título"})
        result = InfrastructureMetadataExtractor().extract(path)
        assert isinstance(result, TrackMetadata)
        assert result.title == "Solo Título"
        assert result.artist == ""
        assert result.album == ""

    def test_unicode_metadata(self, tmp_path):
        title = "Canción ñ ♪ — 日本語"
        path = _build_media(tmp_path, "mp3", tags={"title": title})
        result = InfrastructureMetadataExtractor().extract(path)
        assert result.title == title

    def test_long_metadata(self, tmp_path):
        title = "L" * 500
        path = _build_media(tmp_path, "mp3", tags={"title": title})
        result = InfrastructureMetadataExtractor().extract(path)
        assert result.title == title

    def test_missing_file_raises_typed_error(self, tmp_path):
        missing = tmp_path / "does_not_exist.mp3"
        with pytest.raises(MetadataExtractionError) as excinfo:
            InfrastructureMetadataExtractor().extract(missing)
        assert excinfo.value.path == missing

    def test_disappearing_file_raises_typed_error(self, tmp_path):
        path = _build_media(tmp_path, "mp3", tags={"title": "Doomed"})
        path.unlink()
        with pytest.raises(MetadataExtractionError) as excinfo:
            InfrastructureMetadataExtractor().extract(path)
        assert excinfo.value.path == path

    def test_unknown_extension_untagged_falls_back(self, tmp_path):
        path = tmp_path / "raw.xyz"
        path.write_bytes(b"not an audio file at all\n")
        result = InfrastructureMetadataExtractor().extract(path)
        assert isinstance(result, TrackMetadata)
        assert result.title == path.stem
        assert result.artist == ""
        assert result.album == ""
        assert result.duration_ms == 0


class TestRichExtraction:
    """LOCAL-META-02.2b rich extraction — Phase-1 RED tests.

    Contract (mega-WP §8/§9, DoD §52): InfrastructureMetadataExtractor
    (Mutagen easy=True) populates the TrackMetadata rich fields — musical
    (album_artist, track/disc numbers, composer, date, compilation, sort_*)
    and technical (codec, container, sample_rate_hz, bit_depth, channels,
    bitrate_bps, file_size). 0/''/False mean UNKNOWN honestly; malformed
    single fields must not destroy the rest; technical facts must never be
    fabricated (lossy codecs get bit_depth 0).

    Verified mutagen 1.47 easy keys (see batch report): all ten keys round-
    trip via easy on MP3 (albumartist->TPE2, tracknumber->TRCK, discnumber->
    TPOS, composer->TCOM, date->TDRC, compilation->TCMP, titlesort->TSOT,
    artistsort->TSOP, albumsort->TSOA; NOTE: albumartistsort maps to
    TXXX:ALBUMARTISTSORT, not TSO2) and via plain Vorbis-comment dict keys
    on FLAC. MP3 info exposes .bitrate/.sample_rate/.channels but no
    .bits_per_sample; FLAC info exposes all of them (bitrate 0/None on the
    minimal fixture).
    """

    # --- Musical fields -------------------------------------------------

    def test_mp3_all_musical_fields(self, tmp_path):
        path = _build_media(tmp_path, "mp3")
        _tag_rich(
            path,
            "mp3",
            {
                "albumartist": "Compilation Artists",
                "tracknumber": "3/12",
                "discnumber": "1/2",
                "composer": "C. Composer",
                "date": "1999-11-23",
                "compilation": "1",
                "titlesort": "Zulu",
                "artistsort": "Alpha",
                "albumsort": "Beta",
                "albumartistsort": "Gamma",
            },
        )
        result = InfrastructureMetadataExtractor().extract(path)
        assert isinstance(result, TrackMetadata)
        assert result.album_artist == "Compilation Artists"
        assert result.track_number == 3
        assert result.track_total == 12
        assert result.disc_number == 1
        assert result.disc_total == 2
        assert result.composer == "C. Composer"
        assert result.date == "1999-11-23"
        assert result.compilation is True
        assert result.sort_title == "Zulu"
        assert result.sort_artist == "Alpha"
        assert result.sort_album == "Beta"
        assert result.sort_album_artist == "Gamma"
        assert result.year == 1999

    def test_flac_all_musical_fields(self, tmp_path):
        path = _build_media(tmp_path, "flac")
        _tag_rich(
            path,
            "flac",
            {
                "albumartist": "Compilation Artists",
                "tracknumber": "3/12",
                "discnumber": "1/2",
                "composer": "C. Composer",
                "date": "1999-11-23",
                "compilation": "1",
                "titlesort": "Zulu",
                "artistsort": "Alpha",
                "albumsort": "Beta",
                "albumartistsort": "Gamma",
            },
        )
        result = InfrastructureMetadataExtractor().extract(path)
        assert isinstance(result, TrackMetadata)
        assert result.album_artist == "Compilation Artists"
        assert result.track_number == 3
        assert result.track_total == 12
        assert result.disc_number == 1
        assert result.disc_total == 2
        assert result.composer == "C. Composer"
        assert result.date == "1999-11-23"
        assert result.compilation is True
        assert result.sort_title == "Zulu"
        assert result.sort_artist == "Alpha"
        assert result.sort_album == "Beta"
        assert result.sort_album_artist == "Gamma"
        assert result.year == 1999

    # --- Technical facts ------------------------------------------------

    def test_mp3_technical_facts(self, tmp_path):
        path = _build_media(tmp_path, "mp3", tags={"title": "Technical"})
        result = InfrastructureMetadataExtractor().extract(path)
        assert result.codec == "MP3"
        assert result.container == "mp3"
        assert result.sample_rate_hz == 44100
        assert result.channels == 2
        assert result.bit_depth == 0  # lossy — no bits_per_sample, never fabricated
        assert result.bitrate_bps > 0
        assert result.file_size == path.stat().st_size
        assert result.duration_ms > 0

    def test_flac_technical_facts(self, tmp_path):
        path = _build_media(tmp_path, "flac")
        result = InfrastructureMetadataExtractor().extract(path)
        assert result.codec == "FLAC"
        assert result.container == "flac"
        assert result.sample_rate_hz == 44100
        assert result.bit_depth == 16
        assert result.channels == 2
        # info.bitrate 0/None on minimal fixture — honest
        assert result.bitrate_bps == 0
        assert result.file_size == path.stat().st_size
        assert result.duration_ms == 60000  # 2646000 / 44100 * 1000

    # --- Parse helpers / isolation --------------------------------------

    def test_tracknumber_bare_number(self, tmp_path):
        path = _build_media(tmp_path, "mp3")
        _tag_rich(path, "mp3", {"tracknumber": "7"})
        result = InfrastructureMetadataExtractor().extract(path)
        assert result.track_number == 7
        assert result.track_total == 0

    def test_malformed_tracknumber_isolated(self, tmp_path):
        path = _build_media(
            tmp_path,
            "mp3",
            tags={"title": "Good Title", "artist": "Good Artist"},
        )
        _tag_rich(path, "mp3", {"tracknumber": "xyz"})
        result = InfrastructureMetadataExtractor().extract(path)
        assert result.title == "Good Title"
        assert result.artist == "Good Artist"
        assert result.track_number == 0
        assert result.track_total == 0

    def test_compilation_flag_variants(self, tmp_path):
        for raw, expected in (("1", True), ("true", True), ("", False)):
            path = _build_media(tmp_path, "mp3")
            _tag_rich(path, "mp3", {"compilation": raw})
            result = InfrastructureMetadataExtractor().extract(path)
            assert result.compilation is expected, f"compilation {raw!r} -> {expected}"
        path = _build_media(tmp_path, "mp3")  # tag missing
        result = InfrastructureMetadataExtractor().extract(path)
        assert result.compilation is False

    # --- Honest defaults ------------------------------------------------

    def test_untagged_defaults_honest(self, tmp_path):
        path = _build_media(tmp_path, "mp3")
        result = InfrastructureMetadataExtractor().extract(path)
        # Musical fields are UNKNOWN (0/''/False) — never fabricated.
        assert result.album_artist == ""
        assert result.track_number == 0
        assert result.track_total == 0
        assert result.disc_number == 0
        assert result.disc_total == 0
        assert result.composer == ""
        assert result.date == ""
        assert result.compilation is False
        assert result.sort_title == ""
        assert result.sort_artist == ""
        assert result.sort_album == ""
        assert result.sort_album_artist == ""
        # Technical facts for a readable MP3 ARE known.
        assert result.codec == "MP3"
        assert result.container == "mp3"
        assert result.sample_rate_hz == 44100
        assert result.channels == 2
        assert result.bit_depth == 0
        assert result.bitrate_bps > 0
        assert result.file_size == path.stat().st_size

    def test_missing_file_raises_typed_error(self, tmp_path):
        missing = tmp_path / "does_not_exist.mp3"
        with pytest.raises(MetadataExtractionError) as excinfo:
            InfrastructureMetadataExtractor().extract(missing)
        assert excinfo.value.path == missing
