# QML PR #50 Final Consolidation Report

## Base
- Branch: qml-functional-closure-release-readiness
- HEAD: 4602c0c
- PR: #50
- Date: 2026-07-04
- CI status: GREEN (all checks passed)

## Baseline
| Metric | Result |
|---|---|
| ruff check | 0 errors |
| compileall | PASSED |
| smoke_startup | PASSED |
| smoke_ui_routes | PASSED |
| check_runtime | PASSED |
| pytest tests/qml/ | 354 passed |
| test_playback_controller | 6 passed |
| test_format_probe | 41 passed |
| test_schema | 15 passed |
| route_registry_audit | PASSED |
| bridge_contract_audit | PASSED |
| CI gate (11 steps) | PASSED |

## Correcciones aplicadas

### Playback error propagation
- error_occurred conectado a NowPlayingBridge._on_error()
- _set_command_success/failure helpers con estado de comando
- lastCommand, lastCommandOk, lastCommandError properties

### Uniform contract
- _ok(operation, data) / _err(error_code, message) con operation y data
- Todos los comandos migrados al nuevo contrato
- clearQueue: eliminado fallback a stop()
- enqueueSong: EMPTY_FILEPATH en vez de INVALID_POSITION
- playQueueItem: sin fallback a play(filepath)

### Capabilities (15 properties)
playPauseSupported, seekSupported, volumeSupported, muteSupported,
nextSupported, previousSupported, queueSupported, queueRemoveSupported,
queueClearSupported, queueMoveSupported, queuePlayItemSupported,
shuffleSupported, repeatSupported, historySupported

### Queue normalization
- _normalize_queue_item(): no expone filepath/uri/url
- _queue_internal_refs almacena referencias internas
- Formato público: queue_index, track_id, title, artist, album, etc.

### History
- _add_to_history desde _on_track, max 50, dedup consecutivo
- clearHistory(), playHistoryItem() implementados

### Evidence-based scoring
- Manifest con module_weights (suma 100 por area)
- 25 modulos con evidence estructurada
- Validate verifica consistencia
- Score: 55.3% (honesto, con pesos)
- Physical JSON con status NOT_RUN
