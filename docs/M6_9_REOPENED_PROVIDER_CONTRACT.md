# M6.9 REOPENED — Provider Contract + Library Enrichment Product Completion

Status: **M6.9 — REOPENED** (this document supersedes the stale claims of
`M6_9_LIBRARY_ENRICHMENT_COMPLETE.md` where they conflict).

Reason: Provider Contract + Library Enrichment Product Completion.

## 1. MusicBrainz release-group browse contract (P0-A, FIXED)

`_known_albums_for()` no longer sends `type=release-group` (the endpoint
entity is NOT a valid value of the `type` filter). The browse is:

    GET https://musicbrainz.org/ws/2/release-group/?artist=<MBID>&fmt=json&limit=100[&offset=N]

Bounded pagination: `RELEASE_GROUP_PAGE_SIZE = 100`,
`MAX_RELEASE_GROUP_PAGES = 3`, `MAX_RELEASE_GROUPS_TOTAL = 300`. A short
page stops immediately; results are deduplicated by title.

Regression gate: `test_browse_never_uses_type_release_group` — the
parameter can never reappear.

## 2. Contract tests instead of prefix fakes (P0-B, FIXED)

`tests/test_m6_9_musicbrainz_contract.py` parses every generated URL with
`urllib.parse` (scheme/hostname/path/query keys/values), asserting the
real MusicBrainz contract for: artist search, release-group search,
release-group browse, release lookup (inc=release-groups), parameter
order irrelevance, and Lucene escaping (`AC/DC`, `P!nk`, `+44`, `!!!`,
`M/A/R/R/S`, `name:part`, `artist (UK)`, etc. — §25).

## 3. Live provider contract suite (P0-C, FIXED — opt-in)

`tests/integration/test_enrichment_live_contracts.py`:

    MICHI_RUN_LIVE_NETWORK_TESTS=1 pytest -m live_network -v

Skips (never requests) when the env var is absent. Distinguishes
CONTRACT_FAILURE (reproducible 4xx on Michi-generated URLs) from
temporary provider conditions (429/5xx/network). Ran successfully
against real services: 9 passed / 1 skipped (rate-limit).

## 4. LibraryEnrichmentJob (P0-D, FIXED)

`src/michi/application/library_enrichment_job.py` — application-layer
bulk product operation:

- States: IDLE / PREPARING / RUNNING / CANCELLING / CANCELLED /
  COMPLETED / PARTIAL / FAILED.
- Bounded scheduling: max 2 workers, max 8 in-flight; the admission loop
  admits the next entity only when a slot frees (NEVER one Future per
  library entity). 10k scheduling seal in `test_m6_9_enrichment_job.py`.
- Truthful progress (committed outcomes only): total/processed entities,
  matched/ambiguous/not_found/failed, currentEntity.
- Cache-first: persisted knowledge → skipped (counted as cached); a
  repeat run does zero duplicated fresh work.
- Artists first, then albums (artist identity evidence reused — no
  repeated artist searches per album).
- Cancellation integrates with the coordinator (`cancel_all`); stale
  commits after cancel are never counted. Shutdown-safe.
- `LibraryEnrichmentProjection` stays read-only/cache-only/network-free;
  the job invalidates it with coalescing (batch of 16).

## 5. Enrich Library UX

LibraryToolbar (premium) exposes **Enrich Library** (visible only with
Online Library Enrichment ON; running state shows `Enriching
Library… N / M` and toggles to Cancel). Exactly one intent per click.

## 6. Enrichment doctor

    python -m michi.tools.enrichment_doctor

Checks MusicBrainz / Wikidata / Wikipedia / Wikimedia Commons / Cover
Art Archive without touching the Library. Exit 0 = all OK; 1 =
contract/provider failure; 2 = network unavailable. Result (2026-09):
**5/5 provider contracts reachable**.

## 7. Privacy gates (unchanged + job)

startup/scan/search/lists = zero enrichment network, with the two
explicit exceptions documented in the COMPLETE doc: Artist Gallery
bounded portrait prefetch (Online ON only) and Enrich Library (explicit
user intent). Scan completion NEVER starts enrichment.

## 8. Status

- P0-A..D: FIXED.
- M6.9 may return to **COMPLETE** only after: production MusicBrainz
  contract fixed (done), deterministic contract tests (done), live
  provider contract suite (done, ran green), LibraryEnrichmentJob
  productive (done), Enrich Library UI (done), cancellation (done),
  bounded scheduling (done), privacy gates (done), diagnostics (doctor,
  done), docs/runtime convergence (this document), P0 = 0, P1 crítico =
  0.
