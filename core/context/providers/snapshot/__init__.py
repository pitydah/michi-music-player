"""Snapshot section providers — canonical ContextService sections.

Each provider reads the REAL services injected into ``context.services`` and
reports ``available: False`` with a reason when a service is missing or its
readback fails. Values are never fabricated (ADR-005): an unavailable playback
backend reports ``state: unavailable`` instead of invented defaults.
"""

from __future__ import annotations

from core.context.providers.snapshot.audio import AudioSectionProvider
from core.context.providers.snapshot.capabilities import CapabilitiesSectionProvider
from core.context.providers.snapshot.ecosystem import EcosystemSectionProvider
from core.context.providers.snapshot.errors import ErrorsSectionProvider
from core.context.providers.snapshot.jobs import JobsSectionProvider
from core.context.providers.snapshot.library import LibrarySectionProvider
from core.context.providers.snapshot.playback import PlaybackSectionProvider
from core.context.providers.snapshot.queue import QueueSectionProvider
from core.context.providers.snapshot.radio import RadioSectionProvider
from core.context.providers.snapshot.recognition import RecognitionSectionProvider
from core.context.context_provider_registry import ContextProviderRegistry

__all__ = [
    "AudioSectionProvider",
    "CapabilitiesSectionProvider",
    "ContextProviderRegistry",
    "EcosystemSectionProvider",
    "ErrorsSectionProvider",
    "JobsSectionProvider",
    "LibrarySectionProvider",
    "PlaybackSectionProvider",
    "QueueSectionProvider",
    "RadioSectionProvider",
    "RecognitionSectionProvider",
]


def build_snapshot_registry() -> ContextProviderRegistry:
    """Register the canonical section providers in dependency-free order."""
    registry = ContextProviderRegistry()
    registry.register("playback", PlaybackSectionProvider())
    registry.register("queue", QueueSectionProvider())
    registry.register("library", LibrarySectionProvider())
    registry.register("audio", AudioSectionProvider())
    registry.register("ecosystem", EcosystemSectionProvider())
    registry.register("jobs", JobsSectionProvider())
    registry.register("radio", RadioSectionProvider())
    registry.register("recognition", RecognitionSectionProvider())
    registry.register("errors", ErrorsSectionProvider())
    registry.register("capabilities", CapabilitiesSectionProvider())
    return registry
