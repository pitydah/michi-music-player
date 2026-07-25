from unittest.mock import MagicMock

from core.queue_service import QueueService
from core.runtime_persistence import RuntimePersistence


class FakePlayer:
    def __init__(self):
        self.queue = []
        self.index = -1
        self.repeat = "none"
        self.shuffle = False
        self.played = []
        self.fail_sync = False
        self.fail_play = False
        self.stopped = False

    def play_queue(self, paths, start_index=0):
        if self.fail_sync:
            raise RuntimeError("sync failed")
        self.queue = list(paths)
        self.index = start_index

    def clear_queue(self):
        if self.fail_sync:
            raise RuntimeError("sync failed")
        self.queue = []
        self.index = -1

    def set_repeat(self, mode):
        self.repeat = mode

    def set_shuffle(self, enabled):
        self.shuffle = enabled

    def play(self, filepath, title="", artist="", album=""):
        if self.fail_play:
            raise RuntimeError("play failed")
        self.played.append(filepath)

    def stop(self):
        self.stopped = True


class RestorePlayer(FakePlayer):
    def __init__(self):
        super().__init__()
        self.played_indices = []

    def play_queue_index(self, index):
        self.played_indices.append(index)
        return True


class FailOnceRestorePlayer(RestorePlayer):
    def __init__(self):
        super().__init__()
        self.fail_next_sync = False

    def play_queue(self, paths, start_index=0):
        if self.fail_next_sync:
            self.fail_next_sync = False
            raise RuntimeError("sync failed")
        super().play_queue(paths, start_index)


def _items(*names):
    return [{"title": name, "filepath": f"/{name}.flac"} for name in names]


class TestQueueService:
    def test_create(self):
        svc = QueueService(player_service=MagicMock(), event_bus=MagicMock())
        assert svc._items == []

    def test_queue_empty_by_default(self):
        svc = QueueService()
        assert len(svc._items) == 0

    def test_replace_and_replace_and_play_are_canonical(self):
        player = FakePlayer()
        svc = QueueService(player_service=player)

        replaced = svc.replace(_items("a", "b"))
        played = svc.replace_and_play(_items("c", "d"), 1)

        assert replaced["ok"]
        assert played["ok"]
        assert svc.current_index == 1
        assert player.queue == ["/c.flac", "/d.flac"]
        assert player.played == ["/d.flac"]
        assert svc.revision == 2

    def test_enqueue_and_insert_next_preserve_duplicates(self):
        player = FakePlayer()
        duplicate = {"track_uid": "same", "filepath": "/same.flac"}
        svc = QueueService(player_service=player)
        svc.replace([duplicate, duplicate])

        result = svc.insert_next([duplicate])

        assert result["ok"]
        assert svc.get_items() == [duplicate, duplicate, duplicate]
        assert len(player.queue) == 3

    def test_repeat_navigation_modes(self):
        player = FakePlayer()
        svc = QueueService(player_service=player)
        svc.replace(_items("a", "b"), start_index=1)

        assert svc.next()["error"] == "END_OF_QUEUE"
        assert svc.set_repeat("all")["ok"]
        assert svc.next()["ok"]
        assert svc.current_index == 0
        assert svc.set_repeat("one")["ok"]
        assert svc.next()["ok"]
        assert svc.current_index == 0
        assert player.played[-2:] == ["/a.flac", "/a.flac"]

    def test_shuffle_preserves_current_track_duplicates_and_original_order(self):
        player = FakePlayer()
        items = [
            {"track_uid": "dup", "filepath": "/same.flac", "position": 1},
            {"track_uid": "dup", "filepath": "/same.flac", "position": 2},
            {"track_uid": "c", "filepath": "/c.flac", "position": 3},
        ]
        svc = QueueService(player_service=player)
        svc.replace(items, start_index=1)
        current = svc.get_current()

        enabled = svc.set_shuffle(True)
        shuffled = svc.get_items()
        disabled = svc.set_shuffle(False)

        assert enabled["ok"] and disabled["ok"]
        assert svc.get_current() == current
        assert sorted(item["position"] for item in shuffled) == [1, 2, 3]
        assert svc.get_items() == items
        assert player.queue == [item["filepath"] for item in items]

    def test_sync_failure_rolls_back_without_success_publication(self):
        player = FakePlayer()
        bus = MagicMock()
        svc = QueueService(player_service=player, event_bus=bus)
        svc.replace(_items("a"))
        before = svc.get_state()
        bus.reset_mock()
        player.fail_sync = True

        result = svc.enqueue(_items("b"))

        assert not result["ok"]
        assert result["error"] == "BACKEND_SYNC_FAILED"
        assert svc.get_state() == before
        published = [call.args[0] for call in bus.publish.call_args_list]
        assert "queue.changed" not in published
        assert published == ["queue.operation_failed"]

    def test_playback_failure_rolls_back_index(self):
        player = FakePlayer()
        svc = QueueService(player_service=player)
        svc.replace(_items("a", "b"))
        player.fail_play = True

        result = svc.play_from_index(1)

        assert not result["ok"]
        assert result["error"] == "PLAYBACK_FAILED"
        assert svc.current_index == 0
        assert player.index == 0

    def test_remove_and_reorder_keep_current_item(self):
        player = FakePlayer()
        svc = QueueService(player_service=player)
        svc.replace(_items("a", "b", "c"), start_index=1)

        assert svc.remove([0])["ok"]
        assert svc.current_index == 0
        assert svc.get_current()["title"] == "b"
        assert svc.reorder(0, 1)["ok"]
        assert svc.current_index == 1
        assert svc.get_current()["title"] == "b"

    def test_undo_restores_complete_domain_snapshot(self):
        player = FakePlayer()
        svc = QueueService(player_service=player)
        svc.replace(_items("a", "b"), start_index=1)
        svc.set_repeat("all")
        svc.set_shuffle(True)
        expected = svc.get_state()
        svc.clear()

        result = svc.undo()

        assert result["ok"]
        restored = svc.get_state()
        for key in ("items", "current_index", "repeat", "shuffle", "context"):
            assert restored[key] == expected[key]

    def test_backend_gapless_progress_reconciles_without_replaying(self):
        player = FakePlayer()
        svc = QueueService(player_service=player)
        svc.replace(_items("a", "b"))
        revision = svc.revision

        result = svc.reconcile_backend_progress(
            1, "/b.flac", "gapless", revision
        )
        duplicate = svc.reconcile_backend_progress(
            1, "/b.flac", "gapless", revision
        )

        assert result["ok"] and result["reconciled"]
        assert duplicate["ok"] and duplicate["ignored"]
        assert svc.current_index == 1
        assert player.played == []

    def test_backend_eos_uses_canonical_repeat_and_end_semantics(self):
        player = FakePlayer()
        svc = QueueService(player_service=player)
        svc.replace(_items("a", "b"))

        advanced = svc.reconcile_backend_progress(
            0, "/a.flac", "eos", svc.revision
        )
        ended = svc.reconcile_backend_progress(
            1, "/b.flac", "eos", svc.revision
        )

        assert advanced["ok"]
        assert svc.current_index == 1
        assert player.played == ["/b.flac"]
        assert ended["ok"] and ended["ended"]
        assert player.stopped is True

    def test_stale_backend_event_is_rejected(self):
        player = FakePlayer()
        svc = QueueService(player_service=player)
        svc.replace(_items("a", "b"))

        result = svc.reconcile_backend_progress(
            1, "/b.flac", "gapless", svc.revision - 1
        )

        assert not result["ok"]
        assert result["error"] == "STALE_EVENT"
        assert svc.current_index == 0

    def test_runtime_persistence_roundtrip_preserves_duplicate_token_order(
        self, tmp_path
    ):
        persistence = RuntimePersistence(base_dir=str(tmp_path))
        duplicate = {"track_uid": "same", "filepath": "/same.flac"}
        original = [duplicate, duplicate, {"filepath": "/other.flac"}]
        source = QueueService(runtime_persistence=persistence)
        source.replace(original, start_index=1)
        source.set_shuffle(True)
        effective_items = source.get_items()
        effective_tokens = list(source._item_tokens)
        original_order = list(source._shuffle_original_tokens)

        assert source.save_state()["ok"]
        payload = persistence.read("queue")
        assert payload["original_order"] == original_order
        assert "shuffle_original_tokens" not in payload

        restored = QueueService(runtime_persistence=persistence)
        assert restored.load_state()["ok"]
        assert restored.get_items() == effective_items
        assert restored._item_tokens == effective_tokens
        assert restored._shuffle_original_tokens == original_order
        assert restored.current_index == source.current_index
        assert restored.set_shuffle(False)["ok"]
        assert restored.get_items() == original

    def test_restore_syncs_without_autoplay_and_clears_undo(self, tmp_path):
        persistence = RuntimePersistence(base_dir=str(tmp_path))
        source = QueueService(runtime_persistence=persistence)
        source.replace(_items("a", "b"), start_index=1)
        source.save_state()
        player = RestorePlayer()
        restored = QueueService(
            player_service=player, runtime_persistence=persistence
        )
        restored.replace(_items("old"))

        result = restored.load_state()

        assert result["ok"]
        assert player.queue == ["/a.flac", "/b.flac"]
        assert player.index == 1
        assert player.played == []
        assert player.played_indices == []
        assert restored.can_undo is False
        assert restored.undo()["error"] == "NOTHING_TO_UNDO"

    def test_restore_empty_queue(self, tmp_path):
        persistence = RuntimePersistence(base_dir=str(tmp_path))
        QueueService(runtime_persistence=persistence).save_state()
        player = RestorePlayer()
        restored = QueueService(
            player_service=player, runtime_persistence=persistence
        )
        restored.replace(_items("old"))

        result = restored.load_state()

        assert result == {"ok": True, "count": 0}
        assert restored.get_items() == []
        assert restored.current_index == -1
        assert player.queue == []
        assert player.played == []

    def test_restore_sync_failure_rolls_back_domain(self, tmp_path):
        persistence = RuntimePersistence(base_dir=str(tmp_path))
        source = QueueService(runtime_persistence=persistence)
        source.replace(_items("saved"))
        source.save_state()
        player = FailOnceRestorePlayer()
        restored = QueueService(
            player_service=player, runtime_persistence=persistence
        )
        restored.replace(_items("current"))
        before = restored._capture_snapshot()
        player.fail_next_sync = True

        result = restored.load_state()

        assert not result["ok"]
        assert result["error"] == "BACKEND_SYNC_FAILED"
        assert restored._capture_snapshot() == before
        assert player.queue == ["/current.flac"]

    def test_invalid_saved_state_does_not_mutate_queue(self, tmp_path):
        persistence = RuntimePersistence(base_dir=str(tmp_path))
        persistence.write("queue", {
            "items": _items("saved"),
            "current_index": 4,
        })
        restored = QueueService(runtime_persistence=persistence)
        restored.replace(_items("current"))
        before = restored._capture_snapshot()

        result = restored.load_state()

        assert result["error"] == "INVALID_SAVED_STATE"
        assert restored._capture_snapshot() == before
