"""Tests for Audio Settings Schema."""


class TestAudioSettingsSchema:
    def test_schema_has_audio_keys(self):
        from audio.settings.audio_settings_schema import AUDIO_SETTINGS_SCHEMA
        audio_keys = [k for k in AUDIO_SETTINGS_SCHEMA if k.startswith("audio/")]
        assert len(audio_keys) > 0

    def test_schema_has_eq_keys(self):
        from audio.settings.audio_settings_schema import AUDIO_SETTINGS_SCHEMA
        eq_keys = [k for k in AUDIO_SETTINGS_SCHEMA if k.startswith("eq/")]
        assert len(eq_keys) > 0

    def test_schema_has_mpd_keys(self):
        from audio.settings.audio_settings_schema import AUDIO_SETTINGS_SCHEMA
        mpd_keys = [k for k in AUDIO_SETTINGS_SCHEMA if k.startswith("audio/mpd/")]
        assert len(mpd_keys) > 0

    def test_each_entry_has_default_and_type(self):
        from audio.settings.audio_settings_schema import AUDIO_SETTINGS_SCHEMA
        for key, (default, typ) in AUDIO_SETTINGS_SCHEMA.items():
            assert isinstance(default, typ), f"{key}: {type(default)} != {typ}"

    def test_legacy_map_has_playback_keys(self):
        from audio.settings.audio_settings_schema import LEGACY_KEY_MAP
        assert "playback/replaygain" in LEGACY_KEY_MAP
        assert "playback/crossfade" in LEGACY_KEY_MAP
        assert "playback/gapless" in LEGACY_KEY_MAP

    def test_legacy_map_targets_exist(self):
        from audio.settings.audio_settings_schema import LEGACY_KEY_MAP, AUDIO_SETTINGS_SCHEMA
        for _legacy, canonical in LEGACY_KEY_MAP.items():
            assert canonical in AUDIO_SETTINGS_SCHEMA, f"Target {canonical} not in schema"
