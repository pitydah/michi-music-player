# M11.3B Reference Notes — Qt reference runtime lifecycle

Evidence-based design notes from the external study workspace. ADR 0007
remains canonical; this document records OBSERVED PATTERNS and their Michi
relevance only (no source copies; firewall per LICENSE_BOUNDARIES.md —
everything here is REIMPLEMENT).

| REFERENCE | OBSERVED PATTERN | MICHI RELEVANCE | DECISION | RATIONALE |
| --- | --- | --- | --- | --- |
| Strawberry (`src/engine/enginebase.h:91-127`) | `EngineBase` separates `Init()` from playback ops; `Stop(stop_after)` quiesces before teardown | probe/open (runtime init) is distinct from load/play (transport ops) | ADOPT (already in provider contract) | PlaybackService never sees engine init; the router only forwards transport |
| Strawberry (`gstengine.cpp:318-333`) | `Stop()` calls `StopTimers()` before pipeline teardown — timers/callbacks are quiesced BEFORE the backend is released | provider close must stop the backend BEFORE dropping ownership | ADOPT (Qt provider: `backend.stop()` then `_backend = None`) | No callbacks may fire from a provider that no longer owns its backend |
| DeaDBeeF (`deadbeef.h:1991-2001`) | plugin `stop` = deinit; `disconnect` is called BEFORE `stop` while all plugins are still alive | consumers unsubscribe from the transport BEFORE the provider closes | ADOPT (SWITCH ORDER: router.unbind → provider.close) | Already sealed in M11.3A-R1; productive wiring must honor it |
| Audacious (`plugin.h:200-242`) | output plugin `open_audio`/`close_audio` pair; `force_reopen` requires open after close; `flush()` before close | open after close produces a fresh instance; close is the terminal operation | ADOPT (Qt provider reopen → new backend) | Deterministic ownership: repeated open = same instance until close; reopen = fresh |
| Squeezelite (`output.c:430`) | `output_close_common()` — a single deterministic teardown path shared by all exits | one canonical close path (provider.close), never scattered teardown | ADOPT | Idempotent close; no phantom owned backend after terminal close |
| Audacious (`plugin.h:75`) | docs: flush() only called when it makes sense — the contract is explicit per plugin | transport ops are defined by AudioPort, never by provider quirks | ADOPT | AudioPort stays the single transport contract |

## Design conclusions for M11.3B

1. **Init/playback separation**: provider.probe/open = runtime init; the
   AudioPort returned owns transport ops only. PlaybackService sees only the
   router (transport).
2. **Quiesce-before-release**: provider.close() calls backend.stop() first,
   then releases ownership; the router must be unbound BEFORE close (the
   composition coordinator owns the order, never the provider).
3. **Deterministic reopen**: open() → same instance until close; close() →
   idempotent; reopen() → fresh instance. No uncontrolled second engine.
4. **Callback isolation**: router detach guarantees no backend callback
   reaches PlaybackService/PlaybackCoordinator after the switch/close point.
5. **Failure honesty**: a provider whose runtime is present but whose adapter
   is not implemented must never claim READY (can_activate gate).

No source code was copied; all patterns were reimplemented in Michi-native
contracts (provider/registry/router/lifecycle).
