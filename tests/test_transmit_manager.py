"""Tests for transmit manager."""


def test_add_remove_device():
    from streaming.transmit_manager import TransmitManager, TransmitDevice
    mgr = TransmitManager()
    mgr._devices = []  # reset
    dev = mgr.add_device("Test", "http", "192.168.1.1", 8554)
    assert dev.name == "Test"
    assert len(mgr.get_devices()) == 1
    mgr.remove_device("Test")
    assert len(mgr.get_devices()) == 0


def test_active_device():
    from streaming.transmit_manager import TransmitManager, TransmitDevice
    mgr = TransmitManager()
    mgr._devices = []
    dev = mgr.add_device("Snap", "snapcast", "10.0.0.1", 1704)
    mgr.set_active(dev)
    assert mgr.get_active().name == "Snap"
    mgr.set_active(None)
    assert mgr.get_active() is None
