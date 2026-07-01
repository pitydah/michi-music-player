"""Tests for MPD Config Builder."""

import os
import tempfile


class TestMpdConfigBuilder:
    def test_build_minimal(self):
        from audio.mpd.mpd_config_builder import build_mpd_config
        cfg = build_mpd_config(
            data_dir="/tmp/mpd-test",
            music_dir="/home/user/Music",
            device="hw:0,0")
        assert cfg.music_directory == "/home/user/Music"
        assert cfg.port == 6600
        assert cfg.bind_to_address == "127.0.0.1"
        assert len(cfg.audio_outputs) == 1
        assert cfg.audio_outputs[0]["mixer_type"] == "none"

    def test_build_with_dop(self):
        from audio.mpd.mpd_config_builder import build_mpd_config
        cfg = build_mpd_config(device="hw:1,0", dop=True)
        assert cfg.audio_outputs[0]["dop"] == "yes"

    def test_render_conf(self):
        from audio.mpd.mpd_config_builder import build_mpd_config, render_mpd_conf
        cfg = build_mpd_config(
            data_dir="/tmp/mpd-test",
            music_dir="/music",
            device="hw:0,0")
        text = render_mpd_conf(cfg)
        assert 'music_directory' in text
        assert '/music' in text
        assert 'bind_to_address' in text
        assert 'audio_output' in text
        assert 'hw:0,0' in text

    def test_write_conf(self):
        from audio.mpd.mpd_config_builder import build_mpd_config, write_mpd_conf
        cfg = build_mpd_config(
            data_dir="/tmp/mpd-test",
            music_dir="/music",
            device="hw:0,0")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
            path = f.name
        try:
            result = write_mpd_conf(cfg, path)
            assert result == path
            assert os.path.exists(path)
            with open(path) as f:
                content = f.read()
            assert "music_directory" in content
            assert "audio_output" in content
        finally:
            os.unlink(path)

    def test_default_data_dir(self):
        from audio.mpd.mpd_config_builder import default_data_dir
        path = default_data_dir()
        assert "michi-music-player" in path
        assert "mpd" in path
