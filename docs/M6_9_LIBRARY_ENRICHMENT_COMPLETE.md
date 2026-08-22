# M6.9 — Library Enrichment (Implementation Record)

Status of this branch: **BACKEND COMPLETE — PRESENTATION BLOCKED BY UI
INTEGRATION** (see "Presentation" below). This document records the
implemented runtime truth.

## Architecture

Five bounded contexts preserved (permanent firewall):

```
LOCAL AUDIO FILES → CANONICAL LOCAL LIBRARY → LOCAL IDENTITY EVIDENCE
    → RESOLVED EXTERNAL IDENTITY → EXTERNAL KNOWLEDGE
    → (future) PRESENTATION PROJECTION
```

Never reversed: external knowledge can never write canonical metadata,
library_index, or audio tags.

## Implemented

- M6.9A foundation (identity authority, fail-closed gates, V3 schema,
  transactional migrations, manifest-based assets) — replayed cleanly
  onto M11.3C-R6.2 main (`05a08c9`).
- **Transport**: `UrllibHttpTransport` — HTTPS-only, provider host
  allowlist (validated pre-request and post-redirect), 8 MiB body bound,
  10s timeout, Michi User-Agent; `MusicBrainzRateLimiter` (≤1 req/s,
  process-wide, injectable clock).
- **Provider cache**: `FilesystemProviderCache` — sha256(provider|url)
  keys, atomic writes, fresh/stale reads, 90-day bounded maintenance,
  separate from enrichment.db.
- **Identity**: `MusicBrainzIdentityResolver` (strict JSON validation,
  deterministic candidate order, caps 5/50, bounded retries 429/502/503/504).
- **Hints**: `MutagenIdentityHintExtractor` — read-only, separate from
  the canonical MetadataExtractor; `LibraryEnrichmentEvidenceBuilder`
  projects read-only canonical data + hints into typed evidence.
- **Knowledge**: MusicBrainz structured facts + verified URL relations;
  Wikidata claims (verified QID only); Wikipedia bounded biography
  (verified sitelink only); Wikimedia Commons image metadata; Cover Art
  Archive external cover fallback.
- **Orchestration**: `EnrichmentCoordinator` (workflow) +
  `ThreadPoolEnrichmentExecutor` (off-UI-thread, 2 workers) +
  ephemeral operation states + manual resolution views + refresh/clear/
  reset intents + cancel/shutdown.
- **Composition**: bootstrap wires everything LAZILY — zero network at
  startup; gated by the new `Online Library Enrichment` setting
  (DEFAULT OFF).

## Privacy

Only provider query terms and verified external ids are transmitted —
never filesystem paths, history, queue, ratings or device identity.
Structural gates: canonical scan surface never imports enrichment
network modules.

## Presentation

**BLOCKED BY UI INTEGRATION.** The premium UI branch
(`antigravity/m9-r2-ui-ux-refinement`) is not part of the frozen main
base. Per the M6.9 contract, presentation requires a clean base
containing: current frozen main + complete M6.9 backend + approved
premium UI changes. No such base exists yet → the presentation phase
was NOT started (EnrichmentBridge / QML / manual-resolution UI /
attribution UI are deferred). M6.9 must NOT be reported as 100% until
that base exists and the presentation gates pass.

## Validation

All M6.9A/M6.9B/M6.9C/M6.9D/M6.9E/M6.9F backend suites + full
repository suite + ruff + build + architecture + QML smoke pass on the
branch head. Exact counts in the WP report.

## Known limitations (documented truth)

- No live-network tests in CI (fixtures only); optional smoke tests can
  be added in a later WP.
- `album_artist_ids` matching is not implemented (explicitly deferred).
- Provider-specific UUID syntax validation belongs to provider boundary
  (deferred).
