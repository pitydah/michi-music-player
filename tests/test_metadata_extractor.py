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
from mutagen.mp3 import MP3

from michi.application.ports import MetadataExtractionError
from michi.domain.library import TrackMetadata
from michi.infrastructure.metadata_extractor import InfrastructureMetadataExtractor

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
