# -*- coding: utf-8 -*-
"""Test for library_health."""

from core.audio_lab.library_health import compute_health


def test_compute_health_no_conn():
    result = compute_health(None)
    assert result is not None
    assert result["total_tracks"] == 0


def test_compute_health_returns_dict():
    result = compute_health(None, cache=None)
    assert isinstance(result, dict)
    assert "total_tracks" in result
