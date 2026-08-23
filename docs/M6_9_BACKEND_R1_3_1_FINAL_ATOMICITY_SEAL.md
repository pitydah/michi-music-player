# M6.9-BACKEND-R1.3.1 — Final Begin Linearization + Album Dependency Precommit Seal

Status: implemented. R1.3.1 closes the LAST backend atomicity /
linearization defects found after R1.3. It is a corrective work package
ON TOP of the frozen M11.3D main and the complete R1.3 backend.

- BASE MAIN (current frozen main): `9677734854a3bd8da3ee55b26cbfea88d215553d`
  (`docs(audio): definitively freeze m11.3d` — M11.3D-R2 DONE/TESTED/FROZEN)
- R1.3 SOURCE (audited historical head): `149fb3cabce6919ad7b591fd7630ee5b7180903e`
- FINAL CODE VALIDATED HEAD: `4c9ea5b5dd0fbcae320d53a8b3d103f04747f21f`
- CI HEAD: `4c9ea5b5dd0fbcae320d53a8b3d103f04747f21f` (exact-head CI:
  Lint PASS / Test PASS / Build PASS)
- Tests (full suite, final head, CI environment): 2427 passed, 2 skipped,
  13 warnings (baseline after merge: 2418; +9 new seal tests)

History: `git merge-base --is-ancestor` returns 0 for BOTH the frozen
main and the R1.3 source — the final head contains both histories plus
the R1.3.1 corrections.

## Why this WP exists (P0 + P1, proven red on R1.3)

Three windows remained after R1.3, each demonstrated deterministically
by a test that FAILED against the R1.3 behavior and PASSES after the
fix:

1. **P0 — Album identity persisted with a stale artist dependency.**
   `request_album_enrichment` read Artist identity A, resolved the
   album with it, and — if the ALBUM generation was still current —
   persisted `AlbumExternalIdentity` even when the artist had changed
   A->B or been reset while the resolution was in flight. The R1.3
   dependency check ran only at KNOWLEDGE delivery: knowledge was
   protected, IDENTITY was not.
2. **P1 — non-linearizable operation publication.** `_begin_operation`
   published the token in a SECOND lock section: T1 could allocate
   gen1, T2 gen2, T2 publish, and T1 publish its gen1 token OVER T2 —
   Coordinator token gen1 while the Service current generation was
   gen2 (`assert 1 == 2` on R1.3).
3. **P1 — stale physical work after manual barriers.** Coordinator
   confirm/reset passthroughs never cancelled the in-flight token: the
   old worker kept running provider work and emitted useless FAILED
   terminal states. Also: any non-COMMITTED verdict (including STALE)
   converged to FAILED, misreporting authority loss as a user error.

## FIX-A — Album dependency precommit validation

`request_album_enrichment` now:

- captures the dependency BEFORE the resolver, only when the
  resolution actually uses the PERSISTED artist identity
  (`local_album_artist_key` set, no explicit external id, identity
  row exists): `dependency_artist_local_key` + `dependency_artist_external_id`;
- revalidates under the authority lock, in strict order, BEFORE
  `AlbumExternalIdentity` is persisted:
  - A. the Album generation must still be current (else SUPERSEDED);
  - B. the artist identity must still exist;
  - C. it must still point EXACTLY to the captured external id;
  - D. only then is the identity persisted;
  - E. and the request registered — ONE authority decision.
- never invents a dependency from an explicitly supplied external id
  (§4.3 contract); the embedded-release refine path registers without
  a dependency.
- keeps BOUNDARY 2 (delivery-time revalidation in
  `deliver_album_profile`) — artist changes are covered in both
  windows: during resolution AND after identity persistence / during
  knowledge fetch.

Result: `SUPERSEDED`, `request=None`, zero identity writes, zero
knowledge writes, `pending_count()==0` when the artist changes or is
reset while the album resolution is blocked mid-request.

## FIX-B — linearizable `_begin_operation`

Admission, previous-token cancellation, generation allocation, token
creation and token publication now happen under a SINGLE
coordinator-lock acquisition. No placeholder `None`, no second lock
section. A stale begin can never publish over a newer one because
publication is atomic with the allocation that produced the
generation.

LOCK ORDER (documented): Coordinator lock -> Service authority lock.
Audited: the Service never calls back into the coordinator — no
inverse path exists, no deadlock. No provider/network calls and no
executor waits under either lock.

## FIX-C — manual / reset cancel the physical token

Coordinator `confirm_artist_identity`, `confirm_album_identity`,
`reset_artist_identity`, `reset_album_identity` mark the in-flight
token of the affected entity CANCELLED under the coordinator lock
BEFORE the Service barrier runs. Division of responsibility:

- Service barrier = correctness (generation bump, request
  invalidation, identity persistence/deletion) — the worker can NEVER
  bypass it, cooperation is never required;
- token cancellation = lifecycle truth (the obsolete worker converges
  to CANCELLED at its next checkpoint instead of wasting MusicBrainz /
  Wikidata / Wikipedia / Commons / download work).

## FIX-D — STALE terminal convergence

`_commit_artist` / `_commit_album`: `STALE` verdicts (generation lost
authority) converge to `CANCELLED` — never reported as a functional
user error. `STORAGE_FAILED` / `MISMATCHED` / `UNKNOWN` remain
`FAILED`.

## Test seal

`tests/test_m6_9_backend_r1_3_1_atomicity_seal.py` — 9 deterministic
tests (threading.Event only, 2 real threads, ZERO sleeps), each with a
"WHY THIS FAILED ON R1.3" comment; all were verified RED against the
R1.3 behavior before the fixes:

- P0: artist A->B while album resolution blocked -> SUPERSEDED, zero
  Album identity writes, zero pending requests
- P0: artist reset while album resolution blocked -> same
- control: artist unchanged -> identity persists, request registers,
  dependency_id == A, delivery commits exactly once
- P1: two concurrent begins same key, broken interleaving forced via a
  gated service -> coordinator token == Service current generation;
  generations distinct; max generation stays current
- P1: stale begin cannot publish over newer; public cancel retires
  exactly the current generation; the loser can never retire the
  current authority
- FIX-C: manual confirm / reset (artist) and manual confirm (album)
  cancel the token immediately; worker terminal CANCELLED, zero writes
- FIX-D: STALE delivery converges to CANCELLED, never FAILED

The R1.3 matrix (`tests/test_m6_9_backend_r1_3_final_authority.py`,
22 tests) stays green unchanged — I/J/K/L/M (old failure vs new
request, cancel_all snapshot, shutdown admission, double-delivery
exact-once, MANUAL never downgraded) are re-proven by it.

## Validation (real numbers)

- focused seal: 9 passed
- all M6.9 suites: 596 passed
- audio regressions of the frozen main (MPD, GStreamer, playback,
  audio engine, M11.3B composition): 431 passed, 2 skipped — no
  M11.3D-R2 rollback (`git diff 9677734 -- audio_engines
  playback_service.py audio_engine_service.py` is EMPTY)
- full suite (CI environment): 2427 passed, 2 skipped, 13 warnings (no
  new warnings). NOTE: on this developer machine two PRE-EXISTING
  environmental failures appear (verified identical on the frozen main
  `9677734` in isolation): `test_registry_has_three_canonical_engines`
  (assumes MPD not activable; `/usr/bin/mpd` is installed here) and
  `test_mpd_real_runtime::test_real_private_runtime_smoke` (launches a
  real MPD daemon whose generated config fails on this host). Neither is
  touched by this WP — the audio diff vs main is empty.
- `ruff check src tests`: PASS; `ruff format --check src tests`: PASS
- `python -m build`: PASS
- exact-head CI: Lint PASS / Test PASS / Build PASS

## Scope

Productive changes ONLY in `src/michi/application/enrichment_service.py`
and `src/michi/application/enrichment_coordinator.py` (plus tests and
this doc). No canonical metadata, no presentation/QML, no audio, no
providers, no HTTP/asset policy.

## Frozen status

M6.9 BACKEND — DONE / TESTED / FROZEN (P0 = 0, P1 = 0).
M6.9 TOTAL — BACKEND FROZEN / PRESENTATION NEXT AUTHORIZED WP.
