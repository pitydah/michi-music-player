"""Domain layer — persisted playback session snapshot. Pure: no Qt,
no sqlite3, no filesystem (json is fine).

The snapshot is the durable encoding of "what the player looked like
last time" (queue, current index, playback position, repeat/shuffle
state). The pure codec is deterministic, strict and backwards-migratable:
malformed payloads decode to a fresh snapshot (never a partial one);
unknown extra keys are tolerated so future fields do not break old
builds. Repeat modes persist as stable strings ("none"/"one"/"all"),
never as Python enum representations.
"""

import json
from dataclasses import dataclass

from michi.domain.queue import RepeatMode

FORMAT_VERSION = 1

# Stable serialized representations — part of the on-disk contract.
_REPEAT_MODE_TO_STRING = {
    RepeatMode.NONE: "none",
    RepeatMode.ONE: "one",
    RepeatMode.ALL: "all",
}
_STRING_TO_REPEAT_MODE = {
    string: mode for mode, string in _REPEAT_MODE_TO_STRING.items()
}

# Sentinel distinguishing "key present with null" from "key missing".
_MISSING = object()


@dataclass(frozen=True)
class PersistedQueueEntry:
    file_path: str
    title: str


@dataclass(frozen=True)
class PlaybackSessionSnapshot:
    format_version: int
    queue_entries: tuple[PersistedQueueEntry, ...]
    queue_current_index: int
    playback_path: str | None
    position_ms: int
    repeat_mode: RepeatMode
    shuffle_enabled: bool
    shuffle_seed: int


def fresh_snapshot() -> PlaybackSessionSnapshot:
    """A snapshot representing "no session yet"."""
    return PlaybackSessionSnapshot(
        format_version=FORMAT_VERSION,
        queue_entries=(),
        queue_current_index=-1,
        playback_path=None,
        position_ms=0,
        repeat_mode=RepeatMode.NONE,
        shuffle_enabled=False,
        shuffle_seed=0,
    )


def _is_strict_int(value: object) -> bool:
    """True for JSON integers only — bools are not accepted as ints."""
    return isinstance(value, int) and not isinstance(value, bool)


def encode_snapshot(snapshot: PlaybackSessionSnapshot) -> str:
    """Encode a snapshot as deterministic JSON.

    Key order is stable (``sort_keys=True``) so equal snapshots always
    encode to byte-identical strings; this also makes the persisted row
    a stable target for row-level comparisons.
    """
    payload = {
        "version": snapshot.format_version,
        "queue": [
            {"file_path": entry.file_path, "title": entry.title}
            for entry in snapshot.queue_entries
        ],
        "current_index": snapshot.queue_current_index,
        "playback_path": snapshot.playback_path,
        "position_ms": snapshot.position_ms,
        "repeat_mode": _REPEAT_MODE_TO_STRING[snapshot.repeat_mode],
        "shuffle_enabled": snapshot.shuffle_enabled,
        "shuffle_seed": snapshot.shuffle_seed,
    }
    return json.dumps(payload, sort_keys=True)


def decode_snapshot(raw: str) -> PlaybackSessionSnapshot:
    """Strictly decode a persisted snapshot.

    Every aspect is validated independently; ANY invalid aspect yields a
    fresh snapshot (never a partial one). Missing required keys are
    invalid; unknown extra keys are tolerated (backwards-migratable).
    This function is pure — the caller decides how to surface a warning.
    """
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        return fresh_snapshot()
    if not isinstance(payload, dict):
        return fresh_snapshot()

    version = payload.get("version", _MISSING)
    if not _is_strict_int(version) or version != FORMAT_VERSION:
        return fresh_snapshot()

    queue_raw = payload.get("queue", _MISSING)
    if not isinstance(queue_raw, list):
        return fresh_snapshot()
    entries: list[PersistedQueueEntry] = []
    for item in queue_raw:
        if not isinstance(item, dict):
            return fresh_snapshot()
        file_path = item.get("file_path", _MISSING)
        title = item.get("title", _MISSING)
        if not isinstance(file_path, str) or not isinstance(title, str):
            return fresh_snapshot()
        entries.append(PersistedQueueEntry(file_path=file_path, title=title))

    current_index = payload.get("current_index", _MISSING)
    if not _is_strict_int(current_index):
        return fresh_snapshot()
    if current_index != -1 and not 0 <= current_index < len(entries):
        return fresh_snapshot()

    playback_path = payload.get("playback_path", _MISSING)
    if not (playback_path is None or isinstance(playback_path, str)):
        return fresh_snapshot()

    position_ms = payload.get("position_ms", _MISSING)
    if not _is_strict_int(position_ms) or position_ms < 0:
        return fresh_snapshot()

    repeat_raw = payload.get("repeat_mode", _MISSING)
    if not isinstance(repeat_raw, str) or repeat_raw not in _STRING_TO_REPEAT_MODE:
        return fresh_snapshot()

    shuffle_enabled = payload.get("shuffle_enabled", _MISSING)
    if not isinstance(shuffle_enabled, bool):
        return fresh_snapshot()

    shuffle_seed = payload.get("shuffle_seed", _MISSING)
    if not _is_strict_int(shuffle_seed):
        return fresh_snapshot()

    return PlaybackSessionSnapshot(
        format_version=version,
        queue_entries=tuple(entries),
        queue_current_index=current_index,
        playback_path=playback_path,
        position_ms=position_ms,
        repeat_mode=_STRING_TO_REPEAT_MODE[repeat_raw],
        shuffle_enabled=shuffle_enabled,
        shuffle_seed=shuffle_seed,
    )
