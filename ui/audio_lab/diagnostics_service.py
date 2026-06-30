"""Diagnostics service — wrapper for core/audio_lab/diagnostics_service.

This module re-exports everything from core.audio_lab.diagnostics_service
for backward compatibility. New code should import from core.audio_lab directly.
"""

from core.audio_lab.diagnostics_service import *  # noqa: F401, F403

import warnings
warnings.warn(
    "Import from 'core.audio_lab.diagnostics_service' instead of "
    "'ui.audio_lab.diagnostics_service'.",
    DeprecationWarning, stacklevel=2,
)
