from __future__ import annotations

from michi_ai.v2.core.models import ParsedIntent, ToolDefinition
from michi_ai.v2.intent.capability_resolver import CapabilityResolver
from michi_ai.v2.plan.plan_builder_v2 import PlanBuilderV2
from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2


class TestPlanBuilderV2:
    def setup_method(self):
        self.tool_registry = ToolRegistryV2()
        self.cap_resolver = CapabilityResolver()
        self.builder = PlanBuilderV2(self.tool_registry, self.cap_resolver)

        for tool_name in ["play_track", "play_album", "play_artist", "play_playlist",
                          "create_smart_mix", "create_playlist", "recommend_conversion_profile",
                          "preview_conversion", "start_conversion", "scan_library_health",
                          "preview_library_repair", "apply_library_repair",
                          "plan_device_sync", "start_device_sync"]:
            self.tool_registry.register(ToolDefinition(
                name=tool_name, description=f"Tool {tool_name}",
                handler=lambda: {"ok": True},
            ))

    def test_build_play_album_plan(self):
        intent = ParsedIntent(
            intent_id="play_album", confidence=0.9, source="rules",
            entities={"artist": "Radiohead", "album": "OK Computer"},
        )
        plan = self.builder.build_plan(intent, session_id="s1")
        assert plan.plan_id != ""
        assert plan.session_id == "s1"
        assert plan.intent == "play_album"
        assert len(plan.steps) > 0
        assert plan.steps[0].tool == "play_album"
        assert plan.steps[0].arguments.get("artist") == "Radiohead"

    def test_build_create_mix_plan(self):
        intent = ParsedIntent(
            intent_id="create_smart_mix", confidence=0.9, source="rules",
            entities={"genre": "Rock", "decade": "1990s"},
        )
        plan = self.builder.build_plan(intent, session_id="s1")
        assert plan.intent == "create_smart_mix"
        assert len(plan.steps) > 0
        assert plan.title == "Crear mix inteligente"

    def test_build_conversion_plan(self):
        intent = ParsedIntent(
            intent_id="start_conversion", confidence=0.85, source="rules",
            entities={"format": "OPUS"},
        )
        plan = self.builder.build_plan(intent, session_id="s1")
        assert plan.requires_confirmation is True
        assert len(plan.steps) == 3

    def test_build_scan_health_plan(self):
        intent = ParsedIntent(
            intent_id="scan_library_health", confidence=0.9, source="rules",
        )
        plan = self.builder.build_plan(intent)
        assert plan.intent == "scan_library_health"
        assert plan.title == "Diagnosticar biblioteca"

    def test_unknown_intent_fallback(self):
        intent = ParsedIntent(
            intent_id="nonexistent", confidence=0.0, source="fallback",
        )
        plan = self.builder.build_plan(intent, session_id="s1")
        assert plan.plan_id != ""
        assert plan.title == "Consulta"

    def test_plan_has_risks_when_applicable(self):
        intent = ParsedIntent(intent_id="apply_library_repair", confidence=0.9, source="rules")
        plan = self.builder.build_plan(intent)
        assert len(plan.risks) > 0

    def test_plan_with_context_selection(self):
        intent = ParsedIntent(intent_id="add_to_queue", confidence=0.9, source="rules")
        context = {"selection": {"track_ids": ["1", "2", "3"]}}
        self.builder.build_plan(intent, context)
        # Plan should reference selection
        pass

    def test_expires_at_set(self):
        intent = ParsedIntent(intent_id="pause", confidence=0.95, source="rules")
        plan = self.builder.build_plan(intent)
        assert plan.expires_at != ""
        assert plan.created_at != ""
