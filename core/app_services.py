"""AppServices — immutable DI container for Michi Music Player controllers.

Design: frozen dataclass. Controllers receive only the services they need,
not a mutable proxy to the entire window. Use AppContext for backward
compatibility; migrate controllers to AppServices progressively.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AppServices:
    """Immutable service container — pass to controllers that don't need
    direct window/widget access."""

    # Core — always available
    db: object = None          # LibraryDB
    playback: object = None    # PlayerService
    player: object = None      # PlayerEngine
    model: object = None       # TrackRefTableModel
    workers: object = None     # WorkerManager

    # UI feedback
    toast: object = None       # ToastService
    player_bar: object = None  # PlayerBarController (may be None)

    # Features
    features: object = None    # FeatureManager

    # Repos
    artist_repo: object = None  # ArtistRepository
    genre_repo: object = None   # GenreRepository

    # Navigation (callables — avoid widget references)
    fade_to: callable = None              # (view_name: str) -> None
    navigate: callable = None             # (key: str) -> None
    configure_header: callable = None     # (section_key: str) -> None
    rebuild_sidebar: callable = None
    load_library: callable = None
    play_file: callable = None            # (filepath: str) -> None
    reload_library: callable = None       # (reason: str) -> None
    clear_coverflow_cache: callable = None
    enrich_artist: callable = None        # (key: str, name: str) -> None
    get_content_widget: callable = None   # () -> widget (legacy — pending removal)
    ha_client: object = None              # HomeAssistantClient (optional)
    ha_connected: callable = None         # () -> bool
    local_media_ctrl: object = None       # LocalMediaServerController
    local_ip: callable = None             # () -> str
    context_svc: object = None            # ContextService
