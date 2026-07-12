# Wave XVI Completion Plan

**Base SHA:** 6ccae4ca423f4a9c014caae7fa193a6ae962098a  
**Branch:** qml-wave16-final-closure

## Problemas P0 a corregir

| # | Bloque | Problema | Archivo |
|---|---|---|---|
| 1 | A | cancelled_cb ejecuta lógica desde QRunnable | core/worker_manager.py |
| 2 | A | on_done/on_error no desconectan ambas conexiones | core/worker_manager.py |
| 3 | A | task_id duplicado mezcla resultados | core/worker_manager.py |
| 4 | B | on_cancelled no entregado a WorkerManager | ui_qml_bridge/query_executor.py |
| 5 | B | supersede marca cancelled sin cancelar TaskHandle | ui_qml_bridge/query_executor.py |
| 6 | B | shutdown de QE apaga WM compartido | ui_qml_bridge/query_executor.py |
| 7 | E | JobBridge creado localmente en LibraryBridge | ui_qml_bridge/library_bridge.py |
| 8 | E | ScannerJobAdapter sin TaskContext | core/scanner_job_adapter.py |
| 9 | G | TrackActionService duplicado en LibraryBridge | ui_qml_bridge/library_bridge.py |
| 10 | G | toggleFavoriteById accede a _db directo | ui_qml_bridge/library_bridge.py |
| 11 | H | saveAsPlaylist crea PlaylistsBridge sin dependencias | ui_qml_bridge/queue_bridge.py |
| 12 | L | SmartTaggingBridge no usa TaskContext | ui_qml_bridge/smart_tagging_bridge.py |
| 13 | D | BridgeFactory orden incorrecto | ui_qml_bridge/bridge_factory.py |
| 14 | F | JobsPage refresh es no-op | ui_qml/pages/jobs/JobsPage.qml |

## Commits planeados

```
fix(workers): complete main-thread cancellation and connection lifecycle
fix(qml): complete query executor terminal cancellation semantics
refactor(qml): inject shared core workflow services through bridge factory
fix(scanner): route all qml scans through shared cancellable jobs
feat(jobs): complete job model progress retry cancellation
feat(queue): complete visible queue with injected dependencies
feat(metadata): complete async smart tagging with task context
test(qml): verify wave sixteen closure end to end
```
