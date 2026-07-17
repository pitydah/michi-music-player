from core.audio_lab.reporting import format_txt, format_csv, format_json


class TestReporting:
    def test_format_txt(self):
        result = format_txt({"key": "value"}, title="Test")
        assert "Test" in result
        assert "key" in result

    def test_format_json(self):
        result = format_json({"a": 1})
        assert '"a": 1' in result
