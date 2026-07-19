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


def build_service(control=None):
    return HomeAudioService(
        snapcast_control=control,
        settings=MemorySettings(),
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
