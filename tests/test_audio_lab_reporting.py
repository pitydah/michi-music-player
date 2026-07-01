"""Tests for Report Center."""


class TestReporting:

    def test_format_txt_basic(self):
        from core.audio_lab.reporting import format_txt
        result = format_txt({"total": 10, "status": "ok"}, "Test")
        assert "=== Test ===" in result
        assert "total: 10" in result

    def test_format_csv_basic(self):
        from core.audio_lab.reporting import format_csv
        result = format_csv({"total": 10, "status": "ok"})
        assert "total" in result
        assert "10" in result

    def test_format_json_basic(self):
        from core.audio_lab.reporting import format_json
        result = format_json({"total": 10})
        assert '"total": 10' in result

    def test_health_to_txt(self):
        from core.audio_lab.reporting import health_to_txt
        health = {"total_tracks": 100, "analysed_tracks": 50, "hires_count": 10}
        result = health_to_txt(health)
        assert "100" in result
        assert "50" in result
        assert "Hi-Res" in result or "10" in result

    def test_health_to_json(self):
        from core.audio_lab.reporting import health_to_json
        result = health_to_json({"total_tracks": 100})
        assert '"total_tracks": 100' in result

    def test_format_txt_empty(self):
        from core.audio_lab.reporting import format_txt
        result = format_txt({})
        assert "=== Reporte ===" in result

    def test_format_csv_with_nested_dict(self):
        from core.audio_lab.reporting import format_csv
        result = format_csv({"stats": {"a": 1, "b": 2}})
        assert "a" in result
        assert "b" in result
