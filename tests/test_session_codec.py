"""M5.C2 session snapshot codec — RED/GREEN tests.

The pure codec (encode_snapshot / decode_snapshot) is deterministic,
strict and backwards-migratable: malformed payloads decode to a fresh
snapshot (never a partial one), while unknown extra keys are tolerated.
Repeat modes persist as stable strings ("none"/"one"/"all"), never as
Python enum representations.
"""

import json

import pytest

from michi.domain.queue import RepeatMode
from michi.domain.session import (
    PersistedQueueEntry,
    PlaybackSessionSnapshot,
    decode_snapshot,
    encode_snapshot,
    fresh_snapshot,
)


def _full_snapshot() -> PlaybackSessionSnapshot:
    return PlaybackSessionSnapshot(
        format_version=1,
        queue_entries=(
            PersistedQueueEntry(file_path="X1", title="Alpha"),
            PersistedQueueEntry(file_path="X2", title="Beta"),
            PersistedQueueEntry(file_path="X1", title="Gamma"),
        ),
        queue_current_index=2,
        playback_path="X2",
        position_ms=222000,
        repeat_mode=RepeatMode.ALL,
        shuffle_enabled=True,
        shuffle_seed=424242,
    )


def _base_payload() -> dict:
    return {
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


def _payload(**overrides) -> dict:
    payload = _base_payload()
    payload.update(overrides)
    return payload


def test_encode_decode_round_trip_full():
    snapshot = _full_snapshot()
    assert decode_snapshot(encode_snapshot(snapshot)) == snapshot


def test_encode_stable_values():
    encoded = encode_snapshot(_full_snapshot())
    assert '"repeat_mode": "all"' in encoded
    assert "RepeatMode.ALL" not in encoded
    assert '"version": 1' in encoded

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
        _payload(version=2),
        _payload(version="1"),
        _payload(queue="x"),
        _payload(queue=[42]),
        _payload(queue=[{"file_path": 1, "title": "a"}]),
        _payload(queue=[{"file_path": "a"}]),
        _payload(current_index=5),
        _payload(current_index="1"),
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
    assert snapshot.queue_current_index == 1
    assert snapshot.repeat_mode is RepeatMode.NONE


def test_decode_null_playback_path():
    snapshot = decode_snapshot(json.dumps(_payload(playback_path=None)))
    assert snapshot.playback_path is None


def test_fresh_snapshot_defaults():
    snapshot = fresh_snapshot()
    assert snapshot.format_version == 1
    assert snapshot.queue_entries == ()
    assert snapshot.queue_current_index == -1
    assert snapshot.playback_path is None
    assert snapshot.position_ms == 0
    assert snapshot.repeat_mode is RepeatMode.NONE
    assert snapshot.shuffle_enabled is False
    assert snapshot.shuffle_seed == 0


def test_decode_index_negative_allowed():
    snapshot = decode_snapshot(json.dumps(_payload(current_index=-1)))
    assert snapshot.queue_current_index == -1
