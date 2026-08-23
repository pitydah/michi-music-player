# M6.9A-R3.2.1 — Final Defensive Input + Integration Seal

Status: implemented. Scope: the closing defensive/input corrective seal
on the M6.9A enrichment foundation. NO network providers, NO tag
extraction, NO presentation, NO bootstrap wiring.

## 1. Integration base

`ad7b13c` — M11.3C-R6.1 (DONE / TESTED / DEFINITIVELY FROZEN). The
R3.2.1 branch is reconstructed from this exact main; the R3.2 source
branch (`d64dc6e`, base a02412c) is preserved as historical evidence.

## 2. R3.2 replay purity

The 17 R3.2 enrichment commits (R1 transfer + R2 + R3 + R3.1 + R3.2)
were verified per-commit and cherry-picked in original order onto
ad7b13c. Post-replay diff: audio 0, `application/ports.py` 0 (the
M11.3C-R6.1 version with AudioLoadError semantics is inherited), metadata
canonical 0, bootstrap 0, presentation 0, pyproject 0.

## 3. Release edition invalid-candidate policy (P1-01)

`resolve_release_hint_for_group` is now defensive:

- The resolved-group and hint arguments are programmer/domain-contract
  input: invalid (non-str or blank) values raise ValueError — never
  reinterpreted as remote conflict evidence.
- A MATCHING release candidate whose `release_group_id` is not a
  non-blank str is contradictory external evidence: the verdict is
  IDENTITY_CONFLICT with `release_id ""` — never silently discarded
  (which could let another candidate win), never an IndexError on an
  empty deduped group list. Validation is scoped to candidates matching
  the requested release id (unrelated invalid candidates are ignored).

## 4. Persistent identity runtime type contract (P1-02)

`ArtistExternalIdentity` / `AlbumExternalIdentity.__post_init__`
runtime-validate EVERY string field BEFORE any string method or
attribute access: local keys, external ids, release ids, resolved_at,
status (IdentityStatus), match_method (MatchMethod). Wrong runtime
types raise ValueError — never AttributeError/TypeError.

Durable external identity must ALREADY be canonical: edge whitespace
around external ids / release groups / release ids is REJECTED (never
silently stripped and persisted). Hints remain normalization-tolerant
(`dedupe_identity_ids` strips) — evidence normalization and durable
persistence are different boundaries.

## 5. resolved_at contract (P1-03)

`resolved_at` must be `str` (empty allowed as unknown). No datetime
parsing, no persistence-format change. V2 semantic migration validation
now objectively enforces it: a V2 row whose resolved_at is not a str
fails the migration with ROLLBACK (schema version stays 2, the source
row is preserved).

## 6. V2 manually_confirmed historical-field policy (P2-01)

The legacy boolean is validated as a historical INTEGER flag: exactly
0 or 1 (bool excluded). 2 / -1 / text fail the whole migration with
ROLLBACK. It has ZERO current authority — MatchMethod remains the
authority — and it is dropped in V3. No consistency between
manually_confirmed and match_method is enforced or invented.

## 7. Album knowledge-preservation/invalidation proof (P1-04)

Explicit storage-backed tests: AUTO same RG preserves knowledge; AUTO
changed RG deletes it; EMBEDDED same edition preserves; EMBEDDED
changed edition deletes; late results after changed RG/edition are
STALE; the same-service ledger invalidation path is proven (the
request is registered and invalidated in ONE ledger). The existing
second-service test remains as the durable-identity defense proof.

## 8. Transactional fresh DB initialization (P2-02)

Brand-new enrichment.db initialization is now ONE explicit transaction:
tables + version row + `_validate_current_schema` before COMMIT. An
injected validation failure rolls back — zero partial schema committed
— and a retry after the failure succeeds canonically.

## 9. Metadata firewall

TrackMetadata / TrackRef / ArtistRef / AlbumRef / GenreRef / ComposerRef /
MusicModel / MetadataExtractorPort / InfrastructureMetadataExtractor /
LibraryIndexEntry / library_index / filesystem scanner: unchanged
(blob-verified + diff-verified).

## 10. Audio firewall

M11.3C-R6.1 inherited unchanged: GStreamer blob equals the integration
base blob; application/ports.py (with the R6.1 AudioLoadError semantics)
equals the base blob; PlaybackService / QueueService / Coordinator /
bootstrap unchanged (blob-verified).

## 11. Schema remains V3

`CURRENT_ENRICHMENT_SCHEMA == 3`. No new tables/columns, no V4.

## 12. No network / M6.9B not started

ZERO HTTP code, ZERO new dependencies (pyproject diff zero), no
MusicBrainz / Wikidata / Wikipedia / Wikimedia / Cover Art Archive.

## 13. Validation evidence

`tests/test_m6_9a_r3_2_1_defensive_integration.py` (49 tests, groups
A–F) + the complete R1/R2/R3/R3.1/R3.2 suite. Exact counts recorded in
the WP report.

## 14. Final freeze verdict

M6.9A: DONE / TESTED / FROZEN — pending human audit. Next authorized
work package: M6.9B (EXTERNAL PROVIDER FOUNDATION), not started.
