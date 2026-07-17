# -*- coding: utf-8 -*-
"""Test for metadata_doctor."""

from core.audio_lab.metadata_doctor import suggest_normalizations


def test_suggest_normalizations_no_conn():
    result = suggest_normalizations(None)
    assert result is not None
    assert result == []


def test_suggest_normalizations_returns_list():
    result = suggest_normalizations(None)
    assert isinstance(result, list)
