# -*- coding: utf-8 -*-
"""Test for AccessibilityService."""

from core.accessibility_service import AccessibilityService


def test_create():
    svc = AccessibilityService()
    assert svc is not None


def test_health():
    svc = AccessibilityService()
    result = svc.health()
    assert result is not None
    assert result["available"] is True
