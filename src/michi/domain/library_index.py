"""Persistent library index domain model + strict metadata codec (M6.2).

The index is cached/persisted knowledge about library files — the
FILESYSTEM is the truth about physical existence; the index never is.
"""

import json
from dataclasses import asdict, dataclass

from michi.domain.library import TrackMetadata


@dataclass(frozen=True)
class LibraryIndexEntry:
    """One persisted per-file record: canonical track identity + filesystem
    fingerprint + the full metadata carrier (the canonical identity inputs
    are the metadata fields themselves)."""

    track_id: str
    file_size: int
    mtime_ns: int
    metadata: TrackMetadata


_STR_FIELDS = {
    name for name, f in TrackMetadata.__dataclass_fields__.items() if f.type is str
}
_INT_FIELDS = {
    name for name, f in TrackMetadata.__dataclass_fields__.items() if f.type is int
}
_BOOL_FIELDS = {
    name for name, f in TrackMetadata.__dataclass_fields__.items() if f.type is bool
}


def encode_index_metadata(meta: TrackMetadata) -> str:
    """Deterministic strict JSON of the full metadata carrier."""
    return json.dumps(asdict(meta), sort_keys=True)


def decode_index_metadata(raw: str) -> TrackMetadata | None:
    """Strict decode: every known field must be present with the correct
    type; extra unknown keys are tolerated (future-proof). Any violation
    returns None — the caller logs and skips the row (a malformed row never
    crashes and never fabricates partial metadata)."""
    try:
        payload = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    kwargs = {}
    for name, value in payload.items():
        if name not in TrackMetadata.__dataclass_fields__:
            continue  # future field — tolerated
        if name in _STR_FIELDS:
            if not isinstance(value, str):
                return None
        elif name in _INT_FIELDS:
            if isinstance(value, bool) or not isinstance(value, int):
                return None
        elif name in _BOOL_FIELDS:
            if not isinstance(value, bool):
                return None
        else:
            return None  # unknown field type in this build
        kwargs[name] = value
    if set(kwargs) != set(TrackMetadata.__dataclass_fields__):
        return None  # missing field(s)
    return TrackMetadata(**kwargs)
