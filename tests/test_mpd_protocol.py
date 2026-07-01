"""Tests for MPD protocol parser."""

import pytest


class TestParseResponse:
    def test_ok_response(self):
        from audio.mpd.mpd_protocol import parse_response
        resp = parse_response("OK\n")
        assert resp.is_ok is True
        assert resp.is_ack is False

    def test_ack_response(self):
        from audio.mpd.mpd_protocol import parse_response
        resp = parse_response("ACK [5@0] {play} current song is not in queue\n")
        assert resp.is_ack is True
        assert resp.is_ok is False
        assert resp.ack_code == 5
        assert "current song" in resp.ack_message

    def test_key_value_pairs(self):
        from audio.mpd.mpd_protocol import parse_response
        raw = "state: play\nvolume: 70\nrepeat: 0\nOK\n"
        resp = parse_response(raw)
        assert resp.pairs["state"] == "play"
        assert resp.pairs["volume"] == "70"
        assert resp.pairs["repeat"] == "0"

    def test_multiline_list(self):
        from audio.mpd.mpd_protocol import parse_response
        raw = (
            "file: song1.flac\n"
            "Title: Song One\n"
            "Artist: Artist A\n"
            "\n"
            "file: song2.flac\n"
            "Title: Song Two\n"
            "Artist: Artist B\n"
            "OK\n"
        )
        resp = parse_response(raw)
        assert "file" in resp.lists
        assert len(resp.lists["file"]) == 2
        assert resp.lists["file"][0]["Title"] == "Song One"
        assert resp.lists["file"][1]["Title"] == "Song Two"

    def test_empty_response_raises(self):
        from audio.mpd.mpd_protocol import parse_response
        from audio.mpd.mpd_errors import MpdProtocolError
        with pytest.raises(MpdProtocolError):
            parse_response("")

    def test_ack_code_without_tag(self):
        from audio.mpd.mpd_protocol import parse_response
        resp = parse_response("ACK [2@0] {play} don't know 'foo'\n")
        assert resp.ack_code == 2
        assert "don't know" in resp.ack_message

    def test_require_ok_raises_on_ack(self):
        from audio.mpd.mpd_protocol import parse_response
        from audio.mpd.mpd_errors import MpdAckError
        resp = parse_response("ACK [1@0] {play} error\n")
        with pytest.raises(MpdAckError):
            resp.require_ok()

    def test_require_ok_passes(self):
        from audio.mpd.mpd_protocol import parse_response
        resp = parse_response("OK\n")
        resp.require_ok()

    def test_first_list(self):
        from audio.mpd.mpd_protocol import parse_response
        raw = "file: a.flac\nTitle: A\nOK\n"
        resp = parse_response(raw)
        lst = resp.first_list()
        assert len(lst) == 1
        assert lst[0]["file"] == "a.flac"

    def test_outputs_list(self):
        from audio.mpd.mpd_protocol import parse_response
        raw = (
            "outputid: 0\n"
            "outputname: My DAC\n"
            "outputenabled: 1\n"
            "\n"
            "outputid: 1\n"
            "outputname: HDMI\n"
            "outputenabled: 0\n"
            "OK\n"
        )
        resp = parse_response(raw)
        assert "outputid" in resp.lists
        assert len(resp.lists["outputid"]) == 2
        assert resp.lists["outputid"][0]["outputname"] == "My DAC"


class TestMpdClientMock:
    def test_parse_status_via_client(self):
        from audio.mpd.mpd_client import MpdClient
        from audio.mpd.mpd_protocol import parse_response
        raw = (
            "volume: 80\n"
            "repeat: 0\n"
            "random: 0\n"
            "single: 0\n"
            "consume: 0\n"
            "playlist: 42\n"
            "playlistlength: 10\n"
            "state: play\n"
            "song: 2\n"
            "songid: 5\n"
            "elapsed: 30.5\n"
            "duration: 240.0\n"
            "bitrate: 1411\n"
            "audio: 44100:24:2\n"
            "OK\n"
        )
        resp = parse_response(raw)
        assert resp.pairs["state"] == "play"
        assert resp.pairs["volume"] == "80"
        assert resp.pairs["elapsed"] == "30.5"
        assert resp.pairs["duration"] == "240.0"
        assert resp.pairs["song"] == "2"

    def test_escape_path(self):
        from audio.mpd.mpd_client import _escape
        assert _escape("normal.flac") == "normal.flac"
        assert _escape('quote"file.flac') == 'quote\\"file.flac'
        assert _escape("back\\slash.flac") == "back\\\\slash.flac"

    def test_int_or(self):
        from audio.mpd.mpd_client import _int_or
        assert _int_or("42", 0) == 42
        assert _int_or(None, -1) == -1
        assert _int_or("abc", 0) == 0

    def test_float_or(self):
        from audio.mpd.mpd_client import _float_or
        assert _float_or("30.5", 0.0) == 30.5
        assert _float_or(None, 0.0) == 0.0
