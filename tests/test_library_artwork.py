"""LOCAL-02 artwork pipeline — Phase-1 RED tests.

On the current baseline the module-level imports of the new symbols fail at
collection (ImportError) — that IS the expected Phase-1 red evidence. The
tests encode the target contract and must pass once the production changes
land (michi/domain/library.py Artwork + AlbumRef.has_artwork,
michi/application/ports.py ArtworkProviderPort, michi/infrastructure/
artwork.py MutagenArtworkProvider + ArtworkCache, LibraryService artwork
enrichment on successful scan, bootstrap wiring).

Coverage:
- Provider: MP3 APIC, FLAC picture, untagged, missing, corrupt, over-limit
- Cache: deterministic filename, idempotent store, empty data
- Scan: album enrichment, no-provider fallback, provider-none fall-through,
  failed-scan preservation, deterministic cache key
"""

import hashlib
from pathlib import Path

from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC
from mutagen.mp3 import MP3

from michi.application.library_port import LibraryFilesystemError
from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.queue_service import QueueService
from michi.domain.library import (
    AlbumRef,
    Artwork,
    LibraryDiagnosticCode,
    TrackMetadata,
)
from michi.infrastructure.artwork import ArtworkCache, MutagenArtworkProvider
from tests.conftest import FakeAudioPort
from tests.test_library_metadata import FakeExtractor, FakeScanner
from tests.test_metadata_extractor import _build_media

# Minimal 1x1 PNG payload (magic + padding) — content is irrelevant, only
# size/mime matter to the pipeline.
PNG_1x1 = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 16


class FakeArtworkProvider:
    """Duck-typed provider: canned artwork (or None) for every path."""

    def __init__(self, artwork=None):
        self.artwork = artwork
        self.calls = []

    def get_embedded_artwork(self, file_path):
        self.calls.append(file_path)
        return self.artwork


class FakeArtworkCache:
    """Duck-typed cache: records stores, returns a deterministic path."""

    def __init__(self):
        self.stores = []
        self.paths = {}

    def store(self, album_key, artwork):
        self.stores.append((album_key, artwork))
        if album_key not in self.paths:
            self.paths[album_key] = Path(f"/fake/{album_key}.png")
        return self.paths[album_key]


class FailingScanner(FakeScanner):
    """Like FakeScanner, but scan() raises the configured error when set."""

    def __init__(self, paths=None, scan_error=None):
        super().__init__(paths)
        self.scan_error = scan_error

    def scan(self, root):
        if self.scan_error is not None:
            raise self.scan_error
        return list(self.paths)


def _make_library(scanner, extractor=None, artwork_provider=None, artwork_cache=None):
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService(playback)
    return LibraryService(scanner, queue, extractor, artwork_provider, artwork_cache)


def _album_factory():
    """TrackMetadata factory: two albums (Alpha/Beta) under one artist."""

    def factory(path):
        album = "Alpha" if path.stem.startswith("a") else "Beta"
        return TrackMetadata(
            title=path.stem, artist="Artist One", album=album, duration_ms=1000
        )

    return factory


class TestArtworkProvider:
    def test_provider_mp3_apic(self, tmp_path):
        path = _build_media(tmp_path, "mp3")
        audio = MP3(str(path))
        audio.add_tags()
        audio.tags.add(
            APIC(encoding=3, mime="image/png", type=3, desc="", data=PNG_1x1)
        )
        audio.save()
        artwork = MutagenArtworkProvider().get_embedded_artwork(path)
        assert isinstance(artwork, Artwork)
        assert artwork.data == PNG_1x1
        assert artwork.mime_type == "image/png"

    def test_provider_flac_picture(self, tmp_path):
        path = _build_media(tmp_path, "flac")
        audio = FLAC(str(path))
        picture = Picture()
        picture.type = 3
        picture.mime = "image/jpeg"
        picture.data = JPEG_BYTES
        audio.add_picture(picture)
        audio.save()
        artwork = MutagenArtworkProvider().get_embedded_artwork(path)
        assert isinstance(artwork, Artwork)
        assert artwork.data == JPEG_BYTES
        assert artwork.mime_type == "image/jpeg"

    def test_provider_untagged_returns_none(self, tmp_path):
        path = _build_media(tmp_path, "mp3")
        assert MutagenArtworkProvider().get_embedded_artwork(path) is None

    def test_provider_missing_file_returns_none(self, tmp_path):
        missing = tmp_path / "does_not_exist.mp3"
        assert MutagenArtworkProvider().get_embedded_artwork(missing) is None

    def test_provider_corrupt_file_returns_none(self, tmp_path):
        path = tmp_path / "garbage.mp3"
        path.write_bytes(b"\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99" * 4)
        assert MutagenArtworkProvider().get_embedded_artwork(path) is None

    def test_provider_over_limit_returns_none(self, tmp_path):
        path = _build_media(tmp_path, "mp3")
        audio = MP3(str(path))
        audio.add_tags()
        audio.tags.add(
            APIC(encoding=3, mime="image/png", type=3, desc="", data=PNG_1x1)
        )
        audio.save()
        provider = MutagenArtworkProvider(max_bytes=4)  # PNG_1x1 is bigger
        assert provider.get_embedded_artwork(path) is None


class TestArtworkCache:
    def test_cache_store_creates_deterministic_file(self, tmp_path):
        cache = ArtworkCache(tmp_path / "cache")
        key = "album one::artist one"
        artwork = Artwork(data=PNG_1x1, mime_type="image/png")
        first = cache.store(key, artwork)
        assert first is not None
        assert first.exists()
        digest = hashlib.sha256(key.encode()).hexdigest()[:16]
        assert first.name == f"{digest}.png"
        assert first.read_bytes() == PNG_1x1
        # Idempotent: same key -> same path, content untouched (no rewrite).
        second = cache.store(key, artwork)
        assert second == first
        assert second.read_bytes() == PNG_1x1

    def test_cache_empty_data_returns_none(self, tmp_path):
        cache = ArtworkCache(tmp_path / "cache")
        assert cache.store("some key", Artwork(data=b"", mime_type="image/png")) is None


class TestLibraryArtworkScan:
    def test_scan_enriches_albums_with_artwork(self, tmp_path):
        paths = [
            tmp_path / "a1.mp3",
            tmp_path / "a2.mp3",
            tmp_path / "b1.flac",
            tmp_path / "b2.flac",
        ]
        for p in paths:
            p.write_bytes(b"x")
        provider = FakeArtworkProvider(artwork=Artwork(b"x", "image/png"))
        cache = FakeArtworkCache()
        library = _make_library(
            FakeScanner(paths),
            FakeExtractor(factory=_album_factory()),
            artwork_provider=provider,
            artwork_cache=cache,
        )
        library.scan(str(tmp_path))
        albums = library.state.albums
        assert len(albums) == 2
        assert all(isinstance(a, AlbumRef) for a in albums)
        assert all(a.has_artwork for a in albums)
        # store() is called once per album (first track only).
        assert len(cache.stores) == len(albums)

    def test_scan_no_provider_has_artwork_false(self, tmp_path):
        paths = [tmp_path / "a1.mp3", tmp_path / "b1.mp3"]
        for p in paths:
            p.write_bytes(b"x")
        library = _make_library(
            FakeScanner(paths), FakeExtractor(factory=_album_factory())
        )
        library.scan(str(tmp_path))
        assert len(library.state.albums) == 2
        assert all(not a.has_artwork for a in library.state.albums)

    def test_scan_provider_none_falls_through(self, tmp_path):
        paths = [tmp_path / "a1.mp3", tmp_path / "b1.mp3"]
        for p in paths:
            p.write_bytes(b"x")
        provider = FakeArtworkProvider(artwork=None)
        cache = FakeArtworkCache()
        library = _make_library(
            FakeScanner(paths),
            FakeExtractor(factory=_album_factory()),
            artwork_provider=provider,
            artwork_cache=cache,
        )
        library.scan(str(tmp_path))  # must not crash
        assert len(library.state.albums) == 2
        assert all(not a.has_artwork for a in library.state.albums)
        assert len(provider.calls) > 0  # provider was consulted

    def test_failed_scan_preserves_albums_with_artwork(self, tmp_path):
        paths = [tmp_path / "a1.mp3", tmp_path / "b1.mp3"]
        for p in paths:
            p.write_bytes(b"x")
        scanner = FailingScanner(paths)
        provider = FakeArtworkProvider(artwork=Artwork(b"x", "image/png"))
        cache = FakeArtworkCache()
        library = _make_library(
            scanner,
            FakeExtractor(factory=_album_factory()),
            artwork_provider=provider,
            artwork_cache=cache,
        )
        library.scan(str(tmp_path))
        assert all(a.has_artwork for a in library.state.albums)
        missing = tmp_path / "gone"
        scanner.scan_error = LibraryFilesystemError(
            LibraryDiagnosticCode.DIRECTORY_MISSING, path=missing, detail="gone"
        )
        library.scan(str(missing))
        assert library.state.diagnostic is not None
        assert library.state.diagnostic.code is LibraryDiagnosticCode.DIRECTORY_MISSING
        assert len(library.state.albums) == 2
        assert all(a.has_artwork for a in library.state.albums)

    def test_album_key_deterministic_cache_key(self, tmp_path):
        paths = [tmp_path / "a1.mp3", tmp_path / "b1.mp3"]
        for p in paths:
            p.write_bytes(b"x")
        provider = FakeArtworkProvider(artwork=Artwork(b"x", "image/png"))
        cache = FakeArtworkCache()
        library = _make_library(
            FakeScanner(paths),
            FakeExtractor(factory=_album_factory()),
            artwork_provider=provider,
            artwork_cache=cache,
        )
        library.scan(str(tmp_path))
        keys_first = [key for key, _ in cache.stores]
        paths_first = list(cache.paths.values())
        cache.stores = []
        library.scan(str(tmp_path))
        keys_second = [key for key, _ in cache.stores]
        assert keys_first == keys_second
        assert list(cache.paths.values()) == paths_first
