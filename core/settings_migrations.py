"""Settings migrations — legacy alias to canonical key mapping, idempotent."""
from __future__ import annotations

import logging
from typing import Any

from core.settings_manager import SETTINGS

logger = logging.getLogger("michi.settings_migrations")

# legacy_key -> (canonical_key, type_converter)
_ALIASES: dict[str, tuple[str, callable]] = {
    "audio/buffer_ms": ("buffer/ms", int),
    "playback/gapless": ("gapless/enabled", bool),
    "playback/replaygain": ("replaygain/mode", lambda v: "album" if v else "disabled"),
    "audio/mode": ("bitperfect/enabled", lambda v: v == "bitperfect" or v == "exclusive"),
    "audio/profile": ("audio/profile", str),
    "library/covers_cache_size": ("cache/covers_size", int),
}

_SCHEMA_VERSION_KEY = "schema/version"
_CURRENT_VERSION = 1


def _read_migrated(key: str) -> Any:
    """Read a canonical key, falling back to legacy alias."""
    canonical = key
    if canonical in _ALIASES:
        return SETTINGS.value(canonical, None)
    for legacy, (canonical_key, _) in _ALIASES.items():
        if canonical_key == key:
            val = SETTINGS.value(legacy, None)
            if val is not None:
                return val
    return SETTINGS.value(key, None)


def migrate_all():
    """Run all pending migrations idempotently."""
    version = int(SETTINGS.value(_SCHEMA_VERSION_KEY, 0))
    if version >= _CURRENT_VERSION:
        return

    logger.info("Running settings migrations (v%s -> v%s)...", version, _CURRENT_VERSION)

    for legacy, (canonical, converter) in _ALIASES.items():
        legacy_val = SETTINGS.value(legacy, None)
        if legacy_val is None:
            continue
        canonical_val = SETTINGS.value(canonical, None)
        if canonical_val is not None:
            # Canonical already exists; remove legacy
            SETTINGS.remove(legacy)
            logger.debug("Removed legacy key %s (canonical %s already set)", legacy, canonical)
            continue
        try:
            converted = converter(legacy_val)
            SETTINGS.setValue(canonical, converted)
            SETTINGS.remove(legacy)
            logger.info("Migrated %s -> %s = %s", legacy, canonical, converted)
        except (ValueError, TypeError) as e:
            logger.warning("Migration failed for %s: %s", legacy, e)

    SETTINGS.setValue(_SCHEMA_VERSION_KEY, _CURRENT_VERSION)
    SETTINGS.sync()
    logger.info("Settings migration to v%s complete", _CURRENT_VERSION)


def get_canonical(key: str) -> str:
    """Resolve a possibly-legacy key to its canonical form."""
    if key in _ALIASES:
        return _ALIASES[key][0]
    return key


def get_with_fallback(key: str, default: Any = None) -> Any:
    """Read a canonical key, with legacy fallback and type coercion."""
    canonical = get_canonical(key)
    val = SETTINGS.value(canonical, None)
    if val is not None:
        return val
    # Legacy fallback
    if key != canonical:
        val = SETTINGS.value(key, None)
        if val is not None:
            _, converter = _ALIASES.get(key, (None, lambda x: x))
            try:
                return converter(val)
            except (ValueError, TypeError):
                return val
    return default
