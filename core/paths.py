"""Centralized XDG paths for Michi Music Player.

All persistent file paths (data, cache, config, logs, databases) are
resolved here. Supports overrides for testing via environment variables:
  MICHI_TEST_DATA_DIR, MICHI_TEST_CACHE_DIR, MICHI_TEST_CONFIG_DIR
"""

import os

APP_NAME = "michi-music-player"
LEGACY_DIR = os.path.expanduser("~/.local/share/michi")


def _xdg_data_home() -> str:
    return os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))


def _xdg_cache_home() -> str:
    return os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))


def _xdg_config_home() -> str:
    return os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))


def app_data_dir() -> str:
    if "MICHI_TEST_DATA_DIR" in os.environ:
        return os.environ["MICHI_TEST_DATA_DIR"]
    return os.path.join(_xdg_data_home(), APP_NAME)


def app_cache_dir() -> str:
    if "MICHI_TEST_CACHE_DIR" in os.environ:
        return os.environ["MICHI_TEST_CACHE_DIR"]
    return os.path.join(_xdg_cache_home(), APP_NAME)


def app_config_dir() -> str:
    if "MICHI_TEST_CONFIG_DIR" in os.environ:
        return os.environ["MICHI_TEST_CONFIG_DIR"]
    return os.path.join(_xdg_config_home(), APP_NAME)


def logs_dir() -> str:
    return os.path.join(app_data_dir(), "logs")


def log_file() -> str:
    return os.path.join(logs_dir(), "michi.log")


def database_path() -> str:
    return os.path.join(app_data_dir(), "library.db")


def covers_cache_dir() -> str:
    return os.path.join(app_cache_dir(), "covers", "local")


def remote_covers_cache_dir() -> str:
    return os.path.join(app_cache_dir(), "covers", "remote")


def negative_cover_cache_dir() -> str:
    return os.path.join(app_cache_dir(), "covers", "negative")


def audio_analysis_dir() -> str:
    return os.path.join(app_data_dir(), "audio_analysis")


def audio_features_db_path() -> str:
    return os.path.join(audio_analysis_dir(), "audio_features.db")


def recommendation_dir() -> str:
    return os.path.join(app_data_dir(), "recommendation")


def ai_assistant_dir() -> str:
    return os.path.join(app_data_dir(), "ai_assistant")


def artist_metadata_cache_dir() -> str:
    return os.path.join(app_cache_dir(), "artist_metadata")


def album_metadata_cache_db_path() -> str:
    return os.path.join(artist_metadata_cache_dir(), "index.sqlite")


def metadata_review_db_path() -> str:
    return os.path.join(app_data_dir(), "metadata_review.db")


def sync_manifest_dir() -> str:
    return os.path.join(app_data_dir(), "sync_manifests")


def paired_devices_path() -> str:
    return os.path.join(app_data_dir(), "paired_devices.json")


def subsonic_servers_path() -> str:
    return os.path.join(app_config_dir(), "subsonic_servers.json")


def radio_stations_path() -> str:
    return os.path.join(app_data_dir(), "radio_stations.json")


def auto_eq_cache_dir() -> str:
    return os.path.join(app_cache_dir(), "autoeq")


def legacy_data_dir() -> str:
    """Fallback directory for migrating old data."""
    return LEGACY_DIR
