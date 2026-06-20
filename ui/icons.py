"""Icon resolution — custom SVGs first, then Breeze system, then generic fallback."""

import os
from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QIcon, QPainterPath

BREEZE = "/usr/share/icons/breeze"
HERE = Path(__file__).parent.parent

# ── Custom icons: PNG (clean, no black bg) first, SVG fallback ──

CUSTOM_ICONS = {
    # Sidebar — clean PNGs
    "sidebar_library":    "icons/sidebar_clean/sidebar_library_24.png",
    "sidebar_songs":      "icons/sidebar_clean/sidebar_songs_24.png",
    "sidebar_albums":     "icons/sidebar_clean/sidebar_albums_24.png",
    "sidebar_folders":    "icons/sidebar_clean/sidebar_folders_24.png",
    "sidebar_playlists":  "icons/sidebar_clean/sidebar_playlists_24.png",
    "sidebar_playlist_item": "icons/sidebar_clean/sidebar_playlist_item_24.png",
    "sidebar_mix":        "icons/sidebar_clean/sidebar_mix_24.png",
    "sidebar_unplayed":   "icons/sidebar_clean/sidebar_unplayed_24.png",
    "sidebar_popular":    "icons/sidebar_clean/sidebar_popular_24.png",
    "sidebar_identifier": "icons/sidebar_clean/sidebar_identifier_24.png",
    "sidebar_radio":      "icons/sidebar_clean/sidebar_radio_24.png",
    "sidebar_servers":    "icons/sidebar_clean/sidebar_servers_24.png",
    "sidebar_navidrome":  "icons/sidebar_clean/sidebar_navidrome_24.png",
    "sidebar_jellyfin":   "icons/sidebar_clean/sidebar_jellyfin_24.png",
    "sidebar_add":        "icons/sidebar_clean/sidebar_add_24.png",
    # Sidebar — SVG fallback (not in clean set)
    "sidebar_devices":    "icons/sidebar_devices.svg",

    # NowPlaying — clean PNGs
    "warm_play":          "icons/nowplaying_clean/warm_play_128.png",
    "warm_pause":         "icons/nowplaying_clean/warm_pause_128.png",
    "warm_prev":          "icons/nowplaying_clean/warm_prev_128.png",
    "warm_next":          "icons/nowplaying_clean/warm_next_128.png",
    "warm_shuffle":       "icons/nowplaying_clean/warm_shuffle_128.png",
    "warm_repeat":        "icons/nowplaying_clean/warm_repeat_128.png",
    "warm_eq":            "icons/nowplaying_clean/warm_eq_128.png",
    "warm_transmit":      "icons/nowplaying_clean/warm_transmit_128.png",
    "warm_vol_high":      "icons/nowplaying_clean/warm_vol_high_128.png",
    "warm_vol_medium":    "icons/nowplaying_clean/warm_vol_medium_128.png",
    "warm_vol_low":       "icons/nowplaying_clean/warm_vol_low_128.png",
    "warm_mute":          "icons/nowplaying_clean/warm_mute_128.png",
    "warm_audio_source":  "icons/warm_audio_source.svg",
    "warm_mini_player":   "icons/warm_mini_player.svg",
    "warm_settings":      "icons/warm_settings.svg",
    "tray_icon":          "icons/tray_icon.svg",
    "warm_view_grid":     "/home/cristian/Descargas/iloveimg-resized(2)/view-cover.svg",
    "warm_view_list":     "/home/cristian/Descargas/iloveimg-resized(2)/view-list.svg",
    "warm_view_coverflow": "/home/cristian/Descargas/iloveimg-resized(2)/view-coverflow.svg",
}

# ── Map: icon name → Breeze 24px SVG path ──

BREEZE_MAP = {
    "play":     "actions/24/media-playback-start.svg",
    "pause":    "actions/24/media-playback-pause.svg",
    "stop":     "actions/24/media-playback-stop.svg",
    "prev":     "actions/24/media-skip-backward.svg",
    "next":     "actions/24/media-skip-forward.svg",
    "shuffle":  "actions/24/media-playlist-shuffle.svg",
    "repeat":   "actions/24/media-repeat-all.svg",
    "repeat_one": "actions/24/media-repeat-single.svg",
    "heart":    "actions/24/bookmarks-bookmarked.svg",
    "download": "actions/24/cloud-download.svg",
    "eq":       "actions/24/view-media-equalizer.svg",
    "menu":     "actions/24/application-menu.svg",
    "add":      "actions/24/list-add.svg",
    "remove":   "actions/24/list-remove.svg",
    "grid":     "actions/24/view-grid.svg",
    "list":     "actions/24/view-list-details.svg",
    "coverflow": "actions/24/media-album-cover.svg",
    "search":   "actions/24/edit-find.svg",
    "volume_high":  "status/24/audio-on.svg",
    "volume_mute":  "status/24/audio-off.svg",
}


def _generic_icon() -> QIcon:
    """Simple geometric placeholder — standalone vector fallback."""
    pix = QPixmap(24, 24)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor("#c7c7cc"), 1.5))
    p.setBrush(QColor("#e0e4e7"))
    p.drawRoundedRect(2, 2, 20, 20, 4, 4)
    p.end()
    return QIcon(pix)


def get_icon(name: str) -> str:
    """Returns absolute path to SVG: custom → Breeze → generic."""
    # 1. Custom SVG
    custom_path = CUSTOM_ICONS.get(name)
    if custom_path:
        p = Path(custom_path)
        full = p if p.is_absolute() else HERE / custom_path
        if full.exists():
            return str(full)

    # 2. Breeze system
    breeze_path = os.path.join(BREEZE, BREEZE_MAP.get(name, ""))
    if os.path.exists(breeze_path):
        return breeze_path

    # 3. Generic fallback
    return ""


def get_icon_qicon(name: str) -> QIcon:
    """Returns QIcon with generic fallback — standalone."""
    path = get_icon(name)
    if path:
        return QIcon(path)
    return _generic_icon()


def app_icon() -> str:
    path = HERE / "icons" / "app_icon.png"
    return str(path) if path.exists() else ""
