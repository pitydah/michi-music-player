from unittest.mock import MagicMock, patch

from ui_qml_bridge.home_audio_bridge import HomeAudioBridge


class TestHomeAudioBridge:
    """Cover basic HomeAudioBridge construction."""

    def test_create(self) -> None:
        bridge = HomeAudioBridge(home_audio_service=MagicMock())
        assert bridge is not None


class TestHomeAudioPhaseFeatures:
    """Cover bridge behavior introduced by Home Audio phases 3 through 7."""

    def test_assign_source_to_zone_sets_and_verifies_stream(self) -> None:
        service = MagicMock()
        service.assign_source_to_zone.return_value = {
            "ok": True,
            "stream_id": "stream-jazz",
            "verified": True,
        }
        bridge = HomeAudioBridge(home_audio_service=service)
        bridge._groups = [{"id": "group-1", "stream_id": "stream-old"}]
        bridge._sources = [{"id": "stream-jazz"}]

        result = bridge.assignSourceToZone("group-1", "stream-jazz")

        service.assign_source_to_zone.assert_called_once_with("group-1", "stream-jazz")
        assert result == {"ok": True, "stream_id": "stream-jazz", "verified": True}

    def test_assign_source_to_zone_reports_failed_readback(self) -> None:
        service = MagicMock()
        service.assign_source_to_zone.return_value = {
            "ok": False,
            "error": "STREAM_ASSIGNMENT_NOT_VERIFIED",
            "stream_id": "stream-old",
            "verified": False,
        }
        bridge = HomeAudioBridge(home_audio_service=service)
        bridge._zones = [{"id": "group-1", "stream_id": "stream-old"}]
        bridge._sources = [{"id": "stream-jazz"}]

        result = bridge.assignSourceToZone("group-1", "stream-jazz")

        assert result["ok"] is False
        assert result["stream_id"] == "stream-old"
        assert result["verified"] is False

    def test_refresh_marks_route_with_missing_source_as_orphaned(self) -> None:
        service = MagicMock()
        service.get_devices.return_value = []
        service.get_zones.return_value = []
        service.get_groups.return_value = []
        service.get_streams.return_value = [{"id": "stream-live"}]
        service.get_sources.return_value = [{"id": "stream-live"}]
        service.get_servers.return_value = []
        service.get_receivers.return_value = []
        service.get_destinations.return_value = [{"id": "group-1"}]
        service.list_routes.return_value = [
            {"id": "route-1", "source_id": "stream-gone", "destination_ids": ["group-1"]}
        ]
        bridge = HomeAudioBridge(home_audio_service=service)

        bridge.refresh()

        assert bridge.routes[0]["orphaned"] is True
        assert bridge.routes[0]["orphan_reasons"] == ["SOURCE_NOT_FOUND"]

    def test_refresh_keeps_existing_route_non_orphaned(self) -> None:
        service = MagicMock()
        service.get_devices.return_value = []
        service.get_zones.return_value = []
        service.get_groups.return_value = []
        service.get_streams.return_value = [{"id": "stream-live"}]
        service.get_sources.return_value = [{"id": "stream-live"}]
        service.get_servers.return_value = []
        service.get_receivers.return_value = []
        service.get_destinations.return_value = [{"id": "group-1"}]
        service.list_routes.return_value = [
            {"id": "route-1", "source_id": "stream-live", "destination_ids": ["group-1"]}
        ]
        bridge = HomeAudioBridge(home_audio_service=service)

        bridge.refresh()

        assert bridge.routes[0]["orphaned"] is False
        assert bridge.routes[0]["orphan_reasons"] == []

    def test_configure_ha_forwards_real_form_values(self) -> None:
        service = ConfigurableService()
        bridge = HomeAudioBridge(home_audio_service=service)

        result = bridge.configureHa("ha.local", 8123, "secret")

        assert service.configuration == ("ha.local", 8123, "secret")
        assert result["ok"] is True

    def test_disconnect_ha_closes_client_and_clears_credentials(self) -> None:
        service = MagicMock()
        service.disconnect_home_assistant.return_value = {
            "ok": True,
            "disconnected": True,
        }
        bridge = HomeAudioBridge(home_audio_service=service)

        result = bridge.disconnectHa()

        service.disconnect_home_assistant.assert_called_once_with()
        assert result == {"ok": True, "disconnected": True}

    def test_create_group_returns_service_error_instead_of_raising(self) -> None:
        service = MagicMock()
        service.create_group.side_effect = RuntimeError("group backend offline")
        bridge = HomeAudioBridge(home_audio_service=service)

        result = bridge.createGroup("Downstairs", ["receiver-1", "receiver-2"])

        assert result == {"ok": False, "error": "group backend offline"}

    def test_update_group_sets_exact_snapcast_membership_and_verifies(self) -> None:
        service = MagicMock()
        service.update_group.return_value = {"ok": True, "errors": []}
        bridge = HomeAudioBridge(home_audio_service=service)
        bridge._groups = [
            {"id": "group-1", "name": "Downstairs", "members": ["receiver-1"]}
        ]

        result = bridge.updateGroup("group-1", "Downstairs", ["receiver-2"])

        service.update_group.assert_called_once_with(
            "group-1", "Downstairs", ["receiver-2"]
        )
        assert result == {"ok": True, "errors": []}

    def test_configure_ha_rejects_missing_token_without_calling_service(self) -> None:
        service = ConfigurableService()
        bridge = HomeAudioBridge(home_audio_service=service)

        result = bridge.configureHa("ha.local", 8123, "")

        assert service.configuration is None
        assert result == {"ok": False, "error": "MISSING_CREDENTIALS"}

    def test_assign_source_to_zone_rejects_unknown_destination(self) -> None:
        bridge = HomeAudioBridge(home_audio_service=MagicMock())
        bridge._sources = [{"id": "stream-jazz"}]

        result = bridge.assignSourceToZone("missing", "stream-jazz")

        assert result == {
            "ok": False,
            "error": "UNKNOWN_DESTINATION",
            "stream_id": "",
            "verified": False,
        }

    def test_open_diagnostics_reports_runtime_state_and_receiver_latency(
        self, tmp_path
    ) -> None:
        fifo = tmp_path / "michi-snapfifo"
        fifo.write_bytes(b"audio")
        service = MagicMock()
        service.health.return_value = {"ok": True, "snapserver_running": True}
        bridge = HomeAudioBridge(home_audio_service=service)
        bridge._snapcast_state = "running"
        bridge._streams = [
            {"id": "stream-1", "status": "playing"},
            {"id": "stream-2", "status": "idle"},
        ]
        bridge._receivers = [
            {"id": "receiver-1", "name": "Studio", "connected": True, "latency_ms": 32},
            {"id": "receiver-2", "connected": False, "latency_ms": 90},
        ]

        with patch("integrations.snapcast.fifo_manager.fifo_path", return_value=str(fifo)):
            result = bridge.openDiagnostics()

        assert result["snapserver_state"] == "running"
        assert result["fifo_exists"] is True
        assert result["fifo_size"] == 5
        assert [stream["id"] for stream in result["active_streams"]] == ["stream-1"]
        assert result["receiver_latencies"] == [
            {"id": "receiver-1", "name": "Studio", "latency_ms": 32}
        ]

    def test_open_diagnostics_reports_stopped_without_server(self, tmp_path) -> None:
        missing_fifo = tmp_path / "missing"
        service = MagicMock()
        service.health.return_value = {"ok": True, "snapserver_running": False}
        bridge = HomeAudioBridge(home_audio_service=service)

        with patch(
            "integrations.snapcast.fifo_manager.fifo_path", return_value=str(missing_fifo)
        ):
            result = bridge.openDiagnostics()

        assert result["snapserver_state"] == "stopped"
        assert result["fifo_exists"] is False
        assert result["active_streams"] == []

    def test_test_tone_reports_unsupported_when_service_has_no_generator(self) -> None:
        bridge = HomeAudioBridge(home_audio_service=MagicMock(spec=[]))

        result = bridge.testTone()

        assert result == {"ok": False, "error": "TEST_TONE_UNSUPPORTED"}


class ConfigurableService:
    """Record Home Assistant configuration forwarded by the bridge."""

    def __init__(self) -> None:
        self.configuration: tuple[str, int, str] | None = None

    def configure(self, *, host: str, port: int, access_token: str) -> dict:
        self.configuration = (host, port, access_token)
        return {"ok": True}
