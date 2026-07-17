# -*- coding: utf-8 -*-
"""Test for DeviceDiscoveryService."""

from core.device_discovery_service import DeviceDiscoveryService


def test_create():
    svc = DeviceDiscoveryService()
    assert svc is not None


def test_health():
    svc = DeviceDiscoveryService()
    result = svc.health()
    assert result is not None
    assert result["available"] is True
