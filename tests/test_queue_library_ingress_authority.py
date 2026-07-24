"""Queue authority tests for library and playlist aggregate ingress."""
from __future__ import annotations

from unittest.mock import MagicMock

from ui_qml_bridge.library_bridge import LibraryBridge
from ui_qml_bridge.playlists_bridge import PlaylistsBridge


def _result(**data):
    return {"ok": True, **data}


def test_library_aggregate_actions_use_canonical_queue() -> None:
    queue = MagicMock()
    queue.replace_and_play.return_value = _result()
    queue.enqueue.return_value = _result()
    query = MagicMock()
    query.fetch_album_tracks_internal.return_value = [
        {"track_uid": "1", "filepath": "/a.flac", "title": "A"},
        {"track_uid": "2", "filepath": "/b.flac", "title": "B"},
    ]
    query.fetch_artist_tracks_internal.return_value = query.fetch_album_tracks_internal.return_value
    query.fetch_folder_tracks_internal.return_value = query.fetch_album_tracks_internal.return_value
    player = MagicMock()
    bridge = LibraryBridge(
        query_service=query,
        query_executor=MagicMock(),
        track_action_service=MagicMock(),
        playback_ctrl=player,
        queue_service=queue,
    )

    assert bridge.playAlbum("album")["ok"]
    assert bridge.enqueueAlbum("album")["ok"]
    assert bridge.playArtist("artist")["ok"]
    assert bridge.playFolder("/music")["ok"]
    assert bridge.enqueueSong("/c.flac")["ok"]

    assert queue.replace_and_play.call_count == 3
    queue.enqueue.assert_any_call(
        query.fetch_album_tracks_internal.return_value, play_now=False
    )
    queue.enqueue.assert_any_call({"filepath": "/c.flac"}, play_now=False)
    player.enqueue.assert_not_called()


def test_playlist_keeps_full_order_and_starts_at_requested_index() -> None:
    items = [
        {"track_uid": "dup", "filepath": "/same.flac", "position": 0},
        {"track_uid": "dup", "filepath": "/same.flac", "position": 1},
        {"track_uid": "3", "filepath": "/c.flac", "position": 2},
    ]
    service = MagicMock()
    service.list.return_value = []
    service.get_items_for_queue.return_value = items
    queue = MagicMock()
    queue.replace_and_play.return_value = _result()
    player = MagicMock()
    bridge = PlaylistsBridge(
        db=MagicMock(),
        playlist_service=service,
        player_service=player,
        queue_service=queue,
    )

    result = bridge.playPlaylistFromIndex(4, 1)

    assert result["ok"]
    queue.replace_and_play.assert_called_once_with(items, 1)
    player.enqueue.assert_not_called()
    assert bridge.playPlaylistFromIndex(4, 4)["error"] == "INVALID_INDEX"
