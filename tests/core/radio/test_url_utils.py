import pytest
from core.radio.url_utils import (
    validate_and_normalize_url, urls_are_equivalent, UrlNormalizationError,
)


class TestValidateUrl:
    def test_accepts_http(self):
        url = validate_and_normalize_url("http://example.com/stream")
        assert url.startswith("http://")

    def test_accepts_https(self):
        url = validate_and_normalize_url("https://example.com/stream")
        assert url.startswith("https://")

    def test_adds_scheme(self):
        url = validate_and_normalize_url("example.com/stream")
        assert url.startswith("https://")

    def test_rejects_file_scheme(self):
        with pytest.raises(UrlNormalizationError):
            validate_and_normalize_url("file:///etc/passwd")

    def test_rejects_local_path(self):
        with pytest.raises(UrlNormalizationError):
            validate_and_normalize_url("/etc/passwd")

    def test_rejects_relative_path(self):
        with pytest.raises(UrlNormalizationError):
            validate_and_normalize_url("./relative/path")

    def test_rejects_ftp(self):
        with pytest.raises(UrlNormalizationError):
            validate_and_normalize_url("ftp://example.com/stream")

    def test_rejects_empty(self):
        with pytest.raises(UrlNormalizationError):
            validate_and_normalize_url("")

    def test_rejects_whitespace_only(self):
        with pytest.raises(UrlNormalizationError):
            validate_and_normalize_url("   ")

    def test_strips_whitespace(self):
        url = validate_and_normalize_url("  https://example.com/stream  ")
        assert url.startswith("https://example.com/stream")

    def test_lowercases_hostname(self):
        url = validate_and_normalize_url("HTTPS://EXAMPLE.COM/Stream")
        assert "example.com" in url

    def test_removes_fragment(self):
        url = validate_and_normalize_url("https://example.com/stream#frag")
        assert "#frag" not in url

    def test_normalizes_query_order(self):
        url1 = validate_and_normalize_url("https://example.com/?b=2&a=1")
        url2 = validate_and_normalize_url("https://example.com/?a=1&b=2")
        assert url1 == url2

    def test_accepts_ipv4(self):
        url = validate_and_normalize_url("https://192.168.1.1:8000/stream")
        assert "192.168.1.1" in url

    def test_accepts_ipv6(self):
        url = validate_and_normalize_url("https://[::1]:8000/stream")
        assert "[::1]" in url or "::1" in url

    def test_accepts_unicode_hostname(self):
        url = validate_and_normalize_url("https://ñ.example.com/stream")
        assert url is not None

    def test_rejects_home_path(self):
        with pytest.raises(UrlNormalizationError):
            validate_and_normalize_url("~/music/stream")


class TestUrlsAreEquivalent:
    def test_same_urls(self):
        assert urls_are_equivalent("https://example.com/stream", "https://example.com/stream")

    def test_trailing_slash(self):
        assert urls_are_equivalent("https://example.com/stream", "https://example.com/stream/")

    def test_case_insensitive_host(self):
        assert urls_are_equivalent("https://EXAMPLE.COM/Stream", "https://example.com/Stream")

    def test_different_queries(self):
        assert not urls_are_equivalent("https://example.com/?a=1", "https://example.com/?a=2")

    def test_different_paths(self):
        assert not urls_are_equivalent("https://example.com/stream1", "https://example.com/stream2")

    def test_same_url_without_scheme_input(self):
        assert urls_are_equivalent("example.com/stream", "https://example.com/stream")
