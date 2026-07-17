from integrations.michi_ecosystem.sanitizer import sanitize, sanitize_for_diagnostic


class TestSanitizer:
    def test_sanitize_dict(self):
        data = {"name": "test", "path": "/home/user/music"}
        result = sanitize(data)
        assert result["path"] != "/home/user/music"

    def test_sanitize_for_diagnostic(self):
        data = {"status": "ok", "path": "/secret"}
        result = sanitize_for_diagnostic(data)
        assert result["status"] == "ok"
