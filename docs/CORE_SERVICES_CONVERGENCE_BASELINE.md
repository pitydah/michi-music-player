# Core Services Convergence Baseline

## HEAD

| Field | Value |
|-------|-------|
| Branch | `integration/core-services-convergence-v1` |
| SHA | `8eccd4c5` |
| QML baseline | `origin/qml-wave9-functional-core-services` |

## ServiceContainer

Located at `core/service_container.py`.
Contains 18 required + 12 optional services.
No assistant/lyrics/radio/metadata core services registered yet.

## ServiceBundle

Located at `ui_qml_bridge/service_bundle.py`.
Passes service references to bridges.

## BridgeFactory

Located at `ui_qml_bridge/bridge_factory.py`.
Creates bridges with injected services. Contains legacy blocks that try to create AIController, PlanBuilder, etc.

## Composition Root

Spread across:
- `qml_main.py` (or equivalent)
- `core/application_bootstrap.py`
- `core/service_container.py`

## Bridges Registered

Detected from `bridge_factory.py`:
- navigation
- michi_ai (legacy — creates AIController/PlanBuilder internally)
- cover
- library
- playback
- lyrics (basic)
- radio (basic)
- metadata (basic)
- settings
- diagnostics
- queue
- history

## QML Context Properties

Registered in `ui_qml_bridge/context_bindings.py` or similar.

## Services Created Inside Bridges

- `create_michi_ai_bridge`: creates AIController, PlanBuilder, ToolRegistry, ContextService internally
- Others may have similar patterns

## Tests

QML-related tests in `tests/qml/`.

## Baseline Audit Commands

The following commands will be run after each integration phase:
```bash
ruff check <domain>
python -m compileall -q <domain>
pytest tests/<domain> -q --timeout=900
```
