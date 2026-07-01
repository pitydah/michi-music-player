"""Tests for Audio Settings Migrator."""

from unittest.mock import patch


class TestAudioSettingsMigrator:
    def test_migrate_legacy_keys_noop_when_legacy_none(self):
        with patch("audio.settings.audio_settings_migrator.get") as mock_get:
            mock_get.return_value = None
            from audio.settings.audio_settings_migrator import migrate_legacy_keys
            result = migrate_legacy_keys(dry_run=True)
            assert result == []

    def test_migrate_legacy_keys_dry_run_does_not_write(self):
        with patch("audio.settings.audio_settings_migrator.get") as mock_get:
            with patch("audio.settings.audio_settings_migrator.set_") as mock_set:
                def fake_get(key):
                    legacy = {"playback/replaygain": True,
                              "playback/crossfade": 3,
                              "playback/gapless": False}
                    audio_defaults = {
                        "audio/replaygain_enabled": False,
                        "audio/crossfade_seconds": 0,
                        "audio/gapless_enabled": True,
                    }
                    if key in legacy:
                        return legacy[key]
                    if key in audio_defaults:
                        return audio_defaults[key]
                    return None
                mock_get.side_effect = fake_get
                from audio.settings.audio_settings_migrator import migrate_legacy_keys
                result = migrate_legacy_keys(dry_run=True)
                assert len(result) == 3
                mock_set.assert_not_called()

    def test_migrate_legacy_keys_writes_on_real(self):
        with patch("audio.settings.audio_settings_migrator.get") as mock_get:
            with patch("audio.settings.audio_settings_migrator.set_") as mock_set:
                def fake_get(key):
                    legacy = {"playback/replaygain": True,
                              "playback/crossfade": 3,
                              "playback/gapless": False}
                    audio_defaults = {
                        "audio/replaygain_enabled": False,
                        "audio/crossfade_seconds": 0,
                        "audio/gapless_enabled": True,
                    }
                    if key in legacy:
                        return legacy[key]
                    if key in audio_defaults:
                        return audio_defaults[key]
                    return None
                mock_get.side_effect = fake_get
                from audio.settings.audio_settings_migrator import migrate_legacy_keys
                result = migrate_legacy_keys(dry_run=False)
                assert len(result) == 3
                assert mock_set.call_count == 3

    def test_ensure_mpd_settings(self):
        with patch("audio.settings.audio_settings_migrator.get") as mock_get:
            with patch("audio.settings.audio_settings_migrator.set_") as mock_set:
                mock_get.return_value = None
                from audio.settings.audio_settings_migrator import ensure_mpd_settings
                result = ensure_mpd_settings(dry_run=False)
                assert len(result) > 0
                assert mock_set.call_count > 0

    def test_migrate_all_runs_both(self):
        with patch("audio.settings.audio_settings_migrator.get") as mock_get:
            with patch("audio.settings.audio_settings_migrator.set_") as mock_set:
                mock_get.return_value = None
                from audio.settings.audio_settings_migrator import migrate_all
                result = migrate_all(dry_run=True)
                assert len(result) > 0

    def test_schema_default_returns_none_for_unknown(self):
        from audio.settings.audio_settings_migrator import _schema_default
        assert _schema_default("nonexistent/key") is None

    def test_schema_default_returns_value(self):
        from audio.settings.audio_settings_migrator import _schema_default
        assert _schema_default("audio/profile") == "standard"
