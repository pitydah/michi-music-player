# -*- coding: utf-8 -*-
"""Test for ReplayGainService."""

from core.audio_lab.replaygain_service import ReplayGainResult


def test_replaygain_result_defaults():
    result = ReplayGainResult()
    assert result is not None
    assert result.status == "pending"


def test_replaygain_result_filepath():
    result = ReplayGainResult(filepath="/test/file.flac")
    assert result.filepath == "/test/file.flac"
