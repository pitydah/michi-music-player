"""Audio Settings Schema — canonical keys and defaults for audio configuration.

This module defines the single source of truth for all audio-related settings.
Duplicate or legacy keys are mapped here; the rest of the codebase should read
canonical keys from this schema.

Canonical keys are the ones actually used by GStreamerEngine._load_settings()
and the UI. Legacy keys are kept for backwards compatibility during migration.
"""

import os


AUDIO_SETTINGS_SCHEMA: dict[str, tuple] = {
    # ── Profile & Backend ──
    "audio/profile": ("standard", str),
    "audio/backend": ("auto", str),
    "audio/mode": ("standard", str),

    # ── Output device ──
    "audio/output_device_id": ("auto", str),
    "audio/device": ("default", str),
    "audio/device_backend": ("auto", str),
    "audio/alsa_device": ("", str),
    "audio/alsa_use_hw": (False, bool),

    # ── Buffer / resample ──
    "audio/buffer_ms": (100, int),
    "audio/allow_resample": (True, bool),
    "audio/resample_quality": ("medium", str),
    "audio/target_rate": (0, int),
    "audio/target_format": ("auto", str),
    "audio/allow_fallback": (True, bool),

    # ── Gapless / crossfade ──
    "audio/gapless_enabled": (True, bool),
    "audio/crossfade_seconds": (0, int),

    # ── ReplayGain ──
    "audio/replaygain_enabled": (False, bool),
    "audio/replaygain_mode": ("track", str),
    "audio/replaygain_preamp_db": (0.0, float),
    "audio/replaygain_headroom_db": (0.0, float),

    # ── Spectrum ──
    "audio/spectrum_enabled": (False, bool),

    # ── DSD ──
    "audio/dsd_mode": ("pcm", str),
    "audio/dsd_pcm_rate": ("auto", str),

    # ── EQ ──
    "eq/enabled": (False, bool),
    "eq/mode": ("graphic", str),
    "eq/preamp": (0.0, float),
    "eq/preset": ("Flat", str),
    "eq/show_spectrum": (False, bool),

    # ── MPD ──
    "audio/mpd/enabled": (False, bool),
    "audio/mpd/mode": ("local", str),
    "audio/mpd/host": ("127.0.0.1", str),
    "audio/mpd/port": (6600, int),
    "audio/mpd/password": ("", str),
    "audio/mpd/music_directory": (os.path.expanduser("~/Música"), str),
    "audio/mpd/local_music_root": (os.path.expanduser("~/Música"), str),
    "audio/mpd/remote_music_root": ("", str),
    "audio/mpd/auto_start_local": (True, bool),
    "audio/mpd/bitperfect_verify": (True, bool),
    "audio/mpd/dop_enabled": (False, bool),
    "audio/mpd/path_mapping_enabled": (True, bool),
}


LEGACY_KEY_MAP: dict[str, str] = {
    "playback/replaygain": "audio/replaygain_enabled",
    "playback/crossfade": "audio/crossfade_seconds",
    "playback/gapless": "audio/gapless_enabled",
}
