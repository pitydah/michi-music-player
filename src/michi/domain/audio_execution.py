"""Audio execution-family vocabulary for Audio Phase 2 (AP2-F01).

Pure domain module: stdlib only. The execution family describes HOW audio
executes; it is orthogonal to which engine (Qt/GStreamer/MPD) transports it.
Audio Processing must never become a fourth AudioEngine: ``MANAGED_PCM`` is a
family, not an engine.

Contract anchors: R11-F01 (create-only slice), R11-G03 (output families) and
R11-G02 (authority map).

``DIRECT_PCM`` (current V3.5 strict/compatible Direct, processing forbidden) is
deliberately distinct from ``MANAGED_PCM`` (a Michi-owned processed PCM graph).
No routing, backend or capability logic lives here.
"""

from __future__ import annotations

from enum import StrEnum


class AudioExecutionFamily(StrEnum):
    """Canonical route vocabulary (R11-G03). No routing logic lives here."""

    SHARED_PCM = "shared_pcm"
    DIRECT_PCM = "direct_pcm"
    MANAGED_PCM = "managed_pcm"
    NATIVE_DSD = "native_dsd"
    DOP = "dop"
