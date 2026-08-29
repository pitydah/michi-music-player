"""M6-EXT-R4-I — queue / sequence / session V3 stable library identity."""

import json

from michi.domain.playback_session import (
    PlaybackSequenceEntry,
    RepeatMode,
)
from michi.domain.queue import Track
from michi.domain.session import (
    FORMAT_VERSION,
    PersistedQueueEntry,
    PersistedSessionContext,
    PlaybackSessionSnapshot,
    decode_snapshot,
    encode_snapshot,
    fresh_snapshot,
)


class TestDomainCarriers:
    def test_queue_track_carries_optional_library_id(self) -> None:
        track = Track(Path("/a.flac"), library_track_id="T1")
        assert track.entry_id  # runtime identity still generated
        assert track.library_track_id == "T1"

    def test_two_entries_same_library_id_distinct_entry_ids(self) -> None:
        first = Track(Path("/a.flac"), library_track_id="T1")
        second = Track(Path("/a.flac"), library_track_id="T1")
        assert first.entry_id != second.entry_id
        assert first.library_track_id == second.library_track_id == "T1"

    def test_sequence_entry_carries_optional_library_id(self) -> None:
        entry = PlaybackSequenceEntry(Path("/a.flac"), "A", library_track_id="T1")
        assert entry.library_track_id == "T1"

    def test_legacy_positional_construction_still_works(self) -> None:
        entry = PersistedQueueEntry("/a.flac", "A")
        assert entry.library_track_id is None


class TestSessionV3Codec:
    def test_encode_emits_v3_with_library_ids(self) -> None:
        snapshot = PlaybackSessionSnapshot(
            format_version=FORMAT_VERSION,
            queue_entries=(
                PersistedQueueEntry("/a.flac", "A", "T1"),
                PersistedQueueEntry("/b.flac", "B", None),
            ),
            context=PersistedSessionContext(
                context_type="queue", source_id=None, entries=(), current_index=-1
            ),
            playback_path=None,
            position_ms=0,
            repeat_mode=RepeatMode.NONE,
            shuffle_enabled=False,
            shuffle_seed=0,
        )
        payload = json.loads(encode_snapshot(snapshot))
        assert payload["version"] == 3
        assert payload["queue"][0] == {
            "library_track_id": "T1",
            "fallback_path": "/a.flac",
            "title": "A",
        }
        assert payload["queue"][1]["library_track_id"] is None

    def test_v3_decode_restores_library_ids(self) -> None:
        payload = {
            "version": 3,
            "queue": [
                {"library_track_id": "T1", "fallback_path": "/a.flac", "title": "A"}
            ],
            "context": {
                "type": "queue",
                "source_id": None,
                "entries": [
                    {
                        "library_track_id": "T1",
                        "fallback_path": "/a.flac",
                        "title": "A",
                    }
                ],
                "current_index": 0,
            },
            "playback_path": "/a.flac",
            "position_ms": 1200,
            "repeat_mode": "none",
            "shuffle_enabled": False,
            "shuffle_seed": 0,
        }
        snapshot = decode_snapshot(json.dumps(payload))
        assert snapshot.format_version == 3
        assert snapshot.queue_entries[0].library_track_id == "T1"
        assert snapshot.context.entries[0].library_track_id == "T1"
        assert snapshot.playback_path == "/a.flac"

    def test_v2_decode_maps_paths_without_library_ids(self) -> None:
        payload = {
            "version": 2,
            "queue": [{"file_path": "/a.flac", "title": "A"}],
            "context": {
                "type": "none",
                "source_id": None,
                "entries": [],
                "current_index": -1,
            },
            "playback_path": None,
            "position_ms": 0,
            "repeat_mode": "none",
            "shuffle_enabled": False,
            "shuffle_seed": 0,
        }
        snapshot = decode_snapshot(json.dumps(payload))
        assert snapshot.queue_entries == (PersistedQueueEntry("/a.flac", "A"),)

    def test_v1_decode_still_migrates(self) -> None:
        payload = {
            "version": 1,
            "queue": [{"file_path": "/a.flac", "title": "A"}],
            "current_index": 0,
            "playback_path": "/a.flac",
            "position_ms": 500,
            "repeat_mode": "none",
            "shuffle_enabled": False,
            "shuffle_seed": 0,
        }
        snapshot = decode_snapshot(json.dumps(payload))
        assert snapshot.context.context_type == "queue"
        assert snapshot.queue_entries[0].library_track_id is None
        assert snapshot.playback_path == "/a.flac"

    def test_roundtrip_preserves_library_ids(self) -> None:
        snapshot = PlaybackSessionSnapshot(
            format_version=FORMAT_VERSION,
            queue_entries=(PersistedQueueEntry("/a.flac", "A", "T1"),),
            context=PersistedSessionContext(
                context_type="queue",
                source_id=None,
                entries=(PersistedQueueEntry("/a.flac", "A", "T1"),),
                current_index=0,
            ),
            playback_path="/a.flac",
            position_ms=300,
            repeat_mode=RepeatMode.ONE,
            shuffle_enabled=True,
            shuffle_seed=7,
        )
        decoded = decode_snapshot(encode_snapshot(snapshot))
        assert decoded == snapshot

    def test_malformed_v3_entry_rejects_whole_snapshot(self) -> None:
        payload = {
            "version": 3,
            "queue": [{"fallback_path": "/a.flac", "title": "A"}],  # missing id
            "context": {
                "type": "none",
                "source_id": None,
                "entries": [],
                "current_index": -1,
            },
            "playback_path": None,
            "position_ms": 0,
            "repeat_mode": "none",
            "shuffle_enabled": False,
            "shuffle_seed": 0,
        }
        assert decode_snapshot(json.dumps(payload)) == fresh_snapshot()


class TestQueueToSessionIdentity:
    def test_queue_conversion_preserves_library_id(self) -> None:
        from michi.application.playback_session_service import (
            PlaybackSessionService,
        )
        from michi.application.queue_service import QueueService

        queue = QueueService()
        queue.add(Path("/a.flac"), "A", library_track_id="T1")
        session = PlaybackSessionService(playback_service=None, queue_service=queue)
        entries = session._queue_entries()
        assert entries[0].library_track_id == "T1"
        assert entries[0].entry_id == queue.state.tracks[0].entry_id


def Path(p):  # noqa: N802 - local helper keeps test body readable
    from pathlib import Path as _Path

    return _Path(p)
