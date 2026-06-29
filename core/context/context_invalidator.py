"""Context invalidator — maps events to dirty flags for derived summaries."""

from __future__ import annotations

from core.context.context_events import AppEvent
from core.context import context_repository as repo

_EVENT_DIRTY_MAP: dict[str, set[str]] = {
    AppEvent.SCAN_FINISHED: {"home_snapshot", "assistant_snapshot", "mix_preview", "library_health"},
    AppEvent.TRACK_PLAYED: {"home_snapshot", "assistant_snapshot", "mix_preview", "playback_context"},
    AppEvent.TRACK_PAUSED: {"playback_context"},
    AppEvent.TRACK_FAVORITED: {"home_snapshot", "assistant_snapshot", "mix_preview"},
    AppEvent.TRACK_UNFAVORITED: {"home_snapshot", "assistant_snapshot", "mix_preview"},
    AppEvent.SYNC_FINISHED: {"home_snapshot", "assistant_snapshot", "sync_context"},
    AppEvent.DEVICE_CONNECTED: {"home_snapshot", "assistant_snapshot", "sync_context"},
    AppEvent.DEVICE_DISCONNECTED: {"home_snapshot", "assistant_snapshot", "sync_context"},
    AppEvent.AUDIO_ANALYSIS_FINISHED: {"assistant_snapshot", "mix_preview", "library_health"},
    AppEvent.SECTION_CHANGED: {"assistant_snapshot"},
    AppEvent.LIBRARY_TAB_CHANGED: {"assistant_snapshot"},
    AppEvent.TRACK_SELECTED: {"assistant_snapshot"},
    AppEvent.SELECTION_CHANGED: {"assistant_snapshot"},
    AppEvent.MIX_PREVIEW_GENERATED: {"mix_preview"},
    AppEvent.METADATA_REPAIR_FINISHED: {"home_snapshot", "assistant_snapshot", "library_health"},
    AppEvent.APP_STARTED: {"home_snapshot", "assistant_snapshot", "library_health", "playback_context", "sync_context"},

    AppEvent.ASSISTANT_OPENED: {"assistant_snapshot"},
    AppEvent.ASSISTANT_ACTION_CONFIRMED: {"assistant_snapshot", "home_snapshot", "mix_preview"},

    AppEvent.LIBRARY_RELOADED: {"home_snapshot", "assistant_snapshot", "mix_preview", "library_health"},
    AppEvent.IMPORT_STARTED: {"assistant_snapshot"},
    AppEvent.IMPORT_FINISHED: {"home_snapshot", "assistant_snapshot", "mix_preview", "library_health"},
    AppEvent.SCAN_STARTED: {"assistant_snapshot"},

    AppEvent.METADATA_SAVED: {"home_snapshot", "assistant_snapshot", "library_health"},

    AppEvent.PLAYBACK_STARTED: {"home_snapshot", "assistant_snapshot", "playback_context"},
    AppEvent.PLAYBACK_STOPPED: {"home_snapshot", "assistant_snapshot", "playback_context"},
    AppEvent.NOW_PLAYING_UPDATED: {"home_snapshot", "assistant_snapshot", "playback_context"},
    AppEvent.QUALITY_UPDATED: {"assistant_snapshot", "playback_context"},
    AppEvent.AUDIO_ROUTE_CHANGED: {"assistant_snapshot", "playback_context"},

    AppEvent.PLAYLIST_OPENED: {"assistant_snapshot"},
    AppEvent.PLAYLIST_CREATED: {"home_snapshot", "assistant_snapshot", "mix_preview"},
    AppEvent.PLAYLIST_DELETED: {"home_snapshot", "assistant_snapshot", "mix_preview"},
    AppEvent.PLAYLIST_PLAYED: {"home_snapshot", "assistant_snapshot", "playback_context"},
    AppEvent.PLAYLIST_QUEUED: {"assistant_snapshot", "playback_context"},
    AppEvent.PLAYLIST_IMPORTED: {"home_snapshot", "assistant_snapshot", "library_health"},
    AppEvent.PLAYLIST_EXPORTED: {"assistant_snapshot"},
    AppEvent.TRACK_ADDED_TO_PLAYLIST: {"assistant_snapshot"},

    AppEvent.MIX_OPENED: {"assistant_snapshot", "mix_preview"},
    AppEvent.MIX_PLAYED: {"home_snapshot", "assistant_snapshot", "playback_context"},
    AppEvent.MIX_QUEUED: {"assistant_snapshot", "playback_context"},

    AppEvent.FOLDER_SELECTED: {"assistant_snapshot"},
    AppEvent.FOLDER_SCANNED: {"home_snapshot", "assistant_snapshot", "library_health"},
    AppEvent.FOLDER_QUEUED: {"assistant_snapshot", "playback_context"},

    AppEvent.SEARCH_STARTED: {"assistant_snapshot"},
    AppEvent.SEARCH_PERFORMED: {"assistant_snapshot"},
    AppEvent.SEARCH_CLEARED: {"assistant_snapshot"},

    # Queue
    AppEvent.QUEUE_UPDATED: {"home_snapshot", "assistant_snapshot", "playback_context"},
    AppEvent.QUEUE_CLEARED: {"home_snapshot", "assistant_snapshot", "playback_context"},
    AppEvent.TRACK_QUEUED: {"assistant_snapshot", "playback_context"},
    AppEvent.PLAYBACK_MODE_CHANGED: {"assistant_snapshot", "playback_context"},

    # Metadata extended
    AppEvent.METADATA_REVIEW_OPENED: {"assistant_snapshot"},
    AppEvent.COVER_UPDATED: {"home_snapshot", "assistant_snapshot"},
    AppEvent.LYRICS_UPDATED: {"assistant_snapshot"},
    AppEvent.TAGS_BATCH_UPDATED: {"home_snapshot", "assistant_snapshot", "library_health"},

    # Audio analysis extended
    AppEvent.AUDIO_ANALYSIS_STARTED: {"assistant_snapshot"},
    AppEvent.AUDIO_ANALYSIS_FAILED: {"assistant_snapshot"},
    AppEvent.AUDIO_FEATURES_UPDATED: {"home_snapshot", "assistant_snapshot", "library_health"},

    # Disc Lab
    AppEvent.DISC_DETECTED: {"assistant_snapshot"},
    AppEvent.RIP_STARTED: {"assistant_snapshot"},
    AppEvent.RIP_FINISHED: {"home_snapshot", "assistant_snapshot", "library_health"},
    AppEvent.RIP_FAILED: {"assistant_snapshot"},

    # Identifier / Radio
    AppEvent.IDENTIFICATION_STARTED: {"assistant_snapshot"},
    AppEvent.IDENTIFICATION_MATCHED: {"assistant_snapshot"},
    AppEvent.IDENTIFICATION_FAILED: {"assistant_snapshot"},
    AppEvent.RADIO_STATION_SELECTED: {"assistant_snapshot"},
    AppEvent.RADIO_PLAYED: {"home_snapshot", "assistant_snapshot", "playback_context"},

    # Operational errors
    AppEvent.CONTEXT_ERROR_RECORDED: {"home_snapshot", "assistant_snapshot"},
}

_DIRTY_FLAG_KEYS: set[str] = set()
for flags in _EVENT_DIRTY_MAP.values():
    _DIRTY_FLAG_KEYS.update(flags)


def invalidate_for_event(event_type: str) -> None:
    flags = _EVENT_DIRTY_MAP.get(event_type, set())
    for key in flags:
        repo.mark_dirty(key)


def invalidate_all() -> None:
    for key in _DIRTY_FLAG_KEYS:
        repo.mark_dirty(key)


def clear_dirty(key: str) -> None:
    repo.clear_dirty(key)


def is_dirty(key: str) -> bool:
    return repo.is_dirty(key)


def all_dirty_flags() -> set[str]:
    return _DIRTY_FLAG_KEYS
