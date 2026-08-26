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

M6.1 additions (canonical music model v2 — Phase-1 RED):
- Per-album CANONICAL track ordering: (disc>0 or 10**6, track>0 or 10**6,
  (sort_title or title or "").casefold(), str(file_path)) — UNKNOWN (0)
  sorts LAST within its dimension, never invented as 1; multi-disc albums
  are Disc 1 1..n then Disc 2 1..n; independent of scan/insertion order
- Composer model: ComposerRef + MusicModel.composers (normalized key via
  make_composer_key; empty -> "Unknown Composer"; sorted by key; counts sum
  to total tracks) + LibraryState.composers populated by the service
- AlbumRef V2: disc_count (distinct non-zero discs, 1 when all unknown),
  genres (distinct member genres, sorted casefold, empty excluded),
  composers (distinct member composers, sorted, empty excluded)
- Domain timeline projection: timeline_decade + build_timeline_projection
  (sorted -year, key) with TimelineAlbumProjection rows
"""

from pathlib import Path

from michi.application.library_port import LibraryFilesystemError
from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.playback_session_service import PlaybackSessionService
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
    album_artist="",
    compilation=False,
    track_number=0,
    disc_number=0,
    composer="",
    genre="",
    year=0,
):
    return TrackRef(
        file_path=Path(path),
        display_name=title or Path(path).stem,
        title=title,
        artist=artist,
        album=album,
        duration_ms=duration_ms,
        album_artist=album_artist,
        compilation=compilation,
        track_number=track_number,
        disc_number=disc_number,
        composer=composer,
        genre=genre,
        year=year,
    )


def _make_library(scanner, extractor=None):
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService()
    _session = PlaybackSessionService(playback, queue)
    if extractor is None:
        library = LibraryService(scanner)
    else:
        library = LibraryService(scanner, metadata_extractor=extractor)
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


class TestCompilationAwareAlbumGrouping:
    """LOCAL-META-02.2c compilation-aware album grouping — Phase-1 RED tests.

    Target contract (michi/domain/library.py): the resolved album artist per
    track is ``track.album_artist`` if non-empty, else "Various Artists" when
    ``track.compilation`` is set, else ``track.artist``. Albums group by
    ``make_album_key(track.album, resolved_album_artist)`` and the album
    display artist is the resolved album artist. On the current baseline the
    grouping still uses the per-track artist, so the compilation-aware tests
    fail (RED); the key-function tests fail with ImportError until the public
    ``make_album_key`` / ``make_artist_key`` API lands.
    """

    def test_normal_single_artist_album_unchanged(self):
        from michi.domain.library import make_album_key

        tracks = [
            _track("/m/a.mp3", title="A", artist="Artist One", album="Album One"),
            _track("/m/b.mp3", title="B", artist="Artist One", album="Album One"),
        ]
        model = build_music_model(tracks)
        assert len(model.albums) == 1
        album = model.albums[0]
        assert album.artist == "Artist One"
        assert album.key == make_album_key("Album One", "Artist One")

    def test_compilation_with_albumartist_single_album(self):
        tracks = [
            _track(
                "/m/a.mp3",
                title="A",
                artist="Artist A",
                album="Best of the 80s",
                album_artist="Various Artists",
            ),
            _track(
                "/m/b.mp3",
                title="B",
                artist="Artist B",
                album="Best of the 80s",
                album_artist="Various Artists",
            ),
            _track(
                "/m/c.mp3",
                title="C",
                artist="Artist C",
                album="Best of the 80s",
                album_artist="Various Artists",
            ),
        ]
        model = build_music_model(tracks)
        assert len(model.albums) == 1
        album = model.albums[0]
        assert album.title == "Best of the 80s"
        assert album.artist == "Various Artists"
        assert album.track_count == 3
        assert album.track_paths == (
            Path("/m/a.mp3"),
            Path("/m/b.mp3"),
            Path("/m/c.mp3"),
        )

    def test_compilation_flag_only_groups(self):
        tracks = [
            _track(
                "/m/a.mp3",
                title="A",
                artist="Artist A",
                album="Now That's What I Call Music",
                compilation=True,
            ),
            _track(
                "/m/b.mp3",
                title="B",
                artist="Artist B",
                album="Now That's What I Call Music",
                compilation=True,
            ),
        ]
        model = build_music_model(tracks)
        assert len(model.albums) == 1
        album = model.albums[0]
        assert album.artist == "Various Artists"
        assert album.track_count == 2

    def test_album_artist_absent_groups_by_track_artist(self):
        tracks = [
            _track("/m/a.mp3", title="A", artist="Artist A", album="Split"),
            _track("/m/b.mp3", title="B", artist="Artist B", album="Split"),
        ]
        model = build_music_model(tracks)
        assert len(model.albums) == 2
        assert {a.artist for a in model.albums} == {"Artist A", "Artist B"}
        assert all(a.track_count == 1 for a in model.albums)

    def test_same_album_title_different_album_artists_distinct(self):
        tracks = [
            _track(
                "/m/a.mp3",
                title="A",
                artist="The Band",
                album="Greatest Hits",
                album_artist="Artist One",
            ),
            _track(
                "/m/b.mp3",
                title="B",
                artist="The Band",
                album="Greatest Hits",
                album_artist="Artist Two",
            ),
        ]
        model = build_music_model(tracks)
        assert len(model.albums) == 2
        assert {a.artist for a in model.albums} == {"Artist One", "Artist Two"}
        assert all(a.track_count == 1 for a in model.albums)

    def test_case_and_whitespace_album_artist(self):
        tracks = [
            _track(
                "/m/a.mp3",
                title="A",
                artist="Singer One",
                album="Album One",
                album_artist="Artist A",
            ),
            _track(
                "/m/b.mp3",
                title="B",
                artist="Singer Two",
                album="album one",
                album_artist="artist a",
            ),
        ]
        model = build_music_model(tracks)
        assert len(model.albums) == 1
        album = model.albums[0]
        assert album.title == "Album One"
        assert album.artist == "Artist A"

    def test_compilation_featured_track_artists(self):
        tracks = [
            _track(
                "/m/a.mp3",
                title="A",
                artist="X feat. Y",
                album="Hits",
                album_artist="VA",
                compilation=True,
            ),
            _track(
                "/m/b.mp3",
                title="B",
                artist="Y feat. Z",
                album="Hits",
                album_artist="VA",
                compilation=True,
            ),
        ]
        model = build_music_model(tracks)
        assert len(model.albums) == 1
        album = model.albums[0]
        assert album.artist == "VA"
        assert album.track_count == 2

    def test_album_key_function_used_by_model(self):
        from michi.domain.library import make_album_key

        tracks = [
            _track("/m/a.mp3", title="A", artist="Artist One", album="Album One"),
            _track(
                "/m/b.mp3",
                title="B",
                artist="Artist Two",
                album="Hits",
                compilation=True,
            ),
        ]
        model = build_music_model(tracks)
        assert len(model.albums) == 2
        for album in model.albums:
            assert album.key == make_album_key(album.title, album.artist)
        keys = {a.title: a.key for a in model.albums}
        assert keys["Album One"] == make_album_key("Album One", "Artist One")
        assert keys["Hits"] == make_album_key("Hits", "Various Artists")


class TestCanonicalTrackOrdering:
    """M6.1 — canonical per-album track ordering (Phase-1 RED).

    Target contract (michi/domain/library.py build_music_model): each
    album's ``track_paths`` is ordered by ``(disc_number if >0 else 10**6,
    track_number if >0 else 10**6, (sort_title or title or "").casefold(),
    str(file_path))``. UNKNOWN (0) sorts deterministically LAST within its
    dimension — never invented as 1. The order is independent of the
    scan/insertion order; multi-disc albums are always Disc 1 tracks then
    Disc 2 tracks.
    """

    def test_canonical_multi_disc_ordering(self):
        # Disc 1: tracks 3, 1, 2; Disc 2: tracks 2, 1 — INSERTED SHUFFLED.
        tracks = [
            _track(
                "/m/album/d1t3.mp3",
                title="One Three",
                artist="Artist",
                album="Multi",
                disc_number=1,
                track_number=3,
            ),
            _track(
                "/m/album/d2t2.mp3",
                title="Two Two",
                artist="Artist",
                album="Multi",
                disc_number=2,
                track_number=2,
            ),
            _track(
                "/m/album/d1t1.mp3",
                title="One One",
                artist="Artist",
                album="Multi",
                disc_number=1,
                track_number=1,
            ),
            _track(
                "/m/album/d2t1.mp3",
                title="Two One",
                artist="Artist",
                album="Multi",
                disc_number=2,
                track_number=1,
            ),
            _track(
                "/m/album/d1t2.mp3",
                title="One Two",
                artist="Artist",
                album="Multi",
                disc_number=1,
                track_number=2,
            ),
        ]
        album = build_music_model(tracks).albums[0]
        # ORDER IS INDEPENDENT OF THE INPUT ORDER.
        assert album.track_paths == (
            Path("/m/album/d1t1.mp3"),  # Disc 1 track 1
            Path("/m/album/d1t2.mp3"),  # Disc 1 track 2
            Path("/m/album/d1t3.mp3"),  # Disc 1 track 3
            Path("/m/album/d2t1.mp3"),  # Disc 2 track 1
            Path("/m/album/d2t2.mp3"),  # Disc 2 track 2
        )

    def test_unknown_track_disc_numbers_sort_last_deterministic(self):
        tracks = [
            _track(
                "/m/album/u1.mp3",
                title="Disc0 Track2",
                artist="A",
                album="U",
                disc_number=0,
                track_number=2,
            ),
            _track(
                "/m/album/u2.mp3",
                title="Disc1 Track0",
                artist="A",
                album="U",
                disc_number=1,
                track_number=0,
            ),
            _track(
                "/m/album/u3.mp3",
                title="Disc0 Track0",
                artist="A",
                album="U",
                disc_number=0,
                track_number=0,
            ),
            _track(
                "/m/album/u4.mp3",
                title="Disc1 Track1",
                artist="A",
                album="U",
                disc_number=1,
                track_number=1,
            ),
        ]
        album = build_music_model(tracks).albums[0]
        # Exact expected sequence by sort key
        # (disc>0?disc:10**6, track>0?track:10**6, title, path):
        #   (1, 1)       -> u4 (disc1 track1)
        #   (1, 10**6)   -> u2 (disc1 track0: unknown track sorts last in disc1)
        #   (10**6, 2)   -> u1 (disc0 track2: unknown disc sorts last overall)
        #   (10**6, 10**6) -> u3 (disc0 track0)
        assert album.track_paths == (
            Path("/m/album/u4.mp3"),
            Path("/m/album/u2.mp3"),
            Path("/m/album/u1.mp3"),
            Path("/m/album/u3.mp3"),
        )

    def test_same_input_shuffled_same_canonical_output(self):
        from michi.domain.library import ComposerRef

        base = [
            _track(
                "/m/one.mp3",
                title="One",
                artist="Artist One",
                album="Album One",
                genre="Rock",
                composer="C1",
                disc_number=1,
                track_number=1,
            ),
            _track(
                "/m/two.mp3",
                title="Two",
                artist="Artist One",
                album="Album One",
                genre="Jazz",
                composer="C2",
                disc_number=1,
                track_number=2,
            ),
            _track(
                "/m/three.mp3",
                title="Three",
                artist="Artist Two",
                album="Album Two",
                genre="Rock",
                composer="C1",
            ),
        ]
        shuffled = [base[2], base[0], base[1]]
        first = build_music_model(base)
        second = build_music_model(shuffled)
        assert first == second
        assert first.albums[0].track_paths == second.albums[0].track_paths
        assert first.artists == second.artists
        assert first.genres == second.genres
        assert first.composers == second.composers
        assert all(isinstance(c, ComposerRef) for c in first.composers)


class TestComposerModel:
    """M6.1 — composer model (Phase-1 RED).

    Target contract (michi/domain/library.py): ``ComposerRef`` with
    key/name/track_count; ``MusicModel.composers`` groups composers by
    ``make_composer_key`` (empty composer -> bucket "Unknown Composer");
    sorted by key; sum of composer track_counts == total tracks.
    """

    def test_composer_grouping(self):
        from michi.domain.library import ComposerRef

        tracks = [
            _track(
                "/m/c1a.mp3", title="A", artist="X", album="Al", composer="Composer One"
            ),
            _track(
                "/m/c1b.mp3", title="B", artist="X", album="Al", composer="Composer One"
            ),
            _track(
                "/m/c2.mp3", title="C", artist="X", album="Al", composer="Composer Two"
            ),
            _track("/m/cn.mp3", title="D", artist="X", album="Al", composer=""),
        ]
        model = build_music_model(tracks)
        assert model.composers == (
            ComposerRef(key="composer one", name="Composer One", track_count=2),
            ComposerRef(key="composer two", name="Composer Two", track_count=1),
            ComposerRef(key="unknown composer", name="Unknown Composer", track_count=1),
        )
        assert sum(c.track_count for c in model.composers) == len(tracks)

    def test_composer_key_normalized(self):
        from michi.domain.library import make_composer_key

        tracks = [
            _track(
                "/m/a.mp3",
                title="A",
                artist="X",
                album="Al",
                composer="John Williams",
            ),
            _track(
                "/m/b.mp3",
                title="B",
                artist="X",
                album="Al",
                composer="john williams",
            ),
        ]
        model = build_music_model(tracks)
        assert len(model.composers) == 1
        composer = model.composers[0]
        assert composer.key == make_composer_key("John Williams") == "john williams"
        assert composer.name == "John Williams"  # first member wins
        assert composer.track_count == 2


class TestAlbumModelV2:
    """M6.1 — AlbumRef V2 derived fields (Phase-1 RED).

    Target contract (michi/domain/library.py): AlbumRef gains
    ``disc_count`` (distinct non-zero disc numbers, or 1 when all unknown),
    ``genres`` (distinct member genres, sorted casefold, empty strings
    excluded) and ``composers`` (distinct member composers, sorted, empty
    excluded); build_music_model derives them from the members.
    """

    def test_album_disc_count(self):
        tracks = [
            _track(
                "/m/a.mp3",
                title="A",
                artist="X",
                album="Multi",
                disc_number=1,
                track_number=1,
            ),
            _track(
                "/m/b.mp3",
                title="B",
                artist="X",
                album="Multi",
                disc_number=1,
                track_number=2,
            ),
            _track(
                "/m/c.mp3",
                title="C",
                artist="X",
                album="Multi",
                disc_number=2,
                track_number=1,
            ),
        ]
        multi = build_music_model(tracks).albums[0]
        assert multi.disc_count == 2

        unknown = build_music_model(
            [
                _track("/m/u1.mp3", title="A", artist="X", album="Solo"),
                _track("/m/u2.mp3", title="B", artist="X", album="Solo"),
            ]
        ).albums[0]
        assert unknown.disc_count == 1  # all disc numbers unknown -> 1

    def test_album_genres_and_composers_derived(self):
        tracks = [
            _track(
                "/m/one.mp3",
                title="One",
                artist="X",
                album="Al",
                genre="Rock",
                composer="C1",
            ),
            _track(
                "/m/two.mp3",
                title="Two",
                artist="X",
                album="Al",
                genre="Jazz",
                composer="C2",
            ),
            _track(
                "/m/three.mp3",
                title="Three",
                artist="X",
                album="Al",
                genre="Rock",
                composer="C1",
            ),
            _track(
                "/m/four.mp3",
                title="Four",
                artist="X",
                album="Al",
                genre="",
                composer="",
            ),
        ]
        album = build_music_model(tracks).albums[0]
        # Distinct, sorted casefold; empty strings excluded.
        assert album.genres == ("Jazz", "Rock")
        assert album.composers == ("C1", "C2")


class TestComposersInLibraryState:
    """M6.1 — LibraryService._rebuild_derived_library_state must populate
    state.composers from the model (Phase-1 RED); failed scan preserves;
    empty scan resets."""

    def _composer_factory(self):
        def factory(path):
            return TrackMetadata(
                title=path.stem,
                artist="Artist One",
                album="Album One",
                duration_ms=1000,
                composer=path.stem[:2],  # "c1a" -> "c1", "c2a" -> "c2"
            )

        return factory

    def test_scan_populates_composers(self, tmp_path):
        p1 = tmp_path / "c1a.mp3"
        p2 = tmp_path / "c1b.mp3"
        p3 = tmp_path / "c2a.mp3"
        for p in (p1, p2, p3):
            p.write_bytes(b"x")
        library = _make_library(
            FakeScanner([p1, p2, p3]), FakeExtractor(factory=self._composer_factory())
        )
        library.scan(str(tmp_path))
        assert [c.name for c in library.state.composers] == ["c1", "c2"]
        assert [c.track_count for c in library.state.composers] == [2, 1]

    def test_failed_scan_preserves_composers(self, tmp_path):
        p1 = tmp_path / "c1a.mp3"
        p1.write_bytes(b"x")
        scanner = FailingScanner([p1])
        library = _make_library(
            scanner, FakeExtractor(factory=self._composer_factory())
        )
        library.scan(str(tmp_path))
        before = library.state.composers
        assert before
        scanner.scan_error = LibraryFilesystemError(
            LibraryDiagnosticCode.DIRECTORY_MISSING, path=tmp_path / "gone"
        )
        library.scan(str(tmp_path / "gone"))
        assert library.state.diagnostic is not None
        assert library.state.diagnostic.code is LibraryDiagnosticCode.DIRECTORY_MISSING
        assert library.state.composers == before

    def test_empty_scan_resets_composers(self, tmp_path):
        p1 = tmp_path / "c1a.mp3"
        p1.write_bytes(b"x")
        scanner = FakeScanner([p1])
        library = _make_library(
            scanner, FakeExtractor(factory=self._composer_factory())
        )
        library.scan(str(tmp_path))
        assert library.state.composers
        scanner.paths = []
        library.scan(str(tmp_path / "empty"))
        assert library.state.tracks == []
        assert library.state.composers == ()


class TestTimelineProjection:
    """M6.1 — domain timeline projection (Phase-1 RED).

    Target contract (michi/domain/library.py): ``timeline_decade(year)``
    returns f"{year // 10 * 10}s" for year > 0 else "Unknown era";
    ``build_timeline_projection(albums)`` returns TimelineAlbumProjection
    rows sorted by (-year, key); the bridge adapts these rows (adding
    has_artwork/artworkPath via the service).
    """

    def test_timeline_decade(self):
        from michi.domain.library import timeline_decade

        assert timeline_decade(2021) == "2020s"
        assert timeline_decade(1999) == "1990s"
        assert timeline_decade(0) == "Unknown era"
        assert timeline_decade(-5) == "Unknown era"

    def test_build_timeline_projection(self):
        from michi.domain.library import (
            TimelineAlbumProjection,
            build_timeline_projection,
        )

        tracks = [
            _track(
                "/m/old.mp3",
                title="Old",
                artist="Artist One",
                album="Old Album",
                year=2005,
            ),
            _track(
                "/m/none.mp3",
                title="None",
                artist="Artist One",
                album="No Year",
                year=0,
            ),
            _track(
                "/m/new.mp3",
                title="New",
                artist="Artist Two",
                album="New Album",
                year=2021,
            ),
        ]
        model = build_music_model(tracks)
        projection = build_timeline_projection(model.albums)
        assert isinstance(projection, tuple)
        assert all(isinstance(p, TimelineAlbumProjection) for p in projection)
        assert [p.year for p in projection] == [2021, 2005, 0]
        assert [p.decade for p in projection] == ["2020s", "2000s", "Unknown era"]
        by_year = {a.year: a for a in model.albums}
        for p in projection:
            album = by_year[p.year]
            assert p.album_key == album.key  # matches make_album_key identity
            assert p.title == album.title
            assert p.artist == album.artist
        # Deterministic: same input -> identical projection.
        assert build_timeline_projection(model.albums) == projection
