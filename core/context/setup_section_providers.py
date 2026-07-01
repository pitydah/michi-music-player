"""SetupSectionProviders — factory that creates and registers all section context providers.

Must be called once during application startup, after all services are initialized.
"""
from __future__ import annotations

import logging
from core.context.section_context_registry import SectionContextRegistry
from core.context.providers.library_context_provider import LibraryContextProvider
from core.context.providers.audio_lab_context_provider import AudioLabContextProvider
from core.context.providers.mix_context_provider import MixContextProvider
from core.context.providers.playlist_context_provider import PlaylistContextProvider
from core.context.providers.playback_context_provider import PlaybackContextProvider
from core.context.providers.connections_context_provider import ConnectionsContextProvider
from core.context.providers.devices_context_provider import DevicesContextProvider
from core.context.providers.metadata_context_provider import MetadataContextProvider
from core.context.providers.home_audio_context_provider import HomeAudioContextProvider
from core.context.providers.settings_context_provider import SettingsContextProvider

try:
    from core.context.providers.genre_context_provider import GenreContextProvider
    _HAS_GENRE = True
except ImportError:
    _HAS_GENRE = False

_log = logging.getLogger("michi.setup_providers")


def setup_section_providers(
    db=None,
    playback=None,
    genre_repo=None,
    genre_stats_svc=None,
    cover_art_service=None,
    sync=None,
) -> SectionContextRegistry:
    """Create and register all section context providers.

    Each provider receives its dependencies. Missing optional dependencies
    (like genre_repo) are gracefully handled by the provider itself.
    """
    registry = SectionContextRegistry()

    registry.register(LibraryContextProvider(db=db, cover_art_service=cover_art_service))
    registry.register(AudioLabContextProvider(db=db))
    registry.register(PlaybackContextProvider(playback=playback))
    registry.register(MixContextProvider(db=db))
    registry.register(PlaylistContextProvider(db=db))
    registry.register(DevicesContextProvider(db=db))
    registry.register(MetadataContextProvider(db=db))
    registry.register(ConnectionsContextProvider(db=db))
    registry.register(HomeAudioContextProvider(db=db))
    registry.register(SettingsContextProvider(db=db))

    if _HAS_GENRE:
        registry.register(
            GenreContextProvider(db=db, genre_repo=genre_repo, genre_stats_svc=genre_stats_svc))

    _log.info(
        "Registered %d section context providers",
        len(registry.list_registered()),
    )
    return registry
