"""DAC-V35-100R1.2 QML-facing playback refusal containment gates."""

from __future__ import annotations

from pathlib import Path

from michi.domain.audio_engine import AudioEngineId
from michi.domain.playback_session import (
    PlaybackContextType,
    PlaybackSequenceEntry,
)
from michi.presentation.playback_bridge import PlaybackBridge
from michi.presentation.playback_session_bridge import PlaybackSessionBridge
from tests.dac.test_v35_productive_direct_composition import (
    _close_graph,
    _direct_graph,
)


def _refusing_graph(tmp_path: Path):
    return _direct_graph(
        tmp_path,
        startup_selected_engine=AudioEngineId.QT_MULTIMEDIA,
    )


def _assert_friendly_engine_refusal(graph, bindings) -> None:
    assert graph.playback.state.error_message.startswith("Direct requires GStreamer:")
    assert "ENGINE_UNSUPPORTED_FOR_DIRECT" not in graph.playback.state.error_message
    assert bindings.pipelines == []


def _close_refusing_graph(graph) -> None:
    _close_graph(graph)
    graph.qt_engine_provider.close()


def test_ui100r12_01_song_entry_refusal_never_escapes(qapp, tmp_path: Path) -> None:
    graph, bindings = _refusing_graph(tmp_path)
    try:
        graph.playback_session.play_single(
            PlaybackSequenceEntry(tmp_path / "song.flac", "Song")
        )
        _assert_friendly_engine_refusal(graph, bindings)
    finally:
        _close_refusing_graph(graph)


def test_ui100r12_02_album_context_refusal_never_escapes(qapp, tmp_path: Path) -> None:
    graph, bindings = _refusing_graph(tmp_path)
    entry = PlaybackSequenceEntry(tmp_path / "album-track.flac", "Album track")
    try:
        graph.playback_session.play_context(
            PlaybackContextType.ALBUM,
            "album:test",
            [entry],
        )
        _assert_friendly_engine_refusal(graph, bindings)
    finally:
        _close_refusing_graph(graph)


def test_ui100r12_03_queue_slot_refusal_never_escapes(qapp, tmp_path: Path) -> None:
    graph, bindings = _refusing_graph(tmp_path)
    bridge = PlaybackSessionBridge(graph.playback_session)
    try:
        graph.queue.add(tmp_path / "queued.flac", "Queued")
        bridge.play_queue_index(0)
        _assert_friendly_engine_refusal(graph, bindings)
    finally:
        bridge.dispose()
        _close_refusing_graph(graph)


def test_ui100r12_04_playback_bridge_refusal_never_escapes(
    qapp, tmp_path: Path
) -> None:
    graph, bindings = _refusing_graph(tmp_path)
    bridge = PlaybackBridge(graph.playback)
    try:
        # A stopped logical source is the public replay case. The bridge calls
        # PlaybackService.play(), which reloads through the canonical path.
        graph.playback._state.file_path = tmp_path / "replay.flac"
        graph.playback._accepted = False
        bridge.play()
        _assert_friendly_engine_refusal(graph, bindings)
        assert bridge.errorMessage.startswith("Direct requires GStreamer:")
    finally:
        bridge.dispose()
        _close_refusing_graph(graph)
