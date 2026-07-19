from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
from core.worker_manager import WorkerManager


class DistributionService:
    server_handoff_available = False
    latency_ms = 18

    def __init__(self):
        self.created = None

    def is_connected(self):
        return True

    def get_devices(self):
        return []

    def get_zones(self):
        return [{"id": "living", "name": "Sala"}]

    def get_groups(self):
        return [{"id": "living", "name": "Sala", "stream_id": "music"}]

    def get_streams(self):
        return [{"id": "music", "name": "Music"}]

    def get_sources(self):
        return [{"id": "music", "name": "Music", "routeable": True}]

    def get_servers(self):
        return [{"id": "local_snapserver", "state": "running"}]

    def get_receivers(self):
        return [{"id": "client-1", "state": "online", "connected": True}]

    def get_destinations(self):
        return [{"id": "living", "name": "Sala", "routeable": True}]

    def list_routes(self):
        return []

    def create_route(self, name, source_id, destination_ids):
        self.created = (name, source_id, destination_ids)
        return {
            "ok": True,
            "route": {
                "id": "route-1",
                "name": name,
                "source_id": source_id,
                "destination_ids": destination_ids,
                "state": "configured",
            },
        }


def test_refresh_exposes_all_distribution_models():
    bridge = HomeAudioBridge(home_audio_service=DistributionService())

    result = bridge.refreshDistribution()

    assert result["ok"] is True
    assert bridge.distributionState == "active"
    assert bridge.sources[0]["id"] == "music"
    assert bridge.servers[0]["state"] == "running"
    assert bridge.receiverList[0]["id"] == "client-1"
    assert bridge.destinations[0]["id"] == "living"


def test_create_route_delegates_typed_destination_list():
    service = DistributionService()
    bridge = HomeAudioBridge(home_audio_service=service)

    result = bridge.createRoute("Sala", "music", ["living"])

    assert result["ok"] is True
    assert service.created == ("Sala", "music", ["living"])


def test_worker_manager_keeps_refresh_off_the_qml_thread(qtbot):
    manager = WorkerManager()
    bridge = HomeAudioBridge(
        home_audio_service=DistributionService(),
        worker_manager=manager,
    )

    with qtbot.waitSignal(bridge.operationFinished, timeout=2000):
        accepted = bridge.refreshDistribution()

    assert accepted["accepted"] is True
    assert bridge.operationInProgress is False
    assert bridge.sources[0]["id"] == "music"
    manager.shutdown()


def test_distribution_bridge_exposes_required_compatibility_slots():
    bridge = HomeAudioBridge(home_audio_service=DistributionService())
    for name in (
        "startLocalServer",
        "stopLocalServer",
        "updateRoute",
        "retryRoute",
        "setReceiverVolume",
        "setReceiverMute",
        "setReceiverLatency",
    ):
        assert callable(getattr(bridge, name))
    assert bridge.playbackTransfer("")["error"] == "EMPTY_ZONE"
    assert bridge.syncStatus == {}
