"""Tests for HomeAudioHandlers — connection, multiroom, devices, groups, snapcast."""
from unittest.mock import MagicMock, patch

import pytest

from legacy_widgets.ui.controllers.legacy_controllers.home_audio_handlers import HomeAudioHandlers


@pytest.fixture
def win(qapp):
    from PySide6.QtWidgets import QWidget
    w = MagicMock(spec=QWidget)
    w._home_audio_view = MagicMock()
    w._toast_svc = MagicMock()
    w._ha_client = MagicMock()
    w._ha_connected = False
    w._snapserver = MagicMock()
    w._snapserver.is_running = False
    w._snap_discovery = MagicMock()
    w._michi_api = MagicMock()
    w._local_media = MagicMock()
    w._mdns = MagicMock()
    w._audio_capture = MagicMock()
    w._group_mgr = MagicMock()
    w._ha_ctrl = MagicMock()
    w._ctx = MagicMock()
    w._ctx.transmit_mgr = MagicMock()
    w._show_preferences = MagicMock()
    return w


@pytest.fixture
def handlers(win):
    return HomeAudioHandlers(win)


class TestHomeAudioHandlers:
    def test_wire_signals_connects_view_signals(self, handlers, win):
        handlers.wire_signals()
        v = win._home_audio_view
        v.connect_requested.connect.assert_called_with(handlers.on_connect)
        v.refresh_requested.connect.assert_called_with(handlers.on_refresh)
        v.enable_multiroom_requested.connect.assert_called_with(handlers.on_multiroom)
        v.open_settings_requested.connect.assert_called_with(handlers.on_settings)
        v.open_receiver_wizard_requested.connect.assert_called_with(handlers.on_receiver_wizard)
        v.device_cast_current_requested.connect.assert_called_with(handlers.on_cast)
        v.device_play_requested.connect.assert_called_with(handlers.on_device_play)
        v.device_pause_requested.connect.assert_called_with(handlers.on_device_pause)
        v.device_stop_requested.connect.assert_called_with(handlers.on_device_stop)
        v.device_volume_changed.connect.assert_called_with(handlers.on_device_volume)
        v.group_selected_requested.connect.assert_called_with(handlers.on_group_selected)
        v.create_group_requested.connect.assert_called_with(handlers.on_create_group)

    def test_wire_signals_no_view(self, handlers, win):
        win._home_audio_view = None
        handlers.wire_signals()

    def test_resolve_lan_ip_returns_address(self):
        with patch("socket.socket") as mock_socket:
            sock = MagicMock()
            mock_socket.return_value = sock
            sock.getsockname.return_value = ("192.168.1.10", 12345)
            ip = HomeAudioHandlers.resolve_lan_ip()
            assert ip == "192.168.1.10"

    def test_resolve_lan_ip_returns_empty_on_failure(self):
        with patch("socket.socket") as mock_socket:
            mock_socket.side_effect = OSError("no network")
            ip = HomeAudioHandlers.resolve_lan_ip()
            assert ip == ""

    def test_on_connect_shows_dialog(self, handlers, win):
        with patch("ui.controllers.home_audio_handlers.QDialog") as mock_dlg, \
             patch("ui.controllers.home_audio_handlers.QFormLayout"):
            dlg = MagicMock()
            mock_dlg.return_value = dlg
            handlers.on_connect()
            mock_dlg.assert_called_once_with(win)

    def test_try_ha_connection_saves_settings_and_connects(self, handlers, win):
        with patch("ui.controllers.home_audio_handlers.sset") as mock_sset:
            dialog = MagicMock()
            handlers.try_ha_connection("http://ha:8123", "token123", dialog, True)
            mock_sset.assert_any_call("home_audio/ha_base_url", "http://ha:8123")
            mock_sset.assert_any_call("home_audio/ha_token", "token123")
            dialog.accept.assert_called_once()
            win._ha_client.configure.assert_called_with(
                "http://ha:8123", "token123", True)
            win._ha_client.test_connection.assert_called_once()

    def test_on_ha_connection_result_success(self, handlers, win):
        handlers.on_ha_connection_result(True, "Connected")
        assert win._ha_connected is True
        win._home_audio_view.set_data.assert_called()
        win._ha_client.get_media_players.assert_called_once()
        win._toast_svc.show.assert_called()

    def test_on_ha_connection_result_failure(self, handlers, win):
        handlers.on_ha_connection_result(False, "Bad token")
        assert win._ha_connected is False
        win._toast_svc.show.assert_called()

    def test_on_ha_entities_loaded_sets_devices(self, handlers, win):
        entities = [{"entity_id": "media_player.spotify"}]
        with patch("ui.controllers.home_audio_handlers.entity_to_device",
                   return_value={"id": "spotify", "available": True}):
            handlers.on_ha_entities_loaded(entities)
        win._home_audio_view.set_data.assert_called()
        win._toast_svc.show.assert_called()

    def test_on_ha_error_shows_error(self, handlers, win):
        handlers.on_ha_error("Connection lost")
        win._toast_svc.show.assert_called()

    def test_on_refresh_with_snap_discovery(self, handlers, win):
        handlers.on_refresh()
        win._snap_discovery.refresh.assert_called_once()

    def test_on_refresh_with_ha_connected(self, handlers, win):
        win._ha_connected = True
        handlers.on_refresh()
        win._ha_client.get_media_players.assert_called_once()

    def test_on_multiroom_enable_starts_services(self, handlers, win):
        win._michi_api.is_running = False
        win._local_media.is_running = False
        win._mdns.is_running = False
        win._mdns.is_available = True
        win._snapserver.is_binary_available.return_value = True
        handlers.on_multiroom(True)
        win._michi_api.start.assert_called_once()
        win._local_media.start.assert_called_once()
        win._mdns.start.assert_called_once()
        win._snapserver.configure.assert_called_once()
        win._snapserver.start.assert_not_called()  # starts via on_audio_sink_ready

    def test_on_multiroom_disable_stops_services(self, handlers, win):
        handlers.on_multiroom(False)
        win._snapserver.stop.assert_called_once()
        win._audio_capture.remove_sink.assert_called_once()
        win._mdns.stop.assert_called_once()
        win._michi_api.stop.assert_called_once()
        win._local_media.stop.assert_called_once()

    def test_on_multiroom_enable_no_snapserver(self, handlers, win):
        win._snapserver.is_binary_available.return_value = False
        handlers.on_multiroom(True)
        win._toast_svc.show.assert_called()
        win._home_audio_view.set_data.assert_called()

    def test_on_settings_calls_preferences(self, handlers, win):
        handlers.on_settings()
        win._show_preferences.assert_called_with("home_audio")

    def test_on_receiver_wizard_creates_dialog(self, handlers, win):
        with patch("ui.controllers.home_audio_handlers.ReceiverWizard") as mock_wiz:
            dlg = MagicMock()
            mock_wiz.return_value = dlg
            handlers.on_receiver_wizard()
            mock_wiz.assert_called_once_with(win)
            dlg.exec.assert_called_once()

    def test_on_cast_with_ha_ctrl(self, handlers, win):
        handlers.on_cast({"id": "dev1"})
        win._ha_ctrl.cast_current.assert_called_with({"id": "dev1"})

    def test_on_cast_without_ha_ctrl(self, handlers, win):
        del win._ha_ctrl
        handlers.on_cast({"id": "dev1"})
        win._toast_svc.show.assert_called()

    def test_on_device_play_calls_ha(self, handlers, win):
        handlers.on_device_play({"entity_id": "media_player.spotify"})
        win._ha_client.media_play.assert_called_with("media_player.spotify")

    def test_on_device_play_no_client(self, handlers, win):
        del win._ha_client
        handlers.on_device_play({})
        win._toast_svc.show.assert_called()

    def test_on_device_pause_calls_ha(self, handlers, win):
        handlers.on_device_pause({"entity_id": "media_player.spotify"})
        win._ha_client.media_pause.assert_called_with("media_player.spotify")

    def test_on_device_stop_calls_ha(self, handlers, win):
        handlers.on_device_stop({"entity_id": "media_player.spotify"})
        win._ha_client.media_stop.assert_called_with("media_player.spotify")

    def test_on_device_volume_calls_ha(self, handlers, win):
        handlers.on_device_volume({"entity_id": "media_player.spotify"}, 50)
        win._ha_client.set_volume.assert_called_with("media_player.spotify", 0.5)

    def test_on_group_selected_activates_group(self, handlers, win):
        handlers.on_group_selected({"id": "g1", "name": "Living Room"})
        win._group_mgr.activate_group.assert_called_with("g1")
        win._toast_svc.show.assert_called()

    def test_on_create_group_creates_group(self, handlers, win):
        with patch("ui.controllers.home_audio_handlers.QInputDialog.getText",
                   return_value=("Living Room", True)):
            handlers.on_create_group()
        win._group_mgr.add_group.assert_called_with("Living Room")
        win._toast_svc.show.assert_called()

    def test_on_create_group_cancelled(self, handlers, win):
        with patch("ui.controllers.home_audio_handlers.QInputDialog.getText",
                   return_value=("", False)):
            handlers.on_create_group()
        win._group_mgr.add_group.assert_not_called()

    def test_on_snapserver_started(self, handlers, win):
        handlers.on_snapserver_started()
        win._snap_discovery.refresh.assert_called_once()

    def test_on_snapserver_stopped(self, handlers, win):
        handlers.on_snapserver_stopped()
        win._toast_svc.show.assert_called()

    def test_on_snapserver_error(self, handlers, win):
        handlers.on_snapserver_error("port in use")
        win._toast_svc.show.assert_called()

    def test_on_audio_sink_ready_configures_and_starts(self, handlers, win):
        win._snapserver.tcp_port = 1704
        win._snapserver.control_port = 1705
        win._snapserver.http_port = 1780
        handlers.on_audio_sink_ready("monitor_name")
        win._snapserver.configure.assert_called_with(
            tcp=1704, ctrl=1705, http=1780)
        win._snapserver.start.assert_called_once()

    def test_on_snap_clients_found_refreshes(self, handlers, win):
        with patch.object(handlers, 'refresh_home_audio_state') as mock_refresh:
            handlers.on_snap_clients_found([{"id": "c1"}])
            mock_refresh.assert_called_once()

    def test_on_groups_changed_refreshes(self, handlers, win):
        with patch.object(handlers, 'refresh_home_audio_state') as mock_refresh:
            handlers.on_groups_changed([])
            mock_refresh.assert_called_once()

    def test_refresh_home_audio_state_builds_devices(self, handlers, win):
        win._snap_discovery.clients.return_value = [
            {"id": "s1", "name": "Kitchen", "host": "192.168.1.5", "available": True}]
        win._home_audio_view._devices = [
            {"id": "ha1", "name": "Speaker", "available": True}]
        win._group_mgr.groups.return_value = [{"id": "g1", "name": "All"}]
        win._michi_api.is_running = True
        handlers.refresh_home_audio_state()
        win._home_audio_view.set_data.assert_called_once()
        args, kwargs = win._home_audio_view.set_data.call_args
        assert kwargs["multiroom_active"] is False
        assert len(kwargs["devices"]) == 2
        assert len(kwargs["groups"]) == 1
        assert kwargs["api_running"] is True

    def test_refresh_home_audio_state_with_transmit(self, handlers, win):
        tx_dev = MagicMock()
        tx_dev.name = "Office"
        win._ctx.transmit_mgr.get_active.return_value = tx_dev
        handlers.refresh_home_audio_state()
        args, kwargs = win._home_audio_view.set_data.call_args
        assert kwargs["transmit_active"] is True
        assert kwargs["transmit_device_name"] == "Office"
