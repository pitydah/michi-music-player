"""Icon resolution — custom SVGs first, then Breeze system, then generic fallback."""

import os
from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QIcon, QPainterPath

BREEZE = "/usr/share/icons/breeze"
HERE = Path(__file__).parent.parent

# ── Custom SVG icons (top priority) ──

CUSTOM_ICONS = {
    "sidebar_library":    "icons/sidebar_library.svg",
    "sidebar_playlists":  "icons/sidebar_playlists.svg",
    "sidebar_playlist_item": "icons/sidebar_playlist_item.svg",
    "sidebar_servers":    "icons/sidebar_servers.svg",
    "sidebar_navidrome":  "icons/sidebar_navidrome.svg",
    "sidebar_jellyfin":   "icons/sidebar_jellyfin.svg",
    "sidebar_devices":    "icons/sidebar_devices.svg",
    "sidebar_radio":      "icons/sidebar_radio.svg",
    "sidebar_albums":     "icons/sidebar_albums.svg",
    "sidebar_folders":    "icons/sidebar_folders.svg",
    "sidebar_mix":        "icons/sidebar_mix.svg",
    "sidebar_unplayed":   "icons/sidebar_unplayed.svg",
    "sidebar_popular":    "icons/sidebar_popular.svg",
    "sidebar_add":        "icons/sidebar_add.svg",
    "sidebar_identifier": "icons/sidebar_identifier.svg",
    "sidebar_songs":      "icons/sidebar_songs.svg",
    "warm_play":          "icons/warm_play.svg",
    "warm_pause":         "icons/warm_pause.svg",
    "warm_prev":          "icons/warm_prev.svg",
    "warm_next":          "icons/warm_next.svg",
    "warm_shuffle":       "icons/warm_shuffle.svg",
    "warm_repeat":        "icons/warm_repeat.svg",
    "warm_mute":          "icons/warm_mute.svg",
    "warm_eq":            "icons/warm_eq.svg",
    "warm_vol_low":       "icons/warm_vol_low.svg",
    "warm_vol_medium":    "icons/warm_vol_medium.svg",
    "warm_vol_high":      "icons/warm_vol_high.svg",
    "warm_transmit":      "icons/warm_transmit.svg",
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
