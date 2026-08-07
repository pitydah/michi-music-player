"""Queue authority: QueueService is canonical; the MPD backend syncs from it.

Per AGENTS.md the queue is canonical in Michi and synced to MPD when the MPD
backend is active. This test asserts that the chain
QueueService -> PlayerService.play_queue -> backend.set_queue carries the
canonical queue into the MPD backend (no independent queue authority), and
that MpdBackend.set_queue translates it to MPD playlist commands.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from audio.backends.mpd_backend import MpdBackend


class FakeQueuePlayer:
    """PlayerService facade that records queue pushes from QueueService."""

    def __init__(self, backend):
        self.backend = backend
        self.synced_queues: list[tuple[list, int]] = []

    def play_queue(self, filepaths, start_index=0, revision=None):
        self.synced_queues.append((list(filepaths), start_index))
        self.backend.set_queue(list(filepaths), start_index, revision=revision)

    def clear_queue(self):
        self.backend.clear_queue()

    def set_repeat(self, mode):
        pass

    def set_shuffle(self, enabled):
        pass


@pytest.fixture()
def mock_client():
    client = MagicMock()
    client.clear = MagicMock()
    client.add = MagicMock()
    client.random = MagicMock()
    return client


def _make_backend(mock_client):
    backend = MpdBackend(host="127.0.0.1", port=6600)
    backend._client = mock_client
    backend._mapper = MagicMock()
    backend._mapper.to_mpd_path = lambda p: "/music/" + p.rsplit("/", 1)[-1]
    return backend


class TestMpdQueueSync:
    def test_queue_service_is_single_source(self, mock_client):
        """QueueService drives the backend; the backend keeps no parallel queue."""
        backend = _make_backend(mock_client)
        player = FakeQueuePlayer(backend)

        from core.queue_service import QueueService

        qs = QueueService(player_service=player)
        result = qs.replace([
            {"filepath": "/home/user/Music/a.flac"},
            {"filepath": "/home/user/Music/b.flac"},
        ], start_index=1)
        assert result.get("ok") is True
        assert player.synced_queues, "QueueService must push the queue to the player"
        paths, index = player.synced_queues[-1]
        assert paths == ["/home/user/Music/a.flac", "/home/user/Music/b.flac"]
        assert index == 1

        # Backend state mirrors the canonical push — mapped to MPD paths.
        assert backend._queue_index == 1
        assert backend._local_paths == [
            "/home/user/Music/a.flac", "/home/user/Music/b.flac"]

    def test_mpd_backend_translates_canonical_queue_to_playlist(
            self, mock_client):
        backend = _make_backend(mock_client)
        backend.set_queue(["/home/user/Music/a.flac", "/home/user/Music/b.flac"],
                          start_index=0, revision=7)
        mock_client.clear.assert_called_once()
        assert mock_client.add.call_count == 2
        added = [call.args[0] for call in mock_client.add.call_args_list]
        assert added == ["/music/a.flac", "/music/b.flac"]

    def test_mpd_backend_queue_mirrors_queue_service_revision(self, mock_client):
        backend = _make_backend(mock_client)
        backend.set_queue(["/x/1.flac"], start_index=0, revision=42)
        assert backend._queue_revision == 42

    def test_clear_queue_from_canonical_source(self, mock_client):
        backend = _make_backend(mock_client)
        player = FakeQueuePlayer(backend)
        from core.queue_service import QueueService

        qs = QueueService(player_service=player)
        qs.replace([{"filepath": "/a.flac"}])
        mock_client.clear.assert_called()
        mock_client.clear.reset_mock()
        qs.clear()
        mock_client.clear.assert_called()
        assert backend._local_paths == []
        assert backend._queue_index == -1
