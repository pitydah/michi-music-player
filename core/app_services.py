"""AppServices — immutable DI container for Michi Music Player controllers.

Design: frozen dataclass. Controllers receive only the services they need,
not a mutable proxy to the entire MainWindow. Use AppContext for backward
compatibility; migrate controllers to AppServices progressively.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AppServices:
    """Immutable service container — pass to controllers that don't need
    direct window/widget access."""

    # Core — always available
    db: object = None          # LibraryDB
    playback: object = None    # PlayerService
    player: object = None      # PlayerEngine
    model: object = None       # TrackRefTableModel

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
