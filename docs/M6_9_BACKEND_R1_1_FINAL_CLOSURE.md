# M6.9-BACKEND-R1.1 — Final Transport + Stale + Async + Lifecycle Seal

> **SUPERSEDED BY M6.9-BACKEND-R1.2 (FINAL CORRELATION SEAL).** R1.2
> closes the request-correlation and real-tag-compatibility defects
> found after R1.1. See `docs/M6_9_BACKEND_R1_2_FINAL_CLOSURE.md`.
> R1.1's transport/stale/async work remains in force.

Status: implemented. This WP closes the M6.9 library enrichment BACKEND
definitively (before presentation). NO UI/QML/EnrichmentBridge; NO
M11.3D; NO audio changes; NO canonical metadata changes; NO tag writes;
NO new providers.

## Base / sync / final

- Source branch: `feat/m6-9-backend-r1` (3628f64)
- Synced main: `9f89676` (M11.3C owner-thread seal — merged cleanly;
  audio authority = MAIN, enrichment = M6.9)
- SYNCED_BASE_HEAD: `f63ff56` (this WP's comparison baseline)
- Final HEAD: recorded in the WP report.

## Transport truth (P1-B)

`UrllibHttpTransport` normalizes failures from BOTH `opener.open(...)`
AND `response.read(...)`: TimeoutError / OSError /
http.client.IncompleteRead / HTTPException → `EnrichmentTransportError`
(typed, retryable, response always closed). Invalid JSON, oversized
bodies, unsafe redirects and validation failures are NOT transport
errors.

## One canonical transient policy (P1-C)

`is_transient_provider_failure(exc)` is THE single semantic rule used
by: the bounded retry policy, the stale-cache fallback eligibility and
the OFFLINE/FAILED operation classification.

- Transient: EnrichmentTransportError; HTTP 429/502/503/504.
- NOT transient: 400/401/403/404/418/500/501/505, invalid JSON,
  validation failures, unsafe URLs, provider contract violations.

## Async failure convergence (P1-A)

The exception boundary includes IDENTITY RESOLUTION: a worker Future
can never die silently. Transport failures during identity →
OFFLINE; malformed payloads / non-transient HTTP → FAILED; unexpected
programming errors are logged and FAILED. Pending requests are
invalidated on every terminal failure — no late commit.

## Linearizable cancellation vs delivery (P1-F)

The final commit is serialized against cancel/supersede/shutdown under
the coordinator lock (network phases never hold it). At the gate:
coordinator not shutting down AND token not cancelled AND token still
current — else the request is invalidated and the operation reports
CANCELLED with zero commit. If the gate wins first, the commit happens
exactly once.

## Controlled async search (P1-G)

`search_artist_candidates_async` / `search_album_candidates_async`
return True (accepted) / False (coordinator shutting down — never a
RuntimeError). Provider failures surface via `on_error` — never as an
empty success tuple.

## Stale knowledge end-to-end truthful (P1-D)

Stale cache is KNOWLEDGE-only. Identity resolution stays fresh-only
(stale candidate entries can never remap identity). Knowledge falls
back to stale ONLY after a canonical transient failure (never after
404 or malformed JSON) and marks `is_stale` + truthful `retrieved_at`
in every layer: MusicBrainz links, Wikidata claims, Wikipedia
biography, Commons image metadata and CAA covers. Any stale knowledge
in the final profile makes the operation state PARTIAL — never READY.

## Wikidata verified sitelink → Wikipedia (P1-E)

The biography fetch uses the FINAL projected page/language: verified
MusicBrainz Wikipedia relation first, else the verified Wikidata
sitelink (requested language → enwiki). Never an artist-name search.

## Real Mutagen hint extraction (§8)

`MutagenIdentityHintExtractor` covers the real tag families (mutagen
1.47 semantics): Vorbis/FLAC/Ogg/Opus comment keys, ID3 TXXX frames
with MusicBrainz descriptions + UFID (owner `http://musicbrainz.org`)
for the recording id, MP4 freeform atoms
(`----:com.apple.iTunes:MusicBrainz ...`, bytes values), ASF/WMA
`MusicBrainz/...` keys. Every role keeps ALL distinct observations —
never first-wins. Unreadable containers yield empty hints. (The ASF
container itself requires a real WMA fixture — the production key
mapping is tested at the mapping seam; documented limitation.)

## Bounded cache maintenance (§9)

`remove_expired(max_entries_per_run=1000)` performs deterministic
per-shard traversal that EXAMINES at most the cap without
materializing the tree. Explicit maintenance only; never at startup.

## Firewalls

metadata_extractor / application/ports / domain/library /
infrastructure/library_index: zero R1.1 diff (blob-compared against
SYNCED_BASE_HEAD). Audio R1.1-owned diff: zero. Presentation: zero.
No tag writes. No startup/scan network. Provider set unchanged
(MusicBrainz, Wikidata, Wikipedia, Wikimedia Commons, Cover Art
Archive).

## Closure status

M6.9A FOUNDATION: DONE / TESTED / FROZEN
M6.9 BACKEND: DONE / TESTED / FROZEN
M6.9 PRESENTATION: NOT IMPLEMENTED
M6.9 TOTAL: IN PROGRESS
NEXT AUTHORIZED WP: M6.9 PRESENTATION INTEGRATION
