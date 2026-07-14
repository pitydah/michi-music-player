# Michi AI QWidget Extraction Plan

This document audits the remaining QWidget-based Michi AI components and specifies their migration path to `AssistantCoreService`.

## Audit Results

| File | Widgets | Business Logic | Target Service | Status |
|------|---------|---------------|----------------|--------|
| `michi_ai/ui/michi_ai_page.py` | `QFrame`, `QLabel`, `QScrollArea`, `QVBoxLayout` | Snapshot display, insight cards, action cards | `AssistantCoreService` + `TraceRecorder` | To extract |
| `ui/controllers/michi_ai_controller.py` | (needs verification) | (needs verification) | `AssistantCoreService` | To audit |

## Extraction Strategy

### Phase 1: Legacy Adapter

Create a thin adapter that wraps `AssistantCoreService` in the old interface:

```python
class MichiAIControllerLegacyAdapter:
    def __init__(self, core: AssistantCoreService):
        self._core = core

    def process_message(self, text):
        response = self._core.process_message(
            AssistantRequest(text=text)
        )
        return self._to_legacy_format(response)
```

This adapter lets existing QWidget pages function without modification while the QML migration proceeds.

### Phase 2: Migration of Business Logic

| Current Location | Logic | Destination |
|-----------------|-------|-------------|
| `michi_ai_page.py:set_snapshot()` | Snapshot rendering | Remove (data from `ContextAssembler`) |
| `michi_ai_page.py:set_insights()` | Insight display | Remove (data from `SuggestionEngineV2`) |
| `michi_ai_page.py:set_actions()` | Action list display | Remove (data from `ResponseComposer`) |
| `michi_ai_page.py:_build_insight_card()` | Card HTML generation | Remove (QML renders natively) |

### Phase 3: Remove duplicate engines

Do NOT maintain two AI engines. Once `AssistantCoreService` is fully integrated:

1. Remove `integrations/ai_assistant/service.py` (replaced by `AssistantCoreService`)
2. Remove `integrations/ai_assistant/intent_router.py` (replaced by `IntentRouterV2`)
3. Remove `michi_ai/planner/plan_builder.py` (replaced by `PlanBuilderV2`)
4. Remove `michi_ai/planner/plan_executor.py` (replaced by `PlanExecutorV2`)
5. Remove `michi_ai/planner/confirmation_policy.py` (replaced by `ConfirmationPolicyV2`)
6. Remove `michi_ai/tools/tool_registry.py` (replaced by `ToolRegistryV2`)
7. Refactor `integrations/ai_assistant/tools/*` into proper gateway implementations

### Dependencies Remaining

| Dependency | File(s) | Status |
|-----------|---------|--------|
| `core.context.context_snapshot.sanitize_snapshot` | `prompt_context_builder.py`, `contextual_suggestion_engine.py` | To refactor |
| `core.context.context_events.AppEvent` | `service.py` | To refactor |
| `core.paths.ai_assistant_dir` | `action_log.py`, `conversation_store.py` | To refactor |

## Files NOT to delete (yet)

These will be removed after QML migration verifies the new core:

- `integrations/ai_assistant/*` (all)
- `michi_ai/context/*` (all)
- `michi_ai/planner/*` (all)
- `michi_ai/tools/*` (all)
- `michi_ai/intelligence/*` (all)
- `michi_ai/ui/*` (all)
