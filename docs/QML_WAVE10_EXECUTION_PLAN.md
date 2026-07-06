# QML Wave X — Async Dataflow Recovery + Daily Services Migration

## Branch

`qml-wave10-async-core-daily-services`

## Base SHA

```
46684e64c9b2dfdd9bbbd527df456bb993968cbf
```

## P0 Problems (inherited from Wave IX)

| # | Problem | Severity | File | Fix |
|---|---|---|---|---|
| 1 | BasePagedListModel passes `callback=` to QueryExecutor.submit | HIGH | BasePagedListModel | submit no acepta callback |
| 2 | QueryExecutor.submit no acepta callback | HIGH | query_executor.py | Agregar on_success/on_error |
| 3 | QueryExecutor usa WorkerManager.run (no existe) | HIGH | query_executor.py | Usar run_task |
| 4 | WorkerManager.run no existe | HIGH | worker_manager.py | No tocar; QE adapta a run_task |
| 5 | refresh lanza count y page con mismo owner | HIGH | BasePagedListModel | Combinar en PagedResult |
| 6 | Segundo request invalida primero | HIGH | BasePagedListModel | Usar generación única |
| 7 | `_all_done((p, p))` usa página como totalCount | HIGH | BasePagedListModel | Devolver (count, items) |
| 8 | Todos los modelos usan owner vacío | HIGH | BasePagedListModel | owner único por modelo |
| 9 | fetchMore pierde filtros y sort | HIGH | BasePagedListModel | Guardar _query_args |
| 10 | TrackListModel pasa sort/asc a count_tracks | HIGH | TrackListModel | count no necesita sort |
| 11 | LibraryQueryService._build_where no acepta sort | MEDIUM | library_query_service.py | Sort se extrae antes |
| 12 | TrackListModel pasa `ascending`, QueryService usa `asc` | HIGH | TrackListModel | Unificar a `asc` |
| 13 | AlbumListModel/ArtistListModel repiten inconsistencia | MEDIUM | AlbumListModel.py | Unificar contrato |
| 14 | Consultas background usarían conexión SQLite principal | HIGH | query_executor.py | Thread-safe DB |
| 15 | CI no ejecuta Full QML runtime smoke | MEDIUM | ci.yml | Agregar step |
| 16 | Tests E2E no ejecutan flujo real | HIGH | test_wave9_* | Reemplazar con DB real |

## Contractos incompatibles

| Contrato | Esperado | Real |
|---|---|---|
| submit(owner, fn, callback) | submit(owner, fn, on_success, on_error) | submit(owner, fn, request_context) |
| WorkerManager.run(fn, callback) | WorkerManager.run_task(task_id, fn, on_done, on_error) | No existe |
| asc vs ascending | asc | ascending en modelos, asc en QS |
| PagedResult | (count, items, query) | dos requests separados |

## Flujo esperado (refresh)

```
refresh(search="foo")
  → gen++
  → loading=true
  → executor.submit("tracks", task)
    → task(): PagedResult(count=1000, items=[...250])
    → success signal
  → _on_success:
    → totalCount=1000, beginReset, items=250, endReset
    → loading=false

fetchMore()
  → offset=250
  → executor.submit("tracks", task)
    → task(): items=[250..500]
    → success signal
  → _on_success:
    → beginInsert, extend items, endInsert
    → loadingMore=false
```

## Archivos afectados

| Archivo | Cambio |
|---|---|
| ui_qml_bridge/query_executor.py | Reescritura completa |
| core/worker_manager.py | No tocar (solo verificar compatibilidad) |
| ui_qml/models/BasePagedListModel.py | Reescritura completa |
| ui_qml/models/TrackListModel.py | Unificar contrato, quitar FilepathRole |
| ui_qml/models/AlbumListModel.py | Unificar contrato |
| ui_qml/models/ArtistListModel.py | Unificar contrato |
| ui_qml/models/FolderTreeModel.py | Unificar contrato |
| ui_qml/models/QueueListModel.py | Quitar FilepathRole |
| ui_qml/models/HistoryListModel.py | Quitar FilepathRole |
| ui_qml_bridge/library_query_service.py | FTS5 real, folder roots, thread-safe |
| ui_qml_bridge/library_bridge.py | Privacidad, lazy activation |
| ui_qml_bridge/library_refresh_coordinator.py | Completar métodos |
| ui_qml_bridge/playlists_bridge.py | Export/import corregido |
| ui_qml_bridge/smart_tagging_bridge.py | Async real, cancel, progress |
| ui_qml_bridge/action_registry.py → binder | Handlers reales |
| ui_qml_bridge/job_bridge.py | WorkerManager.run_task |
| ui_qml_bridge/bridge_factory.py | Inyectar dependencias faltantes |
| tests/qml/test_wave10_real_vertical_flow.py | Nuevo |
| docs/QML_WAVE10_EXECUTION_PLAN.md | Este archivo |

## Riesgos SQLite

- Usar `sqlite3.connect()` con `check_same_thread=False` + mutex
- O usar hilo dedicado con cola serializada
- O usar métodos thread-safe de LibraryDB

**Estrategia elegida:** WorkerManager ejecuta en QThreadPool. Cada tarea
abre su propia conexión READ-ONLY a la DB (WAL mode permite lectores concurrentes).
No hay escritura desde background en flujos de solo lectura.

## Criterios de aceptación

1. QueryExecutor.submit acepta on_success/on_error como señales Qt
2. BasePagedListModel.refresh ejecuta una sola tarea combinada (count+page)
3. fetchMore preserva filtros y sort
4. owner único por modelo (tracks, albums, artists, folders, queue, history)
5. Resultados obsoletos ignorados por generación
6. SQLite thread-safe (conexión read-only por tarea)
7. Modelos públicos sin filepath
8. FTS5 real cuando existe tabla, LIKE fallback explícito
9. Folder roots desde LibrarySourcesService (o config existente)
10. CI ejecuta Full QML runtime smoke
11. Test vertical con DB real, 1000 tracks, refresh, fetchMore, search, filters
12. Score funcional honesto

## Commits planeados

```
1. fix(qml): repair query executor and paged model contracts
2. fix(qml): preserve query state across async pagination
3. fix(library): separate query filters sorting and internal references
4. refactor(qml): complete database backed library vertical flow
5. fix(playlists): restore internal playback and import export contracts
6. feat(qml): integrate public safe queue and history models
7. feat(qml): make smart tagging asynchronous cancellable and verified
8. feat(qml): bind command palette actions to real services
9. feat(qml): integrate cancellable jobs through worker manager
10. feat(qml): migrate library sources scanner radio lyrics and mix
11. test(qml): add real wave ten vertical integration coverage
12. docs(qml): publish evidence based functional migration score
```
