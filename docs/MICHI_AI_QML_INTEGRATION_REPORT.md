# Michi AI QML Integration Report

## Baseline

| Field | Value |
|-------|-------|
| Baseline SHA | `c73c76a` |
| Integration branch | `integration/michi-ai-core-v2` |
| Michi AI Core V2 | `0f2a095` |
| Date | 2026-07-14 |

## Commits Integrated

The entire `feature/michi-ai-core-v2` branch (0f2a095) was merged into the QML convergence base (main@c73c76a).

## Gateways Implemented

| Gateway | Status | Service Used |
|---------|--------|--------------|
| `ProductionPlaybackGateway` | ✅ PRODUCTION | `PlayerService` |
| `ProductionQueueGateway` | ✅ PRODUCTION | `PlayerService` (enqueue/queue methods) |
| `ProductionLibraryGateway` | ✅ PRODUCTION | `LibraryDB` |
| `ProductionPlaylistGateway` | ✅ PRODUCTION | `LibraryDB` (playlist methods) |
| `ProductionSettingsGateway` | ✅ PRODUCTION | `SettingsService` |
| `ProductionAudioLabGateway` | ✅ PARTIAL | `AnalysisService` (analyze + cancel methods) |
| `ProductionDeviceGateway` | ✅ PARTIAL | `SyncManager` (list_devices only) |
| `ProductionDiagnosticsGateway` | ✅ BASIC | stub |
| `ProductionMixGateway` | 🔴 UNAVAILABLE | needs `MixQueryService` wiring |
| `ProductionJobGateway` | ✅ PRODUCTION | `JobService` |
| `UnavailableNavigationGateway` | ✅ STUB | returns REQUEST_ACCEPTED |
| `UnavailableRadioGateway` | 🔴 UNAVAILABLE | Radio Core V2 not yet integrated |
| `UnavailableLyricsGateway` | 🔴 UNAVAILABLE | Lyrics Core V2 not yet integrated |
| `UnavailableMetadataGateway` | 🔴 UNAVAILABLE | Metadata Core V2 in development |
| `UnavailableLibraryDoctorGateway` | 🔴 UNAVAILABLE | needs LibraryDoctorService |
| `UnavailableConnectionsGateway` | 🔴 UNAVAILABLE | needs ConnectionService |
| `UnavailableHomeAudioGateway` | 🔴 UNAVAILABLE | needs HomeAudioService |

## Services Connected

| ServiceContainer Name | Connected |
|----------------------|-----------|
| `assistant_core_service` | ✅ built via `_build_assistant_core()` |
| `assistant_tool_registry` | ✅ ToolRegistryV2 with 60+ tools |
| `assistant_capability_resolver` | ✅ dynamic |
| `assistant_context_assembler` | ✅ with 10 context providers |
| `assistant_conversation_service` | ✅ ConversationService |
| `assistant_confirmation_service` | ✅ ConfirmationPolicyV2 |
| `assistant_trace_recorder` | ✅ TraceRecorder |
| `assistant_gateways` | ✅ AssistantGateways dataclass |

## Capabilities

| Capability | Available |
|------------|-----------|
| `playback.control` | ✅ from PlayerService |
| `queue.read` / `queue.modify` | ✅ from PlayerService |
| `library.search` / `library.read` | ✅ from LibraryDB |
| `playlist.read` / `playlist.modify` | ✅ from LibraryDB |
| `settings.read` / `settings.modify` | ✅ from SettingsService |
| `audio_lab.analyze` | ✅ from AnalysisService |
| `audio_lab.convert` | 🔴 UNAVAILABLE |
| `devices.read` / `devices.sync` | 🔴 PARTIAL (list only) |
| `diagnostics.read` | ✅ stub |
| `mix.generate` | 🔴 UNAVAILABLE |
| `radio.control` | 🔴 UNAVAILABLE |
| `navigation.request` | ✅ stub |
| `metadata.read` / `metadata.modify` | 🔴 UNAVAILABLE |
| `library_doctor.scan` / `library_doctor.repair` | 🔴 UNAVAILABLE |

## Tools Registered

60+ tools registered via `register_builtin_tools()` in `ServiceContainer._build_assistant_core()`.

## MichiAIBridge

Refactored to thin adapter:
- Receives only `AssistantCoreService` in constructor
- Exposes: `sendMessage`, `confirmAction`, `rejectAction`, `cancelCurrentRequest`, `requestSuggestions`, `dismissSuggestion`, `clearConversation`, `startNewSession`
- Signals: `responseChanged`, `statusChanged`, `progressChanged`, `confirmationRequested`, `suggestionsChanged`, `errorOccurred`, `sessionChanged`
- Properties: `status`, `currentResponse`, `responseType`, `responseTitle`, `isBusy`, `progress`, `pendingConfirmation`, `suggestions`, `sessionId`
- No legacy `AIController`, `PlanBuilder`, `ToolRegistry` imports

## Confirmation

- Tokens are single-use, session-scoped, with TTL
- QML receives `confirmationRequested(planId, summary, details)` signal
- `confirmAction(confirmationId)` and `rejectAction()` slots
- No `confirmed=True` pattern

## Context Providers

10 providers registered:
- `PlaybackContextProvider`, `QueueContextProvider`, `LibraryContextProvider`
- `SelectionContextProvider`, `NavigationContextProvider`, `DeviceContextProvider`
- `ServerContextProvider`, `SettingsContextProvider`, `JobContextProvider`
- `DiagnosticsContextProvider`

All have timeouts, limited output, and tolerate partial failure.

## Threading

`AssistantCoreService.process_message()` runs in calling thread.
Production gateway methods delegate to service layer which handles thread safety.

## Cancellation

`cancelCurrentRequest()` cancels pending confirmation plans via `AssistantCoreService.cancel_execution()`.
Jobs are cancelled via `JobGateway`.

## Tests

| Suite | Count | Status |
|-------|-------|--------|
| `tests/ai/` | 310 | ✅ ALL PASS |
| `tests/ai/tools_v2/` | 74 | ✅ ALL PASS |

## Gate Results

| Gate | Result |
|------|--------|
| Ruff | ✅ 0 errors |
| Compileall | ✅ PASS |
| QtWidgets imports in `michi_ai/v2` | ✅ 0 |
| QtWidgets imports in `core/assistant_gateways.py` | ✅ 0 |
| Single construction path | ✅ via `ServiceContainer._build_assistant_core()` |
| Shutdown order | ✅ documented |

## Remaining Debt

| Item | Impact | Resolution |
|------|--------|------------|
| 6 gateways unavailable | Some capabilities not available to AI | Wire when corresponding Core V2 services are integrated |
| No QML workflow tests yet | Need QML engine integration | Add in QML branch after this merge |
| Legacy `michi_ai/` directory still present | Not imported by V2 | Remove after full QML integration confirms no regressions |
| Legacy `integrations/ai_assistant/` still present | Not imported by V2 | Remove after full QML integration |

## Shutdown Order

1. Reject new messages
2. Cancel active request
3. Cancel active plans
4. Persist conversation if needed
5. Flush trace recorder
6. Close conversation service
7. Release gateways

`ensure_assistant_core()` is the single entry point. `AssistantCoreService` is a deferred service in `ServiceContainer`.
