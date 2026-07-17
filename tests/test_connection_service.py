# -*- coding: utf-8 -*-
"""Test for ConnectionService."""

from core.connection_service import ConnectionService


def test_create():
    svc = ConnectionService()
    assert svc is not None


def test_health():
    svc = ConnectionService()
    result = svc.health()
    assert result is not None
    assert "available" in result
