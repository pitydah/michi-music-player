"""Icon Registry — centralized icon specification for Astra Music Player."""
from dataclasses import dataclass


@dataclass(frozen=True)
class IconSpec:
    key: str
    path: str
    family: str           # app, sidebar, action, tray, folder, view
    symbolic: bool = True
    allow_background: bool = False
    render_mode: str = "native_color"  # "native_color" or "symbolic_tint"
    theme_fallback: str = ""
    description: str = ""


ICON_REGISTRY: dict[str, IconSpec] = {
    # ── App icon ──
    "app_icon": IconSpec(
        key="app_icon", path="icons/app_icon.png",
        family="app", symbolic=False, allow_background=True,
        description="Icono principal de la aplicacion"),

    # ── Sidebar ──
    "sidebar_library": IconSpec(
        key="sidebar_library", path="icons/sidebar_clean/sidebar_library_24.png",
        family="sidebar", symbolic=True,
        theme_fallback="audio-x-generic",
        description="Todas las canciones"),
    "sidebar_albums": IconSpec(
        key="sidebar_albums", path="icons/sidebar_clean/sidebar_albums_24.png",
        family="sidebar", symbolic=True,
        theme_fallback="media-album-cover",
        description="Albumes"),
    "sidebar_artists": IconSpec(
        key="sidebar_artists", path="icons/sidebar_artist.svg",
        family="sidebar", symbolic=True, allow_background=False,
        render_mode="symbolic_tint",
        description="Artistas"),
    "sidebar_genres": IconSpec(
        key="sidebar_genres", path="icons/sidebar_clean/sidebar_mix_24.png",
        family="sidebar", symbolic=True,
        description="Generos"),
    "sidebar_folders": IconSpec(
        key="sidebar_folders", path="icons/sidebar_clean/sidebar_folders_24.png",
        family="sidebar", symbolic=True,
        theme_fallback="folder",
        description="Carpetas"),
    "sidebar_playlists": IconSpec(
        key="sidebar_playlists", path="icons/sidebar_clean/sidebar_playlists_24.png",
        family="sidebar", symbolic=True,
        description="Playlists"),
    "sidebar_playlist_item": IconSpec(
        key="sidebar_playlist_item", path="icons/sidebar_clean/sidebar_playlist_item_24.png",
        family="sidebar", symbolic=True,
        description="Playlist individual"),
    "sidebar_mix": IconSpec(
        key="sidebar_mix", path="icons/sidebar_clean/sidebar_mix_24.png",
        family="sidebar", symbolic=True,
        description="Herramientas / Mix"),
    "sidebar_unplayed": IconSpec(
        key="sidebar_unplayed", path="icons/sidebar_clean/sidebar_unplayed_24.png",
        family="sidebar", symbolic=True,
        description="No escuchadas"),
    "sidebar_popular": IconSpec(
        key="sidebar_popular", path="icons/sidebar_clean/sidebar_popular_24.png",
        family="sidebar", symbolic=True,
        description="Mas escuchadas"),
    "sidebar_identifier": IconSpec(
        key="sidebar_identifier", path="icons/sidebar_clean/sidebar_identifier_24.png",
        family="sidebar", symbolic=True,
        description="Identificador"),
    "sidebar_radio": IconSpec(
        key="sidebar_radio", path="icons/sidebar_clean/sidebar_radio_24.png",
        family="sidebar", symbolic=True,
        description="Radio"),
    "sidebar_servers": IconSpec(
        key="sidebar_servers", path="icons/sidebar_clean/sidebar_servers_24.png",
        family="sidebar", symbolic=True,
        description="Servidores"),
    "sidebar_navidrome": IconSpec(
        key="sidebar_navidrome", path="icons/sidebar_clean/sidebar_navidrome_24.png",
        family="sidebar", symbolic=True,
        description="Navidrome"),
    "sidebar_jellyfin": IconSpec(
        key="sidebar_jellyfin", path="icons/sidebar_clean/sidebar_jellyfin_24.png",
        family="sidebar", symbolic=True,
        description="Jellyfin"),
    "sidebar_add": IconSpec(
        key="sidebar_add", path="icons/sidebar_clean/sidebar_add_24.png",
        family="sidebar", symbolic=True,
        description="Anadir"),
    "sidebar_devices": IconSpec(
        key="sidebar_devices", path="icons/sidebar_devices.svg",
        family="sidebar", symbolic=True, render_mode="symbolic_tint",
        description="Dispositivos"),
    "sidebar_artist": IconSpec(
        key="sidebar_artist", path="icons/sidebar_artist.svg",
        family="sidebar", symbolic=True, allow_background=False,
        render_mode="native_color",
        description="Artista"),
    "sidebar_recent": IconSpec(
        key="sidebar_recent", path="icons/sidebar_recent.svg",
        family="sidebar", symbolic=True, render_mode="symbolic_tint",
        description="Recientes"),
    "sidebar_songs": IconSpec(
        key="sidebar_songs", path="icons/sidebar_clean/sidebar_songs_24.png",
        family="sidebar", symbolic=True,
        description="Canciones"),

    # ── Home Audio ──
    "home_audio": IconSpec(
        key="home_audio", path="icons/sidebar/home-audio.svg",
        family="sidebar", symbolic=True, render_mode="native_color",
        description="Home Audio / Multiroom"),
    "metadata_editor": IconSpec(
        key="metadata_editor", path="icons/sidebar/metadata.svg",
        family="sidebar", symbolic=True, render_mode="native_color",
        description="Editor de metadatos"),

    # ── NowPlaying actions ──
    "warm_play": IconSpec(
        key="warm_play", path="icons/nowplaying_clean/warm_play_128.png",
        family="action", symbolic=True,
        theme_fallback="media-playback-start",
        description="Play"),
    "warm_pause": IconSpec(
        key="warm_pause", path="icons/nowplaying_clean/warm_pause_128.png",
        family="action", symbolic=True,
        theme_fallback="media-playback-pause",
        description="Pause"),
    "warm_prev": IconSpec(
        key="warm_prev", path="icons/nowplaying_clean/warm_prev_128.png",
        family="action", symbolic=True,
        theme_fallback="media-skip-backward",
        description="Anterior"),
    "warm_next": IconSpec(
        key="warm_next", path="icons/nowplaying_clean/warm_next_128.png",
        family="action", symbolic=True,
        theme_fallback="media-skip-forward",
        description="Siguiente"),
    "warm_shuffle": IconSpec(
        key="warm_shuffle", path="icons/nowplaying_clean/warm_shuffle_128.png",
        family="action", symbolic=True,
        theme_fallback="media-playlist-shuffle",
        description="Aleatorio"),
    "warm_repeat": IconSpec(
        key="warm_repeat", path="icons/nowplaying_clean/warm_repeat_128.png",
        family="action", symbolic=True,
        theme_fallback="media-repeat-all",
        description="Repetir"),
    "warm_eq": IconSpec(
        key="warm_eq", path="icons/nowplaying_clean/warm_eq_128.png",
        family="action", symbolic=True,
        theme_fallback="view-media-equalizer",
        description="Ecualizador"),
    "warm_transmit": IconSpec(
        key="warm_transmit", path="icons/nowplaying_clean/warm_transmit_128.png",
        family="action", symbolic=True,
        description="Transmitir"),
    "warm_vol_high": IconSpec(
        key="warm_vol_high", path="icons/nowplaying_clean/warm_vol_high_128.png",
        family="action", symbolic=True,
        description="Volumen alto"),
    "warm_vol_medium": IconSpec(
        key="warm_vol_medium", path="icons/nowplaying_clean/warm_vol_medium_128.png",
        family="action", symbolic=True,
        description="Volumen medio"),
    "warm_vol_low": IconSpec(
        key="warm_vol_low", path="icons/nowplaying_clean/warm_vol_low_128.png",
        family="action", symbolic=True,
        description="Volumen bajo"),
    "warm_mute": IconSpec(
        key="warm_mute", path="icons/nowplaying_clean/warm_mute_128.png",
        family="action", symbolic=True,
        description="Silencio"),
    "warm_audio_source": IconSpec(
        key="warm_audio_source", path="icons/warm_audio_source.svg",
        family="action", symbolic=True,
        description="Fuente de audio"),
    "warm_mini_player": IconSpec(
        key="warm_mini_player", path="icons/warm_mini_player.svg",
        family="action", symbolic=True,
        description="Mini reproductor"),
    "warm_settings": IconSpec(
        key="warm_settings", path="icons/warm_settings.svg",
        family="action", symbolic=True,
        description="Configuracion"),

    # ── View modes ──
    "warm_view_grid": IconSpec(
        key="warm_view_grid", path="icons/warm_view_grid.svg",
        family="view", symbolic=True,
        theme_fallback="view-grid",
        description="Vista grid"),
    "warm_view_list": IconSpec(
        key="warm_view_list", path="icons/warm_view_list.svg",
        family="view", symbolic=True,
        theme_fallback="view-list-details",
        description="Vista lista"),
    "warm_view_coverflow": IconSpec(
        key="warm_view_coverflow", path="icons/warm_view_coverflow.svg",
        family="view", symbolic=True,
        theme_fallback="media-album-cover",
        description="CoverFlow"),
    "warm_view_tree": IconSpec(
        key="warm_view_tree", path="icons/view/view-tree.svg",
        family="view", symbolic=True,
        description="Vista arbol"),
    "warm_view_details": IconSpec(
        key="warm_view_details", path="icons/view/view-details.svg",
        family="view", symbolic=True,
        description="Vista detalles"),

    # ── Folders ──
    "folder": IconSpec(
        key="folder", path="icons/folder.svg",
        family="folder", symbolic=True,
        theme_fallback="folder",
        description="Carpeta"),

    # ── Tray ──
    "tray_icon": IconSpec(
        key="tray_icon", path="icons/tray_icon.svg",
        family="tray", symbolic=True,
        description="Icono de bandeja del sistema"),
}


def is_valid_ui_icon(key: str) -> bool:
    spec = ICON_REGISTRY.get(key)
    if not spec:
        return False
    if spec.family in ("sidebar", "action", "folder", "tray", "view"):
        return not spec.allow_background
    return True  # app icons may have backgrounds
