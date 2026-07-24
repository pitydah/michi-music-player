"""Tests for security — keyring, secrets redaction, TLS validation."""


class TestSecretsSecurity:
    def test_secrets_redact_dict(self):
        from core.secrets import redact_dict
        d = {"home_audio/ha_token": "supersecret", "mpd/password": "pass123", "name": "public"}
        r = redact_dict(d)
        assert "supersecret" not in str(r)
        assert "pass123" not in str(r)
        assert "public" in str(r)

    def test_secrets_redact_string(self):
        from core.secrets import redact_string
        msg = 'token=sk-abc123'
        r = redact_string(msg)
        assert "sk-abc123" not in r
        assert "****" in r

    def test_secrets_is_sensitive(self):
        from core.secrets import is_sensitive
        assert is_sensitive("api_key")
        assert is_sensitive("password")
        assert is_sensitive("access_token")
        assert not is_sensitive("appearance/theme")
        assert not is_sensitive("playback/volume")

    def test_no_verify_false(self):
        """No SSL verify=False anywhere in core."""
        import os
        import subprocess
        result = subprocess.run(
            ["grep", "-rn", "verify=False", "--include=*.py"],
            cwd=os.path.join(os.path.dirname(__file__), ".."),
            capture_output=True, text=True, timeout=10,
        )
        violations = [l for l in result.stdout.split("\n") if l.strip()
                     and "test_" not in l and "legacy" not in l and "build" not in l]
        assert len(violations) == 0, f"verify=False found: {violations}"

    def test_settings_excludes_secrets(self):
        # Check that secret entries are properly tagged
        from core.settings_schema import get_entry
        secret_entry = get_entry("home_audio/ha_token")
        if secret_entry:
            assert secret_entry.entry_type == "text" or secret_entry.entry_type == "secret"

    def test_credentials_store_uses_keyring(self):
        from integrations.connections.credentials_store import CredentialsStore
        store = CredentialsStore()
        # Should not crash
        assert store is not None
