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
from michi.application.playback_session_service import PlaybackSessionService
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
# A second PNG payload — same mime, DIFFERENT content (M6.5: the cache key
# must be content-digest-aware, so mime alone must not keep the same path).
PNG_1x1_ALT = b"\x89PNG\r\n\x1a\n" + b"\xff" * 20


class FakeArtworkProvider:
    """Duck-typed provider: canned artwork (or None) for every path."""

    def __init__(self, artwork=None, local_artwork=None):
        self.artwork = artwork
        self.local_artwork = local_artwork
        self.calls = []
        self.local_calls = []

    def get_embedded_artwork(self, file_path):
        self.calls.append(file_path)
        return self.artwork

    def get_local_artwork(self, album_dir):
        self.local_calls.append(album_dir)
        return self.local_artwork


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
    queue = QueueService()
    _session = PlaybackSessionService(playback, queue)
    return LibraryService(
        scanner,
        metadata_extractor=extractor,
        artwork_provider=artwork_provider,
        artwork_cache=artwork_cache,
    )


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
        # M6.5: the cache key is content-digest-aware — sha256(album_key +
        # sha256(data))[:16] — so the v1 album-key-only derivation no longer
        # matches the produced filename. The digest participates in the key
        # so CHANGED artwork yields a NEW entry (active on rescan) while
        # unchanged content keeps the same path (see TestCacheDigestInvalidation
        # for the authoritative M6.5 contract).
        content_digest = hashlib.sha256(PNG_1x1).hexdigest()
        digest = hashlib.sha256((key + content_digest).encode()).hexdigest()[:16]
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


class TestFrontCoverPreference:
    """M6.5 — embedded selection must prefer the FRONT COVER designation
    (APIC/Picture type 3) over the first frame, and fall back to the first
    image only when NO front-cover designation exists."""

    def test_embedded_front_wins_when_not_first(self, tmp_path):
        path = _build_media(tmp_path, "mp3")
        audio = MP3(str(path))
        audio.add_tags()
        back = APIC(encoding=3, mime="image/jpeg", type=4, desc="back", data=JPEG_BYTES)
        front = APIC(encoding=3, mime="image/png", type=3, desc="front", data=PNG_1x1)
        audio.tags.add(back)  # BACK tagged FIRST
        audio.tags.add(front)  # FRONT second — must win
        audio.save()
        artwork = MutagenArtworkProvider().get_embedded_artwork(path)
        assert artwork is not None
        assert artwork.data == PNG_1x1
        assert artwork.mime_type == "image/png"

    def test_embedded_flac_front_picture_preferred(self, tmp_path):
        path = _build_media(tmp_path, "flac")
        audio = FLAC(str(path))
        back = Picture()
        back.type = 4
        back.mime = "image/jpeg"
        back.data = JPEG_BYTES
        front = Picture()
        front.type = 3
        front.mime = "image/png"
        front.data = PNG_1x1
        audio.add_picture(back)  # BACK first
        audio.add_picture(front)  # FRONT second — must win
        audio.save()
        artwork = MutagenArtworkProvider().get_embedded_artwork(path)
        assert artwork is not None
        assert artwork.data == PNG_1x1
        assert artwork.mime_type == "image/png"

    def test_embedded_no_front_designation_uses_first(self, tmp_path):
        path = _build_media(tmp_path, "mp3")
        audio = MP3(str(path))
        audio.add_tags()
        first = APIC(
            encoding=3, mime="image/jpeg", type=4, desc="back", data=JPEG_BYTES
        )
        second = APIC(encoding=3, mime="image/png", type=6, desc="media", data=PNG_1x1)
        audio.tags.add(first)
        audio.tags.add(second)
        audio.save()
        artwork = MutagenArtworkProvider().get_embedded_artwork(path)
        assert artwork is not None
        assert artwork.data == JPEG_BYTES  # no front cover -> the FIRST frame
        assert artwork.mime_type == "image/jpeg"


def _album_dir_with_track(tmp_path, name="album"):
    """A directory holding a bare MP3 (no embedded art) — the unit under
    test for the local artwork fallback."""
    album_dir = tmp_path / name
    album_dir.mkdir()
    _build_media(album_dir, "mp3")
    return album_dir


class TestLocalArtworkFallback:
    """M6.5 — deterministic local fallback: cover.jpg, cover.jpeg, cover.png,
    folder.jpg, folder.png, front.jpg, front.png (case-insensitive), read
    from the album directory; unreadable/over-max entries are skipped."""

    def test_cover_jpg_fallback(self, tmp_path):
        album_dir = _album_dir_with_track(tmp_path)
        (album_dir / "cover.jpg").write_bytes(JPEG_BYTES)
        artwork = MutagenArtworkProvider().get_local_artwork(album_dir)
        assert artwork is not None
        assert artwork.data == JPEG_BYTES
        assert artwork.mime_type == "image/jpeg"

    def test_folder_png_fallback(self, tmp_path):
        album_dir = _album_dir_with_track(tmp_path)
        (album_dir / "folder.png").write_bytes(PNG_1x1)
        artwork = MutagenArtworkProvider().get_local_artwork(album_dir)
        assert artwork is not None
        assert artwork.data == PNG_1x1
        assert artwork.mime_type == "image/png"

    def test_front_jpg_fallback(self, tmp_path):
        album_dir = _album_dir_with_track(tmp_path)
        (album_dir / "front.jpg").write_bytes(JPEG_BYTES)
        artwork = MutagenArtworkProvider().get_local_artwork(album_dir)
        assert artwork is not None
        assert artwork.data == JPEG_BYTES
        assert artwork.mime_type == "image/jpeg"

    def test_local_case_insensitive(self, tmp_path):
        album_dir = _album_dir_with_track(tmp_path)
        (album_dir / "COVER.JPG").write_bytes(JPEG_BYTES)
        artwork = MutagenArtworkProvider().get_local_artwork(album_dir)
        assert artwork is not None
        assert artwork.data == JPEG_BYTES
        assert artwork.mime_type == "image/jpeg"

    def test_local_priority_order(self, tmp_path):
        album_dir = _album_dir_with_track(tmp_path)
        (album_dir / "cover.jpg").write_bytes(JPEG_BYTES)
        (album_dir / "folder.png").write_bytes(PNG_1x1)
        artwork = MutagenArtworkProvider().get_local_artwork(album_dir)
        assert artwork is not None
        assert artwork.data == JPEG_BYTES  # cover.jpg wins the order
        assert artwork.mime_type == "image/jpeg"

    def test_local_none_returns_none(self, tmp_path):
        album_dir = _album_dir_with_track(tmp_path)
        assert MutagenArtworkProvider().get_local_artwork(album_dir) is None

    def test_local_unreadable_skipped(self, tmp_path, monkeypatch):
        album_dir = _album_dir_with_track(tmp_path)
        cover_jpg = album_dir / "cover.jpg"
        cover_jpg.write_bytes(JPEG_BYTES)
        folder_png = album_dir / "folder.png"
        folder_png.write_bytes(PNG_1x1)
        provider = MutagenArtworkProvider()

        real_read_bytes = Path.read_bytes

        def fake_read_bytes(self_, *args, **kwargs):
            if self_ == cover_jpg:
                raise OSError("simulated unreadable")
            return real_read_bytes(self_, *args, **kwargs)

        monkeypatch.setattr(Path, "read_bytes", fake_read_bytes)
        artwork = provider.get_local_artwork(album_dir)
        assert artwork is not None
        assert artwork.data == PNG_1x1  # cover.jpg skipped -> folder.png wins
        assert artwork.mime_type == "image/png"

        # Every candidate unreadable -> all skipped -> None.
        def fake_read_bytes_always(self_, *args, **kwargs):
            raise OSError("simulated unreadable")

        monkeypatch.setattr(Path, "read_bytes", fake_read_bytes_always)
        assert provider.get_local_artwork(album_dir) is None

    def test_local_unknown_extension_not_scanned(self, tmp_path):
        album_dir = _album_dir_with_track(tmp_path)
        (album_dir / "cover.jpg2").write_bytes(JPEG_BYTES)
        (album_dir / "notes.txt").write_bytes(b"not art")
        assert MutagenArtworkProvider().get_local_artwork(album_dir) is None


class TestResolutionOrder:
    """M6.5 — per album: 1. embedded (front-preferred) from the tracks in
    order; 2. if none -> local artwork from the album directory; 3. none ->
    has_artwork False (cache untouched)."""

    def test_embedded_wins_over_local(self, tmp_path):
        album_dir = tmp_path / "album"
        album_dir.mkdir()
        track = album_dir / "a1.mp3"
        track.write_bytes(b"x")
        (album_dir / "cover.jpg").write_bytes(JPEG_BYTES)
        provider = FakeArtworkProvider(
            artwork=Artwork(data=PNG_1x1, mime_type="image/png"),
            local_artwork=Artwork(data=JPEG_BYTES, mime_type="image/jpeg"),
        )
        cache = FakeArtworkCache()
        library = _make_library(
            FakeScanner([track]),
            FakeExtractor(factory=_album_factory()),
            artwork_provider=provider,
            artwork_cache=cache,
        )
        library.scan(str(tmp_path))
        album = library.state.albums[0]
        assert album.has_artwork is True
        stored = next(art for key, art in cache.stores if key == album.key)
        assert stored.data == PNG_1x1  # EMBEDDED content, not the local bytes
        assert provider.local_calls == []  # embedded won; local never consulted

    def test_local_fallback_when_no_embedded(self, tmp_path):
        album_dir = tmp_path / "album"
        album_dir.mkdir()
        track = album_dir / "a1.mp3"
        track.write_bytes(b"x")
        (album_dir / "cover.jpg").write_bytes(JPEG_BYTES)
        provider = FakeArtworkProvider(
            artwork=None,  # no embedded art anywhere
            local_artwork=Artwork(data=JPEG_BYTES, mime_type="image/jpeg"),
        )
        cache = FakeArtworkCache()
        library = _make_library(
            FakeScanner([track]),
            FakeExtractor(factory=_album_factory()),
            artwork_provider=provider,
            artwork_cache=cache,
        )
        library.scan(str(tmp_path))
        album = library.state.albums[0]
        assert album.has_artwork is True
        stored = next(art for key, art in cache.stores if key == album.key)
        assert stored.data == JPEG_BYTES  # the LOCAL bytes
        assert stored.mime_type == "image/jpeg"

    def test_no_artwork_anywhere(self, tmp_path):
        album_dir = tmp_path / "album"
        album_dir.mkdir()
        track = album_dir / "a1.mp3"
        track.write_bytes(b"x")
        provider = FakeArtworkProvider(artwork=None, local_artwork=None)
        cache = FakeArtworkCache()
        library = _make_library(
            FakeScanner([track]),
            FakeExtractor(factory=_album_factory()),
            artwork_provider=provider,
            artwork_cache=cache,
        )
        library.scan(str(tmp_path))
        assert library.state.albums[0].has_artwork is False
        assert cache.stores == []  # cache never consulted


class TestCacheDigestInvalidation:
    """M6.5 — the cache key participates in the artwork CONTENT: changed
    artwork yields a NEW path (active on rescan); unchanged content keeps
    the same path without rewriting (idempotent); old entries stay in place
    (stale-aware, no eager deletion)."""

    def test_changed_artwork_invalidates_cache(self, tmp_path):
        cache = ArtworkCache(tmp_path / "cache")
        key = "album one::artist one"
        art_a = Artwork(data=PNG_1x1, mime_type="image/png")
        art_b = Artwork(data=PNG_1x1_ALT, mime_type="image/png")
        path_a = cache.store(key, art_a)
        path_b = cache.store(key, art_b)
        assert path_a is not None
        assert path_b is not None
        assert path_a != path_b  # the content digest participates in the key
        assert path_a.read_bytes() == PNG_1x1
        assert path_b.read_bytes() == PNG_1x1_ALT

    def test_unchanged_content_same_path_no_rewrite(self, tmp_path):
        cache = ArtworkCache(tmp_path / "cache")
        key = "album one::artist one"
        artwork = Artwork(data=PNG_1x1, mime_type="image/png")
        first = cache.store(key, artwork)
        assert first is not None
        mtime_ns = first.stat().st_mtime_ns
        second = cache.store(key, artwork)
        assert second == first  # unchanged content -> the SAME path
        assert second.stat().st_mtime_ns == mtime_ns  # no rewrite
        assert second.read_bytes() == PNG_1x1

    def test_enrichment_updated_artwork_becomes_active(self, tmp_path):
        album_dir = tmp_path / "album"
        album_dir.mkdir()
        track = album_dir / "a1.mp3"
        track.write_bytes(b"x")
        provider = FakeArtworkProvider(
            artwork=Artwork(data=PNG_1x1, mime_type="image/png")
        )
        cache = ArtworkCache(tmp_path / "cache")
        library = _make_library(
            FakeScanner([track]),
            FakeExtractor(factory=_album_factory()),
            artwork_provider=provider,
            artwork_cache=cache,
        )
        library.scan(str(tmp_path))
        album_key = library.state.albums[0].key
        path_a = library.artwork_path_for(album_key)
        assert path_a is not None
        assert Path(path_a).read_bytes() == PNG_1x1

        # The embedded artwork is replaced with different content (same
        # mime) — the digest-aware key must make the NEW artwork active.
        provider.artwork = Artwork(data=PNG_1x1_ALT, mime_type="image/png")
        library.scan(str(tmp_path))
        path_b = library.artwork_path_for(album_key)
        assert path_b is not None
        assert path_a != path_b
        assert Path(path_b).read_bytes() == PNG_1x1_ALT
        # Stale-aware: the old entry is left in place (no eager deletion).
        assert Path(path_a).exists()
