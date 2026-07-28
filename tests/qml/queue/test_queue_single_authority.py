"""Prove QueueService is single authority — no local copies, all paths converge.

Every QML bridge delegates queue mutations to QueueService. No bridge holds a
local copy of queue state. QueueListModel is a read-only projection that
subscribes to QueueService events. Persistence round-trips without autoplay.
Undo restores the exact prior snapshot.
"""
from __future__ import annotations

import inspect
import re
from unittest.mock import MagicMock

import pytest

from core.queue_service import QueueService
from ui_qml.models.QueueListModel import QueueListModel
from ui_qml_bridge.library_bridge import LibraryBridge
from ui_qml_bridge.mix_bridge import MixBridge
from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
from ui_qml_bridge.playlists_bridge import PlaylistsBridge
from ui_qml_bridge.queue_bridge import QueueBridge

pytestmark = [pytest.mark.qml_module("queue")]

# Every QueueService method that mutates domain state. Bridges must route
# through these; QueueListModel must never touch them.
QUEUE_MUTATION_METHODS = (
    "enqueue", "replace_and_play", "replace", "remove", "reorder", "move",
    "clear", "save_state", "load_state", "undo", "persist", "restore",
    "insert", "insert_next", "play_from_index", "set_repeat", "set_shuffle",
)

_OK_RESULT = {
    "ok": True, "operation": "test", "error": None, "message": "",
    "current_index": 0, "count": 1, "revision": 1,
}


def _queue_service_mock(count: int = 5) -> MagicMock:
    """Build a QueueService mock safe for bridge construction and assertions.

    Bridges read ``count``/``current_index`` as properties and compare against
    them with ``<`` / ``>=``. A plain MagicMock would make those comparisons
    return truthy MagicMocks, so they must be real Python scalars. The mock
    also returns a real state dict (QueueListModel reads it during construction)
    and a callable unsubscribe (QueueListModel stores it for disposal).
    """
    mock = MagicMock()
    mock.count = count
    mock.current_index = 0
    mock.can_undo = False
    mock.shuffle = False
    mock.repeat = "none"
    mock.get_state.return_value = {
        "items": [], "current_index": -1, "shuffle": False,
        "repeat": "none", "revision": 0, "can_undo": False,
        "shuffle_order": None, "context": "",
    }
    mock.subscribe.return_value = lambda: None
    for method in QUEUE_MUTATION_METHODS:
        getattr(mock, method).return_value = dict(_OK_RESULT)
    return mock


def _track(filepath: str, title: str = "T") -> dict:
    return {"filepath": filepath, "title": title, "track_id": 0,
            "artist": "", "album": ""}


# ── Test 1: QueueBridge delegates every mutation to QueueService ──────────────

def test_queue_bridge_delegates_all_mutations_to_queue_service():
    """QueueBridge holds no queue state — every Slot calls QueueService."""
    queue_service = _queue_service_mock()
    bridge = QueueBridge(queue_service=queue_service)
    items = [{"filepath": "/a.flac"}]

    # add → enqueue(items, play_now=False)
    assert bridge.add(items)["ok"] is True
    queue_service.enqueue.assert_called_once_with(items, play_now=False)

    # replaceAndPlay → replace_and_play(items, start_index)
    assert bridge.replaceAndPlay(items, 0)["ok"] is True
    queue_service.replace_and_play.assert_called_once_with(items, 0)

    # removeFromQueue(index) → remove([index])
    assert bridge.removeFromQueue(0)["ok"] is True
    queue_service.remove.assert_called_once_with([0])

    # moveItem(from, to) → reorder(from, to)
    assert bridge.moveItem(0, 1)["ok"] is True
    queue_service.reorder.assert_called_once_with(0, 1)

    # clearQueue → clear()
    assert bridge.clearQueue()["ok"] is True
    queue_service.clear.assert_called_once_with()

    # saveState → save_state()
    assert bridge.saveState()["ok"] is True
    queue_service.save_state.assert_called_once_with()

    # loadState → load_state()
    assert bridge.loadState()["ok"] is True
    queue_service.load_state.assert_called_once_with()

    # undo → undo()
    assert bridge.undo()["ok"] is True
    queue_service.undo.assert_called_once_with()

    # persist → persist()
    assert bridge.persist()["ok"] is True
    queue_service.persist.assert_called_once_with()

    # restore → restore()
    assert bridge.restore()["ok"] is True
    queue_service.restore.assert_called_once_with()


# ── Test 2: NowPlayingBridge delegates queue ops to QueueService ──────────────

def test_nowplaying_bridge_delegates_queue_mutations_to_queue_service():
    """NowPlayingBridge routes every queue command through QueueService."""
    queue_service = _queue_service_mock(count=3)
    # player_service=None is accepted (degraded mode); refresh() short-circuits.
    bridge = NowPlayingBridge(player_service=None, queue_service=queue_service,
                              audio_quality_adapter=MagicMock())

    # enqueueSong(filepath) → enqueue({"filepath": fp}, play_now=False)
    assert bridge.enqueueSong("/a.flac")["ok"] is True
    queue_service.enqueue.assert_called_once_with({"filepath": "/a.flac"},
                                                  play_now=False)

    # removeFromQueue(index) → remove([index])
    assert bridge.removeFromQueue(0)["ok"] is True
    queue_service.remove.assert_called_once_with([0])

    # clearQueue → clear()
    assert bridge.clearQueue()["ok"] is True
    queue_service.clear.assert_called_once_with()

    # moveQueueItem(from, to) → reorder(from, to)
    assert bridge.moveQueueItem(0, 2)["ok"] is True
    queue_service.reorder.assert_called_once_with(0, 2)

    # playQueueItem(index) → play_from_index(index)
    assert bridge.playQueueItem(1)["ok"] is True
    queue_service.play_from_index.assert_called_once_with(1)


# ── Test 3: LibraryBridge delegates playback ingress to QueueService ─────────

def test_library_bridge_delegates_queue_mutations_to_queue_service():
    """LibraryBridge never builds a queue locally — it always delegates."""
    queue_service = _queue_service_mock(count=0)
    queue_service.current_index = 1  # exercise playAlbumNext → insert(2, ...)
    query_service = MagicMock()
    tracks = [_track("/a.flac", "A"), _track("/b.flac", "B")]
    query_service.fetch_album_tracks_internal.return_value = tracks
    query_service.fetch_artist_tracks_internal.return_value = tracks
    query_service.fetch_folder_tracks_internal.return_value = tracks
    query_service.fetch_filtered_tracks_internal.return_value = tracks
    # play_song falls back to {"filepath": fp} when resolve returns None.
    query_service.fetch_track_by_filepath.return_value = None
    bridge = LibraryBridge(query_service=query_service, queue_service=queue_service)

    # enqueueSong → enqueue({"filepath": fp}, play_now=False)
    bridge.enqueueSong("/a.flac")
    queue_service.enqueue.assert_called_once_with({"filepath": "/a.flac"},
                                                  play_now=False)

    # playAlbum → replace_and_play(tracks, 0)
    bridge.playAlbum("album_key_1")
    queue_service.replace_and_play.assert_any_call(tracks, 0)

    # playArtist → replace_and_play(tracks, 0)
    bridge.playArtist("Artist X")
    queue_service.replace_and_play.assert_any_call(tracks, 0)

    # playFolder → replace_and_play(tracks, 0)
    bridge.playFolder("/music/folder")
    queue_service.replace_and_play.assert_any_call(tracks, 0)

    # playAllFiltered → replace_and_play(tracks, 0)
    bridge.playAllFiltered()
    queue_service.replace_and_play.assert_any_call(tracks, 0)

    # play_song (radio URI skips filesystem check) → replace_and_play([{fp}])
    bridge.play_song("radio://station")
    queue_service.replace_and_play.assert_any_call([{"filepath": "radio://station"}])

    # playSongs(items_json) → replace_and_play(items, 0)
    bridge.playSongs('[{"filepath": "/x.flac"}]')
    queue_service.replace_and_play.assert_any_call([{"filepath": "/x.flac"}], 0)

    # enqueueAlbum → enqueue(tracks, play_now=False)
    bridge.enqueueAlbum("album_key_2")
    queue_service.enqueue.assert_any_call(tracks, play_now=False)

    # playAlbumNext → insert(current_index + 1, tracks)
    bridge.playAlbumNext("album_key_3")
    queue_service.insert.assert_called_once_with(2, tracks)


# ── Test 4: PlaylistsBridge delegates playback to QueueService ────────────────

def test_playlists_bridge_delegates_queue_mutations_to_queue_service():
    """PlaylistsBridge resolves items then hands playback to QueueService."""
    queue_service = _queue_service_mock()
    playlist_service = MagicMock()
    tracks = [_track("/a.flac", "A"), _track("/b.flac", "B")]
    playlist_service.get_items_for_queue.return_value = tracks
    bridge = PlaylistsBridge(playlist_service=playlist_service,
                             queue_service=queue_service)

    # playPlaylist → replace_and_play(tracks, 0)
    assert bridge.playPlaylist(1)["ok"] is True
    queue_service.replace_and_play.assert_called_once_with(tracks, 0)

    # playPlaylistFromIndex → replace_and_play(tracks, index)
    assert bridge.playPlaylistFromIndex(1, 1)["ok"] is True
    queue_service.replace_and_play.assert_called_with(tracks, 1)


# ── Test 5: MixBridge delegates mix playback to QueueService ──────────────────

def test_mix_bridge_delegates_queue_mutations_to_queue_service():
    """MixBridge never enqueues locally — it delegates to QueueService."""
    queue_service = _queue_service_mock()
    bridge = MixBridge(queue_service=queue_service)
    songs = [_track("/a.flac", "A"), _track("/b.flac", "B")]
    # Bypass the generation state machine by seeding the result directly.
    bridge._current_songs = songs

    # playMix → replace_and_play(songs, 0)
    assert bridge.playMix()["ok"] is True
    queue_service.replace_and_play.assert_called_once_with(songs, 0)

    # enqueueMix → enqueue(songs, play_now=False)
    assert bridge.enqueueMix()["ok"] is True
    queue_service.enqueue.assert_called_once_with(songs, play_now=False)

    # playFromIndex → replace_and_play(songs, index)
    assert bridge.playFromIndex(1)["ok"] is True
    queue_service.replace_and_play.assert_called_with(songs, 1)

    # enqueueTrack → enqueue(songs[index], play_now=False)
    assert bridge.enqueueTrack(0)["ok"] is True
    queue_service.enqueue.assert_called_with(songs[0], play_now=False)


# ── Test 6: QueueListModel is a read-only projection ─────────────────────────

def test_queue_list_model_is_read_only_projection():
    """QueueListModel subscribes to events and never mutates the queue."""
    queue_service = _queue_service_mock()
    model = QueueListModel(queue_service=queue_service)

    # Event-driven: subscribes exactly once (never polls).
    queue_service.subscribe.assert_called_once()

    # Construction + initial refresh touched no mutation method.
    for method in QUEUE_MUTATION_METHODS:
        getattr(queue_service, method).assert_not_called()

    # Structural proof: the model source only reaches for read-only APIs.
    source = inspect.getsource(QueueListModel)
    accessed = set(re.findall(r"\bqueue_service\.(\w+)", source))
    assert accessed <= {"get_state", "subscribe"}, (
        f"QueueListModel reaches beyond read-only service APIs: {accessed}"
    )

    # A second refresh still triggers no mutation.
    model.refresh()
    for method in QUEUE_MUTATION_METHODS:
        getattr(queue_service, method).assert_not_called()


# ── Test 7: Persistence round-trip with no autoplay ──────────────────────────

def test_persistence_round_trip_no_autoplay():
    """persist → restore round-trips items without triggering playback."""
    persistence = MagicMock()
    player = MagicMock()
    svc = QueueService(player_service=player, runtime_persistence=persistence)
    items = [_track("/a.flac", "A"), _track("/b.flac", "B")]
    svc.enqueue(items, play_now=False)
    assert svc.count == 2

    # persist → RuntimePersistence.write("queue", state)
    assert svc.persist()["ok"] is True
    persistence.write.assert_called_once()
    write_call = persistence.write.call_args
    assert write_call.args[0] == "queue"
    saved_state = write_call.args[1]
    assert saved_state["items"] == items
    assert saved_state["current_index"] == 0

    # Simulate a fresh process: new service, persistence returns saved state.
    persistence.read.return_value = saved_state
    fresh_player = MagicMock()
    fresh_svc = QueueService(player_service=fresh_player,
                             runtime_persistence=persistence)

    restore_result = fresh_svc.restore()
    assert restore_result["ok"] is True
    assert fresh_svc.count == 2
    assert fresh_svc.items == items
    assert fresh_svc.current_index == 0

    # NO autoplay: restore syncs the queue but never executes a track.
    # play() and play_queue_index() are only invoked by _execute_current(),
    # which load_state() deliberately does not call.
    fresh_player.play.assert_not_called()
    fresh_player.play_queue_index.assert_not_called()


# ── Test 8: Undo restores the exact prior snapshot ───────────────────────────

def test_undo_restores_state_before_last_mutation():
    """undo() reverts the most recent mutation, restoring the prior snapshot."""
    player = MagicMock()
    svc = QueueService(player_service=player)
    items = [_track("/a.flac", "A"), _track("/b.flac", "B"), _track("/c.flac", "C")]
    svc.enqueue(items, play_now=False)
    assert svc.count == 3
    assert svc.current_index == 0
    state_before_remove = [item["title"] for item in svc.items]

    # Remove the middle track.
    assert svc.remove([1])["ok"] is True
    assert svc.count == 2
    assert [item["title"] for item in svc.items] == ["A", "C"]

    # Undo reverts to the snapshot captured before remove: [A, B, C], index 0.
    assert svc.undo()["ok"] is True
    assert svc.count == 3
    assert [item["title"] for item in svc.items] == state_before_remove
    assert svc.current_index == 0
