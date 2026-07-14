# Michi AI Core V2 Baseline

Generated from audit of existing assistant architecture.

## HEAD

Branch: `feature/michi-ai-core-v2`
Base: `c73c76a` (Macrofases AI-BM)
Date: 2026-07-14

## Files (Existing AI)

### `michi_ai/` (19 source files)

```
michi_ai/__init__.py
michi_ai/context/__init__.py
michi_ai/context/ai_context_bridge.py
michi_ai/context/ai_event_mapper.py
michi_ai/context/ai_insight_service.py
michi_ai/context/ai_snapshot_service.py
michi_ai/intelligence/__init__.py
michi_ai/intelligence/audio_intelligence_bridge.py
michi_ai/planner/__init__.py
michi_ai/planner/action_plan.py
michi_ai/planner/confirmation_policy.py
michi_ai/planner/plan_builder.py
michi_ai/planner/plan_executor.py
michi_ai/tools/__init__.py
michi_ai/tools/audio_lab_tools.py
michi_ai/tools/config_tools.py
michi_ai/tools/library_tools.py
michi_ai/tools/michi_link_tools.py
michi_ai/tools/playlist_tools.py
michi_ai/tools/sync_tools.py
michi_ai/tools/tool_permissions.py
michi_ai/tools/tool_registry.py
michi_ai/tools/tool_result.py
michi_ai/ui/__init__.py
michi_ai/ui/michi_ai_page.py
```

### `integrations/ai_assistant/` (29 source files)

```
integrations/ai_assistant/__init__.py
integrations/ai_assistant/action_confirmation.py
integrations/ai_assistant/action_log.py
integrations/ai_assistant/allowed_actions.py
integrations/ai_assistant/contextual_suggestion_engine.py
integrations/ai_assistant/conversation_store.py
integrations/ai_assistant/intent_router.py
integrations/ai_assistant/ollama_client.py
integrations/ai_assistant/permissions.py
integrations/ai_assistant/privacy_filter.py
integrations/ai_assistant/privacy_guard.py
integrations/ai_assistant/prompt_context_builder.py
integrations/ai_assistant/prompts.py
integrations/ai_assistant/schemas.py
integrations/ai_assistant/service.py
integrations/ai_assistant/tool_registry.py
integrations/ai_assistant/tools/__init__.py
integrations/ai_assistant/tools/audio_analysis_tools.py
integrations/ai_assistant/tools/audio_conversion_tools.py
integrations/ai_assistant/tools/ecosystem_tools.py
integrations/ai_assistant/tools/favorite_tools.py
integrations/ai_assistant/tools/knowledge_tools.py
integrations/ai_assistant/tools/library_tools.py
integrations/ai_assistant/tools/metadata_review_tools.py
integrations/ai_assistant/tools/metadata_tools.py
integrations/ai_assistant/tools/navigation_tools.py
integrations/ai_assistant/tools/playlist_tools.py
integrations/ai_assistant/tools/queue_tools.py
integrations/ai_assistant/tools/recommendation_tools.py
integrations/ai_assistant/tools/stats_tools.py
```

### `core/context/` (21 source files)

```
core/context/__init__.py
core/context/context_events.py
core/context/context_invalidator.py
core/context/context_repository.py
core/context/context_service.py
core/context/context_snapshot.py
core/context/section_context_provider.py
core/context/section_context_registry.py
core/context/setup_section_providers.py
core/context/providers/__init__.py
core/context/providers/audio_lab_context_provider.py
core/context/providers/connections_context_provider.py
core/context/providers/devices_context_provider.py
core/context/providers/genre_context_provider.py
core/context/providers/home_audio_context_provider.py
core/context/providers/library_context_provider.py
core/context/providers/metadata_context_provider.py
core/context/providers/mix_context_provider.py
core/context/providers/playback_context_provider.py
core/context/providers/playlist_context_provider.py
core/context/providers/settings_context_provider.py
```

## Services

| Service | File | Status |
|---------|------|--------|
| `MichiAISnapshotService` | `michi_ai/context/ai_snapshot_service.py` | Existing |
| `MichiAIInsightService` | `michi_ai/context/ai_insight_service.py` | Existing |
| `MichiAIContextBridge` | `michi_ai/context/ai_context_bridge.py` | Existing |
| `AudioIntelligenceBridge` | `michi_ai/intelligence/audio_intelligence_bridge.py` | Existing |
| `PlanBuilder` | `michi_ai/planner/plan_builder.py` | Existing (static) |
| `PlanExecutor` | `michi_ai/planner/plan_executor.py` | Existing |
| `ToolRegistry` | `michi_ai/tools/tool_registry.py` | Existing |
| `AIAssistantService` | `integrations/ai_assistant/service.py` | Existing (monolithic) |
| `IntentRouter` | `integrations/ai_assistant/intent_router.py` | Existing (dead code) |
| `ContextService` | `core/context/context_service.py` | Existing |
| `ContextualSuggestionEngine` | `integrations/ai_assistant/contextual_suggestion_engine.py` | Existing |

## Tools (Existing)

| Tool | Module | Status |
|------|--------|--------|
| `list_config_plans` | `michi_ai/tools/config_tools.py` | Fake success |
| `get_michi_link_status` | `michi_ai/tools/michi_link_tools.py` | Fake success |
| `get_sync_status` | `michi_ai/tools/sync_tools.py` | Fake success |
| `list_sync_peers` | `michi_ai/tools/sync_tools.py` | Fake success |
| `get_pending_analysis` | `michi_ai/tools/audio_lab_tools.py` | Fake success |
| `get_analysis_summary` | `michi_ai/tools/audio_lab_tools.py` | Fake success |
| `search_library` | `integrations/ai_assistant/tools/library_tools.py` | Real |
| 40+ tools | `integrations/ai_assistant/tools/*` | Various |

## Intents (Existing)

| Intent | Detected By | Status |
|--------|-------------|--------|
| 25+ regex patterns | `service.py:_detect_intent()` | Hardcoded |
| 50+ keyword mappings | `intent_router.py:_ACTION_MAPPING` | Hardcoded |
| Ollama fallback | `service.py:_call_ollama()` | Real (NL response only) |

## Plans (Existing)

| Plan | Steps | Status |
|------|-------|--------|
| `prepare_mobile_sync` | 1 | Static |
| `prepare_micro_server_remote` | 1 | Static |
| `prepare_space_saver_mobile` | 1 | Static |
| `prepare_hifi_profile` | 1 | Static |
| `prepare_home_audio` | 1 | Static |
| `clean_library_metadata` | 1 | Static |

## Tests (Existing)

| Test File | Type | Status |
|-----------|------|--------|
| `tests/test_michi_ai.py` | Unit | Smoke |
| `tests/test_intent_router.py` | Unit | Smoke |
| `tests/test_contextual_suggestion_engine.py` | Unit | Smoke |
| `tests/test_ai_assistant_service_context.py` | Context | Smoke |
| `tests/qml/ai/*` | QML | Platform-specific |

## Dependencies on UI

| File | Import | Status |
|------|--------|--------|
| `michi_ai/ui/michi_ai_page.py` | `PySide6.QtWidgets` | To extract |
| All others | None | Clean |

## Technical Debt

| Issue | Severity | Location |
|-------|----------|----------|
| Fake success returns | HIGH | 6 tools in `michi_ai/tools/*` |
| Bare dict contracts | HIGH | All layers (60+ dict literals) |
| Static plans | MEDIUM | `plan_builder.py:_PLAN_DEFS` |
| Silent exception swallowing | MEDIUM | 6 instances across files |
| Dead `IntentRouter._detect_via_ollama()` | MEDIUM | `intent_router.py:141` |
| Unregistered tools in allowed_actions | MEDIUM | `ecosystem_tools` not registered |
| O(n) full-library scans | LOW | 7 tool files call `db.get_all()` |

## Risks

| Risk | Mitigation |
|------|------------|
| Two parallel AI engines during migration | Phase out old after QA |
| QML bridge must reimplement context providers | Contract documented in INTEGRATION_CONTRACT.md |
| Legacy tools with fake success may confuse testing | All replaced by typed OperationResult |
| Privacy filters need adversarial validation | Test suite includes adversarial cases |
