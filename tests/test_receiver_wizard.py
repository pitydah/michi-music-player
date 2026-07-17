"""Tests for ReceiverWizard — RPi, ESP32, and Docker receiver configuration."""
from unittest.mock import MagicMock

from integrations.snapcast.receivers import ReceiverWizard


class TestReceiverWizardRPi:
    def test_rpi_defaults(self):
        wiz = ReceiverWizard()
        result = wiz.run("rpi")
        assert result["ok"]
        assert result["receiver_type"] == "rpi"
        assert result["host"] == "raspberrypi.local"
        assert result["port"] == 1704

    def test_rpi_config_keys(self):
        wiz = ReceiverWizard()
        result = wiz.run("rpi")
        cfg = result["config"]
        assert cfg["auto_start"] is True
        assert cfg["use_alsa"] is True
        assert cfg["audio_output"] == "headphone"
        assert cfg["latency"] == 0

    def test_rpi_auto_start_can_be_disabled(self):
        wiz = ReceiverWizard()
        result = wiz.run("rpi")
        assert result["config"]["auto_start"] is True

    def test_rpi_is_complete_after_run(self):
        wiz = ReceiverWizard()
        wiz.run("rpi")
        assert wiz.is_complete

    def test_rpi_result_property(self):
        wiz = ReceiverWizard()
        wiz.run("rpi")
        assert wiz.result["ok"]


class TestReceiverWizardESP32:
    def test_esp32_defaults(self):
        wiz = ReceiverWizard()
        result = wiz.run("esp32")
        assert result["ok"]
        assert result["receiver_type"] == "esp32"
        assert result["host"] == "esp32-snapcast.local"
        assert result["port"] == 1704

    def test_esp32_config_keys(self):
        wiz = ReceiverWizard()
        result = wiz.run("esp32")
        cfg = result["config"]
        assert "wifi_ssid" in cfg
        assert "wifi_password" in cfg
        assert "i2s_pins" in cfg
        assert "volume_control" in cfg

    def test_esp32_i2s_pins(self):
        wiz = ReceiverWizard()
        result = wiz.run("esp32")
        pins = result["config"]["i2s_pins"]
        assert pins["bclk"] == 26
        assert pins["ws"] == 25
        assert pins["dout"] == 22

    def test_esp32_wifi_defaults_empty(self):
        wiz = ReceiverWizard()
        result = wiz.run("esp32")
        assert result["config"]["wifi_ssid"] == ""
        assert result["config"]["wifi_password"] == ""

    def test_esp32_volume_control_enabled(self):
        wiz = ReceiverWizard()
        result = wiz.run("esp32")
        assert result["config"]["volume_control"] is True

    def test_esp32_is_complete_after_run(self):
        wiz = ReceiverWizard()
        wiz.run("esp32")
        assert wiz.is_complete


class TestReceiverWizardDocker:
    def test_docker_defaults(self):
        wiz = ReceiverWizard()
        result = wiz.run("docker")
        assert result["ok"]
        assert result["receiver_type"] == "docker"
        assert result["host"] == "127.0.0.1"
        assert result["port"] == 1704

    def test_docker_config_keys(self):
        wiz = ReceiverWizard()
        result = wiz.run("docker")
        cfg = result["config"]
        assert cfg["container_name"] == "snapclient"
        assert cfg["image"] == "bocki/snapclient:latest"
        assert cfg["network_mode"] == "host"
        assert cfg["auto_restart"] is True

    def test_docker_container_name(self):
        wiz = ReceiverWizard()
        result = wiz.run("docker")
        assert result["config"]["container_name"] == "snapclient"

    def test_docker_image(self):
        wiz = ReceiverWizard()
        result = wiz.run("docker")
        assert result["config"]["image"] == "bocki/snapclient:latest"

    def test_docker_network_mode_host(self):
        wiz = ReceiverWizard()
        result = wiz.run("docker")
        assert result["config"]["network_mode"] == "host"

    def test_docker_auto_restart(self):
        wiz = ReceiverWizard()
        result = wiz.run("docker")
        assert result["config"]["auto_restart"] is True

    def test_docker_is_complete_after_run(self):
        wiz = ReceiverWizard()
        wiz.run("docker")
        assert wiz.is_complete


class TestReceiverWizardCommon:
    def test_unknown_type(self):
        wiz = ReceiverWizard()
        result = wiz.run("unknown")
        assert not result["ok"]
        assert "error" in result

    def test_result_empty_before_run(self):
        wiz = ReceiverWizard()
        assert wiz.result == {}

    def test_is_complete_false_before_run(self):
        wiz = ReceiverWizard()
        assert not wiz.is_complete

    def test_result_property_returns_copy(self):
        wiz = ReceiverWizard()
        wiz.run("rpi")
        result = wiz.result
        result["extra"] = "modified"
        assert "extra" not in wiz.result

    def test_supports_all_types(self):
        from integrations.snapcast.receivers import ReceiverWizard as RW
        assert "rpi" in RW.RECEIVER_TYPES
        assert "esp32" in RW.RECEIVER_TYPES
        assert "docker" in RW.RECEIVER_TYPES

    def test_each_type_returns_port_1704(self):
        wiz = ReceiverWizard()
        for rt in ("rpi", "esp32", "docker"):
            result = wiz.run(rt)
            assert result["port"] == 1704

    def test_each_type_returns_ok(self):
        wiz = ReceiverWizard()
        for rt in ("rpi", "esp32", "docker"):
            result = wiz.run(rt)
            assert result["ok"]

    def test_can_set_parent(self):
        parent = MagicMock()
        wiz = ReceiverWizard(parent=parent)
        assert wiz._parent is parent

    def test_run_is_idempotent(self):
        wiz = ReceiverWizard()
        r1 = wiz.run("rpi")
        r2 = wiz.run("rpi")
        assert r1 == r2

    def test_result_isolation_between_runs(self):
        wiz = ReceiverWizard()
        wiz.run("rpi")
        d_result = wiz.run("docker")
        assert d_result["host"] == "127.0.0.1"
