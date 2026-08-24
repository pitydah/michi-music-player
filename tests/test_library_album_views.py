"""Album views work package (Grid/Cover/Vinyl/Timeline/Magazine/List) —
Phase-1 RED tests.

The module imports only symbols that already exist on the baseline, so
collection SUCCEEDS; every test fails at runtime because the target contract
is not implemented yet:

- ``TrackMetadata``/``TrackRef``/``AlbumRef`` have no ``year`` field yet
  (accessing ``.year`` raises AttributeError; passing ``year=...`` raises
  TypeError), and the extractor does not read the easy-mode ``date`` key.
- The bridge ``albums`` rows have no ``"year"`` key and the
  ``timelineAlbums`` property does not exist yet.
- ``LibraryView.qml`` has no mode switcher and none of the six mode
  objectNames (``albumGridView`` ... ``albumListView``).

Coverage:
- Year extraction from the easy-mode "date" key (ID3 TDRC via EasyMP3,
  Vorbis date via FLAC; untagged -> 0; invalid/empty -> 0)
- Album year = first member track's year (build_music_model), zero default
- Bridge: albums rows gain "year"; NEW timelineAlbums property sorted by
  year DESC (then key) with decade buckets and the 7-key row shape;
  reactivity after a rescan
- QML smoke: the six album-mode views exist by objectName
"""

import os
import sys
from pathlib import Path

import pytest
from mutagen.flac import FLAC
from mutagen.mp3 import EasyMP3
from PySide6.QtCore import QCoreApplication, QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.playback_session_service import PlaybackSessionService
from michi.application.queue_service import QueueService
from michi.domain.library import (
    AlbumRef,
    TrackMetadata,
    TrackRef,
    build_music_model,
)
from michi.infrastructure.metadata_extractor import InfrastructureMetadataExtractor
from michi.presentation.library_bridge import LibraryBridge
from tests.conftest import FakeAudioPort
from tests.test_library_metadata import FakeExtractor, FakeScanner
from tests.test_metadata_extractor import _build_media

QML_DIR = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


def _make_library(scanner, extractor=None, artwork_provider=None, artwork_cache=None):
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService()
    _session = PlaybackSessionService(playback, queue)
    return (
        LibraryService(
            scanner,
            metadata_extractor=extractor,
            artwork_provider=artwork_provider,
            artwork_cache=artwork_cache,
        ),
        queue,
        playback,
        audio,
    )


def _year_factory(years):
    """One album per file; year comes from the per-file-name mapping."""

    def factory(path):
        return TrackMetadata(
            title=path.stem,
            artist="Artist One",
            album=path.stem,
            duration_ms=1000,
            year=years.get(path.name, 0),
        )

    return factory


class TestYearExtraction:
    def test_extractor_year_from_mp3_date(self, tmp_path):
        path = _build_media(tmp_path, "mp3")
        audio = EasyMP3(str(path))
        audio["date"] = "1999-11-23"
        audio.save()
        meta = InfrastructureMetadataExtractor().extract(path)
        assert meta.year == 1999

    def test_extractor_year_from_flac_date(self, tmp_path):
        path = _build_media(tmp_path, "flac")
        audio = FLAC(str(path))
        audio["date"] = "1984"
        audio.save()
        meta = InfrastructureMetadataExtractor().extract(path)
        assert meta.year == 1984

    def test_extractor_untagged_year_zero(self, tmp_path):
        path = _build_media(tmp_path, "mp3")
        meta = InfrastructureMetadataExtractor().extract(path)
        assert meta.year == 0

    def test_extractor_invalid_date_falls_back_zero(self, tmp_path):
        for raw in ("not-a-date", ""):
            path = _build_media(tmp_path, "mp3")
            audio = EasyMP3(str(path))
            audio["date"] = raw
            audio.save()
            meta = InfrastructureMetadataExtractor().extract(path)
            assert meta.year == 0, f"year must be 0 for date {raw!r}"


class TestAlbumModelYear:
    def test_album_year_from_first_member(self):
        tracks = [
            TrackRef(
                file_path=Path("/m/one.mp3"),
                album="Alpha",
                artist="Artist One",
                year=2001,
            ),
            TrackRef(
                file_path=Path("/m/two.mp3"),
                album="Alpha",
                artist="Artist One",
                year=2005,
            ),
        ]
        albums = build_music_model(tracks).albums
        assert len(albums) == 1
        assert isinstance(albums[0], AlbumRef)
        assert albums[0].year == 2001

    def test_album_year_zero_without_tags(self):
        tracks = [
            TrackRef(file_path=Path("/m/one.mp3"), album="Alpha", artist="A"),
            TrackRef(file_path=Path("/m/two.mp3"), album="Alpha", artist="A"),
        ]
        albums = build_music_model(tracks).albums
        assert len(albums) == 1
        assert isinstance(albums[0], AlbumRef)
        assert albums[0].year == 0


class TestBridgeTimeline:
    def test_album_rows_include_year(self, tmp_path):
        paths = [tmp_path / "a1.mp3", tmp_path / "a2.mp3", tmp_path / "b1.flac"]
        for p in paths:
            p.write_bytes(b"x")
        library, *_ = _make_library(
            FakeScanner(paths),
            FakeExtractor(
                factory=_year_factory({"a1.mp3": 2001, "a2.mp3": 2001, "b1.flac": 1984})
            ),
        )
        library.scan(str(tmp_path))
        bridge = LibraryBridge(library)
        rows = bridge.property("albums")
        assert isinstance(rows, list)
        assert len(rows) == 3
        by_title = {row["title"]: row["year"] for row in rows}
        assert by_title == {"a1": 2001, "a2": 2001, "b1": 1984}
        bridge.dispose()

    def test_timeline_albums_sorted_desc_with_decades(self, tmp_path):
        paths = [
            tmp_path / "a1.mp3",
            tmp_path / "b1.mp3",
            tmp_path / "c1.mp3",
            tmp_path / "d1.mp3",
        ]
        for p in paths:
            p.write_bytes(b"x")
        library, *_ = _make_library(
            FakeScanner(paths),
            FakeExtractor(
                factory=_year_factory(
                    {"a1.mp3": 2005, "b1.mp3": 1999, "c1.mp3": 0, "d1.mp3": 2021}
                )
            ),
        )
        library.scan(str(tmp_path))
        bridge = LibraryBridge(library)
        rows = bridge.property("timelineAlbums")
        assert isinstance(rows, list)
        assert [row["year"] for row in rows] == [2021, 2005, 1999, 0]
        assert [row["decade"] for row in rows] == [
            "2020s",
            "2000s",
            "1990s",
            "Unknown era",
        ]
        for row in rows:
            assert set(row.keys()) == {
                "key",
                "title",
                "artist",
                "year",
                "decade",
                "hasArtwork",
                "artworkPath",
            }
        bridge.dispose()

    def test_timeline_albums_reactive(self, tmp_path):
        p1 = tmp_path / "a1.mp3"
        p2 = tmp_path / "b1.mp3"
        for p in (p1, p2):
            p.write_bytes(b"x")
        scanner = FakeScanner([p1])
        library, *_ = _make_library(
            scanner,
            FakeExtractor(factory=_year_factory({"a1.mp3": 2005, "b1.mp3": 1999})),
        )
        library.scan(str(tmp_path))
        bridge = LibraryBridge(library)
        assert [row["year"] for row in bridge.property("timelineAlbums")] == [2005]
        scanner.paths = [p1, p2]
        library.scan(str(tmp_path))
        assert [row["year"] for row in bridge.property("timelineAlbums")] == [
            2005,
            1999,
        ]
        bridge.dispose()


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


class TestQmlSmoke:
    def test_library_view_has_all_album_modes(self, qapp, tmp_path):
        paths = [tmp_path / "a1.mp3", tmp_path / "b1.mp3", tmp_path / "c1.mp3"]
        for p in paths:
            p.write_bytes(b"x")
        library, *_ = _make_library(
            FakeScanner(paths),
            FakeExtractor(
                factory=_year_factory({"a1.mp3": 2001, "b1.mp3": 1985, "c1.mp3": 2021})
            ),
        )
        library.scan(str(tmp_path))
        bridge = LibraryBridge(library)
        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))
        engine.rootContext().setContextProperty("library", bridge)
        component = QQmlComponent(engine, str(QML_DIR / "views/LibraryView.qml"))
        errs = "; ".join(e.toString() for e in component.errors())
        assert component.status() == QQmlComponent.Ready, f"LibraryView: {errs}"
        obj = component.create()
        assert obj is not None, "LibraryView: null object"
        # M6.7: the six projections live behind LibraryContentHost's Loader —
        # only the ACTIVE album mode is instantiated (master plan §50 allows
        # migrating objectName tests structurally). Activate the albums tab,
        # then drive the host's albumMode through all six modes.
        obj.setProperty("currentTab", "albums")
        QCoreApplication.processEvents()
        albums_host = obj.findChild(QObject, "albumsView")
        assert albums_host is not None, (
            "albumsView host missing after activating the albums tab"
        )
        for mode, name in (
            ("grid", "albumGridView"),
            ("cover", "albumCoverView"),
            ("vinyl", "albumVinylView"),
            ("timeline", "albumTimelineView"),
            ("magazine", "albumMagazineView"),
            ("list", "albumListView"),
        ):
            albums_host.setProperty("albumMode", mode)
            QCoreApplication.processEvents()
            assert obj.findChild(QObject, name) is not None, (
                f"{name} not found — album mode view missing in mode {mode!r}"
            )
        obj.deleteLater()
        bridge.dispose()
