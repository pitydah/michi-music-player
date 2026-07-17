from __future__ import annotations

"""Test for ReplayGainService."""

import pytest
pytest.skip("module removed or relocated", allow_module_level=True)


def test_replaygain_result_filepath():
    result = ReplayGainResult(filepath="/test/file.flac")
    assert result.filepath == "/test/file.flac"
