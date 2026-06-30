"""Audio Lab badges — bridge between Biblioteca and Diagnostics.

This module provides clean functions for Biblioteca to consume
technical badges computed by Audio Lab's Diagnostics service.
It does NOT import PySide and does NOT depend on ui.audio_lab.
"""

from __future__ import annotations

import os
from typing import Any


def get_audio_lab_badge_for_path(path: str) -> dict[str, str]:
    """Return a technical badge for a file path.

    Delegates to core.audio_lab.diagnostics_service.get_badge_for_file.
    Falls back to extension-based badge if no cache is available.

    Returns dict with keys: label, kind, tooltip.
    kind: hires | lossless | lossy | dsd | unknown | warning | error
    """
    try:
        from core.audio_lab.diagnostics_service import get_badge_for_file
        return get_badge_for_file(path)
    except Exception:
        return _fallback_badge(path)


def get_audio_lab_badges_for_paths(paths: list[str]) -> dict[str, dict[str, str]]:
    """Return badges for multiple paths in a single batch call.

    Uses core.audio_lab.diagnostics_service.get_badges_for_files for efficiency.
    """
    try:
        from core.audio_lab.diagnostics_service import get_badges_for_files
        return get_badges_for_files(paths)
    except Exception:
        pass
    result: dict[str, dict[str, str]] = {}
    for p in paths:
        try:
            result[p] = get_audio_lab_badge_for_path(p)
        except Exception:
            result[p] = _fallback_badge(p)
    return result


def get_spectral_badge_from_result(result: dict[str, Any]) -> dict[str, str]:
    """Convert a spectral analysis result dict to a badge dict.

    Delegates to core.audio_lab.diagnostics_service.get_spectral_badge.
    """
    try:
        from core.audio_lab.diagnostics_service import get_spectral_badge
        return get_spectral_badge(result)
    except Exception:
        return {"label": "Error", "kind": "error", "tooltip": str(result)}


def get_quality_filter_value(path: str) -> str:
    """Return a quality filter value for a file path.

    Returns one of: hires | lossless | lossy | dsd | unknown | warning | error
    """
    try:
        badge = get_audio_lab_badge_for_path(path)
        return badge.get("kind", "unknown")
    except Exception:
        return "unknown"


def is_analysis_pending(path: str) -> bool:
    """Check if a file has not been analysed yet.

    Returns True if the file exists but has no valid cache entry.
    Returns False if the file does not exist (nothing to analyse).
    Returns False if the cache has an error (not pending — is error).
    """
    if not os.path.isfile(path):
        return False
    try:
        from core.audio_lab.diagnostics_service import DiagnosticsCache
        cache = DiagnosticsCache()
        cached = cache.get(path)
        if cached is None:
            return True
        if cached.get("error"):
            return False
        return False
    except Exception:
        return True


def matches_quality_filter(path: str, value: str) -> bool:
    """Check if a file matches a quality filter value.

    value: hires | lossless | lossy | dsd | unknown
    """
    kind = get_quality_filter_value(path)
    return kind == value


def matches_analysis_filter(path: str, value: str) -> bool:
    """Check if a file matches an analysis filter value.

    value: pending | error
    """
    if value == "pending":
        return is_analysis_pending(path)
    if value == "error":
        badge = get_audio_lab_badge_for_path(path)
        return badge.get("kind") == "error"
    return False


def matches_spectral_filter(path: str, value: str) -> bool:
    """Check if a file matches a spectral filter value.

    value: suspicious | inconclusive
    Only works if spectral analysis has been cached for the file.
    """
    try:
        from core.audio_lab.diagnostics_service import DiagnosticsCache
        cache = DiagnosticsCache()
        cached = cache.get(path)
        if cached is None:
            return False
        spec = cached.get("spectral", {})
        verdict = spec.get("verdict", "")
        if value == "suspicious":
            return verdict in ("SUSPICIOUS_UPSAMPLING", "POSSIBLE_LOSSY_SOURCE")
        if value == "inconclusive":
            return verdict == "INCONCLUSIVE"
        return False
    except Exception:
        return False


def get_quality_filter_values(paths: list[str]) -> dict[str, str]:
    """Return quality filter values for multiple paths."""
    badges = get_audio_lab_badges_for_paths(paths)
    return {p: b.get("kind", "unknown") for p, b in badges.items()}


def get_analysis_pending_map(paths: list[str]) -> dict[str, bool]:
    """Return analysis pending status for multiple paths."""
    return {p: is_analysis_pending(p) for p in paths}


def _fallback_badge(path: str) -> dict[str, str]:
    """Return a basic extension-based badge when cache/unavailable."""
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    label = ext.upper() if ext else "?"
    kind = "unknown"
    if ext in ("flac", "wav", "aiff", "alac"):
        kind = "lossless"
    elif ext in ("mp3", "aac", "ogg", "opus"):
        kind = "lossy"
    elif ext in ("dsf", "dff"):
        kind = "dsd"
    return {"label": label, "kind": kind, "tooltip": ""}
