from __future__ import annotations

from michi_ai.v2.intent.capability_resolver import CapabilityResolver
from michi_ai.v2.tools.fake_gateways import (
    FakeAudioLabGateway, FakeDeviceGateway, FakeDiagnosticsGateway,
    FakeJobGateway, FakeLibraryGateway, FakeMixGateway,
    FakePlaybackGateway, FakePlaylistGateway, FakeQueueGateway,
    FakeSettingsGateway,
)
from michi_ai.v2.tools.register_builtin import (
    AssistantGateways, register_builtin_tools,
)
from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2


def _make_full_gateways() -> AssistantGateways:
    return AssistantGateways(
        playback=FakePlaybackGateway(),
        queue=FakeQueueGateway(),
        library=FakeLibraryGateway(),
        playlist=FakePlaylistGateway(),
        audio_lab=FakeAudioLabGateway(),
        device=FakeDeviceGateway(),
        settings=FakeSettingsGateway(),
        diagnostics=FakeDiagnosticsGateway(),
        mix=FakeMixGateway(),
        job=FakeJobGateway(),
        navigation=None,
    )


class TestRegisterBuiltinTools:
    def test_registers_all_tools(self):
        registry = ToolRegistryV2()
        gws = _make_full_gateways()
        register_builtin_tools(registry, gws)

        tools = registry.list_tools()
        assert len(tools) >= 62, f"Expected >=62 tools, got {len(tools)}"

    def test_all_tools_have_handlers(self):
        registry = ToolRegistryV2()
        gws = _make_full_gateways()
        register_builtin_tools(registry, gws)

        for defn in registry.list_tools():
            handler = registry.get_handler(defn.name)
            assert handler is not None, f"Tool '{defn.name}' has no handler after registration"

    def test_search_library_works(self):
        registry = ToolRegistryV2()
        gws = _make_full_gateways()
        register_builtin_tools(registry, gws)

        result = registry.execute("search_library", {"query": "Song"})
        assert result.ok is True
        assert result.data is not None
        assert "results" in result.data

    def test_playback_pause_play(self):
        registry = ToolRegistryV2()
        gws = _make_full_gateways()
        register_builtin_tools(registry, gws)

        play = registry.execute("play_track", {"track_id": "1"})
        assert play.ok is True

        pause = registry.execute("pause", {})
        assert pause.ok is True

        resume = registry.execute("resume", {})
        assert resume.ok is True

    def test_queue_operations(self):
        registry = ToolRegistryV2()
        gws = _make_full_gateways()
        register_builtin_tools(registry, gws)

        add = registry.execute("add_to_queue", {"track_ids": ["1", "2"]})
        assert add.ok is True

        q = registry.execute("get_queue", {})
        assert q.ok is True

        clear = registry.execute("clear_queue", {})
        assert clear.ok is True

    def test_playlist_create(self):
        registry = ToolRegistryV2()
        gws = _make_full_gateways()
        register_builtin_tools(registry, gws)

        result = registry.execute("create_playlist", {"name": "Test Playlist", "track_ids": ["1"]})
        assert result.ok is True

    def test_unavailable_gateway_returns_capability_error(self):
        registry = ToolRegistryV2()
        gws = AssistantGateways()
        register_builtin_tools(registry, gws)

        result = registry.execute("search_library", {"query": "test"})
        assert result.ok is False
        assert result.code.value in ("CAPABILITY_UNAVAILABLE", "TOOL_FAILED")

    def test_capability_resolver_updated(self):
        registry = ToolRegistryV2()
        caps = CapabilityResolver()
        gws = _make_full_gateways()
        register_builtin_tools(registry, gws, capabilities=caps)

        assert caps.all_available("playback.control")
        assert caps.all_available("library.search")
        assert not caps.all_available("sample.unavailable")

    def test_unique_tool_names(self):
        registry = ToolRegistryV2()
        gws = _make_full_gateways()
        register_builtin_tools(registry, gws)

        names = [t.name for t in registry.list_tools()]
        assert len(names) == len(set(names))


class TestRegisterBuiltinConfirmation:
    def test_destructive_tools_require_confirmation(self):
        registry = ToolRegistryV2()
        gws = _make_full_gateways()
        register_builtin_tools(registry, gws)

        for defn in registry.list_tools():
            if defn.destructive:
                assert defn.requires_confirmation, f"Tool '{defn.name}' destructive but no confirmation"

    def test_replace_queue_requires_confirmation(self):
        registry = ToolRegistryV2()
        gws = _make_full_gateways()
        register_builtin_tools(registry, gws)
        defn = registry.get("replace_queue")
        assert defn is not None
        assert defn.requires_confirmation is True

    def test_clear_queue_requires_confirmation(self):
        registry = ToolRegistryV2()
        gws = _make_full_gateways()
        register_builtin_tools(registry, gws)
        defn = registry.get("clear_queue")
        assert defn is not None
        assert defn.requires_confirmation is True


class TestFakeGatewayBehavior:
    def test_playback_gateway_state(self):
        gw = FakePlaybackGateway()
        assert gw.state["is_playing"] is False
        gw.play_track("1")
        assert gw.state["is_playing"] is True
        gw.pause()
        assert gw.state["is_paused"] is True
        assert gw.state["is_playing"] is False
        gw.resume()
        assert gw.state["is_playing"] is True

    def test_playback_gateway_pause_when_not_playing(self):
        gw = FakePlaybackGateway()
        result = gw.pause()
        assert result.get("ok") is False
        assert "NOT_PLAYING" in str(result.get("error", ""))

    def test_playback_gateway_volume_validation(self):
        gw = FakePlaybackGateway()
        result = gw.set_volume(150)
        assert result.get("ok") is False
        result = gw.set_volume(50)
        assert result.get("ok") is True
        assert gw.state["volume"] == 50

    def test_queue_gateway_empty(self):
        gw = FakeQueueGateway()
        q = gw.get_queue()
        assert q["count"] == 0

    def test_queue_gateway_add_and_clear(self):
        gw = FakeQueueGateway()
        gw.add_to_queue(["1", "2", "3"])
        assert gw.get_queue()["count"] == 3
        gw.clear_queue()
        assert gw.get_queue()["count"] == 0

    def test_playlist_gateway_create(self):
        gw = FakePlaylistGateway()
        result = gw.create_playlist("Test", ["1", "2"])
        assert result["ok"] is True
        assert result["playlist"]["name"] == "Test"

    def test_audio_lab_conversion_job(self):
        gw = FakeAudioLabGateway()
        result = gw.start_conversion("plan_1")
        assert result["ok"] is True
        assert result["status"] == "JOB_STARTED"
        assert result["job_id"] != ""

        cancel = gw.cancel_conversion(result["job_id"])
        assert cancel["ok"] is True
        assert cancel["status"] == "cancelled"

    def test_audio_lab_cancel_unknown(self):
        gw = FakeAudioLabGateway()
        result = gw.cancel_conversion("unknown")
        assert result.get("ok") is False

    def test_device_sync_job_lifecycle(self):
        gw = FakeDeviceGateway()
        plan = gw.plan_sync("pl1", "d1")
        assert plan["ok"] is True
        result = gw.start_sync(plan["plan_id"])
        assert result["ok"] is True
        assert result["status"] == "JOB_STARTED"
        cancel = gw.cancel_sync(result["job_id"])
        assert cancel["ok"] is True

    def test_settings_gateway_crud(self):
        gw = FakeSettingsGateway()
        result = gw.get_setting("audio/volume")
        assert result["ok"] is True
        assert result["value"] == 80

        result = gw.get_setting("nonexistent")
        assert result["ok"] is False

        result = gw.apply_change("audio/volume", 50)
        assert result["ok"] is True
        assert result["new_value"] == 50

        result = gw.get_setting("audio/volume")
        assert result["value"] == 50

    def test_diagnostics_gateway(self):
        gw = FakeDiagnosticsGateway()
        result = gw.get_diagnostics()
        assert result["ok"] is True
        assert "audio" in result

    def test_library_gateway_search(self):
        gw = FakeLibraryGateway()
        result = gw.search("Song")
        assert result["ok"] is True
        assert result["total"] > 0

        result = gw.search("Nonexistent")
        assert result["ok"] is True
        assert result["total"] == 0

    def test_library_get_track(self):
        gw = FakeLibraryGateway()
        result = gw.get_track("1")
        assert result["ok"] is True
        assert result["track"]["title"] == "Song A"

        result = gw.get_track("999")
        assert result["ok"] is False

    def test_mix_gateway(self):
        gw = FakeMixGateway()
        mix = gw.create_mix("genre", genre="Rock")
        assert mix["ok"] is True
        assert "mix_id" in mix
        explain = gw.explain_mix(mix["mix_id"])
        assert explain["ok"] is True
        save = gw.save_mix_as_playlist(mix["mix_id"], "Rock Mix")
        assert save["ok"] is True
