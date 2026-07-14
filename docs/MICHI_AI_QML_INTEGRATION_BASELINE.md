# Michi AI QML Integration Baseline

## Metadata

| Field | Value |
|-------|-------|
| Baseline SHA | `c73c76a` |
| QML base branch | `main` (QML convergence point) |
| Integration branch | `integration/michi-ai-core-v2` |
| Michi AI Core SHA | `0f2a095` |
| Date | 2026-07-14 |

## ServiceContainer (current)

The current `core/service_container.py` manages:
- `audio` — AudioService/GStreamerEngine
- `playback` — PlayerService
- `library` — LibraryService
- `queue` — QueueService
- `playlists` — PlaylistService
- `settings` — SettingsService
- `recognition` — RecognitionService
- `context` — ContextService
- `diagnostics` — DiagnosticsService
- `tools` — ToolRegistry (legacy)

## BridgeFactory (current)

`ui_qml_bridge/bridge_factory.py` creates QML-facing bridges.

## MichiAIBridge (current)

`ui_qml_bridge/michi_ai_bridge.py` — contains legacy integration with old AI assistant.

## ActionRegistry (current)

`ui_qml_bridge/action_registry.py` — general UI action registry.

## Tests (existing)

| Suite | Path | Count |
|-------|------|-------|
| AI tests | `tests/ai/` | 310 |
| QML AI tests | `tests/qml/ai/` | ~10 |

## V2 Modules Imported

| Module | Status |
|--------|--------|
| `michi_ai/v2/` | ✅ |
| `michi_ai/v2/core/` | ✅ |
| `michi_ai/v2/context/` | ✅ |
| `michi_ai/v2/intent/` | ✅ |
| `michi_ai/v2/plan/` | ✅ |
| `michi_ai/v2/tools/` | ✅ |
| `michi_ai/v2/provider/` | ✅ |
| `michi_ai/v2/conversation/` | ✅ |
| `michi_ai/v2/trace/` | ✅ |
| `michi_ai/v2/suggest/` | ✅ |
| `michi_ai/v2/eval/` | ✅ |
| `tests/ai/` (310 tests) | ✅ |
| `tests/ai/tools_v2/` | ✅ |
| `docs/MICHI_AI_CORE_V2_BASELINE.md` | ✅ |
| `docs/MICHI_AI_TOOL_MIGRATION_MATRIX.md` | ✅ |
| `docs/MICHI_AI_INTEGRATION_CONTRACT.md` | ✅ |
| `docs/MICHI_AI_CORE_V2_CLOSURE_REPORT.md` | ✅ |
