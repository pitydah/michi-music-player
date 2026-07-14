# Core Services Convergence Report

## Baseline

| Field | Value |
|-------|-------|
| Branch | `integration/core-services-convergence-v1` |
| HEAD | current |
| QML baseline | `origin/qml-wave9-functional-core-services` at `8eccd4c` |
| Date | 2026-07-14 |

## Source SHAs

| Service | Ref | SHA |
|---------|-----|-----|
| Radio Core V2 | `feature/radio-core-v2` | `c73c76a` (base only) |
| Lyrics Core V2 | `feature/lyrics-core-v2` | `2b2f2bc` |
| Metadata Core V2 | `integration/metadata-core-v2` | `c73c76a` (base only) |
| Michi AI Core V2 | `feature/michi-ai-core-v2` | `0f2a095` |
| Michi AI Integration | `integration/michi-ai-core-v2` | `033d9cb` |

## Commits Integrated

1. `convergence: establish source manifest and baseline`
2. `convergence: integrate Michi AI Core V2` (62 files, 8642 lines)

## Architecture Delivered

```
Application
├── ServiceContainer (core/service_container.py)
│   ├── REQUIRED: event_bus, settings_service, job_service
│   │             playback_service, queue_service, library_query_service
│   ├── OPTIONAL: radio_service, lyrics_service, metadata_service
│   │             assistant_core_service, assistant_tool_registry
│   │             assistant_capability_resolver, assistant_context_assembler
│   │             assistant_conversation_service, assistant_confirmation_service
│   │             assistant_trace_recorder, assistant_gateways
│   │             diagnostics_service, action_registry
│   └── DEFERRED: musicbrainz_provider, cover_art_provider
│                 lrclib_provider, assistant_local_model_provider
│
├── AssistantGateways (core/assistant_gateways.py)
│   ├── ProductionPlaybackGateway → PlayerService
│   ├── ProductionQueueGateway → PlayerService
│   ├── ProductionLibraryGateway → LibraryDB
│   ├── ProductionPlaylistGateway → LibraryDB
│   ├── ProductionSettingsGateway → SettingsService
│   ├── ProductionAudioLabGateway → AnalysisService
│   ├── ProductionDeviceGateway → SyncManager
│   ├── ProductionDiagnosticsGateway → stub
│   └── UnavailableNavigationGateway, UnavailableRadioGateway...
│
├── Context Providers (core/assistant_context_providers.py)
│   └── 10 providers registered on ContextAssembler
│
├── ServiceBundle (ui_qml_bridge/service_bundle.py)
│   └── Typed dataclass with all service references
│
├── BridgeFactory (ui_qml_bridge/bridge_factory.py)
│   └── 34 bridge creation methods, NO service construction
│
└── MichiAIBridge (ui_qml_bridge/michi_ai_bridge.py)
    └── Thin adapter → AssistantCoreService
```

## Services Registered

| Name | Type | Available | Shutdown Support |
|------|------|-----------|-----------------|
| event_bus | OPTIONAL | depends on wiring | — |
| settings_service | REQUIRED | depends on wiring | — |
| job_service | REQUIRED | depends on wiring | — |
| playback_service | REQUIRED | via PlayerService | — |
| queue_service | REQUIRED | via PlayerService | — |
| library_query_service | REQUIRED | via LibraryDB | — |
| assistant_core_service | OPTIONAL | ✅ built via ensure_assistant_core() | has shutdown |
| assistant_tool_registry | OPTIONAL | ✅ | — |
| assistant_capability_resolver | OPTIONAL | ✅ | — |
| assistant_context_assembler | OPTIONAL | ✅ | — |
| assistant_gateways | OPTIONAL | ✅ | — |

## Bridges

| Bridge | Service Creation | Domain Logic | Status |
|--------|-----------------|--------------|--------|
| MichiAIBridge | ❌ NONE | ❌ NONE — delegates to AssistantCoreService | ✅ THIN |
| MetadataBridge | ❌ NONE | depends on metadata service | NEEDS WIRING |
| LyricsBridge | ❌ NONE | depends on lyrics service | NEEDS WIRING |
| RadioBridge | ❌ NONE | depends on radio service | NEEDS WIRING |

## Tests

| Suite | Count | Status |
|-------|-------|--------|
| `tests/ai/` | 310 | ✅ ALL PASS |

## Gates

| Gate | Result |
|------|--------|
| Ruff (new code) | ✅ 0 errors |
| Compileall (new code) | ✅ PASS |
| AI tests | ✅ 310 passed |
| QtWidgets imports in michi_ai/v2 | ✅ 0 |
| Bridge service creation | ✅ 0 |

## Remaining Debt

| Item | Impact | Resolution |
|------|--------|------------|
| Lyrics/Metadata/Radio Core services not wired | Some gateways return UNAVAILABLE | Wire when core services exist |
| No QML workflow tests for convergence | Need QML + engine | Add in next phase |
| Legacy michi_ai/ directory still present | Not imported by V2 | Remove after testing |
| Legacy integrations/ai_assistant/ still present | Not imported by V2 | Remove after testing |
