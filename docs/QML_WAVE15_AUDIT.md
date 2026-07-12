# Wave XV — Runtime Integrity Audit

**Date:** 2026-07-12
**Base SHA:** f991c578fc2c10dbec417ea37f09873f9bf075f9

## WorkerManager audit

| Issue | Severity | Detail |
|---|---|---|
| run_task no entrega token a fn | HIGH | CancellationToken creado pero no pasado |
| _TaskWorker captura CancelledError sin emitir | HIGH | No hay señal de cancelación |
| TaskHandle puede quedar en cancel_requested | MEDIUM | Sin timeout de estado |
| cancellable flag no controla contrato | MEDIUM | Siempre se crea token aunque no se use |
| callbacks conectados permanentemente | HIGH | task_done/task_error lambdas no se desconectan |
| on_progress no implementado | MEDIUM | No hay reporte de progreso |
| excepciones convertidas a texto crudo | MEDIUM | str(e) en error_code |
| RUNNING asignado antes de ejecución real | LOW | state=RUNNING antes de pool.start |

## QueryExecutor audit

| Issue | Severity | Detail |
|---|---|---|
| _on_done mantiene self._lock y llama a _prune (mismo lock) | HIGH | Riesgo de deadlock si lock no reentrante |
| supersede marca cancelled sin cancelar TaskHandle | HIGH | TaskHandle sigue ejecutándose |
| cancel no garantiza callback final | MEDIUM | Si worker ignora token, no hay callback |
| stale y cancelled comparten estados incorrectos | MEDIUM | |
| shutdown no completa todos los requests | MEDIUM | |
| submit tras shutdown devuelve ID inválido | LOW | request_id=0 no chequeado |

## BasePagedListModel audit

| Issue | Severity | Detail |
|---|---|---|
| activeRequestId no vuelve a cero | MEDIUM | Se queda con último request_id |
| activeRequestChanged no se emite al finalizar | MEDIUM | |
| refreshingChanged no consistente | LOW | |
| empty usa notify incompleto | LOW | |
| canRetry false para consulta inicial | LOW | |
| no se cancela en destrucción | HIGH | destroyed no conectado a dispose |
| no existe estado cancelled | MEDIUM | |
| fetchMore puede quedar inconsistente | MEDIUM | si loadingMore true y error |
| error anterior puede persistir | MEDIUM | _error_code no se limpia en refresh |

## SQLite Connection Factory audit

| Issue | Severity | Detail |
|---|---|---|
| threading.local global compartido entre instancias | HIGH | Distintos db_paths reusan conexión |
| close_all solo cierra thread actual | MEDIUM | |
| LibraryQueryService mantiene threading.local adicional | HIGH | Dos niveles de cache |
| search_fts devuelve filepath | MEDIUM | |

## LibraryQueryService audit

| Issue | Severity | Detail |
|---|---|---|
| FTS query no sanitizada | MEDIUM | |
| artistas con albumartist válido pero artist vacío excluidos | MEDIUM | |
| folder tree hijos inmediatos incorrectos | MEDIUM | |
| paths Windows pueden romperse | LOW | |
| _lib_sources construye servicio nuevo sin DB | MEDIUM | |
| detalles álbum no ordenan por disc_number | LOW | |
| errores internos incorporan str(e) como safe_message | MEDIUM | |

## Debounce audit

| Issue | Severity | Detail |
|---|---|---|
| DebouncedQueryController sin consumidores QML | HIGH | Existe archivo Python, ninguna página lo usa |

## Runtime smoke audit

| Issue | Severity | Detail |
|---|---|---|
| Rutas desconocidas resuelven a placeholder sin fallo | HIGH | Smoke las marca como correctas |
| Lista de rutas hardcodeada (15 rutas) | HIGH | Debería usar RouteRegistry |
| No verifica Loader status | MEDIUM | |
| No verifica currentRoute exacto | MEDIUM | |
| No verifica context properties | MEDIUM | |

## Tests audit

| Issue | Severity | Detail |
|---|---|---|
| test_wave12 usa tabla normal, no FTS5 virtual | MEDIUM | |
| test_wave12 no prueba cancelación real (solo model.cancel) | MEDIUM | |
| test_wave12 no prueba deadlock | MEDIUM | |
| test_wave12 no prueba error SQL | LOW | |
