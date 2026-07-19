from copy import deepcopy

from core.home_audio_service import HomeAudioService


class MemorySettings:
    def __init__(self):
        self.data = {}

    def value(self, key, default=None):
        return self.data.get(key, default)

    def setValue(self, key, value):
        self.data[key] = value

    def sync(self):
        return None

    def status(self):
        return 0


class FakeSnapcast:
    def __init__(self):
        self.connected = True
        self.groups = [
            {
                "id": "living",
                "name": "Sala",
                "stream_id": "old",
                "clients": [
                    {
                        "id": "client-1",
                        "name": "Receiver",
                        "connected": True,
                        "config": {
                            "volume": {"percent": 60, "muted": False},
                            "latency": 25,
                        },
                    }
                ],
            }
        ]
        self.streams = [
            {
                "id": "music",
                "name": "Music",
                "status": "idle",
                "uri": {"codec": "flac", "sampleFormat": "44100:16:2"},
            },
            {
                "id": "old",
                "name": "Previous",
                "status": "idle",
                "uri": {"codec": "pcm", "sampleFormat": "48000:16:2"},
            },
        ]

    def get_groups(self):
        return deepcopy(self.groups)

    def get_streams(self):
        return deepcopy(self.streams)

    def get_client_list(self):
        group = self.groups[0]
        client = group["clients"][0]
        volume = client["config"]["volume"]
        return [
            {
                "id": client["id"],
                "name": client["name"],
                "connected": client["connected"],
                "volume": volume["percent"],
                "muted": volume["muted"],
                "latency_ms": client["config"]["latency"],
                "group": group["id"],
                "group_name": group["name"],
                "stream_id": group["stream_id"],
                "backend": "snapcast",
            }
        ]

    def set_group_stream(self, group_id, stream_id):
        for group in self.groups:
            if group["id"] == group_id:
                group["stream_id"] = stream_id
                return True
        raise RuntimeError("unknown group")

    def set_client_volume(self, client_id, volume, mute=False):
        client = self.groups[0]["clients"][0]
        assert client["id"] == client_id
        client["config"]["volume"] = {"percent": volume, "muted": mute}
        return True

    def set_client_latency(self, client_id, latency_ms):
        client = self.groups[0]["clients"][0]
        assert client["id"] == client_id
        client["config"]["latency"] = latency_ms
        return True

    def set_client_name(self, client_id, name):
        client = next(
            item
            for group in self.groups
            for item in group["clients"]
            if item["id"] == client_id
        )
        client["config"]["name"] = name
        client["name"] = name
        return True

    def set_group_clients(self, group_id, client_ids):
        all_clients = {
            client["id"]: client
            for group in self.groups
            for client in group["clients"]
        }
        for group in self.groups:
            if group["id"] == group_id:
                group["clients"] = [all_clients[item] for item in client_ids]
            else:
                group["clients"] = [
                    client for client in group["clients"] if client["id"] not in client_ids
                ]
        return True


def build_service(control=None, settings=None):
    return HomeAudioService(
        snapcast_control=control,
        settings=settings or MemorySettings(),
    )


def test_route_activation_and_stop_are_verified_against_snapcast():
    control = FakeSnapcast()
    service = build_service(control)

    created = service.create_route("Sala", "music", ["living"])
    assert created["ok"] is True

    started = service.start_route(created["route"]["id"])
    assert started["ok"] is True
    assert started["route"]["state"] == "active"
    assert control.groups[0]["stream_id"] == "music"

    stopped = service.stop_route(created["route"]["id"])
    assert stopped["ok"] is True
    assert stopped["route"]["state"] == "stopped"
    assert control.groups[0]["stream_id"] == "old"


def test_route_never_reports_success_without_snapcast_control():
    service = build_service()
    service._routes.append(
        {
            "id": "route-1",
            "name": "Broken",
            "source_id": "music",
            "destination_ids": ["living"],
            "state": "configured",
            "previous_streams": {},
        }
    )

    result = service.start_route("route-1")

    assert result["ok"] is False
    assert result["error"] == "SNAPCAST_CONTROL_UNAVAILABLE"
    assert result["route"]["state"] == "error"


def test_receiver_volume_mute_and_latency_require_readback():
    control = FakeSnapcast()
    service = build_service(control)

    volume = service.set_receiver_volume("client-1", 72)
    mute = service.set_receiver_mute("client-1", True)
    latency = service.set_receiver_latency("client-1", 140)

    assert volume["ok"] is True
    assert mute["ok"] is True
    assert latency["ok"] is True
    receiver = service.get_receivers()[0]
    assert receiver["volume"] == 72
    assert receiver["muted"] is True
    assert receiver["latency_ms"] == 140


def test_local_playback_is_not_claimed_as_routeable_without_pipe_connection():
    class Playback:
        current_track = {"title": "Song"}

    service = HomeAudioService(
        snapcast_control=FakeSnapcast(),
        playback_service=Playback(),
        settings=MemorySettings(),
    )

    local = next(source for source in service.get_sources() if source["id"] == "local_playback")
    assert local["routeable"] is False


def test_routes_persist_but_active_state_is_not_trusted_after_reload():
    settings = MemorySettings()
    control = FakeSnapcast()
    service = build_service(control, settings)
    created = service.create_route("Sala", "music", ["living"])
    assert service.start_route(created["route"]["id"])["ok"] is True

    restored = build_service(control, settings).list_routes()[0]

    assert restored["state"] == "configured"
    assert restored["previous_streams"] == {"living": "old"}


def test_route_creation_rejects_unknown_source_and_destination():
    service = build_service(FakeSnapcast())
    assert service.create_route("Bad", "missing", ["living"])["error"] == "UNKNOWN_SOURCE"
    assert service.create_route("Bad", "music", ["missing"])["error"] == "UNKNOWN_DESTINATION"


def test_activation_requires_readback_and_records_destination_error():
    class NoReadbackSnapcast(FakeSnapcast):
        def set_group_stream(self, group_id, stream_id):
            return True

    service = build_service(NoReadbackSnapcast())
    route = service.create_route("Sala", "music", ["living"])["route"]

    result = service.start_route(route["id"])

    assert result["ok"] is False
    assert result["route"]["state"] == "error"
    assert result["route"]["destination_errors"] == {"living": "ROUTE_VERIFICATION_FAILED"}


def test_receiver_not_found_is_distinct_from_offline():
    control = FakeSnapcast()
    service = build_service(control)
    assert service.set_receiver_volume("missing", 10)["error"] == "RECEIVER_NOT_FOUND"
    control.groups[0]["clients"][0]["connected"] = False
    assert service.set_receiver_volume("client-1", 10)["error"] == "RECEIVER_OFFLINE"


def test_receiver_name_requires_readback():
    service = build_service(FakeSnapcast())
    result = service.set_receiver_name("client-1", "Sala principal")
    assert result["ok"] is True
    assert result["receiver"]["name"] == "Sala principal"


def test_update_route_changes_persisted_configuration():
    service = build_service(FakeSnapcast())
    route = service.create_route("Old", "music", ["living"])["route"]

    result = service.update_route(route["id"], "New", "music", ["living"])

    assert result["ok"] is True
    assert service.list_routes()[0]["name"] == "New"


class TwoGroupSnapcast(FakeSnapcast):
    def __init__(self):
        super().__init__()
        second = deepcopy(self.groups[0])
        second["id"] = "kitchen"
        second["name"] = "Cocina"
        second["clients"][0]["id"] = "client-2"
        self.groups.append(second)
        self.known_clients = {
            client["id"]: client for group in self.groups for client in group["clients"]
        }
        self.failures = set()

    def get_client_list(self):
        receivers = []
        for group in self.groups:
            for client in group["clients"]:
                volume = client["config"]["volume"]
                receivers.append(
                    {
                        "id": client["id"],
                        "name": client["name"],
                        "connected": client["connected"],
                        "volume": volume["percent"],
                        "muted": volume["muted"],
                        "latency_ms": client["config"]["latency"],
                        "group": group["id"],
                        "group_name": group["name"],
                        "stream_id": group["stream_id"],
                    }
                )
        return receivers

    def set_group_stream(self, group_id, stream_id):
        if (group_id, stream_id) in self.failures:
            raise RuntimeError("rpc failed")
        return super().set_group_stream(group_id, stream_id)

    def set_group_clients(self, group_id, client_ids):
        for group in self.groups:
            if group["id"] == group_id:
                group["clients"] = [self.known_clients[item] for item in client_ids]
            else:
                group["clients"] = [
                    client for client in group["clients"] if client["id"] not in client_ids
                ]
        return True


def test_partial_activation_is_degraded():
    control = TwoGroupSnapcast()
    service = build_service(control)
    route = service.create_route("House", "music", ["living", "kitchen"])["route"]
    control.failures.add(("kitchen", "music"))

    result = service.start_route(route["id"])

    assert result["ok"] is False
    assert result["partial"] is True
    assert result["route"]["state"] == "degraded"


def test_receiver_move_requires_group_readback():
    service = build_service(TwoGroupSnapcast())
    result = service.move_receiver("client-1", "kitchen")
    assert result["ok"] is True
    assert result["receiver"]["group"] == "kitchen"


def test_partial_stop_keeps_recovery_metadata():
    control = TwoGroupSnapcast()
    service = build_service(control)
    route = service.create_route("House", "music", ["living", "kitchen"])["route"]
    assert service.start_route(route["id"])["ok"] is True
    control.failures.add(("kitchen", "old"))

    result = service.stop_route(route["id"])

    assert result["ok"] is False
    assert result["partial"] is True
    assert result["route"]["state"] == "degraded"
    assert result["route"]["previous_streams"] == {"living": "old", "kitchen": "old"}


def test_route_creation_reports_persistence_failure():
    class FailingSettings(MemorySettings):
        def status(self):
            return 1

    service = build_service(FakeSnapcast(), FailingSettings())
    result = service.create_route("Sala", "music", ["living"])

    assert result["ok"] is False
    assert result["error"] == "ROUTE_PERSISTENCE_FAILED"
    assert service.list_routes() == []
