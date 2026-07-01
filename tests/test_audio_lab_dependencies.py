"""Tests for Dependency Center."""



class TestDependencies:

    def test_check_dependencies_returns_dict(self):
        from core.audio_lab.dependencies import check_dependencies
        result = check_dependencies()
        assert isinstance(result, dict)
        assert "ffmpeg" in result
        assert "flac" in result
        assert "lame" in result

    def test_each_dep_has_required_fields(self):
        from core.audio_lab.dependencies import check_dependencies
        result = check_dependencies()
        for dep in result.values():
            assert "available" in dep
            assert "label" in dep
            assert "required_for" in dep
            assert isinstance(dep["available"], bool)

    def test_check_tools_returns_bool(self):
        from core.audio_lab.dependencies import check_tools
        result = check_tools("ffmpeg", "flac")
        assert isinstance(result, dict)
        assert "ffmpeg" in result
        assert isinstance(result["ffmpeg"], bool)

    def test_missing_for_returns_list(self):
        from core.audio_lab.dependencies import missing_for
        result = missing_for("flac")
        assert isinstance(result, list)

    def test_format_needs_tool(self):
        from core.audio_lab.dependencies import format_needs_tool
        assert format_needs_tool("wav") is None
        assert format_needs_tool("flac") == "flac"
        assert format_needs_tool("alac") == "ffmpeg"
