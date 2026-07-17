# -*- coding: utf-8 -*-
"""Test for DiagnosticsService."""

from core.diagnostics_service import DiagnosticsService


def test_create():
    svc = DiagnosticsService()
    assert svc is not None


def test_check_service_health():
    svc = DiagnosticsService()
    result = svc.check_service_health()
    assert result is not None
    assert result["status"] == "ok"
