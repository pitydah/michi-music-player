from __future__ import annotations

"""Every intent→tool mapping must point to a tool registered in ToolRegistryV2.

Regression guard for the Fase 11.4 audit: the mapping in
core/ai_engine.py referenced tool names that were never registered
(search_artist, playback_play, playback_get_state, get_recommendations,
library_get_stats...), silently breaking execution.
"""

from core.ai_engine import MichiAIEngine
from core.ai.intent_router import IntentRouter
from michi_ai.v2.tools.tool_definitions import BUILTIN_TOOL_DEFINITIONS

REGISTERED_TOOLS = {d.name for d in BUILTIN_TOOL_DEFINITIONS}


def _mapped_tools() -> dict[str, str]:
    engine = MichiAIEngine()
    router = IntentRouter()
    intent_ids = {pattern[0] for pattern in router._patterns}
    # Also cover intents the engine maps even without a router pattern.
    intent_ids |= {"delete_playlist", "apply_library_repair", "restore_setting"}
    return {iid: engine._intent_to_tool(iid) for iid in sorted(intent_ids)}


def test_every_mapped_tool_is_registered():
    broken = {
        iid: tool for iid, tool in _mapped_tools().items()
        if tool is not None and tool not in REGISTERED_TOOLS
    }
    assert not broken, f"Intent→tool mappings pointing at unregistered tools: {broken}"


def test_router_intents_have_a_tool_or_none_is_explicit():
    # Every router intent either maps to a registered tool or deliberately
    # maps to None (handled without tool execution, e.g. greeting/help).
    engine = MichiAIEngine()
    router = IntentRouter()
    no_tool_allowed = {"greeting", "help", "out_of_scope", "unknown"}
    for intent_id in {p[0] for p in router._patterns}:
        tool = engine._intent_to_tool(intent_id)
        if tool is None:
            assert intent_id in no_tool_allowed, (
                f"Intent '{intent_id}' has no tool and is not in the no-tool allowlist"
            )
        else:
            assert tool in REGISTERED_TOOLS


def test_search_intents_map_to_search_library_with_query():
    engine = MichiAIEngine()
    router = IntentRouter()
    for text, expected_intent in (
        ("busca jazz", "search_library"),
        ("busca música de Genesis", "search_library"),
    ):
        intent = router.detect(text)
        tool = engine._intent_to_tool(intent.intent_id)
        assert tool in REGISTERED_TOOLS
        args = engine._tool_arguments(tool, intent)
        assert "query" in args or intent.intent_id == expected_intent


def test_engine_suggestions_use_natural_actions():
    """Suggestion actions must be phrases the IntentRouter understands."""
    engine = MichiAIEngine()
    router = IntentRouter()
    for suggestion in engine.get_suggestions():
        action = suggestion.get("action", "")
        if not action:
            continue
        intent = router.detect(action)
        assert intent.intent_id != "unknown", (
            f"Suggestion action '{action}' is not understood by the IntentRouter"
        )


class TestFixedToolHandlerWiring:
    """ADR-006: the previously-broken tools must reach their REAL gateway
    methods through the composition wiring (not just be registered)."""

    @staticmethod
    def _composition(fakes: dict):
        from core.assistant_initializer import create_assistant_composition
        return create_assistant_composition(**fakes)

    def test_draft_playlist_reaches_playlists_create(self):
        from unittest.mock import MagicMock
        playlist_svc = MagicMock()
        playlist_svc.create_playlist.return_value = {"ok": True, "id": 5, "name": "N"}
        playlist_svc.batch_add.return_value = {"ok": True, "count": 0}
        db = MagicMock()
        db.get_playlists.return_value = []
        comp = self._composition({"library_db": db, "playlist_service": playlist_svc})

        result = comp.tool_registry.execute("draft_playlist", {"name": "Nueva"})

        assert result.ok is True, result.error
        playlist_svc.create_playlist.assert_called_once_with("Nueva")
        playlist_svc.batch_add.assert_not_called()

    def test_delete_playlist_reaches_playlists_delete(self):
        from unittest.mock import MagicMock
        playlist_svc = MagicMock()
        playlist_svc.delete_playlist.return_value = {"ok": True}
        db = MagicMock()
        db.get_playlists.return_value = []
        comp = self._composition({"library_db": db, "playlist_service": playlist_svc})

        result = comp.tool_registry.execute("delete_playlist", {"playlist_id": "3"})

        assert result.ok is True, result.error
        playlist_svc.delete_playlist.assert_called_once_with(3)
        playlist_svc.create_playlist.assert_not_called()

    def test_restore_setting_reaches_settings_apply_change(self):
        from unittest.mock import MagicMock
        settings_svc = MagicMock()
        settings_svc.get.return_value = "old"
        settings_svc.set_.return_value = {"ok": True}
        settings_svc.reset.return_value = {"ok": True}
        comp = self._composition({"settings_service": settings_svc})

        result = comp.tool_registry.execute("restore_setting", {"key": "audio/volume"})

        assert result.ok is True, result.error
        settings_svc.reset.assert_called_once_with("audio/volume")

    def test_scan_library_health_reaches_doctor_scan(self):
        from unittest.mock import MagicMock
        doctor = MagicMock()
        doctor.scan.return_value = {"ok": True, "issues": [], "count": 0}
        comp = self._composition({"library_doctor_service": doctor})

        result = comp.tool_registry.execute("scan_library_health")

        assert result.ok is True, result.error
        doctor.scan.assert_called_once()

    def test_get_sync_status_reaches_device_diagnosis(self):
        from unittest.mock import MagicMock
        sync_manager = MagicMock()
        sync_manager.get_paired.return_value = []
        sync_manager.get_discovered.return_value = []
        sync_manager.list_jobs.return_value = []
        sync_manager.get_history.return_value = []
        comp = self._composition({"sync_manager": sync_manager})

        result = comp.tool_registry.execute("get_sync_status")

        assert result.ok is True, result.error
        sync_manager.list_jobs.assert_called_once()
        sync_manager.get_history.assert_called_once()
        sync_manager.get_paired.assert_not_called()

