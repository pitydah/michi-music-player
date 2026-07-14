from __future__ import annotations

from michi_ai.v2.core.assistant_core import AssistantCoreService
from michi_ai.v2.core.models import (
    AssistantRequest, AssistantResponseType, ErrorCode,
)
from michi_ai.v2.intent.capability_resolver import CapabilityResolver
from michi_ai.v2.tools.fake_gateways import (
    FakeAudioLabGateway, FakeDeviceGateway, FakeDiagnosticsGateway,
    FakeLibraryGateway, FakeMixGateway, FakePlaybackGateway,
    FakePlaylistGateway, FakeQueueGateway, FakeSettingsGateway,
)
from michi_ai.v2.tools.register_builtin import (
    AssistantGateways, register_builtin_tools,
)


def _make_core() -> AssistantCoreService:
    core = AssistantCoreService()
    gws = AssistantGateways(
        playback=FakePlaybackGateway(),
        queue=FakeQueueGateway(),
        library=FakeLibraryGateway(),
        playlists=FakePlaylistGateway(),
        audio_lab=FakeAudioLabGateway(),
        devices=FakeDeviceGateway(),
        settings=FakeSettingsGateway(),
        diagnostics=FakeDiagnosticsGateway(),
        mix=FakeMixGateway(),
        jobs=None,
        navigation=None,
    )
    caps = CapabilityResolver()
    register_builtin_tools(core.tool_registry, gws, capabilities=caps)
    core.capability_resolver = caps
    core.register_gateways(gws.to_dict())
    core.initialize()
    return core


class TestWorkflowPlayback:
    def test_play_track_workflow(self):
        core = _make_core()
        result = core.tool_registry.execute("play_track", {"track_id": "1"})
        assert result.ok is True

    def test_pause_resume_workflow(self):
        core = _make_core()
        core.tool_registry.execute("play_track", {"track_id": "1"})
        pause = core.tool_registry.execute("pause", {})
        assert pause.ok is True
        resume = core.tool_registry.execute("resume", {})
        assert resume.ok is True

    def test_volume_validation(self):
        core = _make_core()
        result = core.tool_registry.execute("set_volume", {"volume": 50})
        assert result.ok is True
        result = core.tool_registry.execute("set_volume", {"volume": -1})
        assert result.ok is False

    def test_play_album_assistant_flow(self):
        core = _make_core()
        request = AssistantRequest(text="reproduce el ultimo album de Radiohead")
        response = core.process_message(request)
        valid_types = {
            AssistantResponseType.ANSWER,
            AssistantResponseType.PLAN_PREVIEW,
            AssistantResponseType.EXECUTION_RESULT,
            AssistantResponseType.ERROR,
        }
        assert response.type in valid_types, f"Unexpected: {response.type}"


class TestWorkflowQueue:
    def test_add_to_queue_then_get(self):
        core = _make_core()
        add = core.tool_registry.execute("add_to_queue", {"track_ids": ["1", "2", "3"]})
        assert add.ok is True
        q = core.tool_registry.execute("get_queue", {})
        assert q.ok is True

    def test_clear_queue_flow(self):
        core = _make_core()
        core.tool_registry.execute("add_to_queue", {"track_ids": ["1"]})
        clear = core.tool_registry.execute("clear_queue", {})
        assert clear.ok is True
        q = core.tool_registry.execute("get_queue", {})
        assert q.ok is True
        assert q.data is not None
        assert q.data.get("count", 999) == 0


class TestWorkflowPlaylist:
    def test_create_and_add_to_playlist(self):
        core = _make_core()
        create = core.tool_registry.execute("create_playlist", {"name": "Test", "track_ids": ["1"]})
        assert create.ok is True
        pl_id = create.data.get("playlist", {}).get("id", "")
        if pl_id:
            add = core.tool_registry.execute("add_to_playlist", {"playlist_id": pl_id, "track_ids": ["2"]})
            assert add.ok is True

    def test_create_playlist_from_assistant(self):
        core = _make_core()
        request = AssistantRequest(text="crea una playlist con estas canciones")
        response = core.process_message(request)
        assert response.type in (
            AssistantResponseType.ANSWER,
            AssistantResponseType.PLAN_PREVIEW,
            AssistantResponseType.CLARIFICATION,
            AssistantResponseType.ERROR,
        )


class TestWorkflowConversion:
    def test_conversion_recommend_and_preview(self):
        core = _make_core()
        recommend = core.tool_registry.execute(
            "recommend_conversion_profile",
            {"track_ids": ["1", "2"], "target": "mobile"},
        )
        assert recommend.ok is True
        plan_id = recommend.data.get("plan_id", "")
        if plan_id:
            preview = core.tool_registry.execute("preview_conversion", {"plan_id": plan_id})
            assert preview.ok is True

    def test_conversion_start_and_cancel(self):
        core = _make_core()
        recommend = core.tool_registry.execute(
            "recommend_conversion_profile",
            {"track_ids": ["1", "2"], "target": "mobile"},
        )
        plan_id = recommend.data.get("plan_id", "conv_plan_1")
        start = core.tool_registry.execute("start_conversion", {"plan_id": plan_id})
        assert start.ok is True
        job_id = start.data.get("job_id", "")
        if job_id:
            cancel = core.tool_registry.execute("cancel_conversion", {"job_id": job_id})
            assert cancel.ok is True

    def test_conversion_multiple_steps(self):
        core = _make_core()
        recommend = core.tool_registry.execute(
            "recommend_conversion_profile",
            {"track_ids": ["1"], "target": "hifi"},
        )
        assert recommend.ok is True
        assert "plan_id" in (recommend.data or {})

        preview = core.tool_registry.execute(
            "preview_conversion",
            {"plan_id": recommend.data["plan_id"]},
        )
        assert preview.ok is True

        start = core.tool_registry.execute(
            "start_conversion",
            {"plan_id": recommend.data["plan_id"]},
        )
        assert start.ok is True
        job_id = start.data.get("job_id", "")
        assert job_id != ""

        cancel = core.tool_registry.execute("cancel_conversion", {"job_id": job_id})
        assert cancel.ok is True


class TestWorkflowSync:
    def test_plan_and_cancel_sync(self):
        core = _make_core()
        plan = core.tool_registry.execute("plan_device_sync", {"playlist_id": "pl1", "device_id": "d1"})
        assert plan.ok is True
        plan_id = plan.data.get("plan_id", "sync_plan_1")
        start = core.tool_registry.execute("start_device_sync", {"plan_id": plan_id})
        assert start.ok is True
        job_id = start.data.get("job_id", "")
        if job_id:
            cancel = core.tool_registry.execute("cancel_device_sync", {"job_id": job_id})
            assert cancel.ok is True


class TestWorkflowErrorHandling:
    def test_unregistered_tool(self):
        core = _make_core()
        result = core.tool_registry.execute("nonexistent_tool", {})
        assert result.ok is False
        assert result.code == ErrorCode.TOOL_NOT_FOUND

    def test_invalid_arguments(self):
        core = _make_core()
        result = core.tool_registry.execute("search_library", {})
        assert result.ok is False
        assert result.code == ErrorCode.INVALID_ARGUMENTS

    def test_gateway_unavailable(self):
        core = AssistantCoreService()
        gws = AssistantGateways()
        register_builtin_tools(core.tool_registry, gws)
        result = core.tool_registry.execute("search_library", {"query": "test"})
        assert result.ok is False
        assert result.code in (ErrorCode.CAPABILITY_UNAVAILABLE, ErrorCode.TOOL_FAILED)

    def test_playback_not_playing_error(self):
        gw = FakePlaybackGateway()
        result = gw.pause()
        assert result.get("ok") is False
        assert "NOT_PLAYING" in str(result.get("error", ""))

    def test_settings_unknown_key(self):
        gw = FakeSettingsGateway()
        result = gw.get_setting("nonexistent/key")
        assert result.get("ok") is False


class TestWorkflowAssistantSession:
    def test_create_session_and_process(self):
        core = _make_core()
        session = core.create_session()
        assert session.ok is True
        sess_id = session.data.session_id
        request = AssistantRequest(text="busca jazz", session_id=sess_id)
        response = core.process_message(request)
        assert response.type in (
            AssistantResponseType.ANSWER,
            AssistantResponseType.PLAN_PREVIEW,
            AssistantResponseType.ERROR,
            AssistantResponseType.CLARIFICATION,
            AssistantResponseType.EXECUTION_RESULT,
        )

    def test_get_suggestions(self):
        core = _make_core()
        suggestions = core.get_suggestions()
        assert isinstance(suggestions, list)
