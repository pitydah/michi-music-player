"""Settings Manager — unified QSettings for Astra Music Player."""

import os
import json
from PySide6.QtCore import QSettings


SETTINGS = QSettings("Astra", "MusicPlayer")

DEFAULTS = {
    "general/start_minimized": False,
    "general/confirm_exit": False,
    "general/remember_session": True,
    "general/music_folder": os.path.expanduser("~/Música"),
    "general/download_folder": os.path.expanduser("~/Descargas"),
    "interface/show_menubar": True,
    "interface/show_quality_badge": True,
    "interface/cover_size": 260,
    "interface/compact_mode": False,
    "library/auto_scan": False,
    "library/exclude_hidden": True,
    "library/covers_cache_size": 100,
    "playback/default_volume": 70,
    "playback/repeat_mode": "none",
    "playback/shuffle_default": False,
    "playback/replaygain": False,
    "playback/crossfade": 0,
    "playback/gapless": True,
    "audio/device": "default",
    "audio/mode": "standard",
    "audio/sample_rate": 0,
    "audio/buffer_ms": 100,
    "audio/profile": "standard",
    "audio/device_backend": "auto",
    "audio/output_device_id": "auto",
    "audio/alsa_device": "",
    "audio/alsa_use_hw": False,
    "audio/allow_resample": True,
    "audio/resample_quality": "medium",
    "audio/dsd_mode": "pcm",
    "audio/dsd_pcm_rate": "auto",
    "audio/gapless_enabled": True,
    "audio/crossfade_seconds": 0,
    "audio/replaygain_enabled": False,
    "audio/replaygain_mode": "track",
    "audio/spectrum_enabled": False,
    "audio/exclusive_warning_shown": False,
    "audio/allow_fallback": True,
    "audio/pure_audio_enabled": False,
    "audio/studio_monitor_enabled": False,
    "audio/replaygain_preamp_db": 0,
    "audio/replaygain_headroom_db": 0,
    "audio/period_count": 4,
    "eq/enabled": False,
    "eq/mode": "graphic",
    "eq/preamp": 0.0,
    "eq/preset": "Flat",
    "eq/show_spectrum": False,
    "transmit/quality": "320",
    "transmit/latency": 0,
    "transmit/keep_local": True,
    "sync/auto_start": False,
    "sync/port": 53318,
    "sync/alias": "Astra PC",
    "sync/discovery_enabled": True,
    "sync/announce_interval": 5,
    "radio/auto_update": True,
    "radio/auto_reconnect": True,
    "radio/reconnect_interval": 5,
    "radio/record_streams": False,
    "radio/record_folder": os.path.expanduser("~/Música/Grabaciones"),
    "shortcuts/global_enabled": False,
    "advanced/debug_log": False,
    "advanced/log_level": "Error",
    "advanced/thread_limit": 4,
    "home_audio/enabled": False,
    "home_audio/ha_base_url": "",
    "home_audio/ha_token": "",
    "home_audio/ha_verify_ssl": True,
    "home_audio/snapserver_enabled": False,
    "home_audio/snapserver_tcp_port": 1704,
    "home_audio/snapserver_control_port": 1705,
    "home_audio/snapserver_http_port": 1780,
    "home_audio/astra_api_enabled": False,
    "home_audio/astra_api_port": 8124,
    "home_audio/astra_api_token": "",
    "home_audio/mdns_enabled": False,
    "home_audio/local_media_server_enabled": False,
    "home_audio/local_media_server_port": 8125,
    "home_audio/play_local_monitor": True,
    "home_audio/last_destination": "",
    "artist_enrichment/enabled": True,
    "artist_enrichment/provider": "theaudiodb",
    "artist_enrichment/api_key": "2",
    "artist_enrichment/language": "es",
    "artist_enrichment/download_images": True,
    "artist_enrichment/refresh_days": 30,
    "artist_enrichment/preload_visible": True,
    "identifier/provider": "none",
    "identifier/auto_enabled": False,
    "identifier/listen_radio": True,
    "identifier/listen_remote": True,
    "identifier/listen_local": False,
    "identifier/interval_seconds": 45,
    "identifier/save_history": True,
    "identifier/download_artwork": True,
    "identifier/api_key_audd": "",
    "identifier/api_key_acrcloud": "",
    "identifier/api_key_acoustid": "",
}


def get(key: str):
    return SETTINGS.value(key, DEFAULTS.get(key))


def set_(key: str, value):
    SETTINGS.setValue(key, value)


def export_to_file(path: str):
    data = {k: get(k) for k in DEFAULTS}
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def import_from_file(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path) as f:
        data = json.load(f)
    for k, v in data.items():
        if k in DEFAULTS:
            set_(k, v)


def restore_defaults():
    for k in DEFAULTS:
        set_(k, DEFAULTS[k])
