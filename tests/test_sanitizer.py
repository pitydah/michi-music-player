from integrations.michi_ecosystem.sanitizer import sanitize_for_diagnostic, sanitize_report


class TestSanitizer:
    def test_sanitize_report(self):
        data = {"name": "test", "path": "/home/user/music"}
        result = sanitize_report(data)
        assert "path" not in result or result["path"] != "/home/user/music"

    def test_sanitize_for_diagnostic(self):
        data = {"status": "ok", "path": "/secret"}
        result = sanitize_for_diagnostic(data)
        assert result["status"] == "ok"
