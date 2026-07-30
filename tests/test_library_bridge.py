import json
import sqlite3
from types import SimpleNamespace
from unittest.mock import MagicMock

from library.schema import Schema
from ui_qml_bridge.library_bridge import LibraryBridge


class TestLibraryBridge:
    def test_create(self):
        bridge = LibraryBridge(query_service=MagicMock(), track_action_service=MagicMock())
        assert bridge is not None

    def test_set_favorite_bulk_updates_all_requested_tracks_in_one_call(self):
        connection = sqlite3.connect(":memory:")
        Schema.initialize(connection)
        connection.executemany(
            "INSERT INTO media_items "
            "(filepath, filename, directory, ext, kind, title) VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("/music/one.flac", "one.flac", "/music", ".flac", "audio", "One"),
                ("/music/two.flac", "two.flac", "/music", ".flac", "audio", "Two"),
                ("/music/three.flac", "three.flac", "/music", ".flac", "audio", "Three"),
            ],
        )
        bridge = LibraryBridge(
            db=SimpleNamespace(conn=connection),
            query_service=MagicMock(),
            track_action_service=MagicMock(),
        )

        added = bridge.setFavoriteBulk(json.dumps([1, 3]), True)
        favorites = connection.execute(
            "SELECT track_id FROM favorites ORDER BY track_id"
        ).fetchall()
        removed = bridge.setFavoriteBulk(json.dumps([3]), False)

        assert added == {"ok": True, "favorite": True, "count": 2}
        assert favorites == [("/music/one.flac",), ("/music/three.flac",)]
        assert removed == {"ok": True, "favorite": False, "count": 1}
        assert connection.execute(
            "SELECT track_id FROM favorites ORDER BY track_id"
        ).fetchall() == [("/music/one.flac",)]

    def test_set_favorite_bulk_rejects_invalid_json_and_track_ids(self):
        connection = sqlite3.connect(":memory:")
        Schema.initialize(connection)
        bridge = LibraryBridge(
            db=SimpleNamespace(conn=connection),
            query_service=MagicMock(),
            track_action_service=MagicMock(),
        )

        malformed = bridge.setFavoriteBulk("not-json", True)
        invalid_ids = bridge.setFavoriteBulk(json.dumps([1, "2"]), True)

        assert malformed["ok"] is False
        assert malformed["error"].startswith("INVALID_JSON")
        assert invalid_ids == {"ok": False, "error": "INVALID_TRACK_IDS"}

    def test_bulk_queue_operations_fetch_once_and_mutate_queue_once(self):
        connection = sqlite3.connect(":memory:")
        Schema.initialize(connection)
        connection.executemany(
            "INSERT INTO media_items "
            "(filepath, filename, directory, ext, kind, title, artist, album, album_key) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("/music/one.flac", "one.flac", "/music", ".flac", "audio", "One",
                 "Artist", "Album", "album-key"),
                ("/music/two.flac", "two.flac", "/music", ".flac", "audio", "Two",
                 "Artist", "Album", "album-key"),
            ],
        )
        queue = MagicMock()
        queue.enqueue.return_value = {"ok": True, "added": 2}
        queue.replace_and_play.return_value = {"ok": True, "replaced": 2}
        bridge = LibraryBridge(
            db=SimpleNamespace(conn=connection),
            query_service=MagicMock(),
            queue_service=queue,
        )

        enqueue_result = bridge.enqueueBulk(json.dumps([2, 1]))
        play_result = bridge.playBulk(json.dumps([1, 2]))

        assert enqueue_result == {"ok": True, "added": 2}
        assert play_result == {"ok": True, "replaced": 2}
        queued = queue.enqueue.call_args.args[0]
        played = queue.replace_and_play.call_args.args[0]
        assert [track["track_id"] for track in queued] == [2, 1]
        assert [track["track_id"] for track in played] == [1, 2]
        queue.enqueue.assert_called_once()
        queue.replace_and_play.assert_called_once()

    def test_bulk_queue_operations_reject_invalid_or_missing_ids(self):
        connection = sqlite3.connect(":memory:")
        Schema.initialize(connection)
        bridge = LibraryBridge(
            db=SimpleNamespace(conn=connection),
            query_service=MagicMock(),
            queue_service=MagicMock(),
        )

        assert bridge.enqueueBulk(json.dumps([])) == {
            "ok": False,
            "error": "INVALID_TRACK_IDS",
        }
        assert bridge.playBulk(json.dumps([999])) == {
            "ok": False,
            "error": "NO_TRACKS",
        }
