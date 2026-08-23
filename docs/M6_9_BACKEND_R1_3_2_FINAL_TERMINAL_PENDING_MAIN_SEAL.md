# M6.9-BACKEND-R1.3.2 — Final Terminal + Pending Request + Current-Main Seal

Status: implemented. R1.3.2 closes the two residual backend defects
found after R1.3.1 and converges ONCE with the current frozen audio
main.

## SHAs (real)

- SOURCE R1.3.1: `c54e60da6b2936854d267f5e338658179dd032c0`
- BASE_MAIN_SHA: `8a2537f27e9c72b5dfd3e0015578f9ca99b6a08f`
  (origin/main at closure — `docs(audio): reconcile m11.3d closure
  leftovers`; M11.3D explicitly DONE / TESTED / REAL-RUNTIME VERIFIED /
  FROZEN. NOTE: main advanced DURING this WP by two DOCUMENTATION-ONLY
  commits (`8970dec`, `8a2537f`; zero src/tests changes, both reassert
  the M11.3D freeze and authorize M11.3E as the NEXT WP — no M11.3E
  code exists; rule §1 A/B/C applied, no STOP triggered). The
  integration therefore performed two documentation-only convergence
  merges, never chasing a moving audio baseline.)
- FINAL CODE HEAD: `413c1b4fd3b163aa35a636aa91c2876af59d3bb7`
  (post-merge code head; final HEAD = docs commit, see CI section)
- Merge base: `git merge-base --is-ancestor 8a2537f HEAD` = 0 and
  `git merge-base --is-ancestor c54e60d HEAD` = 0 — HEAD contains the
  frozen main AND the full R1.3.1 backend plus the R1.3.2 corrections.

## P1-01 — LATE FAILURE AFTER CANCELLATION MUST BE CANCELLED

An operation is OBSOLETE when: its token was cancelled (manual confirm /
reset / supersession), the coordinator is shutting down, the registry no
longer holds THAT token, or the Service says the generation is no
longer current.

`_terminal_failure` / `_terminal_unexpected` now gate on obsolescence
FIRST (`_operation_is_obsolete`, lock order Coordinator -> Service):

- OBSOLETE OPERATION + LATE ERROR = CANCELLED (never OFFLINE/FAILED)
- CURRENT OPERATION + TRANSIENT NETWORK ERROR = OFFLINE
- CURRENT OPERATION + NON-TRANSIENT / UNEXPECTED ERROR = FAILED

Late invalidation stays exact: request_id + generation, or
`retire_operation(entity, key, exact_generation)` — a stale worker can
never cancel a newer request.

## P1-02 — NEW GENERATION MUST IMMEDIATELY SUPERSEDE OLD PENDING REQUEST

`begin_operation` now invalidates the previous pending request of the
entity under the SAME `_authority_lock` before allocating the next
monotonic generation. Atomic: BEGIN NEW OPERATION = PREVIOUS REQUEST
IMMEDIATELY SUPERSEDED. No zombie request can outlive the operation
that produced it — `pending_count()` returns to zero even when the new
operation fails before registering its own request. The invalidation
can never touch a newer request (this begin holds the highest
generation by construction); concurrent begin stays linearizable.

## Tests (real)

`tests/test_m6_9_backend_r1_3_2_terminal_pending_seal.py` — 7
deterministic tests (threading.Event, real threads, zero sleeps),
each with WHY THIS FAILED ON R1.3.1 and verified RED against the
R1.3.1 behavior before the fix:

- A. artist cancelled then transient provider failure -> CANCELLED;
  OFFLINE/FAILED never appear; MANUAL identity stays; zero writes;
  pending_count == 0
- B. album reset then transient provider failure -> CANCELLED; no
  Album identity/knowledge resurrection
- C. control: current transient failure -> OFFLINE
- D. control: current non-transient failure -> FAILED
- E. new begin retires the old pending request immediately
  (pending_count == 0 before the new request exists); old worker
  cannot commit nor leave a zombie
- F. double-begin linearization regression (coordinator token
  generation == Service current generation)
- G. old failure vs new request: obsolete A -> CANCELLED and its exact
  invalidation cannot touch B; B commits exactly once

## Validation (real numbers)

- focused (R1.3.2 + R1.3.1 + R1.3 + R1.2 + R1.1 + R1 cancellation):
  69 passed
- all M6.9: 603 passed
- full suite: **2440 passed, 1 skipped, 13 warnings** — zero failures
  (the two R1.3.1-era environmental failures on this machine were
  fixed by the frozen main itself: MPD config-value quoting + updated
  availability probe). The 1 skip is the pre-existing m11_3b Qt-runtime
  conditional skip.
- Ruff check: PASS · Ruff format --check: PASS · `python -m build`:
  PASS
- Warnings: 13 (unchanged from baseline; no new warnings)

## Firewall proofs (diffs vs BASE_MAIN_SHA `8a2537f`)

- audio (`audio_engines/**`, `playback_service.py`,
  `audio_engine_service.py`, `audio_transport_router.py`,
  `audio_engine_registry.py`): **EMPTY (0 lines)**
- canonical metadata (`metadata_extractor.py`, `library_index.py`,
  `domain/library.py`): **EMPTY (0 lines)**
- QML / presentation: **EMPTY (0 files)**
- src diff vs main = only the historical M6.9 enrichment delta
  (16 files, all enrichment domain/service/coordinator/infra/docs)

## CI

- The repo workflow (`ci.yml`) uses `actions/checkout` on the PR merge
  ref — this is **PR MERGE-REF CI**, not exact-branch-head CI.
  Reported truthfully below.
- PR: #220 (supersedes #219; #219 stays open until the replacement is
  audited — no merge/close without explicit authorization)
- Run ID: recorded after the run; ref: `refs/pull/<n>/merge` against
  base main `8a2537f`
- Lint / Test / Build: see run conclusion (must be success)

## FINAL TERMINAL LINEARIZATION (last P1)

The original R1.3.2 terminal path still contained a TOCTOU:

    check obsolete (Coordinator lock released)
    -> race window: manual/reset/cancel/supersession steals authority
    -> retire_operation returns False
    -> bool IGNORED
    -> OFFLINE / FAILED (wrong: authority was lost BEFORE terminalizing)

The final seal makes the terminal authority claim ONE linearizable
decision: `_claim_terminal_authority(token)` performs the Coordinator
state check (shutdown / token cancelled / registry no longer holds
this token) AND the Service retirement (`retire_operation` -> bool)
under the SAME `Coordinator._lock` acquisition. The retire bool IS the
verdict:

- True  -> this terminal path won: transient -> OFFLINE,
  non-transient/unexpected -> FAILED;
- False -> authority was already lost: CANCELLED.

Both `_terminal_failure` and `_terminal_unexpected` use the SAME
helper (order: CLAIM -> exact request cleanup via
`cancel_request_exact` (request_id + generation) -> classify). The old
`_operation_is_obsolete` method is removed (no remaining callers).

Deterministic proof (`GatedRetireService` gates `retire_operation`
before the service authority lock): while the terminal claim owns the
Coordinator lock, a concurrent `confirm_artist_identity` is provably
BLOCKED (`manual_done` unset); after the claim finishes, the worker
reports OFFLINE (it won), the manual confirm completes and the MANUAL
identity stands. This test was RED on R1.3.2 (the manual confirm
completed during the worker's gated retire because the retire ran
outside the Coordinator lock) and is GREEN after the fix.

## Final verdict

- P0 = 0
- P1 = 0
- M6.9 BACKEND — DONE / TESTED / FROZEN
- M6.9 TOTAL — BACKEND FROZEN / PRESENTATION NEXT AUTHORIZED WP
  (M6.9-PRESENTATION-R1 — EnrichmentBridge + Artist/Album Knowledge +
  Manual Review Integration — NOT started)
