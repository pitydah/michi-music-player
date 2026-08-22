# M6.9-BACKEND-R1 — Provider Truth + Identity Hints + Async Cancellation + Offline Convergence

Status: implemented. This WP closes the backend P1/P2 list of M6.9
BEFORE any presentation work. NO UI/QML/EnrichmentBridge; NO M11.3D;
NO audio changes; NO canonical metadata changes; NO tag writes; NO new
identity sources; NO new providers.

## Base / final

- Base before sync: `d79a0e9` (feat/m6-9-complete-enrichment, on 05a08c9)
- Synced main: `94fc2d6` (M11.3C-R6.4 — merged into the branch;
  audio authority = MAIN, enrichment = M6.9; zero conflicts)
- Final HEAD: recorded in the WP report.

## Identity hint model (P1-01)

`ExternalIdentityHints` carries TUPLES for every direct role:
`musicbrainz_artist_ids / album_artist_ids / release_group_ids /
release_ids / recording_ids / release_track_ids`. No scalar parallel
authority. Extractor: all observations per role, strip, drop blanks,
dedupe identical, preserve distinct — never first-wins. Aggregation
across tracks is a UNION. Typed projections keep roles separate.

## Offline embedded identity semantics (P1-12)

Explicit hints resolve WITHOUT network: single artist hint → EMBEDDED_HINT
(no search call); conflicting hints → IDENTITY_CONFLICT (zero network);
album RG hint → RG persists without a group search; release edition
stays `""` without corroboration (offline edition lookup never invents
identity); release-only hint + offline → provider failure, no invented
RG.

## Retry policy (P1-05/P1-06)

`ProviderRequestExecutor` — ONE policy: GET only; max 3 attempts;
retries `EnrichmentTransportError` + HTTP 429/502/503/504; Retry-After
(0<x<=10) else 1s/2s backoff; never retries 400/401/403/404, malformed
JSON or validation failures. MusicBrainz: cache hits consume no
rate-limit slot; every physical attempt (retries included) waits.

## Stale policy (P1-07)

Stale cache is KNOWLEDGE-only. Identity resolution never reads stale
entries. Knowledge falls back to stale only on transient network
failure, marks `KnowledgeProvenance.is_stale=True` + truthful
`retrieved_at`, and the coordinator reports PARTIAL — never READY.

## Cancellation model (P1-02)

Per-operation `EnrichmentOperationToken`; supersession cancels the
previous operation; `cancel_all()` cancels ACTIVE operations only
(reusable); `shutdown()` is terminal (freeze, cancel, invalidate
pending requests via service `cancel_*_request` APIs, join executor —
the coordinator owns the executor lifecycle). Gates run before
resolution, after resolution, around remote phases, before assets and
immediately before delivery: cancelled operations never commit.

## Async search boundary (P1-03)

`search_artist_candidates_async` / `search_album_candidates_async` run
the resolver on the enrichment executor — the caller thread is never
blocked. Safe typed candidate DTOs; never raw JSON; provider score is
never authority.

## False-uniqueness gate (P1-04)

A support-evidence (album browse) failure during candidate expansion
ABORTS the whole artist resolution — a failed candidate can never
disappear and fake uniqueness. Only candidate-local malformed fields
skip a single candidate.

## Wikidata semantics (P1-08/P1-09)

Deterministic claim selection: deprecated discarded; preferred rank
first, then normal; deduplicated distinct values only — contradictions
stay unresolved; permutation-independent. Country is a QID
(`country_qid`), labels never invented. Verified sitelinks provide the
Wikipedia fallback (requested language → enwiki); no name search ever.

## Provenance ownership (P1-10)

MusicBrainz facts stay MB-attributed (begin/end); Wikidata facts carry
`wikidata_provenance` with `wikidata_begin_year` /
`wikidata_end_year` / country QID / official website / Commons image;
biographies carry Wikipedia provenance; every provider payload
populates truthful `retrieved_at` (UTC ISO-8601, injectable clock) and
`is_stale`.

## External artwork MIME (P1-11)

`mime_type=""` means UNKNOWN — the sniffed canonical MIME decides; a
non-empty declared MIME must match exactly or the asset is rejected;
completed records always carry the validated canonical MIME. The
coordinator derives the declared MIME from Content-Type only when
supported (never hardcoded JPEG). JPEG/PNG/WebP accepted; failed
replacements preserve the previous valid asset.

## Smaller R1 items

- `EnrichmentOperationState.DISABLED` — a user policy decision is
  never reported as OFFLINE (P2-01).
- Optional sources treat 404 as EMPTY optional results — PARTIAL,
  never FAILED (P2-02).
- Provider cache lives under the canonical Qt CacheLocation authority
  resolved in bootstrap (P2-03).
- Coordinator owns enrichment shutdown; the container never closes the
  executor directly (P2-04).
- Cache maintenance is bounded (`max_entries_per_run=1000`,
  deterministic traversal, never automatic at startup) (P2-05).

## Protected files

`metadata_extractor.py`, `application/ports.py`, `domain/library.py`,
`infrastructure/library_index.py`: zero R1 changes (blob-compared
against the synced base). Audio surface diff attributable to R1: ZERO
(main's own audio changes inherited through the merge).

## Validation

Full suite, ruff, format, build, architecture gates, QML smoke and
exact-head remote CI — exact counts in the WP report.

## Known limitations

Presentation remains NOT IMPLEMENTED (blocked by UI integration —
separate work package). Network smoke tests remain optional/deferred.
Provider-specific UUID syntax validation and album_artist_ids matching
remain deferred.
