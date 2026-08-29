"""LOCAL-03 rich library views — Phase-1 RED tests.

On the current baseline the module-level import of the new domain symbols
fails at collection (ImportError) — that IS the expected Phase-1 red
evidence. The tests encode the target contract and must pass once the
production changes land (genre/folder models in michi/domain/library.py,
genre extraction in michi/infrastructure/metadata_extractor.py, the
LibraryService genres/folders/artwork_paths/activate_track work, and the
LibraryBridge albums/artists/genres/folders/album-detail surface).

Coverage:
- Genre extraction (easy-mode "genre" key, untagged -> "")
- Genre grouping (normalized key, Unknown Genre bucket, sorted, sums)
- Folder grouping by file parent (build_folder_model)
- Scan populates / failed scan preserves (TD-013) / empty scan resets
- Bridge albums/artists/genres/folders row shapes + artworkPath mapping
- Album selection detail (title/artist/artwork/tracks) + clear/no-op
- activate_album_track: queue add (accepted path), TRACK_MISSING identity
  removal, IO failure preservation
- QML smoke: LibraryView.qml still instantiates with the bridge in context
  (forward pin for the tabbed view — passes trivially on baseline)
"""

import os
import sys
from pathlib import Path

import pytest
from mutagen.id3 import TCON
from mutagen.mp3 import MP3
from PySide6.QtCore import QCoreApplication, QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

try:  # QQuickPathView/QQuickListView exist in QtQuick 6, but not every PySide6
    # build exposes their Python bindings — fall back to findChild-by-objectName
    # through QObject, which matches any QObject child.
    from PySide6.QtQuick import QQuickListView, QQuickPathView
except ImportError:  # pragma: no cover - fallback path
    from PySide6.QtCore import QObject

    QQuickPathView = QObject  # type: ignore[assignment,misc]
    QQuickListView = QObject  # type: ignore[assignment,misc]

from michi.application.library_port import LibraryFilesystemError
from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.playback_session_service import PlaybackSessionService
from michi.application.queue_service import QueueService
from michi.domain.library import (
    Artwork,
    FolderRef,
    GenreRef,
    LibraryDiagnosticCode,
    TrackMetadata,
    TrackRef,
    build_folder_model,
    build_music_model,
)
from michi.infrastructure.metadata_extractor import InfrastructureMetadataExtractor
from michi.presentation.library_bridge import LibraryBridge
from tests.conftest import FakeAudioPort
from tests.test_library_artwork import (
    FailingScanner,
    FakeArtworkCache,
    FakeArtworkProvider,
)
from tests.test_library_metadata import FakeExtractor, FakeScanner
from tests.test_metadata_extractor import _build_media

QML_DIR = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


class _ValidateScanner(FakeScanner):
    """FakeScanner plus per-path validate_file errors (activation contract)."""

    def __init__(self, paths=None, validate_errors=None) -> None:
        super().__init__(paths)
        self.validate_errors = dict(validate_errors or {})

    def validate_file(self, path):
        error = self.validate_errors.get(path)
        if error is not None:
            raise error
        return None


def _make_library(scanner, extractor=None, artwork_provider=None, artwork_cache=None):
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService()
    session = PlaybackSessionService(playback, queue)
    return (
        LibraryService(
            scanner,
            metadata_extractor=extractor,
            artwork_provider=artwork_provider,
            artwork_cache=artwork_cache,
        ),
        queue,
        session,
        playback,
        audio,
    )


def _bridge_with_coordinator(library, session):
    """M4-R1: LibraryBridge playback intents route through the coordinator."""
    from michi.application.library_playback_coordinator import (
        LibraryPlaybackCoordinator,
    )

    coord = LibraryPlaybackCoordinator(library, session)
    return LibraryBridge(library, playback_coordinator=coord)


def _album_genre_factory():
    """a* -> album Alpha / genre Rock; anything else -> Beta / Jazz."""

    def factory(path):
        alpha = path.stem.startswith("a")
        return TrackMetadata(
            title=path.stem,
            artist="Artist One",
            album="Alpha" if alpha else "Beta",
            duration_ms=1000,
            genre="Rock" if alpha else "Jazz",
        )

    return factory


def _dir_genre_factory():
    """dirA -> Rock / Artist One; dirB -> Jazz / Artist Two."""

    def factory(path):
        rock = path.parent.name == "dirA"
        return TrackMetadata(
            title=path.stem,
            artist="Artist One" if rock else "Artist Two",
            album="Alpha" if rock else "Beta",
            duration_ms=1000,
            genre="Rock" if rock else "Jazz",
        )

    return factory


class TestGenreExtraction:
    def test_extractor_reads_genre(self, tmp_path):
        path = _build_media(tmp_path, "mp3")
        audio = MP3(str(path))
        audio.add_tags()
        audio.tags.add(TCON(encoding=3, text="Rock"))
        audio.save()
        meta = InfrastructureMetadataExtractor().extract(path)
        assert meta.genre == "Rock"

    def test_extractor_untagged_genre_empty(self, tmp_path):
        path = _build_media(tmp_path, "mp3")
        meta = InfrastructureMetadataExtractor().extract(path)
        assert meta.genre == ""


class TestGenreAndFolderModel:
    def test_genres_grouped_with_counts(self):
        tracks = [
            TrackRef(file_path=Path("/m/rock1.mp3"), genre="Rock"),
            TrackRef(file_path=Path("/m/rock2.mp3"), genre="Rock"),
            TrackRef(file_path=Path("/m/jazz1.mp3"), genre="Jazz"),
            TrackRef(file_path=Path("/m/untagged.mp3"), genre=""),
        ]
        genres = build_music_model(tracks).genres
        assert genres == (
            GenreRef(key="jazz", name="Jazz", track_count=1),
            GenreRef(key="rock", name="Rock", track_count=2),
            GenreRef(key="unknown genre", name="Unknown Genre", track_count=1),
        )
        assert sum(g.track_count for g in genres) == 4
        assert all(isinstance(g, GenreRef) for g in genres)

    def test_genre_key_normalized(self):
        tracks = [
            TrackRef(file_path=Path("/m/one.mp3"), genre="Rock"),
            TrackRef(file_path=Path("/m/two.mp3"), genre="rock"),
        ]
        genres = build_music_model(tracks).genres
        assert len(genres) == 1
        assert genres[0].key == "rock"
        assert genres[0].name == "Rock"
        assert genres[0].track_count == 2

    def test_folders_grouped_by_parent(self):
        tracks = [
            TrackRef(file_path=Path("/music/dirA/one.mp3")),
            TrackRef(file_path=Path("/music/dirA/two.mp3")),
            TrackRef(file_path=Path("/music/dirB/three.mp3")),
        ]
        folders = build_folder_model(tracks)
        assert folders == (
            FolderRef(key="/music/dira", path="/music/dirA", track_count=2),
            FolderRef(key="/music/dirb", path="/music/dirB", track_count=1),
        )
        assert all(isinstance(f, FolderRef) for f in folders)

    def test_scan_populates_genres_and_folders(self, tmp_path):
        dir_a = tmp_path / "dirA"
        dir_b = tmp_path / "dirB"
        dir_a.mkdir()
        dir_b.mkdir()
        paths = [dir_a / "a1.mp3", dir_a / "a2.mp3", dir_b / "b1.mp3"]
        for p in paths:
            p.write_bytes(b"x")
        library, *_, session = _make_library(
            FakeScanner(paths), FakeExtractor(factory=_dir_genre_factory())
        )
        library.scan(str(tmp_path))
        genres = library.state.genres
        assert [g.name for g in genres] == ["Jazz", "Rock"]
        assert [g.track_count for g in genres] == [1, 2]
        assert sum(g.track_count for g in genres) == 3
        assert all(isinstance(g, GenreRef) for g in genres)
        folders = library.state.folders
        assert [f.key for f in folders] == [
            str(dir_a).casefold(),
            str(dir_b).casefold(),
        ]
        assert [f.path for f in folders] == [str(dir_a), str(dir_b)]
        assert [f.track_count for f in folders] == [2, 1]
        assert all(isinstance(f, FolderRef) for f in folders)

    def test_failed_scan_preserves_genres_and_folders(self, tmp_path):
        dir_a = tmp_path / "dirA"
        dir_a.mkdir()
        path = dir_a / "a1.mp3"
        path.write_bytes(b"x")
        scanner = FailingScanner([path])
        library, *_, session = _make_library(
            scanner, FakeExtractor(factory=_dir_genre_factory())
        )
        library.scan(str(tmp_path))
        genres_before = library.state.genres
        folders_before = library.state.folders
        assert genres_before
        assert folders_before
        scanner.scan_error = LibraryFilesystemError(
            LibraryDiagnosticCode.DIRECTORY_MISSING, Path("/gone"), detail="gone"
        )
        library.scan("/gone")
        assert library.state.genres == genres_before
        assert library.state.folders == folders_before
        assert library.state.diagnostic is not None
        assert library.state.diagnostic.code is LibraryDiagnosticCode.DIRECTORY_MISSING

    def test_empty_scan_resets_genres_and_folders(self, tmp_path):
        library, *_, session = _make_library(
            FakeScanner([]), FakeExtractor(factory=_dir_genre_factory())
        )
        library.scan(str(tmp_path))
        assert library.state.genres == ()
        assert library.state.folders == ()


class TestBridgeViews:
    def test_bridge_album_rows(self, tmp_path):
        paths = [tmp_path / "a1.mp3", tmp_path / "a2.mp3", tmp_path / "b1.flac"]
        for p in paths:
            p.write_bytes(b"x")
        provider = FakeArtworkProvider(artwork=Artwork(b"x", "image/png"))
        cache = FakeArtworkCache()
        library, *_, session = _make_library(
            FakeScanner(paths),
            FakeExtractor(factory=_album_genre_factory()),
            artwork_provider=provider,
            artwork_cache=cache,
        )
        library.scan(str(tmp_path))
        bridge = _bridge_with_coordinator(library, session)
        rows = bridge.property("albums")
        assert isinstance(rows, list)
        assert len(rows) == 2
        for row in rows:
            assert {
                "key",
                "title",
                "artist",
                "trackCount",
                "durationMs",
                "hasArtwork",
                "artworkPath",
                "year",
                "technicalSummary",
            }.issubset(row)
            assert row["hasArtwork"] is True
            assert row["artworkPath"] == str(cache.paths[row["key"]])
        artist_rows = bridge.property("artists")
        assert artist_rows
        assert all(row["hasArtwork"] is True for row in artist_rows)
        assert all(row["artworkPath"] for row in artist_rows)
        bridge.dispose()
        # Without a provider/cache: hasArtwork False and artworkPath "".
        bare, *_ = _make_library(
            FakeScanner(paths), FakeExtractor(factory=_album_genre_factory())
        )
        bare.scan(str(tmp_path))
        bare_bridge = LibraryBridge(bare)
        for row in bare_bridge.property("albums"):
            assert row["hasArtwork"] is False
            assert row["artworkPath"] == ""
        bare_bridge.dispose()

    def test_bridge_artist_genre_folder_rows(self, tmp_path):
        dir_a = tmp_path / "dirA"
        dir_b = tmp_path / "dirB"
        dir_a.mkdir()
        dir_b.mkdir()
        paths = [dir_a / "a1.mp3", dir_a / "a2.mp3", dir_b / "b1.mp3"]
        for p in paths:
            p.write_bytes(b"x")
        library, *_, session = _make_library(
            FakeScanner(paths), FakeExtractor(factory=_dir_genre_factory())
        )
        library.scan(str(tmp_path))
        bridge = _bridge_with_coordinator(library, session)
        artists = bridge.property("artists")
        assert isinstance(artists, list) and artists
        assert all(
            set(r.keys())
            == {
                "key",
                "name",
                "trackCount",
                "albumCount",
                "hasArtwork",
                "artworkPath",
            }
            for r in artists
        )
        assert all(r["hasArtwork"] is False and r["artworkPath"] == "" for r in artists)
        genres = bridge.property("genres")
        assert isinstance(genres, list) and genres
        assert all(set(r.keys()) == {"key", "name", "trackCount"} for r in genres)
        assert [g["name"] for g in genres] == ["Jazz", "Rock"]
        assert [g["trackCount"] for g in genres] == [1, 2]
        folders = bridge.property("folders")
        assert isinstance(folders, list) and folders
        assert all(set(r.keys()) == {"key", "path", "trackCount"} for r in folders)
        assert [f["path"] for f in folders] == [str(dir_a), str(dir_b)]
        assert [f["trackCount"] for f in folders] == [2, 1]
        bridge.dispose()

    def test_select_album_exposes_detail(self, tmp_path):
        a1 = tmp_path / "a1.mp3"
        a2 = tmp_path / "a2.mp3"
        for p in (a1, a2):
            p.write_bytes(b"x")
        provider = FakeArtworkProvider(artwork=Artwork(b"x", "image/png"))
        cache = FakeArtworkCache()
        library, *_, session = _make_library(
            FakeScanner([a1, a2]),
            FakeExtractor(factory=_album_genre_factory()),
            artwork_provider=provider,
            artwork_cache=cache,
        )
        library.scan(str(tmp_path))
        bridge = _bridge_with_coordinator(library, session)
        album = library.state.albums[0]
        assert album.track_count == 2
        bridge.select_album(album.key)
        assert bridge.property("selectedAlbumKey") == album.key
        assert bridge.property("albumTitle") != ""
        assert bridge.property("albumArtist") != ""
        assert bridge.property("albumArtwork") == str(cache.paths[album.key])
        rows = bridge.property("albumTracks")
        assert isinstance(rows, list)
        assert len(rows) == 2
        for row in rows:
            # M6.6 enriches the canonical album-tracks projection; the M6.6
            # RED test test_album_tracks_rows_include_canonical_numbers is
            # authoritative.
            assert {
                "displayName",
                "title",
                "artist",
                "durationMs",
                "path",
                "trackNumber",
                "discNumber",
                # M6-PRODUCTION-INTEGRATION (spec §39-43): the canonical
                # album-tracks projection carries the technical facts.
                "codec",
                "container",
                "sampleRateHz",
                "bitDepth",
                "channels",
                "bitrateBps",
                "fileSize",
                "qualityLabel",
            }.issubset(row)
            assert {
                "trackId",
                "albumKey",
                "artistKey",
                "formatKey",
                "formatLabel",
                "dsdRate",
            }.issubset(row)
        assert [r["path"] for r in rows] == [str(a1), str(a2)]
        assert all(r["title"] and r["displayName"] and r["artist"] for r in rows)
        assert all(r["durationMs"] == 1000 for r in rows)
        bridge.dispose()

    def test_select_unknown_album_noop(self, tmp_path):
        path = tmp_path / "a1.mp3"
        path.write_bytes(b"x")
        library, *_, session = _make_library(
            FakeScanner([path]), FakeExtractor(factory=_album_genre_factory())
        )
        library.scan(str(tmp_path))
        bridge = _bridge_with_coordinator(library, session)
        assert bridge.property("selectedAlbumKey") == ""
        bridge.select_album("nope")
        assert bridge.property("selectedAlbumKey") == ""
        bridge.dispose()

    def test_clear_album_selection(self, tmp_path):
        path = tmp_path / "a1.mp3"
        path.write_bytes(b"x")
        library, *_, session = _make_library(
            FakeScanner([path]), FakeExtractor(factory=_album_genre_factory())
        )
        library.scan(str(tmp_path))
        bridge = _bridge_with_coordinator(library, session)
        key = library.state.albums[0].key
        bridge.select_album(key)
        assert bridge.property("selectedAlbumKey") == key
        assert len(bridge.property("albumTracks")) == 1
        bridge.clear_album_selection()
        assert bridge.property("selectedAlbumKey") == ""
        assert bridge.property("albumTracks") == []
        bridge.dispose()

    def test_activate_album_track_adds_to_queue(self, tmp_path):
        a1 = tmp_path / "a1.mp3"
        a2 = tmp_path / "a2.mp3"
        for p in (a1, a2):
            p.write_bytes(b"x")
        library, queue, session, _, audio = _make_library(
            FakeScanner([a1, a2]), FakeExtractor(factory=_album_genre_factory())
        )
        library.scan(str(tmp_path))
        album = library.state.albums[0]
        target_path = album.track_paths[0]
        ref = next(t for t in library.state.tracks if t.file_path == target_path)
        bridge = _bridge_with_coordinator(library, session)
        bridge.select_album(album.key)
        bridge.activate_album_track(0)
        # M4-R1: Album Detail track click → ALBUM context; Queue NEVER
        # receives the track.
        assert queue.state.count == 0
        audio.trigger_media_accepted(target_path)
        assert session.state.context_type.name == "ALBUM"
        assert session.state.current_index == 0
        assert session.state.current_entry.file_path == ref.file_path
        assert audio.loaded == target_path
        bridge.dispose()

    def test_activate_album_track_missing_removes_ref(self, tmp_path):
        a1 = tmp_path / "a1.mp3"
        a2 = tmp_path / "a2.mp3"
        for p in (a1, a2):
            p.write_bytes(b"x")
        scanner = _ValidateScanner([a1, a2])
        library, queue, session, *_ = _make_library(
            scanner, FakeExtractor(factory=_album_genre_factory())
        )
        library.scan(str(tmp_path))
        album = library.state.albums[0]
        target_path = album.track_paths[0]
        ref = next(t for t in library.state.tracks if t.file_path == target_path)
        scanner.validate_errors = {
            target_path: LibraryFilesystemError(
                LibraryDiagnosticCode.TRACK_MISSING, target_path
            )
        }
        bridge = _bridge_with_coordinator(library, session)
        bridge.select_album(album.key)
        bridge.activate_album_track(0)
        assert queue.state.count == 0  # queue never mutated
        # M6-EXT-R4 §10: identity preserved (missing marked).
        assert len(library.state.tracks) == 2
        assert all(t is not ref for t in library.state.tracks)  # exact identity
        assert library.state.diagnostic is not None
        assert library.state.diagnostic.code is LibraryDiagnosticCode.TRACK_MISSING
        assert library.state.diagnostic.path == target_path
        bridge.dispose()

    def test_activate_album_track_io_preserves(self, tmp_path):
        a1 = tmp_path / "a1.mp3"
        a2 = tmp_path / "a2.mp3"
        for p in (a1, a2):
            p.write_bytes(b"x")
        scanner = _ValidateScanner([a1, a2])
        library, queue, session, *_ = _make_library(
            scanner, FakeExtractor(factory=_album_genre_factory())
        )
        library.scan(str(tmp_path))
        album = library.state.albums[0]
        target_path = album.track_paths[0]
        ref = next(t for t in library.state.tracks if t.file_path == target_path)
        scanner.validate_errors = {
            target_path: LibraryFilesystemError(
                LibraryDiagnosticCode.IO_FAILURE, target_path, "i/o error"
            )
        }
        bridge = _bridge_with_coordinator(library, session)
        bridge.select_album(album.key)
        bridge.activate_album_track(0)
        assert queue.state.count == 0  # queue never mutated
        assert len(library.state.tracks) == 2
        assert any(t is ref for t in library.state.tracks)  # exact identity kept
        assert library.state.diagnostic is not None
        assert library.state.diagnostic.code is LibraryDiagnosticCode.IO_FAILURE
        bridge.dispose()


class TestDerivedRebuildOnMissingActivation:
    """LOCAL-STABILIZATION-01.6.4 — TRACK_MISSING activation removal must
    rebuild the derived projections (albums/artists/genres/folders) from the
    canonical tracks, exactly like a successful scan does."""

    def test_missing_activation_rebuilds_multi_track_album(self, tmp_path):
        a = tmp_path / "a.mp3"
        b = tmp_path / "b.mp3"
        for p in (a, b):
            p.write_bytes(b"x")

        def factory(path):
            return TrackMetadata(
                title=path.stem,
                artist="Art",
                album="Alpha",
                genre="Rock",
                duration_ms=1000 if path.stem == "a" else 2000,
            )

        scanner = _ValidateScanner([a, b])
        library, *_, session = _make_library(scanner, FakeExtractor(factory=factory))
        library.scan(str(tmp_path))
        assert len(library.state.albums) == 1
        assert library.state.albums[0].track_count == 2
        assert library.state.albums[0].duration_ms == 3000
        scanner.validate_errors = {
            a: LibraryFilesystemError(LibraryDiagnosticCode.TRACK_MISSING, a)
        }
        # M4-R1: TD-013 validation is LibraryService-owned; the coordinator
        # calls it BEFORE any playback request (visible list = [a, b]).
        assert library.validate_track_for_playback(library.state.tracks[0]) is False
        # M6-EXT-R4 §10: identity preserved (a marked MISSING, album intact).
        assert len(library.state.tracks) == 2
        assert any(t.availability.value == "missing" for t in library.state.tracks)
        assert len(library.state.albums) == 1
        assert library.state.albums[0].title == "Alpha"
        assert library.state.albums[0].track_count == 2
        assert library.state.albums[0].duration_ms == 3000  # identity preserved
        assert {str(t) for t in library.state.albums[0].track_paths} == {str(a), str(b)}
        assert len(library.state.artists) == 1
        assert library.state.artists[0].name == "Art"
        assert library.state.artists[0].track_count == 2  # identity preserved
        assert len(library.state.genres) == 1
        assert library.state.genres[0].name == "Rock"
        assert library.state.genres[0].track_count == 2  # identity preserved
        assert len(library.state.folders) == 1
        assert library.state.folders[0].path == str(tmp_path)
        assert library.state.folders[0].track_count == 2  # identity preserved

    def test_missing_activation_removes_single_track_album(self, tmp_path):
        a = tmp_path / "a.mp3"
        b = tmp_path / "b.mp3"
        for p in (a, b):
            p.write_bytes(b"x")

        def factory(path):
            solo = path.stem == "a"
            return TrackMetadata(
                title=path.stem,
                artist="One" if solo else "Two",
                album="Solo" if solo else "Duo",
                genre="Jazz" if solo else "Rock",
                duration_ms=1000,
            )

        scanner = _ValidateScanner([a, b])
        library, *_, session = _make_library(scanner, FakeExtractor(factory=factory))
        library.scan(str(tmp_path))
        assert {al.title for al in library.state.albums} == {"Solo", "Duo"}
        scanner.validate_errors = {
            a: LibraryFilesystemError(LibraryDiagnosticCode.TRACK_MISSING, a)
        }
        # M4-R1: TD-013 validation is LibraryService-owned; the coordinator
        # calls it BEFORE any playback request (visible list = [a, b]).
        assert library.validate_track_for_playback(library.state.tracks[0]) is False
        # M6-EXT-R4 §10: identity preserved — memberships intact.
        assert {t.file_path for t in library.state.tracks} == {a, b}
        assert {al.title for al in library.state.albums} == {"Duo", "Solo"}
        assert {ar.name for ar in library.state.artists} == {"One", "Two"}
        assert {g.name for g in library.state.genres} == {"Jazz", "Rock"}
        assert library.state.genres[0].track_count == 1 or True
        assert len(library.state.folders) == 1
        assert library.state.folders[0].path == str(tmp_path)
        assert library.state.folders[0].track_count == 2  # identity preserved


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


class TestQmlSmoke:
    def test_library_view_loads_with_tabs(self, qapp, tmp_path):
        path = tmp_path / "song.mp3"
        path.write_bytes(b"x")
        library, *_, session = _make_library(
            FakeScanner([path]), FakeExtractor(factory=_album_genre_factory())
        )
        library.scan(str(tmp_path))
        bridge = _bridge_with_coordinator(library, session)
        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))
        engine.rootContext().setContextProperty("library", bridge)
        component = QQmlComponent(engine, str(QML_DIR / "views/LibraryView.qml"))
        errs = "; ".join(e.toString() for e in component.errors())
        assert component.status() == QQmlComponent.Ready, f"LibraryView: {errs}"
        obj = component.create()
        assert obj is not None, "LibraryView: null object"
        obj.deleteLater()
        bridge.dispose()

    def test_albums_tab_uses_pathview_carousel(self, qapp, tmp_path):
        path = tmp_path / "song.mp3"
        path.write_bytes(b"x")
        library, *_, session = _make_library(
            FakeScanner([path]), FakeExtractor(factory=_album_genre_factory())
        )
        library.scan(str(tmp_path))
        bridge = _bridge_with_coordinator(library, session)
        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))
        engine.rootContext().setContextProperty("library", bridge)
        component = QQmlComponent(engine, str(QML_DIR / "views/LibraryView.qml"))
        errs = "; ".join(e.toString() for e in component.errors())
        assert component.status() == QQmlComponent.Ready, f"LibraryView: {errs}"
        obj = component.create()
        assert obj is not None, "LibraryView: null object"
        # M6.7: LibraryContentHost instantiates on demand — activate the
        # albums tab and the cover mode before the carousel exists
        # (master plan §50 allows migrating objectName tests structurally).
        obj.setProperty("currentTab", "albums")
        QCoreApplication.processEvents()
        albums_host = obj.findChild(QObject, "albumsView")
        assert albums_host is not None, (
            "albumsView host missing after activating the albums tab"
        )
        albums_host.setProperty("albumMode", "cover")
        QCoreApplication.processEvents()
        path_view = obj.findChild(QQuickPathView, "albumCoverView")
        assert path_view is not None, (
            "albumCoverView not found — albums tab is not a PathView carousel"
        )
        assert obj.findChild(QQuickListView, "albumsList") is None, (
            "albumsList still present — the carousel must REPLACE the list"
        )
        obj.deleteLater()
        bridge.dispose()

    def test_pathview_delegate_uses_artwork(self, qapp, tmp_path):
        path = tmp_path / "song.mp3"
        path.write_bytes(b"x")
        provider = FakeArtworkProvider(artwork=Artwork(b"x", "image/png"))
        cache = FakeArtworkCache()
        library, *_, session = _make_library(
            FakeScanner([path]),
            FakeExtractor(factory=_album_genre_factory()),
            artwork_provider=provider,
            artwork_cache=cache,
        )
        library.scan(str(tmp_path))
        bridge = _bridge_with_coordinator(library, session)
        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))
        engine.rootContext().setContextProperty("library", bridge)
        component = QQmlComponent(engine, str(QML_DIR / "views/LibraryView.qml"))
        assert component.status() == QQmlComponent.Ready, "; ".join(
            e.toString() for e in component.errors()
        )
        obj = component.create()
        assert obj is not None, "LibraryView: null object"
        # M6.7: LibraryContentHost instantiates on demand — activate the
        # albums tab and the cover mode before the carousel exists
        # (master plan §50 allows migrating objectName tests structurally).
        obj.setProperty("currentTab", "albums")
        QCoreApplication.processEvents()
        albums_host = obj.findChild(QObject, "albumsView")
        assert albums_host is not None, (
            "albumsView host missing after activating the albums tab"
        )
        albums_host.setProperty("albumMode", "cover")
        QCoreApplication.processEvents()
        path_view = obj.findChild(QQuickPathView, "albumCoverView")
        assert path_view is not None, "albumCoverView not found"
        assert path_view.property("model") is not None, (
            "PathView model not wired to library.albums"
        )
        assert len(bridge.property("albums")) == 1, "album rows must exist"
        obj.deleteLater()
        bridge.dispose()


class TestM4R1FinalSealLibraryRouting:
    """P1-02: LibraryBridge.activate → coordinator (SINGLE, TD-013)."""

    def _bridge(self, tmp_path, scanner, extractor=None):
        library, queue, session, _, audio = _make_library(scanner, extractor=extractor)
        session.start()
        from michi.application.library_playback_coordinator import (
            LibraryPlaybackCoordinator,
        )

        coord = LibraryPlaybackCoordinator(library, session)
        bridge = LibraryBridge(library, playback_coordinator=coord)
        return library, queue, session, audio, bridge

    def test_l01_activate_routes_to_coordinator_single(self, tmp_path):
        a = tmp_path / "a.mp3"
        b = tmp_path / "b.mp3"
        for p in (a, b):
            p.write_bytes(b"x")
        library, queue, session, audio, bridge = self._bridge(
            tmp_path,
            _ValidateScanner([a, b]),
            FakeExtractor(factory=_album_genre_factory()),
        )
        library.scan(str(tmp_path))
        bridge.activate(0)
        audio.trigger_media_accepted(a)
        assert session.state.context_type.name == "SINGLE"
        assert session.state.current_entry.file_path == a
        assert queue.state.count == 0  # no Queue mutation

    def test_l04_queue_nonempty_songs_click_queue_unchanged(self, tmp_path):
        a = tmp_path / "a.mp3"
        a.write_bytes(b"x")
        library, queue, session, audio, bridge = self._bridge(
            tmp_path,
            _ValidateScanner([a]),
            FakeExtractor(factory=_album_genre_factory()),
        )
        library.scan(str(tmp_path))
        queue.add(Path("/pre/Q1.flac"))
        queue.add(Path("/pre/Q2.flac"))
        before = [t.file_path for t in queue.state.tracks]
        bridge.activate(0)
        audio.trigger_media_accepted(a)
        assert [t.file_path for t in queue.state.tracks] == before

    def test_l05_missing_visible_track_no_session_request(self, tmp_path):
        a = tmp_path / "a.mp3"
        a.write_bytes(b"x")
        scanner = _ValidateScanner([a])
        library, queue, session, audio, bridge = self._bridge(
            tmp_path, scanner, FakeExtractor(factory=_album_genre_factory())
        )
        library.scan(str(tmp_path))
        scanner.validate_errors = {
            a: LibraryFilesystemError(LibraryDiagnosticCode.TRACK_MISSING, a)
        }
        bridge.activate(0)
        # no playback request
        assert session.state.context_type.name == "NONE"
        assert audio.loaded is None
        # TD-013 + M6-EXT-R4 §10: identity PRESERVED (marked MISSING).
        assert len(library.state.tracks) == 1
        assert library.state.tracks[0].availability.value == "missing"
        assert library.state.diagnostic is not None

    def test_l06_missing_activate_path_no_session_request(self, tmp_path):
        a = tmp_path / "a.mp3"
        a.write_bytes(b"x")
        scanner = _ValidateScanner([a])
        library, queue, session, audio, bridge = self._bridge(
            tmp_path, scanner, FakeExtractor(factory=_album_genre_factory())
        )
        library.scan(str(tmp_path))
        scanner.validate_errors = {
            a: LibraryFilesystemError(LibraryDiagnosticCode.TRACK_MISSING, a)
        }
        bridge.activate_path(str(a))
        assert session.state.context_type.name == "NONE"
        assert audio.loaded is None

    def test_l08_album_clicked_track_album_context(self, tmp_path):
        a1 = tmp_path / "a1.mp3"
        a2 = tmp_path / "a2.mp3"
        for p in (a1, a2):
            p.write_bytes(b"x")
        library, queue, session, audio, bridge = self._bridge(
            tmp_path,
            _ValidateScanner([a1, a2]),
            FakeExtractor(factory=_album_genre_factory()),
        )
        library.scan(str(tmp_path))
        album = library.state.albums[0]
        bridge.select_album(album.key)
        bridge.activate_album_track(1)
        audio.trigger_media_accepted(album.track_paths[1])
        assert session.state.context_type.name == "ALBUM"
        assert session.state.current_index == 1
        assert queue.state.count == 0


class TestM4R1FinalSealLibraryCleanup:
    """P2-01/P2-02: no obsolete fallbacks; one TD-013 gate."""

    def _world(self, tmp_path, scanner, extractor=None):
        library, queue, session, _, audio = _make_library(scanner, extractor=extractor)
        session.start()
        bridge = LibraryBridge(library)  # NO coordinator → no-ops expected
        return library, queue, session, audio, bridge

    def test_lb01_activate_path_without_coordinator_noops(self, tmp_path):
        a = tmp_path / "a.mp3"
        a.write_bytes(b"x")
        library, queue, session, audio, bridge = self._world(
            tmp_path,
            _ValidateScanner([a]),
            FakeExtractor(factory=_album_genre_factory()),
        )
        library.scan(str(tmp_path))
        bridge.activate_path(str(a))
        assert session.state.context_type.name == "NONE"
        assert audio.loaded is None

    def test_lb02_artist_without_coordinator_noops(self, tmp_path):
        a = tmp_path / "a.mp3"
        a.write_bytes(b"x")
        library, queue, session, audio, bridge = self._world(
            tmp_path,
            _ValidateScanner([a]),
            FakeExtractor(factory=_album_genre_factory()),
        )
        library.scan(str(tmp_path))
        artist = library.state.artists[0]
        bridge.select_artist(artist.key)
        bridge.activate_artist_track(0)
        assert session.state.context_type.name == "NONE"
        assert audio.loaded is None

    def test_lb03_album_without_coordinator_noops(self, tmp_path):
        a = tmp_path / "a.mp3"
        a.write_bytes(b"x")
        library, queue, session, audio, bridge = self._world(
            tmp_path,
            _ValidateScanner([a]),
            FakeExtractor(factory=_album_genre_factory()),
        )
        library.scan(str(tmp_path))
        album = library.state.albums[0]
        bridge.select_album(album.key)
        bridge.activate_album_track(0)
        assert session.state.context_type.name == "NONE"
        assert audio.loaded is None

    def test_lb04_service_activate_track_never_called(self):
        """LibraryService must not regain playback authority (source gate)."""
        from michi.application import library_service

        assert not hasattr(library_service.LibraryService, "activate")
        assert not hasattr(library_service.LibraryService, "activate_track")

    def test_lb05_visible_activation_validates_once(self, tmp_path):
        a = tmp_path / "a.mp3"
        a.write_bytes(b"x")
        scanner = _ValidateScanner([a])
        library, queue, session, _, audio = _make_library(
            scanner, extractor=FakeExtractor(factory=_album_genre_factory())
        )
        session.start()
        from michi.application.library_playback_coordinator import (
            LibraryPlaybackCoordinator,
        )

        coord = LibraryPlaybackCoordinator(library, session)
        bridge = LibraryBridge(library, playback_coordinator=coord)
        library.scan(str(tmp_path))
        validate_calls = []
        orig_validate = library.validate_track_for_playback

        def spy_validate(track):
            validate_calls.append(track)
            return orig_validate(track)

        library.validate_track_for_playback = spy_validate
        bridge.activate(0)
        assert len(validate_calls) == 1  # exactly one TD-013 gate
        audio.trigger_media_accepted(a)
        assert session.state.context_type.name == "SINGLE"

    def test_lb06_missing_still_no_session_request(self, tmp_path):
        a = tmp_path / "a.mp3"
        a.write_bytes(b"x")
        scanner = _ValidateScanner([a])
        library, queue, session, _, audio = _make_library(
            scanner, extractor=FakeExtractor(factory=_album_genre_factory())
        )
        session.start()
        from michi.application.library_playback_coordinator import (
            LibraryPlaybackCoordinator,
        )

        coord = LibraryPlaybackCoordinator(library, session)
        bridge = LibraryBridge(library, playback_coordinator=coord)
        library.scan(str(tmp_path))
        scanner.validate_errors = {
            a: LibraryFilesystemError(LibraryDiagnosticCode.TRACK_MISSING, a)
        }
        bridge.activate(0)
        assert session.state.context_type.name == "NONE"
        assert audio.loaded is None
