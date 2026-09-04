"""Bridge-level gates for the M9 premium presentation projections."""

import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import FakeAudioPort
from PySide6.QtCore import Property, QCoreApplication, QMetaObject, QObject, Qt, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QSignalSpy, QTest

from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.playlist_service import PlaylistService
from michi.application.queue_service import QueueService
from michi.domain.library import TrackMetadata, TrackRef, build_music_model
from michi.presentation.library_bridge import LibraryBridge
from michi.presentation.playback_bridge import PlaybackBridge
from michi.presentation.queue_bridge import QueueBridge


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


class _Scanner:
    def __init__(self, paths) -> None:
        self.paths = list(paths)

    def scan(self, _root):
        return list(self.paths)

    def validate_file(self, _path):
        return None


class _Extractor:
    def __init__(self, factory) -> None:
        self.factory = factory

    def extract(self, path):
        return self.factory(path)


class _PaletteExtractor:
    def __init__(self) -> None:
        self.callback = None
        self.callbacks = []
        self.sources = ()
        self.requests = []
        self.closed = False

    def request_palette(self, source_paths, callback) -> None:
        self.sources = source_paths
        self.callback = callback
        self.callbacks.append(callback)
        self.requests.append(source_paths)

    def close(self) -> None:
        self.closed = True


class _ProjectionLibrary:
    def __init__(self, tracks, *, artwork=False) -> None:
        model = build_music_model(tracks)
        self._artwork = artwork
        self.state = SimpleNamespace(
            albums=model.albums,
            artists=model.artists,
            tracks=tuple(tracks),
            favorite_paths=(),
            recently_added_paths=(),
            search_active=False,
            search_projection=None,
        )

    def subscribe_changed(self, _callback) -> None:
        return None

    def unsubscribe_changed(self, _callback) -> None:
        return None

    def artwork_path_for(self, album_key) -> str:
        return f"/virtual/artwork/{album_key}.jpg" if self._artwork else ""


class _LibraryEnrichment(QObject):
    revision = Property(int, lambda self: 0)

    @Slot(str, int, result="QVariantMap")
    def album(self, key, _revision):
        return {
            "albumKey": key,
            "hasCachedKnowledge": False,
            "knowledge": {},
        }


def test_canonical_album_projection_handles_10k_albums(qapp) -> None:
    tracks = [
        TrackRef(
            Path(f"/virtual/{index:05d}.flac"),
            title=f"Track {index:05d}",
            artist=f"Artist {index:05d}",
            album=f"Album {index:05d}",
            year=1950 + index % 76,
            duration_ms=180_000,
            codec="FLAC",
            sample_rate_hz=96_000 if index % 7 == 0 else 44_100,
            bit_depth=24 if index % 7 == 0 else 16,
        )
        for index in range(10_000)
    ]
    bridge = LibraryBridge(_ProjectionLibrary(tracks))

    started = time.perf_counter()
    rows = bridge.property("albums")
    elapsed = time.perf_counter() - started

    assert len(rows) == 10_000
    assert len({row["key"] for row in rows}) == 10_000
    assert rows[0]["artworkPalette"]["accentSafe"].startswith("#")
    assert elapsed < 8.0

    qml_dir = Path(__file__).parents[1] / "src/michi/presentation/qml"
    engine = QQmlEngine()
    engine.addImportPath(str(qml_dir))
    engine.rootContext().setContextProperty("library", bridge)
    component = QQmlComponent(engine, str(qml_dir / "views/AlbumGridView.qml"))
    errors = "; ".join(error.toString() for error in component.errors())
    assert component.status() == QQmlComponent.Ready, errors
    view = component.create()
    window = QQuickWindow()
    try:
        assert view is not None
        view.setParentItem(window.contentItem())
        window.setGeometry(0, 0, 1440, 900)
        view.setProperty("width", 1440)
        view.setProperty("height", 900)
        window.show()
        QCoreApplication.processEvents()
        assert view.property("count") == 10_000

        max_y = max(0.0, float(view.property("contentHeight")) - 900)
        slowest_scroll_step = 0.0
        for step in range(120):
            step_started = time.perf_counter()
            view.setProperty("contentY", max_y * ((step % 30) / 29))
            QCoreApplication.processEvents()
            slowest_scroll_step = max(
                slowest_scroll_step, time.perf_counter() - step_started
            )
        assert len(view.findChildren(QObject)) < 600
        # El presupuesto del paso de scroll (0.5s) se calibró en main SIN
        # el delegate contextual premium (AlbumCard + AlbumContextArea +
        # menú). Bajo la suite completa el runner de CI queda al límite
        # (0.5-0.7s observados, ~0.001s aislado). 1.0s sigue detectando un
        # scroll patológico (con 10k álbumes y processEvents por paso)
        # sin falsear por la carga del runner.
        assert slowest_scroll_step < 1.0
    finally:
        window.close()
        window.deleteLater()
        if view is not None:
            view.deleteLater()

    enrichment_projection = _LibraryEnrichment()
    enrichment = {
        "onlineEnabled": False,
        "activeKind": "",
        "state": "idle",
        "stateMessage": "",
        "busy": False,
        "albumArtworkPath": "",
        "albumKnowledge": {},
        "albumHasKnowledge": False,
        "albumAttributions": [],
        "reviewOpen": False,
        "reviewKind": "",
        "reviewLoading": False,
        "reviewError": "",
        "albumCandidates": [],
    }
    engine = QQmlEngine()
    engine.addImportPath(str(qml_dir))
    engine.rootContext().setContextProperty("library", bridge)
    engine.rootContext().setContextProperty("libraryEnrichment", enrichment_projection)
    engine.rootContext().setContextProperty("enrichment", enrichment)
    component = QQmlComponent(engine, str(qml_dir / "views/AlbumsView.qml"))
    errors = "; ".join(error.toString() for error in component.errors())
    assert component.status() == QQmlComponent.Ready, errors
    albums_view = component.create()
    window = QQuickWindow()
    started = time.perf_counter()
    try:
        assert albums_view is not None
        albums_view.setParentItem(window.contentItem())
        window.setGeometry(0, 0, 1440, 900)
        albums_view.setProperty("width", 1440)
        albums_view.setProperty("height", 900)
        window.show()
        QTest.qWait(100)

        albums_view.setProperty("albumFilterMode", "hires")
        QCoreApplication.processEvents()
        filtered = albums_view.property("presentationAlbums")
        if hasattr(filtered, "toVariant"):
            filtered = filtered.toVariant()
        assert len(filtered) == 1429

        albums_view.setProperty("albumSortMode", "year")
        albums_view.setProperty("albumSortDescending", True)
        albums_view.setProperty("albumFilterMode", "all")
        QCoreApplication.processEvents()
        restored = albums_view.property("presentationAlbums")
        if hasattr(restored, "toVariant"):
            restored = restored.toVariant()
        assert len(restored) == 10_000

        slowest_navigation = 0.0
        for mode, object_name in (
            ("grid", "albumGridView"),
            ("cover", "albumCoverView"),
            ("vinyl", "albumVinylView"),
            ("timeline", "albumTimelineView"),
            ("magazine", "albumMagazineView"),
            ("list", "albumListView"),
        ):
            albums_view.setProperty("albumMode", mode)
            QTest.qWait(420)
            active = albums_view.findChild(QObject, object_name)
            assert active is not None, f"{object_name} did not materialize"
            navigation_started = time.perf_counter()
            if active.property("currentIndex") is not None:
                active.setProperty("currentIndex", 9999)
                QCoreApplication.processEvents()
            if mode == "magazine":
                magazine_list = albums_view.findChild(QObject, "albumMagazineList")
                assert magazine_list is not None
                assert int(magazine_list.property("count")) > 9_000
                magazine_list.setProperty(
                    "currentIndex", int(magazine_list.property("count")) - 1
                )
                assert QMetaObject.invokeMethod(
                    magazine_list, "positionViewAtEnd", Qt.DirectConnection
                )
                QCoreApplication.processEvents()
                assert float(magazine_list.property("contentY")) > 0
            slowest_navigation = max(
                slowest_navigation, time.perf_counter() - navigation_started
            )
            assert len(albums_view.findChildren(QObject)) < 2_500

        assert time.perf_counter() - started < 20.0
        assert slowest_navigation < 1.5
    finally:
        window.close()
        window.deleteLater()
        if albums_view is not None:
            albums_view.deleteLater()
    bridge.dispose()


def test_album_palette_projection_is_async_clamped_and_owned(qapp, tmp_path) -> None:
    library, *_rest = _library_world(tmp_path)
    extractor = _PaletteExtractor()
    bridge = LibraryBridge(library, palette_extractor=extractor)
    artwork = tmp_path / "cover.png"
    artwork.write_bytes(b"placeholder")

    bridge._album_artwork_paths["album::palette"] = str(artwork)
    initial = bridge._album_palette("album::palette")
    assert initial["dominant"] == "#152A45"
    assert extractor.sources == ()

    bridge.request_album_palette("album::palette")
    assert extractor.sources == (str(artwork),)
    assert extractor.callback is not None

    extractor.callback(("#204080", "#183050", "#0A0D14"))
    QCoreApplication.processEvents()
    QCoreApplication.processEvents()
    projected = bridge._album_palette("album::palette")

    assert projected["dominant"] == "#204080"
    assert projected["backplane"] == "#0A0D14"
    assert projected["accentSafe"].startswith("#")
    assert 0 <= projected["luminance"] <= 1
    assert projected["warmth"] < 0
    bridge.dispose()
    assert extractor.closed is True


def test_palette_updates_are_granular_and_reset_when_artwork_disappears(qapp) -> None:
    track = TrackRef(
        Path("/virtual/palette.flac"),
        title="Palette",
        artist="Michi",
        album="Palette",
    )
    library = _ProjectionLibrary([track], artwork=True)
    extractor = _PaletteExtractor()
    bridge = LibraryBridge(library, palette_extractor=extractor)
    row = bridge.property("albums")[0]
    palette_spy = QSignalSpy(bridge.albumPaletteChanged)
    library_spy = QSignalSpy(bridge.library_changed)

    bridge.request_album_palette(row["key"])
    extractor.callback(("#204080", "#183050", "#0A0D14"))
    QCoreApplication.processEvents()

    assert palette_spy.count() == 1
    assert palette_spy.at(0)[0] == row["key"]
    assert palette_spy.at(0)[1]["dominant"] == "#204080"
    assert library_spy.count() == 0

    library._artwork = False
    bridge.request_album_palette(row["key"])

    assert palette_spy.count() == 2
    assert palette_spy.at(1)[1]["dominant"] == "#152A45"
    assert row["key"] not in bridge._album_palettes
    assert library_spy.count() == 0
    bridge.dispose()


def test_10k_projection_only_requests_palettes_for_materialized_albums(qapp) -> None:
    tracks = [
        TrackRef(
            Path(f"/virtual/{index:05d}.flac"),
            title=f"Track {index:05d}",
            artist=f"Artist {index:05d}",
            album=f"Album {index:05d}",
        )
        for index in range(10_000)
    ]
    extractor = _PaletteExtractor()
    bridge = LibraryBridge(
        _ProjectionLibrary(tracks, artwork=True), palette_extractor=extractor
    )

    rows = bridge.property("albums")
    assert len(rows) == 10_000
    assert extractor.requests == []

    visible_keys = [row["key"] for row in rows[:24]]
    for key in visible_keys:
        bridge.request_album_palette(key)
        bridge.request_album_palette(key)

    assert len(extractor.requests) == len(visible_keys)
    assert len(bridge._palette_sources) == len(visible_keys)

    palette_spy = QSignalSpy(bridge.albumPaletteChanged)
    library_spy = QSignalSpy(bridge.library_changed)
    started = time.perf_counter()
    for callback in extractor.callbacks:
        callback(("#204080", "#183050", "#0A0D14"))
    QCoreApplication.processEvents()

    assert palette_spy.count() == len(visible_keys)
    assert library_spy.count() == 0
    assert time.perf_counter() - started < 0.5
    bridge.dispose()


def test_queue_bridge_exposes_rows_and_existing_remove_intent() -> None:
    service = QueueService()
    bridge = QueueBridge(service)
    service.add(Path("/music/one.flac"), "One")
    service.add(Path("/music/two.flac"), "Two")

    rows = bridge.property("trackRows")
    assert [(row["title"], row["path"]) for row in rows] == [
        ("One", "/music/one.flac"),
        ("Two", "/music/two.flac"),
    ]
    assert all(row["formatLabel"] == "UNKNOWN" for row in rows)
    assert all(row["unavailable"] is True for row in rows)

    bridge.remove_track(0)
    remaining = bridge.property("trackRows")
    assert len(remaining) == 1
    assert remaining[0]["title"] == "Two"
    assert remaining[0]["path"] == "/music/two.flac"
    bridge.dispose()


def test_track_row_projection_contains_only_canonical_facts() -> None:
    ref = TrackRef(
        file_path=Path("/music/one.flac"),
        display_name="01 One.flac",
        title="One",
        artist="Artist",
        album="Album",
        duration_ms=123_000,
        codec="FLAC",
        sample_rate_hz=96_000,
        bit_depth=24,
        channels=2,
        file_size=42_000_000,
    )

    row = LibraryBridge._track_row(ref)

    assert row["title"] == "One"
    assert row["qualityLabel"] == "FLAC · 24-bit · 96 kHz"
    assert row["sampleRateHz"] == 96_000
    assert row["bitDepth"] == 24
    assert row["fileSize"] == 42_000_000


def _library_world(tmp_path):
    first = tmp_path / "one.flac"
    second = tmp_path / "two.flac"
    first.write_bytes(b"x")
    second.write_bytes(b"x")
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService()

    def metadata(path):
        return TrackMetadata(
            title=path.stem.title(),
            artist="Michi Artist",
            album="Michi Album",
            duration_ms=123_000,
            codec="FLAC",
            sample_rate_hz=96_000,
            bit_depth=24,
        )

    library = LibraryService(
        _Scanner([first, second]), metadata_extractor=_Extractor(metadata)
    )
    library.scan(str(tmp_path))
    from michi.application.library_playback_coordinator import (
        LibraryPlaybackCoordinator,
    )
    from michi.application.playback_session_service import (
        PlaybackSessionService,
    )

    session = PlaybackSessionService(playback, queue)
    coordinator = LibraryPlaybackCoordinator(library, session)
    return library, queue, session, coordinator, playback, audio, first


def test_artist_detail_projection_is_canonical_and_activatable(tmp_path) -> None:
    library, queue, session, coordinator, _playback, audio, _first = _library_world(
        tmp_path
    )
    bridge = LibraryBridge(library, playback_coordinator=coordinator)
    artist = bridge.property("artists")[0]

    bridge.select_artist(artist["key"])

    album_key = bridge.property("artistAlbums")[0]["key"]
    library.artwork_path_for = lambda key: (
        "/cache/michi-album.jpg" if key == album_key else None
    )

    assert bridge.property("artistName") == "Michi Artist"
    assert bridge.property("artistAlbumCount") == 1
    assert len(bridge.property("artistAlbums")) == 1
    assert [row["title"] for row in bridge.property("artistTracks")] == [
        "One",
        "Two",
    ]
    assert {row["artworkPath"] for row in bridge.property("artistTracks")} == {
        "/cache/michi-album.jpg"
    }
    bridge.activate_artist_track(1)
    audio.trigger_media_accepted(audio.loaded)
    # M4-R1: artist track → SINGLE context (Queue untouched)
    assert session.state.context_type.name == "SINGLE"
    assert session.state.current_entry.file_path.name == "two.flac"
    assert queue.state.count == 0
    bridge.dispose()


def test_playlist_search_is_separate_from_frozen_m7_total(tmp_path) -> None:
    library, queue, _playback, session, coordinator, _audio, _first = _library_world(
        tmp_path
    )
    playlists = PlaylistService()
    playlists.create_playlist("Late Night")
    bridge = LibraryBridge(library)
    # M9-R1: playlist search projection lives in the PlaylistsBridge.
    from michi.presentation.playlists_bridge import PlaylistsBridge

    pl_bridge = PlaylistsBridge(playlists, library=library)

    bridge.search("late")

    assert bridge.property("searchTotalCount") == 0
    assert bridge.property("searchDisplayTotalCount") == 0  # M7 entities only
    rows = pl_bridge.property("searchPlaylists")
    assert [(r["name"], r["trackCount"], "playlistId" in r) for r in rows] == [
        ("Late Night", 0, True)
    ]
    assert pl_bridge.property("searchPlaylistCount") == 1
    bridge.dispose()
    pl_bridge.dispose()


def test_playback_and_queue_enrich_current_track_from_library(tmp_path) -> None:
    library, queue, session, coordinator, playback, audio, first = _library_world(
        tmp_path
    )
    playback_bridge = PlaybackBridge(playback, library)
    queue_bridge = QueueBridge(queue, library)

    queue.add(first, "One")
    session.play_queue_index(0)
    audio.trigger_media_accepted(first)

    assert playback_bridge.property("currentPath") == str(first)
    assert playback_bridge.property("title") == "One"
    assert playback_bridge.property("artist") == "Michi Artist"
    assert playback_bridge.property("qualityLabel") == "FLAC · 24-bit · 96 kHz"
    assert playback_bridge.property("formatLabel") == "FLAC"
    assert queue_bridge.property("trackRows")[0]["durationMs"] == 123_000
    playback_bridge.dispose()
    queue_bridge.dispose()
