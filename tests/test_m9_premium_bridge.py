"""Bridge-level gates for the M9 premium presentation projections."""

from pathlib import Path

from conftest import FakeAudioPort

from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.playlist_service import PlaylistService
from michi.application.queue_service import QueueService
from michi.domain.library import TrackMetadata, TrackRef
from michi.presentation.library_bridge import LibraryBridge
from michi.presentation.playback_bridge import PlaybackBridge
from michi.presentation.queue_bridge import QueueBridge


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


def test_queue_bridge_exposes_rows_and_existing_remove_intent() -> None:
    service = QueueService(PlaybackService(FakeAudioPort()))
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
    queue = QueueService(playback)

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

    library = LibraryService(_Scanner([first, second]), queue, _Extractor(metadata))
    library.scan(str(tmp_path))
    return library, queue, playback, audio, first


def test_artist_detail_projection_is_canonical_and_activatable(tmp_path) -> None:
    library, queue, _playback, audio, _first = _library_world(tmp_path)
    bridge = LibraryBridge(library)
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
    assert queue.state.current_track.file_path.name == "two.flac"
    bridge.dispose()


def test_playlist_search_is_separate_from_frozen_m7_total(tmp_path) -> None:
    library, queue, _playback, _audio, _first = _library_world(tmp_path)
    playlists = PlaylistService(queue)
    playlists.create_playlist("Late Night")
    bridge = LibraryBridge(library, playlists)

    bridge.search("late")

    assert bridge.property("searchTotalCount") == 0
    assert bridge.property("searchPlaylistCount") == 1
    assert bridge.property("searchDisplayTotalCount") == 1
    rows = bridge.property("searchPlaylists")
    assert [(r["name"], r["trackCount"], "playlistId" in r) for r in rows] == [
        ("Late Night", 0, True)
    ]
    bridge.dispose()


def test_playback_and_queue_enrich_current_track_from_library(tmp_path) -> None:
    library, queue, playback, audio, first = _library_world(tmp_path)
    playback_bridge = PlaybackBridge(playback, library)
    queue_bridge = QueueBridge(queue, library)

    queue.add(first, "One")
    queue.play_index(0)
    audio.trigger_media_accepted(first)

    assert playback_bridge.property("currentPath") == str(first)
    assert playback_bridge.property("title") == "One"
    assert playback_bridge.property("artist") == "Michi Artist"
    assert playback_bridge.property("qualityLabel") == "FLAC · 24-bit · 96 kHz"
    assert playback_bridge.property("formatLabel") == "FLAC"
    assert queue_bridge.property("trackRows")[0]["durationMs"] == 123_000
    playback_bridge.dispose()
    queue_bridge.dispose()
