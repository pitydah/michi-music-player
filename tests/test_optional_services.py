"""Test that optional services initialize without errors."""
import pytest


def test_ums_transport_discover_no_crash():
    """UMS transport discovery doesn't crash without devices."""
    from sync.transports.usb_mass_storage import UsbMassStorageTransport
    transport = UsbMassStorageTransport()
    devices = transport.discover()
    assert isinstance(devices, list)


def test_micro_server_health_no_crash():
    """MicroServerService health check doesn't crash without server."""
    from integrations.micro_server_service import MicroServerService
    service = MicroServerService(host="127.0.0.1", port=19999)
    result = service.health()
    assert isinstance(result, dict)
    assert "ok" in result


def test_snapcast_no_server():
    """Snapcast service doesn't crash without server."""
    from integrations.home_audio_service import SnapcastService
    snap = SnapcastService(host="127.0.0.1", port=19999)
    with pytest.raises(Exception):
        snap.get_client_list()


def test_home_assistant_no_server():
    """Home Assistant service doesn't crash without server."""
    from integrations.home_audio_service import HomeAssistantService
    ha = HomeAssistantService(host="http://127.0.0.1:19999", token="test")
    states = ha.get_states()
    assert isinstance(states, list)
