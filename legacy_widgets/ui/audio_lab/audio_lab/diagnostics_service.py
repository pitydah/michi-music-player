"""Diagnostics service wrapper — DEPRECATED.

All logic has moved to core/audio_lab/diagnostics_service.py.
This module is kept only for backward compatibility.
Re-exports all public symbols from core.
"""

import warnings

warnings.warn(
    "Import from 'core.audio_lab.diagnostics_service' instead of "
    "'ui.audio_lab.diagnostics_service'.",
    DeprecationWarning, stacklevel=2,
)

from core.audio_lab.diagnostics_service import (  # noqa: F401, E402
    AUDIO_EXTS,
    analyse_file,
    analyse_spectral,
    generate_report,
    get_badge_for_file,
    get_spectral_badge,
)

__all__ = [
    "AUDIO_EXTS",
    "analyse_file",
    "analyse_spectral",
    "generate_report",
    "get_badge_for_file",
    "get_spectral_badge",
]
