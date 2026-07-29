"""Tests for Snapcast lifecycle — adapter, discovery, and TransmitManager."""
import json
from unittest.mock import MagicMock, patch


class TestSnapcastAdapter:
    """Cover Snapcast connection adapter behavior."""

    def test_snapcast_adapter_connects(self) -> None:
        from integrations.connections.adapters.snapcast_adapter import SnapcastAdapter
        adapter = SnapcastAdapter("192.168.1.100", port=1705, ssl=False)
        assert adapter._host == "192.168.1.100"
        assert adapter._port == 1705
        assert adapter.base_url == "http://192.168.1.100:1705"

    @patch("integrations.connections.adapters.snapcast_adapter.urllib.request.urlopen")
    def test_snapcast_adapter_rpc(self, mock_urlopen) -> None:
        fake_resp = MagicMock()
        fake_resp.read.return_value = json.dumps({
            "jsonrpc": "2.0", "id": 1,
            "result": {"server": {"groups": [{"id": "g1", "clients": []}], "clients": 0}},
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = fake_resp

        from integrations.connections.adapters.snapcast_adapter import SnapcastAdapter
        adapter = SnapcastAdapter("192.168.1.100")
        assert adapter.ping() is True
        caps = adapter.get_capabilities()
        assert "snapcast" in caps
        assert "multiroom" in caps
        assert mock_urlopen.called


class TestTransmitManagerLifecycle:
    """Cover transmit-device lifecycle and persistence."""

    def test_transmit_manager_add_device(self) -> None:
        from streaming.transmit_manager import TransmitManager
        mgr = TransmitManager()
        mgr._devices = []
        dev = mgr.add_device("Salon", "snapcast", "10.0.0.50", 1704)
        assert dev.name == "Salon"
        assert dev.stype == "snapcast"
        assert dev.address == "10.0.0.50"
        assert dev.port == 1704
        assert len(mgr.get_devices()) == 1

    def test_transmit_manager_remove_device(self) -> None:
        from streaming.transmit_manager import TransmitManager
        mgr = TransmitManager()
        mgr._devices = []
        mgr.add_device("Salon", "snapcast", "10.0.0.50", 1704)
        mgr.remove_device("Salon")
        assert len(mgr.get_devices()) == 0

    @patch("streaming.transmit_manager.json.dump")
    @patch("streaming.transmit_manager.json.load")
    @patch("streaming.transmit_manager.os.path.exists")
    @patch("streaming.transmit_manager.os.makedirs")
    @patch("streaming.transmit_manager.open", new_callable=MagicMock)
    def test_transmit_manager_persistence(
        self, mock_open, mock_makedirs, mock_exists, mock_load, mock_dump
    ) -> None:
        mock_exists.return_value = False
        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_open.return_value = mock_file

        from streaming.transmit_manager import TransmitDevice, TransmitManager
        mgr = TransmitManager()
        mgr._devices = []
        mgr.add_device("Cocina", "http", "10.0.0.60", 8554)

        written = mock_dump.call_args[0][0]
        assert written == [
            {
                "name": "Cocina",
                "stype": "http",
                "address": "10.0.0.60",
                "port": 8554,
            }
        ]

        reloaded = [TransmitDevice.from_dict(d) for d in written]
        assert reloaded[0].name == "Cocina"
        assert reloaded[0].port == 8554


class TestSnapcastDiscovery:
    """Cover Avahi and manual receiver discovery."""

    def test_snapcast_discovery_mdns(self) -> None:
        from integrations.snapcast import discovery as disc_module
        disc_module.AVAHI_BROWSE = "/usr/bin/avahi-browse"

        fake_stdout = (
            "+;eth0;IPv4;Snapcast-Living;_snapcast._tcp;local;10.0.0.10;1704;\n"
            "+;eth0;IPv4;Snapcast-Kitchen;_snapcast._tcp;local;10.0.0.20;1704;\n"
        )
        mock_run = MagicMock(stdout=fake_stdout, returncode=0)

        disc = disc_module.SnapClientDiscovery()
        with patch.object(disc_module, "subprocess") as mock_subp:
            mock_subp.run.return_value = mock_run
            result = disc._discover_avahi()

        assert len(result) == 2
        assert result[0]["name"] == "Snapcast-Living"
        assert result[0]["host"] == "10.0.0.10"
        assert result[0]["port"] == 1704
        assert result[1]["name"] == "Snapcast-Kitchen"
        assert result[1]["host"] == "10.0.0.20"
        assert result[1]["port"] == 1704
        mock_subp.run.assert_called_once()

    def test_manual_receiver_persists_across_instances(self) -> None:
        from integrations.snapcast.discovery import SnapClientDiscovery

        settings = MemorySettings()
        first = SnapClientDiscovery(settings=settings)
        first.add_manual("10.0.0.30", 1704, "Studio")

        second = SnapClientDiscovery(settings=settings)

        assert second.clients() == [
            {
                "id": "manual:10.0.0.30:1704",
                "name": "Studio",
                "host": "10.0.0.30",
                "port": 1704,
                "type": "snapclient",
                "backend": "snapcast",
                "manual": True,
                "available": True,
            }
        ]

    def test_remove_manual_receiver_updates_persistence(self) -> None:
        from integrations.snapcast.discovery import SnapClientDiscovery

        settings = MemorySettings()
        discovery = SnapClientDiscovery(settings=settings)
        discovery.add_manual("10.0.0.30", 1704, "Studio")

        discovery.remove_manual("manual:10.0.0.30:1704")

        reloaded = SnapClientDiscovery(settings=settings)
        assert reloaded.clients() == []


class MemorySettings:
    """Minimal in-memory QSettings substitute for persistence tests."""

    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    def value(self, key: str, default: object = None) -> object:
        return self.values.get(key, default)

    def setValue(self, key: str, value: object) -> None:
        self.values[key] = value

    def sync(self) -> None:
        return None
