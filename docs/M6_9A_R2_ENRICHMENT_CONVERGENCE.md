# M6.9A-R2 — Enrichment Identity + Storage Convergence

Status: implemented; reconstructed cleanly on current main by M6.9A-R3.

> **M6.9A-R3 supersedes parts of this document** (no-artist album gate,
> release corroboration, truthful identity/knowledge reads+writes,
> STORAGE_FAILED, transactional clears, non-mutating schema discovery,
> biography provenance, object integrity). See
> `docs/M6_9A_R3_FINAL_FOUNDATION_SEAL.md` for the current contract.

## Clean branch reconstruction

The R1 branch (`feat/m6-9a-r1-identity-semantics-hardening`) was based on
an intermediate M11.3C audio line (merge-base `042611b`, before the audio
workstream finalized on main). It was NOT merged wholesale. The four PURE
enrichment R1 commits were cherry-picked in order onto the audited current
main (`fd21c40`):

- `2275014` fix(enrichment): separate artist and album identity evidence
- `bc742b4` feat(enrichment): persist external identity authority
- `dbad260` fix(enrichment): harden correlation assets and provenance
- `6b180c9` test(enrichment): seal r1 identity semantics and document hardening

Post-transfer gates: audio diff 0, M11 diff 0, metadata canonical diff 0,
bootstrap diff 0, presentation diff 0.

## Common-title album safety (R2 album artist gate)

`ReleaseGroupCandidate` now carries BOTH `artist_credit_external_ids` and
`artist_credit_names`. The album resolution hierarchy:

- explicit release-group hint (authoritative, corroborated);
- else TITLE gate (required, normalized);
- else ARTIST gate (strict, fail-closed):
  - resolved artist external id -> candidates must INCLUDE it in their
    credits;
  - else local album-artist NAME -> a candidate credit name must match
    (normalized);
  - candidates that cannot prove compatibility are EXCLUDED;
- duplicates remain AMBIGUOUS without any artist information;
- `first_release_year` corroborates ONLY among title+artist-verified
  same-artist duplicates (documented); ties stay AMBIGUOUS.

YEAR IS NEVER CROSS-ARTIST IDENTITY: album title + year cannot distinguish
two candidates belonging to different artists.

## Request invalidation (no stale commit after reset/clear)

- `EnrichmentRequestLedger.invalidate(entity_kind, local_entity_key)` and
  `invalidate_all()`: an invalidated request is recorded as superseded —
  its late delivery yields STALE, never COMMITTED.
- `reset_artist_identity` / `reset_album_identity`: invalidate FIRST, then
  delete identity, then delete knowledge.
- `clear_identities()` (service): invalidate ALL pending requests, clear
  the identity authority, clear active knowledge. No old request can
  repopulate anything.
- Delivery requires the CURRENT persisted identity to EXIST and match
  (defense-in-depth on top of ledger invalidation).

## Identity transitions (centralized)

`_persist_artist_identity_transition` / `_persist_album_identity_transition`
apply to AUTO, EMBEDDED_HINT and MANUAL uniformly:

- load current identity; if the external identity CHANGED (artist id;
  album (release_group_id, release_id) tuple): invalidate the pending
  request and delete the stale knowledge BEFORE persisting;
- same external id with a different MatchMethod (AUTO -> MANUAL)
  preserves knowledge;
- requests are registered only AFTER the identity persisted.

## Release-edition correlation

`EnrichmentRequest.external_variant_id`:
ARTIST: "" (artist MBID in external_entity_id); ALBUM: release MBID when
the edition is known, else "". `deliver_album_profile` validates
`profile.release_id == request.external_variant_id` exactly — release-
level knowledge can never commit against the wrong edition.

## Truthful persistence

- `EnrichmentStorageError` is the normalized failure contract;
  sqlite3.Error never crosses the boundary.
- Identity saves/deletes/clears RAISE it (authority never fails
  silently); knowledge writes stay documented best-effort cache
  semantics.
- Manual confirmation never returns a fake success; a failed identity
  save blocks request registration (no fetch authority).
- Reset invalidates the pending request BEFORE the truthful delete.

## Knowledge read authority

`get_artist_knowledge` / `get_album_knowledge` return a profile only when
the current identity exists AND the profile's external identity matches
(albums: group AND edition). Stale rows are invisible to presentation.

## Schema 3 + real historical migration

`CURRENT_ENRICHMENT_SCHEMA = 3`. Migration chain is transactional:

- v1 (M6.9A): knowledge rows carry `source` + `generation`. Migration
  TRANSFORMS them with literal historical decoders (never the current
  encoder): `source` -> `provenance.provider`, `generation` DROPPED,
  release-level facts without a release identity DROPPED (never invented);
  malformed rows are deleted deterministically (cache policy; identity
  authority and canonical library are never harmed).
- v2 (R1): identity tables with the legacy `manually_confirmed` column are
  rebuilt into the v3 shape (MANUAL authority = MatchMethod only).
- v3: current shape. Newer schemas fail closed.

The redundant `manually_confirmed` field was REMOVED from the identity
models (schema 3 stores no redundant boolean).

## Manifest-based asset storage (failure-atomic)

```
<root>/objects/<sha256>.jpg|png|webp   immutable, content-addressed
<root>/records/<asset_id>.json          manifest — the visibility COMMIT POINT
```

- The manifest swap (atomic os.replace) is the only visibility event; a
  failure at any step preserves the previous valid asset AND its
  provenance. Orphaned immutable objects are invisible and cleared by
  clear().
- `path_for` resolves through the manifest only; checksum authority:
  the managed object name must equal the content-addressed name of the
  record's checksum + MIME-derived extension (never from URLs/names).
- `EnrichmentAssetRecord.managed_object` is RELATIVE — absolute runtime
  paths are never persisted (backup/restore/data-root migration safe).
- R1 validation retained: size bound, MIME allowlist, magic bytes,
  QImageReader decode, strict asset ids.

## Firewall preservation

TrackMetadata / MetadataExtractorPort / InfrastructureMetadataExtractor /
LibraryIndexEntry / library_index schema / ArtistRef / AlbumRef /
MusicModel: unchanged. External-to-local metadata flow ZERO. Tag writes
ZERO. Audio/Presentation/bootstrap diffs ZERO. Enforced permanently by
`tests/test_m6_9a_structural_gates.py` (+ R2 gates).

## Validation surface

- `tests/test_m6_9a_r2_album_identity.py` — common-title safety,
  artist gate, permutations
- `tests/test_m6_9a_r2_request_invalidation.py` — reset/clear flight
  guards, transitions, release-edition changes, read authority
- `tests/test_m6_9a_r2_migrations.py` — literal V1/V2 fixtures, real
  data transformation, fail-closed
- `tests/test_m6_9a_r2_asset_transactions.py` — manifest commit point,
  failure injection, orphans, checksum authority
- plus the full R1 suite (domain/firewall/cross-contamination/
  persistence/assets/structural gates) kept green or made stricter

## Next authorized WP

M6.9B — EXTERNAL PROVIDER FOUNDATION (MusicBrainz first). NOT started by R2.
