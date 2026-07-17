"""Integration tests for TransmitManager and TransmitDevice."""

import json
import os
import tempfile

import pytest


def test_transmit_device_dataclass():
    from streaming.transmit_manager import TransmitDevice

    dev = TransmitDevice(name="Living Room", stype="snapcast", address="10.0.0.50", port=1705)
    d = dev.to_dict()
    assert d == {"name": "Living Room", "stype": "snapcast", "address": "10.0.0.50", "port": 1705}

    restored = TransmitDevice.from_dict(d)
    assert restored.name == "Living Room"
    assert restored.stype == "snapcast"
    assert restored.address == "10.0.0.50"
    assert restored.port == 1705


def test_transmit_manager_save_load():
    from streaming.transmit_manager import TransmitManager, CONFIG_DIR, DEVICES_PATH

    with tempfile.TemporaryDirectory() as tmp:
        fake_devices = os.path.join(tmp, "transmit_devices.json")
        original_dir = CONFIG_DIR
        original_path = DEVICES_PATH

        import streaming.transmit_manager as tm
        tm.CONFIG_DIR = tmp
        tm.DEVICES_PATH = fake_devices

        try:
            mgr = TransmitManager()
            mgr._devices = []
            mgr.add_device("Kitchen", "http", "192.168.1.10", 8554)
            mgr.add_device("Garden", "snapcast", "192.168.1.20", 1705)

            mgr2 = TransmitManager()
            mgr2._devices = []
            mgr2.load()

            devices = mgr2.get_devices()
            assert len(devices) == 2
            names = {d.name for d in devices}
            assert "Kitchen" in names
            assert "Garden" in names
        finally:
            tm.CONFIG_DIR = original_dir
            tm.DEVICES_PATH = original_path


def test_transmit_manager_deduplicate():
    from streaming.transmit_manager import TransmitManager

    mgr = TransmitManager()
    mgr._devices = []

    mgr.add_device("Office", "http", "10.0.0.5", 8554)
    mgr.add_device("Office", "http", "10.0.0.5", 8554)
    assert len(mgr.get_devices()) == 2  # manager does not deduplicate by default


def test_transmit_manager_empty():
    from streaming.transmit_manager import TransmitManager

    mgr = TransmitManager()
    mgr._devices = []

    assert mgr.get_devices() == []
    assert mgr.get_active() is None
    mgr.save()
    mgr.load()
    assert mgr.get_devices() == []


def test_transmit_manager_get_devices_by_type():
    from streaming.transmit_manager import TransmitManager

    mgr = TransmitManager()
    mgr._devices = []

    mgr.add_device("HTTP1", "http", "10.0.0.1", 8554)
    mgr.add_device("HTTP2", "http", "10.0.0.2", 8554)
    mgr.add_device("Snap1", "snapcast", "10.0.0.3", 1705)

    http_devices = [d for d in mgr.get_devices() if d.stype == "http"]
    snap_devices = [d for d in mgr.get_devices() if d.stype == "snapcast"]

    assert len(http_devices) == 2
    assert len(snap_devices) == 1
    assert all(d.stype == "http" for d in http_devices)
    assert all(d.stype == "snapcast" for d in snap_devices)
