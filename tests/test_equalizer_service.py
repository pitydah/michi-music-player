# -*- coding: utf-8 -*-
"""Test for EqualizerService."""

from core.equalizer_service import EqualizerService


def test_create():
    svc = EqualizerService()
    assert svc is not None


def test_health():
    svc = EqualizerService()
    result = svc.health()
    assert result is not None
    assert "available" in result
