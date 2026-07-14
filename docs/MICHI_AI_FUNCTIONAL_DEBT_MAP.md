# Michi AI Functional Debt Map

| Issue | Severity | Location | Status | Fix |
|-------|----------|----------|--------|-----|
| `ProductionMetadataGateway` missing | BLOCKER | `core/assistant_gateways.py` | `MISSING` | Create new file |
| `to_dict()` missing fields | BLOCKER | `core/assistant_gateways.py:AssistantGateways` | `PARTIAL` | Add all 17 fields |
| `ensure_assistant_core()` in BridgeFactory | BLOCKER | `ui_qml_bridge/bridge_factory.py` | `LEGACY_ADAPTER` | Move to composition root |
| No `assistant_initializer.py` | BLOCKER | composition root | `MISSING` | Create |
| QueueGateway uses PlayerService | FALSE_SUCCESS | `core/assistant_gateways.py` | `CAPABILITY_MISMATCH` | Connect to QueueService |
| PlaylistGateway uses LibraryDB | FALSE_SUCCESS | `core/assistant_gateways.py` | `CAPABILITY_MISMATCH` | Connect to PlaylistService |
| `set_shuffle` non-idempotent | FALSE_SUCCESS | `core/assistant_gateways.py` | `PARTIAL` | Add state check |
| No async execution | ASYNC_REQUIRED | `ui_qml_bridge/michi_ai_bridge.py` | `MISSING` | Add worker runtime |
| No cancellation propagation | ASYNC_REQUIRED | `ui_qml_bridge/michi_ai_bridge.py` | `MISSING` | Wire tokens |
| No dynamic capabilities | CAPABILITY_MISMATCH | `core/assistant_gateways.py` | `MISSING` | Add CapabilityState enum |
| No metadata context provider | PARTIAL | `core/assistant_context_providers.py` | `MISSING` | Add provider |
| No stale request guard | ASYNC_REQUIRED | `ui_qml_bridge/michi_ai_bridge.py` | `MISSING` | Add request_id check |
| No metadata workflow tests | TEST_MISSING | `tests/ai/gateways/` | `MISSING` | Add |
| No composition tests | TEST_MISSING | `tests/qml/convergence/ai/` | `MISSING` | Add |
