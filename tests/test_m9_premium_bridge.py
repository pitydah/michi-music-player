"""Bridge-level gates for the M9 premium presentation projections."""

from pathlib import Path

from conftest import FakeAudioPort

from michi.application.playback_service import PlaybackService
from michi.application.queue_service import QueueService
from michi.domain.library import TrackRef
from michi.presentation.library_bridge import LibraryBridge
from michi.presentation.queue_bridge import QueueBridge


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
