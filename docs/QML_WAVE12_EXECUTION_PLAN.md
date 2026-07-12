# QML Wave XII — Runtime, Dataflow and SQLite Hardening

## Branch
`qml-wave12-runtime-dataflow-hardening`

## Base SHA
```
6664880e7bf52ae9a2e3aa8e655de1851bbb2681
```

## Problem Inventory

| # | Problem | File | Severity |
|---|---|---|---|
| 1 | WorkerManager no tiene cancelación cooperativa real | core/worker_manager.py | HIGH |
| 2 | QueryExecutor conecta lambdas permanentes a task_done | ui_qml_bridge/query_executor.py | HIGH |
| 3 | refresh ignora nueva query si loading=true | ui_qml/models/BasePagedListModel.py | HIGH |
| 4 | fetchMore puede insertar rango vacío | ui_qml/models/BasePagedListModel.py | MEDIUM |
| 5 | No hay debounce en búsqueda | QML pages | MEDIUM |
| 6 | LibraryQueryService sin db_path de producción | ui_qml_bridge/library_query_service.py | HIGH |
| 7 | FTS5 no conectado a flujo paginado normal | ui_qml_bridge/library_query_service.py | MEDIUM |
| 8 | LibraryPage aún expone songs/artists legacy | ui_qml_bridge/library_bridge.py | HIGH |
| 9 | Runtime smoke no detecta warnings semánticos | scripts/qml_full_runtime_smoke.py | MEDIUM |
| 10 | Tests E2E no usan WorkerManager real | tests/qml/test_wave10_*.py | HIGH |

## Commits planeados
```
fix(workers): add cancellable task handles and safe lifecycle
fix(qml): harden query executor cancellation and request cleanup
fix(qml): make paged models supersede stale requests safely
fix(library): use production sqlite connection factory for qml queries
feat(library): connect fts5 to normal paginated search
refactor(qml): remove synchronous legacy library bindings
feat(qml): add debounced search and resilient model states
feat(qml): add debounced search and resilient model states
test(qml): add real asynchronous production dataflow coverage
ci(qml): fail on semantic qml runtime warnings
```
