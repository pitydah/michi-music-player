# M6.9A-R1 — Identity Semantics Hardening

Status: implemented; reconstructed cleanly on current main by M6.9A-R2.

> **M6.9A-R2 supersedes parts of this document** (album artist gate,
> request invalidation, identity transitions, truthful persistence,
> schema 3, manifest-based assets). See
> `docs/M6_9A_R2_ENRICHMENT_CONVERGENCE.md` for the current contract.

## Corrections applied

1. **Track artist != album artist (roles separated)** — the raw
   `ExternalIdentityHints` carrier remains, but matching NEVER merges
   artist roles. Typed carriers `ArtistIdentityHints { artist_ids }`
   (track-artist role) and `AlbumIdentityHints { release_group_ids,
   release_ids, album_artist_ids }` project the raw file hints per role.
   `combined_artist_ids()` is DELETED. A track artist MBID A and an
   album artist MBID B (e.g. Freddie Mercury / Various Artists) are
   never an identity conflict.
2. **Entity-specific evidence** — generic `IdentityEvidence` is gone.
   `ArtistIdentityEvidence { local_artist_key, local_artist_name,
   known_albums, identity_hints }` and `AlbumIdentityEvidence {
   local_album_key, local_album_title, local_album_artist_key,
   local_album_artist_name, resolved_artist_external_id, local_year,
   identity_hints }` are separate, non-interchangeable types.
3. **Paired album evidence** — `LocalAlbumEvidence { title, year }` keeps
   title/year association per album. Independent title/year bags can no
   longer create false cross-matches (Album A-1978 / Album B-1990 stay
   paired).
4. **Year-only matching forbidden** — artist AND album/release-group
   resolution can never be created by year coincidence alone. Years only
   CORROBORATE a title match.
5. **Structural matching, not point soup** — eligibility gates run
   before any comparison: candidate canonical name must match the local
   artist name; album candidate title must match the local album title.
   Then required evidence (at least one associated album title match for
   artists), then corroborating years, then deterministic uniqueness.
   Ties stay AMBIGUOUS; candidate order never changes a verdict.
6. **Name is a gate, not evidence** — NAME + ALBUM TITLE (+ compatible
   year) can resolve; NAME alone never does; YEAR alone never does;
   popularity/candidate order are never identity evidence.
7. **Artist compatibility for albums** — when the artist identity is
   already resolved, release-group candidates whose known artist credits
   exclude that external id are ineligible.
8. **Release Group != Release preserved** — the specific release edition
   is NEVER inferred from title/year; `release_id` requires an explicit
   release id hint corroborated against the resolved group. Release-level
   facts (`release_year`, `label`) enforce a `release_id` invariant.

## Persistent identity authority (identity != knowledge)

- `ArtistExternalIdentity` / `AlbumExternalIdentity` records persist in
  enrichment.db tables `artist_identity` / `album_identity` — separate
  from the knowledge tables.
- `MatchMethod`: EMBEDDED_HINT / AUTO / MANUAL. MANUAL is authoritative:
  it overrides automatic re-resolution and is never fabricated as a hint.
- `IdentityStatus`: RESOLVED / AMBIGUOUS / IDENTITY_CONFLICT / NOT_FOUND;
  a candidate is never persisted as resolved when the gate said AMBIGUOUS.
- Service manual operations (`confirm_artist_identity`,
  `reset_artist_identity`, `confirm_album_identity`,
  `reset_album_identity`) touch ONLY the identity authority — never local
  tags.
- `clear_knowledge()` preserves identity mappings; `reset_*_identity`
  removes the mapping AND its associated knowledge (one safe contract:
  nothing displays under an unresolved identity). An identity CHANGE
  invalidates the old knowledge profile (no stale biography under a new
  MBID).
- `IdentityRepositoryPort` is separate from `KnowledgeRepositoryPort`; a
  SINGLE infrastructure class (`SqliteEnrichmentRepository`) owns the
  enrichment.db schema (no competing migration owners).

## Schema migration

Enrichment schema 1 -> 2, transactional, preserving existing knowledge
profiles. Fail-closed on newer schemas. The generic `clear()` of M6.9A
is replaced by explicit `clear_knowledge()` / `clear_identities()`.

## Correlation hardening

- Immutable request correlation preserved (request_id / entity_kind /
  local_entity_key / external_entity_id / generation).
- `generation` REMOVED from persisted knowledge profiles — async
  lifecycle state never lives in cached data.
- Failure deliveries are kind-checked: `deliver_artist_failure` on an
  album request returns MISMATCHED and never consumes it (and vice
  versa).
- Deliveries are additionally guarded by the CURRENT identity authority:
  a result whose external id no longer matches the persisted identity is
  STALE.

## Provenance (before any network provider)

- `KnowledgeProvenance` (provider, external_entity_id, source_url,
  retrieved_at, language, license, license_url, attribution) replaces the
  global `source` string; biography carries its own optional provenance
  (identity may come from MusicBrainz while biography comes from
  Wikipedia).
- `EnrichmentAssetRecord` gives external assets structured provenance +
  validation metadata (checksum, dimensions, local_path).

## Asset store hardening (before any real download)

`FilesystemEnrichmentAssetStore` enforces: one documented size bound
(`MAX_EXTERNAL_IMAGE_BYTES` = 10 MiB), image MIME allowlist
(jpeg/png/webp), magic-byte content verification, decodable-image
validation via QImageReader (no Pillow; unsupported formats fail closed),
strict asset-id validation (remote titles never become paths), sha256
checksum, atomic temp+`os.replace` writes, provenance sidecars, no
partial visible assets. Local artwork cache and audio files are never
touched.

## Firewall preserved

TrackMetadata / MetadataExtractorPort / InfrastructureMetadataExtractor /
LibraryIndexEntry / library_index schema / ArtistRef / AlbumRef /
MusicModel remain byte-for-byte unchanged. External knowledge -> local
metadata path: ZERO. Tag writes: ZERO. Canonical library writes during
enrichment: ZERO. Enforced permanently by
`tests/test_m6_9a_structural_gates.py`.

## Validation surface

- `tests/test_m6_9a_enrichment_domain.py` — pure gates, role separation,
  paired evidence, permutations, codecs
- `tests/test_m6_9a_r1_identity_semantics.py` — year-only forbidden,
  homonym safety, correlation guards, release invariants
- `tests/test_m6_9a_r1_persistence.py` — identity authority, schema
  migration 1->2, clear/reset semantics, manual override, kind guards
- `tests/test_m6_9a_r1_assets.py` — asset validation, atomicity,
  checksum, provenance
- `tests/test_m6_9a_enrichment_firewall.py`,
  `tests/test_m6_9a_cross_contamination.py` — concurrency + the 15
  cross-contamination gates
- `tests/test_m6_9a_structural_gates.py` — permanent structural gates
  (R1 role-separation / identity-vs-knowledge / no-request-state gates
  added)

## Next authorized WP

M6.9B — EXTERNAL PROVIDER FOUNDATION (MusicBrainz first). NOT started by
R1.
