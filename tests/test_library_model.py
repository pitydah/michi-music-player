"""LOCAL-01 canonical music model — Phase-1 RED tests.

On the current baseline the module-level imports of the new domain symbols
fail at collection (ImportError) — that IS the expected Phase-1 red evidence.
The tests encode the target contract and must pass once the production
changes land (michi/domain/library.py AlbumRef/ArtistRef/MusicModel/
build_music_model + LibraryState.albums/artists, LibraryService model
rebuild on successful scan, LibraryBridge albumCount/artistCount).

Coverage:
- Album grouping by (album, primary artist) with normalized keys
- Case-insensitive album key normalization
- Artist grouping with track/album counts
- "Unknown Album" / "Unknown Artist" buckets
- Deterministic ordering by key
- Scan success rebuilds the model (service integration)
- Failed scan preserves albums/artists (TD-013 failure atomicity)
- Successful empty scan resets the model
- Bridge albumCount/artistCount projections with notify
"""

from pathlib import Path

from michi.application.library_port import LibraryFilesystemError
from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.queue_service import QueueService
from michi.domain.library import (
    AlbumRef,
    ArtistRef,
    LibraryDiagnosticCode,
    LibraryState,
    MusicModel,
    TrackMetadata,
    TrackRef,
    build_music_model,
)
from michi.presentation.library_bridge import LibraryBridge
from tests.conftest import FakeAudioPort
from tests.test_library_metadata import FakeExtractor, FakeScanner


def _track(
    path,
    title="",
    artist="",
    album="",
    duration_ms=0,
):
    return TrackRef(
        file_path=Path(path),
        display_name=title or Path(path).stem,
        title=title,
        artist=artist,
        album=album,
        duration_ms=duration_ms,
    )


def _make_library(scanner, extractor=None):
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService(playback)
    if extractor is None:
        library = LibraryService(scanner, queue)
    else:
        library = LibraryService(scanner, queue, extractor)
    return library


class FailingScanner(FakeScanner):
    """Like FakeScanner, but scan() raises the configured error when set."""

    def __init__(self, paths=None, scan_error=None):
        super().__init__(paths)
        self.scan_error = scan_error

    def scan(self, root):
        if self.scan_error is not None:
            raise self.scan_error
        return list(self.paths)


class TestBuildMusicModel:
    def test_albums_group_by_album_and_artist(self):
        tracks = [
            _track(
                "/m/a.mp3",
                title="A",
                artist="Artist One",
                album="Album One",
                duration_ms=1000,
            ),
            _track(
                "/m/b.mp3",
                title="B",
                artist="Artist One",
                album="Album One",
                duration_ms=2000,
            ),
            _track(
                "/m/c.mp3",
                title="C",
                artist="Artist Two",
                album="Album Two",
                duration_ms=3000,
            ),
        ]
        model = build_music_model(tracks)
        assert len(model.albums) == 2
        album_one = next(a for a in model.albums if a.title == "Album One")
        assert isinstance(album_one, AlbumRef)
        assert album_one.artist == "Artist One"
        assert album_one.track_count == 2
        assert album_one.duration_ms == 3000
        assert album_one.track_paths == (Path("/m/a.mp3"), Path("/m/b.mp3"))

    def test_same_album_title_different_artists_are_distinct(self):
        tracks = [
            _track("/m/a.mp3", title="A", artist="Artist One", album="Album"),
            _track("/m/b.mp3", title="B", artist="Artist Two", album="Album"),
        ]
        model = build_music_model(tracks)
        assert len(model.albums) == 2
        assert {a.artist for a in model.albums} == {"Artist One", "Artist Two"}
        assert all(a.track_count == 1 for a in model.albums)

    def test_album_key_normalization_case_insensitive(self):
        tracks = [
            _track("/m/a.mp3", title="A", artist="The Artist", album="Album One"),
            _track("/m/b.mp3", title="B", artist="The Artist", album="album one"),
        ]
        model = build_music_model(tracks)
        assert len(model.albums) == 1
        album = model.albums[0]
        assert album.track_count == 2
        assert album.title == "Album One"  # display title = first track's album

    def test_artist_grouping_track_and_album_counts(self):
        tracks = [
            _track("/m/a.mp3", title="A", artist="Artist One", album="Album One"),
            _track("/m/b.mp3", title="B", artist="Artist One", album="Album Two"),
            _track("/m/c.mp3", title="C", artist="Artist One", album="Album One"),
        ]
        model = build_music_model(tracks)
        assert len(model.artists) == 1
        artist = model.artists[0]
        assert isinstance(artist, ArtistRef)
        assert artist.name == "Artist One"
        assert artist.track_count == 3
        assert artist.album_count == 2

    def test_unknown_album_and_artist_buckets(self):
        tracks = [
            _track("/m/a.mp3", title="A", artist="", album=""),
            _track("/m/b.mp3", title="B", artist="", album=""),
            _track("/m/c.mp3", title="C", artist="Artist One", album="Album One"),
        ]
        model = build_music_model(tracks)
        unknown_album = next(a for a in model.albums if a.title == "Unknown Album")
        assert unknown_album.artist == "Unknown Artist"
        assert unknown_album.track_count == 2
        unknown_artist = next(ar for ar in model.artists if ar.name == "Unknown Artist")
        assert unknown_artist.track_count == 2
        assert unknown_artist.album_count == 1
        assert sum(a.track_count for a in model.albums) == len(tracks)

    def test_model_sorted_deterministically(self):
        tracks = [
            _track("/m/z.mp3", title="Z", artist="Zed", album="Zed Album"),
            _track("/m/a.mp3", title="A", artist="Alpha", album="Alpha Album"),
        ]
        first = build_music_model(tracks)
        second = build_music_model(tracks)
        assert isinstance(first, MusicModel)
        assert isinstance(first.albums[0], AlbumRef)
        assert isinstance(first.artists[0], ArtistRef)
        assert first == second
        keys = [a.key for a in first.albums]
        assert keys == sorted(keys)
        artist_keys = [a.key for a in first.artists]
        assert artist_keys == sorted(artist_keys)


class TestLibraryStateModelIntegration:
    def test_scan_success_rebuilds_model(self, tmp_path):
        p1 = tmp_path / "one.mp3"
        p2 = tmp_path / "two.mp3"
        p1.write_bytes(b"x")
        p2.write_bytes(b"x")

        def factory(path):
            return TrackMetadata(
                title=path.stem,
                artist="Artist One",
                album="Album One",
                duration_ms=1000,
            )

        library = _make_library(FakeScanner([p1, p2]), FakeExtractor(factory=factory))
        library.scan(str(tmp_path))
        assert isinstance(library.state, LibraryState)
        assert len(library.state.albums) == 1
        album = library.state.albums[0]
        assert album.title == "Album One"
        assert album.artist == "Artist One"
        assert album.track_count == 2
        assert album.duration_ms == 2000
        assert len(library.state.artists) == 1
        assert library.state.artists[0].track_count == 2

    def test_failed_scan_preserves_model(self, tmp_path):
        p1 = tmp_path / "one.mp3"
        p2 = tmp_path / "two.mp3"
        p1.write_bytes(b"x")
        p2.write_bytes(b"x")

        def factory(path):
            return TrackMetadata(
                title=path.stem,
                artist="Artist One",
                album="Album One",
                duration_ms=1000,
            )

        missing = tmp_path / "gone"
        scanner = FailingScanner([p1, p2])
        library = _make_library(scanner, FakeExtractor(factory=factory))
        library.scan(str(tmp_path))
        assert len(library.state.tracks) == 2
        assert len(library.state.albums) == 1
        assert len(library.state.artists) == 1
        scanner.scan_error = LibraryFilesystemError(
            LibraryDiagnosticCode.DIRECTORY_MISSING, path=missing, detail="gone"
        )
        library.scan(str(missing))
        assert library.state.diagnostic is not None
        assert library.state.diagnostic.code is LibraryDiagnosticCode.DIRECTORY_MISSING
        assert len(library.state.tracks) == 2
        assert len(library.state.albums) == 1
        assert len(library.state.artists) == 1

    def test_empty_scan_resets_model(self, tmp_path):
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        p1 = dir_a / "one.mp3"
        p2 = dir_a / "two.mp3"
        p1.write_bytes(b"x")
        p2.write_bytes(b"x")
        scanner = FakeScanner([p1, p2])
        library = _make_library(scanner, FakeExtractor())
        library.scan(str(dir_a))
        assert len(library.state.tracks) == 2
        assert len(library.state.albums) == 1
        assert len(library.state.artists) == 1
        scanner.paths = []
        library.scan(str(dir_b))
        assert library.state.tracks == []
        assert library.state.albums == ()
        assert library.state.artists == ()

    def test_bridge_album_and_artist_counts(self, tmp_path):
        p1 = tmp_path / "one.mp3"
        p2 = tmp_path / "two.mp3"
        p3 = tmp_path / "three.mp3"
        for p in (p1, p2, p3):
            p.write_bytes(b"x")

        def factory(path):
            if path == p3:
                return TrackMetadata(
                    title=path.stem,
                    artist="Artist Two",
                    album="Album Two",
                    duration_ms=500,
                )
            return TrackMetadata(
                title=path.stem,
                artist="Artist One",
                album="Album One",
                duration_ms=1000,
            )

        library = _make_library(
            FakeScanner([p1, p2, p3]), FakeExtractor(factory=factory)
        )
        bridge = LibraryBridge(library)
        fired = []
        bridge.library_changed.connect(lambda: fired.append(1))
        library.scan(str(tmp_path))
        assert bridge.property("albumCount") == 2
        assert bridge.property("artistCount") == 2
        assert len(fired) == 1
        bridge.dispose()
