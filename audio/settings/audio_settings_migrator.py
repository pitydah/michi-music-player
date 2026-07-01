"""Audio Settings Migrator — migrates legacy keys to canonical keys.

Reads old keys and writes canonical keys, then optionally removes old keys.
Does NOT delete user settings without being asked.
"""

import logging

from audio.settings.audio_settings_schema import LEGACY_KEY_MAP, AUDIO_SETTINGS_SCHEMA
from core.settings_manager import get, set_

logger = logging.getLogger("michi.settings.migrator")


def migrate_legacy_keys(dry_run: bool = False) -> list[str]:
    """Migrate legacy playback/* keys to audio/* canonical keys.

    Returns list of migration messages (empty if nothing to migrate).
    """
    messages = []
    for legacy_key, canonical_key in LEGACY_KEY_MAP.items():
        legacy_val = get(legacy_key)
        if legacy_val is None:
            continue
        canonical_val = get(canonical_key)
        if canonical_val is None or canonical_val == _schema_default(canonical_key):
            if not dry_run:
                set_(canonical_key, legacy_val)
                logger.info("Migrated %s → %s = %s", legacy_key, canonical_key, legacy_val)
            messages.append(f"{legacy_key} → {canonical_key} = {legacy_val}")
    return messages


def ensure_mpd_settings(dry_run: bool = False) -> list[str]:
    """Ensure MPD-specific settings exist with defaults if not set."""
    messages = []
    mpd_keys = [k for k in AUDIO_SETTINGS_SCHEMA if k.startswith("audio/mpd/")]
    for key in mpd_keys:
        val = get(key)
        if val is None:
            default, _ = AUDIO_SETTINGS_SCHEMA[key]
            if not dry_run:
                set_(key, default)
                logger.info("Set default %s = %s", key, default)
            messages.append(f"Set default {key} = {default}")
    return messages


def _schema_default(key: str):
    entry = AUDIO_SETTINGS_SCHEMA.get(key)
    if entry:
        return entry[0]
    return None


def migrate_all(dry_run: bool = False) -> list[str]:
    """Run all migrations. Returns list of actions taken."""
    actions = []
    actions.extend(migrate_legacy_keys(dry_run))
    actions.extend(ensure_mpd_settings(dry_run))
    return actions
