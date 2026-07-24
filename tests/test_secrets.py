"""Tests for secrets management — redaction, sensitive key detection."""


class TestSecretsRedact:
    def test_redact_short(self):
        from core.secrets import redact
        assert redact("ab") == "****"

    def test_redact_long(self):
        from core.secrets import redact
        result = redact("my-secret-token-12345")
        assert result == "my-s****"
        assert "token" not in result[5:]

    def test_redact_dict(self):
        from core.secrets import redact_dict
        d = {"api_key": "sk-1234567890", "name": "test", "nested": {"token": "abc123"}}
        r = redact_dict(d)
        assert r["api_key"] == "sk-****" or "****" in r["api_key"]
        assert r["name"] == "test"
        assert "abc" not in r["nested"]["token"]

    def test_redact_string(self):
        from core.secrets import redact_string
        msg = "Connecting with token=abc123 and password=secret!"
        r = redact_string(msg)
        assert "abc123" not in r
        assert "secret" not in r
        assert "****" in r

    def test_sanitize_log(self):
        from core.secrets import sanitize_log
        msg = 'api_key = "sk-proj-abc123def456"'
        r = sanitize_log(msg)
        assert "sk-proj" not in r
        assert "****" in r


class TestSecretsDetection:
    def test_is_sensitive_token(self):
        from core.secrets import is_sensitive
        assert is_sensitive("home_audio/ha_token")
        assert is_sensitive("mpd/password")
        assert is_sensitive("api_key")

    def test_is_sensitive_negative(self):
        from core.secrets import is_sensitive
        assert not is_sensitive("playback/default_volume")
        assert not is_sensitive("appearance/theme")
        assert not is_sensitive("library/exclude_hidden")
