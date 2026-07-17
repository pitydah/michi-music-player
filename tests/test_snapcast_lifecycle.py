"""Tests for Snapcast lifecycle — adapter, discovery, and TransmitManager."""
import json
from unittest.mock import MagicMock, patch


class TestSnapcastAdapter:
    def test_snapcast_adapter_connects(self):
        from integrations.connections.adapters.snapcast_adapter import SnapcastAdapter
        adapter = SnapcastAdapter("192.168.1.100", port=1705, ssl=False)
        assert adapter._host == "192.168.1.100"
        assert adapter._port == 1705
        assert adapter.base_url == "http://192.168.1.100:1705"

    @patch("integrations.connections.adapters.snapcast_adapter.urllib.request.urlopen")
    def test_snapcast_adapter_rpc(self, mock_urlopen):
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
    def test_transmit_manager_add_device(self):
        from streaming.transmit_manager import TransmitManager
        mgr = TransmitManager()
        mgr._devices = []
        dev = mgr.add_device("Salon", "snapcast", "10.0.0.50", 1704)
        assert dev.name == "Salon"
        assert dev.stype == "snapcast"
        assert dev.address == "10.0.0.50"
        assert dev.port == 1704
        assert len(mgr.get_devices()) == 1

    def test_transmit_manager_remove_device(self):
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
    def test_transmit_manager_persistence(self, mock_open, mock_makedirs,
                                          mock_exists, mock_load, mock_dump):
        mock_exists.return_value = False
        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_open.return_value = mock_file

        from streaming.transmit_manager import TransmitManager, TransmitDevice
        mgr = TransmitManager()
        mgr._devices = []
        mgr.add_device("Cocina", "http", "10.0.0.60", 8554)

        written = mock_dump.call_args[0][0]
        assert written == [{"name": "Cocina", "stype": "http", "address": "10.0.0.60", "port": 8554}]

        reloaded = [TransmitDevice.from_dict(d) for d in written]
        assert reloaded[0].name == "Cocina"
        assert reloaded[0].port == 8554


class TestSnapcastDiscovery:
    def test_snapcast_discovery_mdns(self):
        from integrations.snapcast import discovery as disc_module
        disc_module.AVAHi_BROWSE = "/usr/bin/avahi-browse"

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
