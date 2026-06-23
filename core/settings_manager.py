"""Settings Manager — unified QSettings for Michi Music Player."""

import os
import json
from PySide6.QtCore import QSettings


SETTINGS = QSettings("Michi", "MusicPlayer")

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
    "eq/enabled": False,
    "eq/mode": "graphic",
    "eq/preamp": 0.0,
    "eq/preset": "Flat",
    "eq/show_spectrum": False,
    "transmit/quality": "320",
    "sync/auto_start": False,
    "sync/port": 53318,
    "sync/alias": "Michi PC",
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
    "home_audio/michi_api_enabled": False,
    "home_audio/michi_api_port": 8124,
    "home_audio/michi_api_token": "",
    "home_audio/mdns_enabled": False,
    "home_audio/local_media_server_enabled": False,
    "home_audio/local_media_server_port": 8125,
    "home_audio/play_local_monitor": True,
    "artist_enrichment/enabled": True,
    "artist_enrichment/provider": "musicbrainz",
    "artist_enrichment/api_key": "",
    "artist_enrichment/language": "",
    "artist_enrichment/wiki_lang": "",
    "artist_enrichment/download_images": True,
    "artist_enrichment/refresh_days": 30,
    "artist_enrichment/preload_visible": True,
    "artist_enrichment/online_enabled": True,
    "artist_enrichment/coverart_enabled": True,
    "artist_enrichment/offline_strict": False,
    "identifier/provider": "none",
    "identifier/auto_enabled": False,
    "identifier/listen_radio": True,
    "identifier/listen_remote": True,
    "identifier/listen_local": False,
    "identifier/interval_seconds": 45,
    "identifier/save_history": True,
    "identifier/download_artwork": True,
    "identifier/api_key_audd": "",
    "identifier/api_key_acoustid": "",
    "ai_assistant/enabled": False,
    "ai_assistant/model": "llama3.1:8b",
    "ai_assistant/base_url": "http://127.0.0.1:11434",
    "ai_assistant/save_history": False,
    "ai_assistant/max_results": 30,
    "ai_assistant/allow_write_actions": False,
    "ai_assistant/offline_strict": True,
    "ai_assistant/ollama_timeout": 30,
    "ai_assistant/allow_reversible_actions": True,
    "ai_assistant/require_confirmation": True,
    "ai_assistant/action_log_enabled": True,
    "ai_assistant/max_playlist_draft_tracks": 50,
    "ai_assistant/max_action_tracks": 100,
    "knowledge_broker/enabled": False,
    "knowledge_broker/offline_strict": True,
    "knowledge_broker/cache_only": True,
    "knowledge_broker/allow_musicbrainz": False,
    "knowledge_broker/allow_coverart": False,
    "knowledge_broker/allow_wikidata": False,
    "knowledge_broker/allow_wikipedia": False,
    "knowledge_broker/auto_refresh": False,
    "knowledge_broker/refresh_interval_days": 30,
    "knowledge_broker/wiki_language": "es",
    "ai_assistant/metadata_review_enabled": True,
    "ai_assistant/metadata_apply_to_files": False,
    "ai_assistant/metadata_apply_to_db": True,
    "ai_assistant/metadata_require_field_confirmation": True,
    "ai_assistant/metadata_min_confidence": 0.75,
    "ai_assistant/metadata_allow_low_confidence": False,
    "ai_assistant/metadata_max_batch": 50,
    "recommendation/enabled": True,
    "recommendation/use_listening_history": False,
    "recommendation/use_favorites": True,
    "recommendation/use_playlists": True,
    "recommendation/use_skips": False,
    "recommendation/use_quality_signals": True,
    "recommendation/max_results": 30,
    "recommendation/max_profile_items": 200,
    "recommendation/cache_days": 7,
    "recommendation/explain_reasons": True,
    "recommendation/save_feedback": True,
}


def get(key: str):
    return SETTINGS.value(key, DEFAULTS.get(key))

def get_bool(key: str) -> bool:
    v = SETTINGS.value(key, DEFAULTS.get(key))
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() in ("true", "1", "yes")
    if isinstance(v, int):
        return v != 0
    return False

def get_int(key: str) -> int:
    v = SETTINGS.value(key, DEFAULTS.get(key))
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (ValueError, TypeError):
        return 0

def get_float(key: str) -> float:
    v = SETTINGS.value(key, DEFAULTS.get(key))
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0

def get_str(key: str) -> str:
    v = SETTINGS.value(key, DEFAULTS.get(key))
    if v is None:
        return ""
    return str(v)

def get_list(key: str) -> list:
    import json as _json
    v = SETTINGS.value(key, DEFAULTS.get(key))
    if v is None:
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            return _json.loads(v)
        except (_json.JSONDecodeError, ValueError):
            return []
    return []

def set_(key: str, value):
    SETTINGS.setValue(key, value)

def set_bool(key: str, value: bool):
    SETTINGS.setValue(key, bool(value))

def set_int(key: str, value: int):
    SETTINGS.setValue(key, int(value))

def set_float(key: str, value: float):
    SETTINGS.setValue(key, float(value))

def set_str(key: str, value: str):
    SETTINGS.setValue(key, str(value))


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
