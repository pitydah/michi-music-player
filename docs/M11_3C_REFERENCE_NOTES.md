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

## M11.3C-R2 final runtime truth seal

- ASYNC_DONE = acceptance only; NEVER publishes PLAYING (runtime state truth
  comes exclusively from STATE_CHANGED new_state == PLAYING).
- State requests are failure-atomic: preroll PAUSED failure rejects the
  candidate once (+ best-effort NULL teardown + port reusable); play/pause
  roll back intents on FAILURE; stop publishes STOPPED only after a
  successful NULL; pipeline replacement aborts if the previous NULL fails;
  close reports teardown errors but stays best-effort.
- Pump termination integrity: join(timeout) followed by is_alive() — a live
  worker retains its references and raises instead of being silently lost.
- Real adapter smoke: GStreamerAudioPort with real GI (custom MainContext/
  bus GSource/fakesink) — SKIP truthful when local plugins lack WAV decode.

## M11.3C-R3 final failure-atomicity seal

- load() is TRANSACTIONAL (PHASE A REPLACE OLD / PHASE B ARM NEW): the old
  pipeline stays canonical until its NULL teardown succeeds; a failed
  replacement preserves old pipeline + bus observability + current_path +
  generation + play intent and never creates the new pipeline (commit
  point = successful NULL of the old pipeline, not entry into load()).
- Preroll failure cleanup is failure-atomic: the candidate is rejected
  FIRST (primary semantic event); NULL cleanup success releases the failed
  pipeline; NULL cleanup failure RETAINS pipeline ownership (never pretend
  cleanup succeeded) and raises the cleanup error to the caller — close()
  can still clean the retained pipeline later.
- close() is FIRST-ERROR-WINS: the chronologically first failure (pipeline
  teardown before pump shutdown) is authoritative; a later pump timeout
  never replaces it.
- Real bus watch fixed: create_watch()+set_callback() silently dropped
  every real message in PyGObject (GstBusSource dispatch calls the
  GSourceFunc as (user_data) — the message arrived as None and was
  discarded behind the message-None guard, silencing the whole real
  runtime). The canonical bus.add_watch (GstBusFunc marshaller) attached to
  the pump context via push_thread_default restores real delivery: the real
  adapter smoke now PASSES end-to-end (real playbin3 + fakesink + WAV
  preroll + real pump + close/join).
- Real smoke is TRUTHFUL: SKIP only with a dependency proven absent via
  ElementFactory preflight (named factory), FAIL on timeout/rejection when
  all mandatory factories are present. Code-validation evidence: full suite
  1681 passed at CODE_VALIDATED_HEAD c20360d (1 pre-existing conditional
  skip: M11.3B Qt-runtime).

## M11.3C-R4 bus watch lifecycle seal

- Gst.Bus.add_watch() is correct for install; its return value is a source
  ID for bookkeeping only. Removal uses Gst.Bus.remove_watch() with NO
  source-id parameter (verified against real GI: passing an id raises
  TypeError). The previous remove_bus_watch(bus, watch_id) + blanket
  suppress(Exception) hid that TypeError and leaked old bus watches across
  load(A)→load(B)→load(C)→close().
- remove_bus_watch(bus) now uses the real contract and returns bool;
  _detach_pipeline_sources() raises on failed/impossible removal; load
  replacement aborts before arming B when old watch removal fails; close()
  composes removal failure into first-error-wins.
- Repeated real-watch lifecycle verified: real Gst.Bus add/remove across
  A→B→C→close (TrackingRealBindings: add 3 / remove 3 / active watches 0).
  Code-validation evidence: full suite 1689 passed at CODE_VALIDATED_HEAD
  1f5a481 (1 pre-existing conditional skip: M11.3B Qt-runtime).
