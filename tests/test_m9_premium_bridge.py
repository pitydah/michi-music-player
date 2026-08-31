"""Bridge-level gates for the M9 premium presentation projections."""

import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import FakeAudioPort
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QGuiApplication

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
        self.sources = ()
        self.closed = False

    def request_palette(self, source_paths, callback) -> None:
        self.sources = source_paths
        self.callback = callback

    def close(self) -> None:
        self.closed = True


class _ProjectionLibrary:
    def __init__(self, tracks) -> None:
        model = build_music_model(tracks)
        self.state = SimpleNamespace(
            albums=model.albums,
            artists=model.artists,
            tracks=model.tracks,
            favorite_paths=(),
            recently_added_paths=(),
            search_active=False,
            search_projection=None,
        )

    def subscribe_changed(self, _callback) -> None:
        return None

    def unsubscribe_changed(self, _callback) -> None:
        return None

    def artwork_path_for(self, _album_key) -> str:
        return ""


def test_canonical_album_projection_handles_10k_albums(qapp) -> None:
    tracks = [
        TrackRef(
            Path(f"/virtual/{index:05d}.flac"),
            title=f"Track {index:05d}",
            artist=f"Artist {index:05d}",
            album=f"Album {index:05d}",
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
    bridge.dispose()


def test_album_palette_projection_is_async_clamped_and_owned(qapp, tmp_path) -> None:
    library, *_rest = _library_world(tmp_path)
    extractor = _PaletteExtractor()
    bridge = LibraryBridge(library, palette_extractor=extractor)
    artwork = tmp_path / "cover.png"
    artwork.write_bytes(b"placeholder")

    initial = bridge._album_palette("album::palette", str(artwork))
    assert initial["dominant"] == "#152A45"
    assert extractor.sources == (str(artwork),)
    assert extractor.callback is not None

    extractor.callback(("#204080", "#183050", "#0A0D14"))
    QCoreApplication.processEvents()
    QCoreApplication.processEvents()
    projected = bridge._album_palette("album::palette", str(artwork))

    assert projected["dominant"] == "#204080"
    assert projected["backplane"] == "#0A0D14"
    assert projected["accentSafe"].startswith("#")
    assert 0 <= projected["luminance"] <= 1
    assert projected["warmth"] < 0
    bridge.dispose()
    assert extractor.closed is True


def test_queue_bridge_exposes_rows_and_existing_remove_intent() -> None:
    service = QueueService()
    bridge = QueueBridge(service)
    service.add(Path("/music/one.flac"), "One")
    service.add(Path("/music/two.flac"), "Two")

    assert bridge.property("trackRows") == [
        {"title": "One", "path": "/music/one.flac"},
        {"title": "Two", "path": "/music/two.flac"},
    ]

    bridge.remove_track(0)
    assert bridge.property("trackRows") == [{"title": "Two", "path": "/music/two.flac"}]
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

    assert bridge.property("artistName") == "Michi Artist"
    assert bridge.property("artistAlbumCount") == 1
    assert len(bridge.property("artistAlbums")) == 1
    assert [row["title"] for row in bridge.property("artistTracks")] == [
        "One",
        "Two",
    ]
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
