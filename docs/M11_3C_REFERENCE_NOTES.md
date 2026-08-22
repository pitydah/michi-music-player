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
- `close()` invalida la generación y ejecuta el teardown terminal ANTES de detener el pump (ver Teardown order).

## Teardown order (M11.3C-R6.2 current truth)

1. marcar port closed e invalidar la generación;
2. detach del bus watch (best-effort — su fallo se registra, no corta);
3. `pipeline.set_state(NULL)` — SIEMPRE intentado aunque el detach haya
   fallado (non-negotiable);
4. limpieza del timer;
5. quit/join del pump (timeout → ownership retenido + error secundario);
6. liberar SOLO los recursos realmente muertos; pipeline retenido si NULL
   falló; bookkeeping del watch retenido si su remoción falló;
7. FIRST-ERROR-WINS: el primer fallo cronológico es el autoritativo;
8. sin callbacks tras close (guard post-close).

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
  **SUPERSEDED BY R3/R4** — current truth: the bus watch is installed with
  `Gst.Bus.add_watch()` (GstBusFunc marshaller) while the port's custom
  MainContext is thread-default, and removed with `Gst.Bus.remove_watch()`
  (no watch-id argument); the position timer remains the explicit GSource.
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

## M11.3C-R5 terminal cleanup seal

- close() is BEST-EFFORT: a bus-watch removal failure can never skip the
  pipeline NULL request; the pipeline is cleared only when NULL succeeds
  (retained when it fails) and timer/pump cleanup always continues. The
  first chronological cleanup failure is authoritative (remove → NULL →
  timer → pump), later failures are secondary (never replace the primary).
- Failed-preroll cleanup ordering: NULL cleanup failure is PRIMARY; a
  later bus-watch detach failure is SECONDARY and never replaces the NULL
  error. media_rejected remains the semantic event, emitted before
  cleanup. Contract table: PAUSED+NULL OK+remove OK → reject only;
  PAUSED+NULL OK+remove FAIL → bus cleanup error; PAUSED+NULL FAIL+remove
  FAIL (triple) → NULL cleanup error primary, pipeline retained.
- Code-validation evidence: full suite 1696 passed at CODE_VALIDATED_HEAD
  43a1281 (1 pre-existing conditional skip: M11.3B Qt-runtime).

## M11.3C-R5.1 cleanup exception-boundary seal

- The two best-effort cleanup boundaries (terminal close teardown and
  failed-preroll lifecycle cleanup) catch ANY normal Exception from the
  GStreamer bindings (TypeError, ValueError, GLib.Error, ...), not only
  RuntimeError: the error is recorded, later cleanup steps (NULL, timer,
  pump) always run, and first-error-wins preserves the original exception
  object. BaseException (KeyboardInterrupt/SystemExit/GeneratorExit) is
  never caught. Normal load replacement stays transactional/strict.
## M11.3C-R6 transport lifecycle & arm transaction seal

- stop() has TWO semantics: a PENDING candidate stop cancels the candidate
  (transactional teardown, generation invalidation blocks late
  acceptance); an ACCEPTED source stop stops the transport WITHOUT
  unloading — current_path/generation/pipeline/bus watch stay intact, so
  play()/resume() replay the same source with no new load and position
  polling keeps working.
- EOS converges to STOPPED before emitting EOM exactly once per terminal
  cycle; the current source is retained; a late EOS queued before an
  explicit user stop is ignored (pending-play guard). play() after EOS
  performs a controlled NULL→PLAYING restart on the same pipeline (no
  reload, no second media_accepted); failure-atomic: the EOS marker
  resets only when PLAYING succeeds.
- The pipeline ARM (PHASE B of load) is exception-atomic: any normal
  Exception during construction/configuration/watch/timer/PAUSED request
  triggers _rollback_failed_arm() — failed-candidate generation
  invalidation, candidate identity cleared, broken timer destroyed,
  best-effort NULL + watch detach, truthful ownership — and the ORIGINAL
  arm exception is re-raised as primary. After a successful old-source
  teardown the adapter converges to STOPPED before arming B.
- Code-validation evidence: full suite 1730 passed at CODE_VALIDATED_HEAD
  f88e729 (1 pre-existing conditional skip: M11.3B Qt-runtime).


## M11.3C-R6.1 resource ownership & load-disposition convergence seal

- Failed-ARM ownership invariant: the pipeline is the retryable cleanup
  anchor — it is released ONLY when NULL AND the bus watch removal both
  succeeded (NULL OK + detach FAIL retains pipeline/bus/watch, so close()
  or a later load can retry the removal; `_pipeline is None` implies
  `_bus_source is None` in normal states). No permanently orphaned
  Gst.Bus watch.
- AudioLoadError (application/ports.py): canonical synchronous load
  failure with explicit previous_source_preserved disposition. GStreamer
  raises it with False for any PHASE B ARM failure (the old source already
  crossed the destructive teardown commit point), chaining the original
  low-level exception as __cause__. Pre-commit failures (teardown failure,
  watch detach failure while A is retained) keep the preserved semantics.
- PlaybackService: destructive failures no longer restore backend
  acceptance/intent (file_path stays the last committed LOGICAL track;
  status STOPPED); play() reloads the committed track through the
  canonical candidate path when no backend acceptance exists — no silent
  no-op. M11.3D MPD MUST raise AudioLoadError with truthful disposition.
- Real stop→play gate: real playbin3 + fakesink WAV — accept, real
  PLAYING, stop → NULL (source/generation/pipeline retained), second play
  → PLAYING again, single acceptance, close clean.
- Code-validation evidence: full suite 1745 passed at CODE_VALIDATED_HEAD
  04a5063 (1 pre-existing conditional skip: M11.3B Qt-runtime).


## M11.3C-R6.2 terminal runtime truth seal

- Playback-state authority restored: state_of() now unpacks the
  parse_state_changed() TUPLE — PyGObject returns (old, new, pending), so
  the previous `.new` attribute access always raised and the real
  STATE_CHANGED signal was silently dropped: with the real runtime the
  adapter never published any PlaybackStatus even though the pipeline was
  physically PLAYING (pipeline.get_state() worked; the productive
  contract did not). Provenance stays strict: top-level pipeline
  STATE_CHANGED accepted, child-element state changes ignored (verified
  with real GI — same wrapper identity for the pipeline, children
  rejected).
- Real gate: AudioPort callbacks now deliver PLAYING → STOPPED → PLAYING
  over a real playbin3 + fakesink WAV (get_state kept as diagnostics).
- Two-phase load_and_play: PHASE 1 load() keeps the AudioLoadError
  disposition; PHASE 2 play() failure after a successful load(B) never
  restores previous A acceptance/intent (accepted=intent=False, STOPPED,
  logical file_path = last committed track; late media_accepted(B)
  ignored; play() reloads A canonically).
- Code-validation evidence: full suite 1749 passed at CODE_VALIDATED_HEAD
  2328591 (1 pre-existing conditional skip: M11.3B Qt-runtime).
