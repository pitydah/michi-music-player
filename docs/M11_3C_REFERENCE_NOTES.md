# M11.3C Reference Notes — GStreamer AudioPort transport

Evidence-based design notes from the external study workspace. ADR 0007
remains canonical. REIMPLEMENT policy: no source copied (firewall per
LICENSE_BOUNDARIES.md).

## Pipeline topology — PLAYBIN3

| SOURCE | OBSERVATION | MICHÍ DECISION | REJECTED | LICENSE |
| --- | --- | --- | --- | --- |
| Strawberry `gstenginepipeline.cpp:559-611` | `playbin3` desde GStreamer ≥ 1.24 (fallback `playbin`); sink custom reemplazado | **PLAYBIN3** — transporte local de alto nivel (URI, decode, seek, duration, sink seam) | custom pipeline (complejidad que solapa M11.4/M11.5) | GPL evidence → REIMPLEMENT |

M11.3C necesita transporte confiable, no un grafo audiophile todavía. El seam
de sink de playbin3 preserva la futura selección de salida M11.4 (no se
implementa ahora).

## Bus / event model

| SOURCE | OBSERVATION | MICHÍ DECISION | LICENSE |
| --- | --- | --- | --- |
| GStreamer `gstbus.c:943-1056` | `gst_bus_add_watch_full` sobre un GLib MainContext | Adapter posee su PROPIO GLib MainContext/MainLoop + hilo pump dedicado; `gst_bus_add_watch` en ese contexto | LGPL evidence → REIMPLEMENT |
| Strawberry `gstenginepipeline.cpp:1045` | bus watch registrado; mensajes EOS/ERROR/STATE_CHANGED en el callback | Traducción de mensajes en el pump; **nunca** invocar servicios de aplicación desde hilos GStreamer arbitrarios | GPL → REIMPLEMENT |
| Strawberry `:2084` | estado cacheado desde STATE_CHANGED (no `gst_element_get_state()` bloqueante) | Estado de runtime = mensajes STATE_CHANGED observados | GPL → REIMPLEMENT |
| Repo Michi (ThreadScanRunner/ScanRelay/LibraryScanDispatcher) | worker thread → señales Qt → QueuedConnection al hilo owner | **Dispatch**: pump GLib emite eventos vía puente Qt (signals) con QueuedConnection → callbacks del AudioPort entregados en el hilo del owner — MISMA thread-affinity que QtMultimediaBackend | interno |

## State semantics — preroll vs user pause

| SOURCE | OBSERVATION | MICHÍ DECISION |
| --- | --- | --- |
| Strawberry `:2234` | "Preroll paused… then transition to the requested state once the seek completes (pending_state_)" | `pending_state_` explícito: PAUSED de preroll ≠ user PAUSED; el adapter rastrea la intención de comando y el estado real del pipeline |

## Acceptance semantics

- `media_accepted(path)` = el pipeline alcanzó evidencia runtime de aceptación
  (preroll/ASYNC_DONE del fuente actual con generación vigente) — nunca por
  el simple hecho de asignar URI o llamar play().
- `media_rejected(path, reason)` = ERROR pre-acceptance con generación vigente.

## Seek / time conversion

- Externo: milisegundos (contract AudioPort). Interno: GST_TIME_AS_NSECONDS.
- Helpers explícitos: `millis_to_gst_time()` / `gst_time_to_millis()`.
- Sin flags avanzados sin evidencia; seek fallido nunca commitea posición falsa.

## Stale isolation

- `generation` por fuente: `load()` incrementa; todo mensaje de una generación
  anterior se IGNORA (acceptance/rejection/EOS/state/duration/position/error).
- `close()` invalida la generación y detiene el pump antes de `set_state(NULL)`.

## Teardown order

1. invalidar generación; 2. detener pump/context; 3. remover bus watch;
4. `pipeline.set_state(NULL)`; 5. liberar referencias; 6. sin callbacks tras
close (guard post-close).

## Thread-affinity contract

- PRODUCER: pump GLib (hilo del adapter) para mensajes GStreamer.
- DISPATCH: señales Qt (emit thread-safe) + QueuedConnection → hilo owner.
- CONSUMER: hilo del owner (app) — idéntico a QtMultimediaBackend.

## Reuse map

| CAPABILITY | REFERENCE | MICHI LAYER | CLASS |
| --- | --- | --- | --- |
| playbin3 transporte | Strawberry/GStreamer | infrastructure/gstreamer.py | REIMPLEMENT |
| bus watch + MainContext propio | GStreamer | infrastructure | REIMPLEMENT |
| pending_state_ preroll | Strawberry | infrastructure | REIMPLEMENT |
| generation guard | — (Michi) | infrastructure | REIMPLEMENT |
| dispatch Qt QueuedConnection | ThreadScanRunner (repo) | infrastructure | ADOPT (interno) |

Zero source copied; todas las decisiones reimplementadas en contratos
Michi-nativos.

## M11.3C-R1 runtime correction (real GI verification)

- Real Gst.State values verified: NULL=1, READY=2, PAUSED=3, PLAYING=4 —
  the fake had modeled incompatible values; production now uses ONLY
  symbolic `bindings.STATE.*` (regression-locked).
- GLib ownership corrected: ONE MainContext/MainLoop/pump thread per port;
  bus watch via `bus.create_watch()` + `source.set_callback` +
  `source.attach(custom_context)`; position poll via
  `GLib.timeout_source_new` + attach. Sources destroyed on pipeline
  replacement/close; no orphan pump (pump_start_count == 1 across loads).
- Provenance is TYPE-AWARE: STATE_CHANGED top-level pipeline only; ERROR
  accepts child-element sources of the CURRENT generation; EOS/ASYNC_DONE/
  DURATION_CHANGED generation-guarded. No catch-all src rule.
- Provider probe truth: GI + Gst 1.0 + playbin3 factory must all exist for
  available=True (playbin3 missing → unavailable with truthful reason).
