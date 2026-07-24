from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest

from core.library.library_filtered_query_service import LibraryFilteredQueryService
from core.library.library_query_service import LibraryQueryService
from core.playlist_service import PlaylistService
from core.queue_service import QueueService
from core.track_action_service import TrackActionService
from ui_qml_bridge.library_bridge import LibraryBridge


class _Database:
    def __init__(self, conn):
        self.conn = conn


@pytest.fixture
def track_actions():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE media_items ("
        "id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, artist TEXT, "
        "album TEXT, duration REAL, track_uid TEXT, album_key TEXT, deleted_at INTEGER)"
    )
    conn.executemany(
        "INSERT INTO media_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)",
        [
            (1, "/music/a.flac", "A", "Artist", "Album", 180, "uid-a", "album-a"),
            (2, "/music/b.flac", "B", "Artist", "Album", 200, "uid-b", "album-a"),
            (3, "/music/c.flac", "C", "Artist", "Album", 220, "uid-c", "album-a"),
        ],
    )
    db = _Database(conn)
    query = LibraryFilteredQueryService(LibraryQueryService(db=db))
    player = MagicMock()
    queue = QueueService(player_service=player)
    service = TrackActionService(
        query_service=query,
        queue_service=queue,
        playlist_service=PlaylistService(),
        db=db,
    )
    yield service, queue, player, query, db
    conn.close()


def test_track_actions_use_real_query_and_canonical_queue(track_actions):
    service, queue, player, _query, _db = track_actions

    assert service.play_track(1)["ok"]
    assert service.enqueue_track(2)["ok"]
    assert service.play_next(3)["ok"]

    assert [item["track_id"] for item in queue.items] == [1, 3, 2]
    assert queue.current_index == 0
    player.play.assert_called_once_with(
        "/music/a.flac", "A", "Artist", "Album"
    )
    player.enqueue.assert_not_called()
    player.enqueue_next.assert_not_called()


def test_library_bridge_delegates_track_id_actions(track_actions):
    service, _queue, _player, query, db = track_actions
    bridge = LibraryBridge(
        db=db,
        query_service=query,
        track_action_service=service,
    )

    assert bridge.playTrackById(1)["ok"]
    assert bridge.enqueueTrackById(2)["ok"]
    assert bridge.playNextTrackById(3)["ok"]
    assert service.play_track(999)["error"] == "NOT_FOUND"
