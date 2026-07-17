from core.audio_lab.dependencies import check_dependencies


class TestDependencies:
    def test_check(self):
        result = check_dependencies()
        assert isinstance(result, dict)
        assert "ffmpeg" in result
