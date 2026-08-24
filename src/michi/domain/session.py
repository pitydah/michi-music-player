"""Domain layer — persisted playback session snapshot (M4-R1, V2).

Pure: no Qt, no sqlite3, no filesystem (json is fine).

The snapshot is the durable encoding of "what the player looked like
last time": QUEUE CONTENT (temporary user list), PLAYBACK CONTEXT (the
active PlaybackSession: context type / source id / context entries /
current index), PLAYBACK (path + position), and SESSION NAVIGATION
(repeat / shuffle / seed). The pure codec is deterministic, strict and
backwards-migratable: malformed payloads decode to a fresh snapshot
(never a partial one); unknown extra keys are tolerated; V1 snapshots
migrate to V2 (old queue becomes queue_entries; a valid old
current_index becomes a QUEUE context; an incoherent legacy playback
path is never fabricated).
"""

import json
from dataclasses import dataclass

from michi.domain.playback_session import (
    PlaybackContextType,
    RepeatMode,
)

FORMAT_VERSION = 2
V1_FORMAT_VERSION = 1

# Stable serialized representations — part of the on-disk contract.
_REPEAT_MODE_TO_STRING = {
    RepeatMode.NONE: "none",
    RepeatMode.ONE: "one",
    RepeatMode.ALL: "all",
}
_STRING_TO_REPEAT_MODE = {
    string: mode for mode, string in _REPEAT_MODE_TO_STRING.items()
}

_CONTEXT_TYPE_TO_STRING = {
    PlaybackContextType.NONE: "none",
    PlaybackContextType.SINGLE: "single",
    PlaybackContextType.ALBUM: "album",
    PlaybackContextType.PLAYLIST: "playlist",
    PlaybackContextType.QUEUE: "queue",
}
_STRING_TO_CONTEXT_TYPE = {
    string: context for context, string in _CONTEXT_TYPE_TO_STRING.items()
}

# Sentinel distinguishing "key present with null" from "key missing".
_MISSING = object()


@dataclass(frozen=True)
class PersistedQueueEntry:
    file_path: str
    title: str


@dataclass(frozen=True)
class PersistedSessionContext:
    """The durable playback-context portion (V2)."""

    context_type: str  # canonical string: "none"/"single"/"album"/"playlist"/"queue"
    source_id: str | None
    entries: tuple[PersistedQueueEntry, ...]
    current_index: int


@dataclass(frozen=True)
class PlaybackSessionSnapshot:
    format_version: int
    queue_entries: tuple[PersistedQueueEntry, ...]
    context: PersistedSessionContext
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
        context=PersistedSessionContext(
            context_type="none", source_id=None, entries=(), current_index=-1
        ),
        playback_path=None,
        position_ms=0,
        repeat_mode=RepeatMode.NONE,
        shuffle_enabled=False,
        shuffle_seed=0,
    )


def _is_strict_int(value: object) -> bool:
    """True for JSON integers only — bools are not accepted as ints."""
    return isinstance(value, int) and not isinstance(value, bool)


def _entry_to_dict(entry: PersistedQueueEntry) -> dict:
    return {"file_path": entry.file_path, "title": entry.title}


def _decode_entries(raw: object) -> tuple[PersistedQueueEntry, ...] | None:
    if not isinstance(raw, list):
        return None
    entries: list[PersistedQueueEntry] = []
    for item in raw:
        if not isinstance(item, dict):
            return None
        file_path = item.get("file_path", _MISSING)
        title = item.get("title", _MISSING)
        if not isinstance(file_path, str) or not isinstance(title, str):
            return None
        entries.append(PersistedQueueEntry(file_path=file_path, title=title))
    return tuple(entries)


def encode_snapshot(snapshot: PlaybackSessionSnapshot) -> str:
    """Encode a snapshot as deterministic JSON (stable key order)."""
    payload = {
        "version": snapshot.format_version,
        "queue": [_entry_to_dict(e) for e in snapshot.queue_entries],
        "context": {
            "type": snapshot.context.context_type,
            "source_id": snapshot.context.source_id,
            "entries": [_entry_to_dict(e) for e in snapshot.context.entries],
            "current_index": snapshot.context.current_index,
        },
        "playback_path": snapshot.playback_path,
        "position_ms": snapshot.position_ms,
        "repeat_mode": _REPEAT_MODE_TO_STRING[snapshot.repeat_mode],
        "shuffle_enabled": snapshot.shuffle_enabled,
        "shuffle_seed": snapshot.shuffle_seed,
    }
    return json.dumps(payload, sort_keys=True)


def decode_snapshot(raw: str) -> PlaybackSessionSnapshot:
    """Strictly decode a persisted snapshot (V2 native; V1 migrated).

    Every aspect is validated independently; ANY invalid aspect yields a
    fresh snapshot (never a partial one). Missing required keys are
    invalid; unknown extra keys are tolerated. V1 payloads migrate:
    queue_entries = old queue; valid old current_index → QUEUE context;
    current_index == -1 → NONE context; a legacy playback_path is
    preserved for resume ONLY when it matches the migrated session current
    entry (otherwise playback_path=None, position=0).
    """
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        return fresh_snapshot()
    if not isinstance(payload, dict):
        return fresh_snapshot()

    version = payload.get("version", _MISSING)
    if not _is_strict_int(version):
        return fresh_snapshot()

    if version == V1_FORMAT_VERSION:
        return _decode_v1(payload)
    if version != FORMAT_VERSION:
        return fresh_snapshot()

    # --- V2 native decode -------------------------------------------
    queue_raw = payload.get("queue", _MISSING)
    queue_entries = _decode_entries(queue_raw)
    if queue_entries is None:
        return fresh_snapshot()

    context_raw = payload.get("context", _MISSING)
    if not isinstance(context_raw, dict):
        return fresh_snapshot()
    context_type = context_raw.get("type", _MISSING)
    if not isinstance(context_type, str) or context_type not in _STRING_TO_CONTEXT_TYPE:
        return fresh_snapshot()
    source_id = context_raw.get("source_id", _MISSING)
    if not (source_id is None or isinstance(source_id, str)):
        return fresh_snapshot()
    ctx_entries = _decode_entries(context_raw.get("entries", _MISSING))
    if ctx_entries is None:
        return fresh_snapshot()
    current_index = context_raw.get("current_index", _MISSING)
    if not _is_strict_int(current_index):
        return fresh_snapshot()
    if current_index != -1 and not 0 <= current_index < len(ctx_entries):
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

    # V2 playback coherence: never fabricate a playback identity the session
    # context does not confirm.
    if playback_path is not None:
        coherent = (
            0 <= current_index < len(ctx_entries)
            and ctx_entries[current_index].file_path == playback_path
        )
        if not coherent:
            playback_path = None
            position_ms = 0

    return PlaybackSessionSnapshot(
        format_version=version,
        queue_entries=queue_entries,
        context=PersistedSessionContext(
            context_type=context_type,
            source_id=source_id,
            entries=ctx_entries,
            current_index=current_index,
        ),
        playback_path=playback_path,
        position_ms=position_ms,
        repeat_mode=_STRING_TO_REPEAT_MODE[repeat_raw],
        shuffle_enabled=shuffle_enabled,
        shuffle_seed=shuffle_seed,
    )


def _decode_v1(payload: dict) -> PlaybackSessionSnapshot:
    """Migrate a V1 snapshot to V2 (strict; any invalid aspect → fresh)."""
    queue_raw = payload.get("queue", _MISSING)
    queue_entries = _decode_entries(queue_raw)
    if queue_entries is None:
        return fresh_snapshot()

    current_index = payload.get("current_index", _MISSING)
    if not _is_strict_int(current_index):
        return fresh_snapshot()
    if current_index != -1 and not 0 <= current_index < len(queue_entries):
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

    # Migration rule: valid old current_index → QUEUE context; -1 → NONE.
    if current_index >= 0:
        context_type = "queue"
        ctx_entries = queue_entries
        ctx_index = current_index
        coherent = (
            playback_path is not None
            and 0 <= current_index < len(queue_entries)
            and queue_entries[current_index].file_path == playback_path
        )
        if not coherent:
            # Do not fabricate a V2 playback context from incoherent legacy
            # data: keep the QUEUE content but no playback path/position.
            playback_path = None
            position_ms = 0
    else:
        context_type = "none"
        ctx_entries = ()
        ctx_index = -1
        playback_path = None
        position_ms = 0

    return PlaybackSessionSnapshot(
        format_version=FORMAT_VERSION,
        queue_entries=queue_entries,
        context=PersistedSessionContext(
            context_type=context_type,
            source_id=None,
            entries=ctx_entries,
            current_index=ctx_index,
        ),
        playback_path=playback_path,
        position_ms=position_ms,
        repeat_mode=_STRING_TO_REPEAT_MODE[repeat_raw],
        shuffle_enabled=shuffle_enabled,
        shuffle_seed=shuffle_seed,
    )
