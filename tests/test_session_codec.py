"""M5.C2 / M4-R1 session snapshot codec — RED/GREEN tests (V2 + V1→V2).

The pure codec (encode_snapshot / decode_snapshot) is deterministic,
strict and backwards-migratable: malformed payloads decode to a fresh
snapshot (never a partial one), unknown extra keys are tolerated, and V1
payloads migrate to V2 (queue → queue_entries; valid old current_index →
QUEUE context; incoherent legacy playback path never fabricated).
"""

import json

import pytest

from michi.domain.playback_session import RepeatMode
from michi.domain.session import (
    FORMAT_VERSION,
    PersistedQueueEntry,
    PersistedSessionContext,
    PlaybackSessionSnapshot,
    decode_snapshot,
    encode_snapshot,
    fresh_snapshot,
)


def _full_snapshot() -> PlaybackSessionSnapshot:
    return PlaybackSessionSnapshot(
        format_version=FORMAT_VERSION,
        queue_entries=(
            PersistedQueueEntry(file_path="Q1", title="QAlpha"),
            PersistedQueueEntry(file_path="Q2", title="QBeta"),
        ),
        context=PersistedSessionContext(
            context_type="album",
            source_id="album-1",
            entries=(
                PersistedQueueEntry(file_path="X1", title="Alpha"),
                PersistedQueueEntry(file_path="X2", title="Beta"),
                PersistedQueueEntry(file_path="X1", title="Gamma"),
            ),
            current_index=2,
        ),
        playback_path="X1",
        position_ms=222000,
        repeat_mode=RepeatMode.ALL,
        shuffle_enabled=True,
        shuffle_seed=424242,
    )


def _base_payload() -> dict:
    return {
        "version": FORMAT_VERSION,
        "queue": [
            {"file_path": "Q1.mp3", "title": "QAlpha"},
            {"file_path": "Q2.mp3", "title": "QBeta"},
        ],
        "context": {
            "type": "album",
            "source_id": "album-1",
            "entries": [
                {"file_path": "A.mp3", "title": "Alpha"},
                {"file_path": "B.mp3", "title": "Beta"},
            ],
            "current_index": 1,
        },
        "playback_path": "B.mp3",
        "position_ms": 5000,
        "repeat_mode": "none",
        "shuffle_enabled": False,
        "shuffle_seed": 7,
    }


def _payload(**overrides) -> dict:
    payload = _base_payload()
    payload.update(overrides)
    return payload


def _v1_payload(**overrides) -> dict:
    payload = {
        "version": 1,
        "queue": [
            {"file_path": "A.mp3", "title": "Alpha"},
            {"file_path": "B.mp3", "title": "Beta"},
        ],
        "current_index": 1,
        "playback_path": "B.mp3",
        "position_ms": 5000,
        "repeat_mode": "none",
        "shuffle_enabled": False,
        "shuffle_seed": 7,
    }
    payload.update(overrides)
    return payload


def test_encode_decode_round_trip_full():
    snapshot = _full_snapshot()
    assert decode_snapshot(encode_snapshot(snapshot)) == snapshot


def test_encode_stable_values():
    encoded = encode_snapshot(_full_snapshot())
    assert '"repeat_mode": "all"' in encoded
    assert "RepeatMode.ALL" not in encoded
    assert f'"version": {FORMAT_VERSION}' in encoded
    assert '"type": "album"' in encoded

    assert decode_snapshot(json.dumps(_payload(repeat_mode="one"))).repeat_mode is (
        RepeatMode.ONE
    )
    assert decode_snapshot(json.dumps(_payload(repeat_mode="none"))).repeat_mode is (
        RepeatMode.NONE
    )


def test_encode_deterministic():
    snapshot = _full_snapshot()
    assert encode_snapshot(snapshot) == encode_snapshot(snapshot)


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        "[]",
        "{}",
        _payload(version=FORMAT_VERSION + 1),  # future version stays malformed
        _payload(version="1"),
        _payload(queue="x"),
        _payload(queue=[42]),
        _payload(queue=[{"file_path": 1, "title": "a"}]),
        _payload(queue=[{"file_path": "a"}]),
        _payload(context="x"),
        _payload(context={"type": "bogus"}),
        _payload(context={"type": "album", "entries": [], "current_index": 0}),
        _payload(position_ms=-1),
        _payload(position_ms="x"),
        _payload(repeat_mode="RepeatMode.ALL"),
        _payload(repeat_mode="sometimes"),
        _payload(shuffle_enabled="yes"),
        _payload(shuffle_seed="abc"),
        _payload(shuffle_seed=None),
        {k: v for k, v in _payload().items() if k != "shuffle_seed"},
    ],
)
def test_decode_fresh_on_malformed(payload):
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    assert decode_snapshot(raw) == fresh_snapshot()


def test_decode_tolerates_extra_keys():
    snapshot = decode_snapshot(json.dumps(_payload(future_field="x")))
    assert snapshot == decode_snapshot(json.dumps(_base_payload()))
    assert snapshot.context.current_index == 1
    assert snapshot.repeat_mode is RepeatMode.NONE


def test_decode_null_playback_path():
    snapshot = decode_snapshot(json.dumps(_payload(playback_path=None)))
    assert snapshot.playback_path is None


def test_decode_incoherent_playback_path_not_fabricated():
    # playback_path does not match the session current entry → dropped
    snapshot = decode_snapshot(json.dumps(_payload(playback_path="NOT_IN_CONTEXT.mp3")))
    assert snapshot.playback_path is None
    assert snapshot.position_ms == 0


def test_fresh_snapshot_defaults():
    snapshot = fresh_snapshot()
    assert snapshot.format_version == FORMAT_VERSION
    assert snapshot.queue_entries == ()
    assert snapshot.context.context_type == "none"
    assert snapshot.context.current_index == -1
    assert snapshot.playback_path is None
    assert snapshot.position_ms == 0
    assert snapshot.repeat_mode is RepeatMode.NONE
    assert snapshot.shuffle_enabled is False
    assert snapshot.shuffle_seed == 0


def test_decode_index_negative_allowed():
    snapshot = decode_snapshot(json.dumps(_payload(context=_base_payload()["context"])))
    assert snapshot.context.current_index == 1


# ---------------------------------------------------------------------------
# V1 → V2 migration
# ---------------------------------------------------------------------------


def test_v1_valid_queue_session_migrates_to_queue_context():
    snapshot = decode_snapshot(json.dumps(_v1_payload()))
    assert snapshot.format_version == FORMAT_VERSION
    assert snapshot.queue_entries == (
        PersistedQueueEntry("A.mp3", "Alpha"),
        PersistedQueueEntry("B.mp3", "Beta"),
    )
    assert snapshot.context.context_type == "queue"
    assert snapshot.context.current_index == 1
    # coherent legacy playback path preserved
    assert snapshot.playback_path == "B.mp3"
    assert snapshot.position_ms == 5000


def test_v1_current_index_minus_one_migrates_to_none_context():
    snapshot = decode_snapshot(json.dumps(_v1_payload(current_index=-1)))
    assert snapshot.context.context_type == "none"
    assert snapshot.context.current_index == -1
    assert snapshot.context.entries == ()
    assert snapshot.playback_path is None  # never fabricated
    assert snapshot.position_ms == 0
    # Queue content NOT lost
    assert len(snapshot.queue_entries) == 2


def test_v1_incoherent_playback_path_not_fabricated():
    snapshot = decode_snapshot(json.dumps(_v1_payload(playback_path="NOPE.mp3")))
    assert snapshot.playback_path is None
    assert snapshot.position_ms == 0
    assert snapshot.context.context_type == "queue"
    assert snapshot.context.current_index == 1  # queue content preserved


def test_v1_malformed_fresh():
    assert decode_snapshot(json.dumps(_v1_payload(current_index=9))) == fresh_snapshot()
    assert decode_snapshot(json.dumps(_v1_payload(queue=[42]))) == fresh_snapshot()
    assert decode_snapshot(json.dumps(_v1_payload(repeat_mode="x"))) == fresh_snapshot()


def test_v1_duplicates_preserved():
    payload = _v1_payload(
        queue=[
            {"file_path": "A.mp3", "title": "Alpha"},
            {"file_path": "B.mp3", "title": "Beta"},
            {"file_path": "A.mp3", "title": "Alpha2"},
        ],
        current_index=2,
    )
    snapshot = decode_snapshot(json.dumps(payload))
    assert len(snapshot.queue_entries) == 3
    assert snapshot.context.entries[2].file_path == "A.mp3"
