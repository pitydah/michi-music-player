# M6.9-BACKEND-R1.3 — Final Authority Barrier + Resurrection Prevention Seal

Status: implemented. R1.3 closes the last backend authority gaps found
after R1.2 (which is therefore SUPERSEDED FOR FINAL AUTHORITY CLOSURE by
this seal). NO UI/QML/EnrichmentBridge; NO M11.3D; NO audio; NO
canonical metadata; NO tag writes; NO new providers. Protected surfaces
(MetadataExtractor, LibraryIndexRepository, enrichment ports, audio,
presentation) carry ZERO diff in this work package.

## Why R1.3 exists (resurrection vectors closed)

R1.2 introduced the generation + authority-gate model, but three gaps
remained, all proven by deterministic tests in this WP:

1. **Generation ownership split**: the coordinator computed generations
   itself (`_generation_counter`) and only mirrored them into the
   service. Two code paths could disagree on the current generation.
2. **Key-scoped cancellation**: `cancel_artist_request(key)` /
   `cancel_all_requests()` invalidated by LOCAL KEY, not by generation —
   a late cancel could invalidate a NEWER request for the same key.
3. **Album artist dependency**: an album in flight after its artist
   identity changed/reset could still commit knowledge correlated with
   the OLD artist.

## The final authority model (FIX-01..FIX-08)

### Single generation authority (FIX-01)

`EnrichmentService` is now the SOLE generation authority:

- `begin_operation(entity_kind, local_key) -> int` — allocates the next
  strictly monotonic generation under the authority lock (never cleared,
  never re-used).
- `retire_operation(entity_kind, local_key, generation) -> bool` — the
  canonical retirement barrier: if the generation is NOT current it
  returns False (a stale worker can never retire a newer generation); if
  current, the epoch advances AND the same-generation pending request is
  invalidated atomically via `ledger.invalidate_if_generation_current`.
- The coordinator's `_generation_counter` is deleted; every operation
  asks the service for its generation.

### Generation-scoped cancellation everywhere (FIX-02/05/06)

- `cancel_artist_request` / `cancel_album_request` /
  `cancel_all_requests` / `cancel_operation` are REMOVED from the public
  API. Nothing key-scoped exists anymore.
- One coordinator helper `_retire_token(token)` = token.cancel() +
  service.retire_operation(kind, key, token.generation). All worker
  gates, public cancel, cancel_all, shutdown and terminal failures use
  it — a stale worker can NEVER touch a newer generation.
- `cancel_all()` takes a SNAPSHOT of the active tokens and retires each
  one by its own generation: an operation started AFTER the snapshot is
  never accidentally cancelled.
- `shutdown()` closes admission FIRST, retires every active generation,
  THEN waits on the executor — a resolver returning during shutdown can
  never cross an authority gate.

### Identity barriers (FIX-03/04/06) — the resurrection seal

`confirm_artist_identity`, `reset_artist_identity`,
`confirm_album_identity`, `reset_album_identity` and
`clear_identities` are now authority-locked barriers: each advances the
generation epoch and invalidates the same-generation pending request
under the same lock that serializes delivery. A late AUTO/EMBEDDED
result can never resurrect an identity, a request or knowledge after a
manual confirm, a reset or a clear. `clear_identities` bumps EVERY known
generation epoch (the dict stays monotonic, never cleared).

MANUAL identities can never be downgraded: any later automatic
operation short-circuits against the MANUAL identity and can never
replace it (§51-53).

### Album artist-dependency revalidation (FIX-07)

`request_album_enrichment` captures the resolved artist dependency
(artist local key + external id) on the `EnrichmentRequest`.
`deliver_album_profile` revalidates it under the authority lock before
commit: if the artist identity is missing (reset) or points to a
different external id (re-confirm A -> B), the result is STALE with
zero writes. A dependency key without a captured id played no part in
resolution and is not enforced.

## Test seal

`tests/test_m6_9_backend_r1_3_final_authority.py` — 22 deterministic
tests over the PUBLIC application surface (2 real executor workers,
threading.Event only, zero sleeps):

- manual-vs-inflight-AUTO (P0), MANUAL-never-downgrade (artist+album)
- reset / clear_identities resurrection seal + fresh next generation
- album artist-dependency: A->B, reset, unchanged-control
- delivery races in BOTH orders, artist AND album
- old-failure-vs-new-request (artist + album, §30)
- retire_operation barrier semantics + strict monotonicity
- dedicated ledger unit test for `invalidate_if_generation_current`
- cancel_all SNAPSHOT semantics (C started after the snapshot commits)
- public-cancel race, shutdown admission race (coordinator level)

Plus the M6.9A suites re-expressed on the new API
(`test_m6_9a_r1_persistence`, `cross_contamination`, `enrichment_firewall`,
`r2_request_invalidation`, `r3_1_final_invariants`) and a determinism fix
for the R1.2 direct-ledger race test (worker parked in fetch_artist).

## Final validation

- Full suite: 2396 passed, 2 skipped (baseline 2374 + 22 new).
- ruff clean across `src/michi` and `tests/`.
- Protected-surface diff vs the M11.3D sync base (SYNCED_BASE_HEAD
  `cb41c0a`): ZERO audio/index/metadata/presentation changes.
- Exact-head CI verified on the R1.3 PR (Lint / Test / Build success).

## Frozen status

M6.9 BACKEND: DONE / TESTED / FROZEN.
M6.9 TOTAL: IN PROGRESS (Presentation not implemented).
PR #217 (R1.2) stays unmerged; the R1.3 branch supersedes it in one PR.
