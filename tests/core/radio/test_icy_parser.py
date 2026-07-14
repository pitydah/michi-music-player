from core.radio.icy_parser import (
    parse_icy_headers, parse_stream_title, IcyMetadataTracker,
    parse_icy_metaint,
)


class TestParseIcyHeaders:
    def test_parses_icy_name(self):
        raw = b"icy-name: My Radio Station\r\nicy-genre: Rock\r\n"
        meta = parse_icy_headers(raw)
        assert meta.icy_name == "My Radio Station"
        assert meta.icy_genre == "Rock"

    def test_parses_icy_br(self):
        raw = b"icy-br: 128\r\n"
        meta = parse_icy_headers(raw)
        assert meta.icy_br == "128"

    def test_parses_icy_url(self):
        raw = b"icy-url: https://example.com\r\n"
        meta = parse_icy_headers(raw)
        assert meta.icy_url == "https://example.com"

    def test_handles_missing_values(self):
        meta = parse_icy_headers(b"")
        assert meta.icy_name == ""

    def test_handles_binary_encoding(self):
        raw = b"icy-name: \xff\xfeR\x00a\x00d\x00i\x00o\x00\r\n"
        meta = parse_icy_headers(raw)
        assert isinstance(meta.icy_name, str)

    def test_truncates_long_fields(self):
        raw = b"icy-name: " + b"X" * 2000 + b"\r\n"
        meta = parse_icy_headers(raw)
        assert len(meta.icy_name) <= 1024

    def test_handles_null_bytes(self):
        raw = b"icy-name: Radio\x00Station\r\n"
        meta = parse_icy_headers(raw)
        assert "\x00" not in meta.icy_name

    def test_parses_icy_metaint(self):
        raw = b"icy-metaint: 8192\r\n"
        val = parse_icy_metaint(raw)
        assert val == 8192

    def test_icy_metaint_default(self):
        assert parse_icy_metaint(b"") == 0


class TestParseStreamTitle:
    def test_parses_stream_title(self):
        data = b"StreamTitle='Song Name - Artist';"
        title = parse_stream_title(data)
        assert title == "Song Name - Artist"

    def test_handles_double_quotes(self):
        data = b'StreamTitle="Song Name - Artist";'
        title = parse_stream_title(data)
        assert title == "Song Name - Artist"

    def test_returns_none_for_empty(self):
        assert parse_stream_title(b"") is None

    def test_returns_none_for_null_only(self):
        assert parse_stream_title(b"\x00" * 10) is None

    def test_handles_repeated_same_title(self):
        data = b"StreamTitle='Test';"
        title = parse_stream_title(data)
        assert title == "Test"

    def test_strips_non_printable(self):
        data = b"StreamTitle='Test\x01\x02Song';"
        title = parse_stream_title(data)
        assert title is not None


class TestIcyMetadataTracker:
    def test_tracks_header_changes(self):
        changes = []
        tracker = IcyMetadataTracker(lambda m: changes.append(m))
        tracker.update_headers(b"icy-name: Radio1\r\n")
        assert len(changes) == 1
        tracker.update_headers(b"icy-name: Radio1\r\n")
        assert len(changes) == 1
        tracker.update_headers(b"icy-name: Radio2\r\n")
        assert len(changes) == 2

    def test_tracks_stream_title_changes(self):
        changes = []
        tracker = IcyMetadataTracker(lambda m: changes.append(m))
        tracker.update_stream_title(b"StreamTitle='Song A';")
        assert len(changes) == 1
        tracker.update_stream_title(b"StreamTitle='Song A';")
        assert len(changes) == 1
        tracker.update_stream_title(b"StreamTitle='Song B';")
        assert len(changes) == 2

    def test_reset(self):
        tracker = IcyMetadataTracker()
        tracker.update_headers(b"icy-name: Test\r\n")
        assert tracker.current.icy_name == "Test"
        tracker.reset()
        assert tracker.current.icy_name == ""

    def test_headers_emit_only_on_change(self):
        changes = []
        tracker = IcyMetadataTracker(lambda m: changes.append(m))
        tracker.update_headers(b"icy-name: A\r\nicy-genre: Rock\r\n")
        tracker.update_headers(b"icy-name: A\r\nicy-genre: Pop\r\n")
        assert len(changes) == 2
