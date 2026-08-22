# M6.9A-R3 — Final Enrichment Foundation Seal

Status: implemented. Scope: the final foundation-hardening pass before
real external providers are authorized. NO network providers, NO tag
extraction, NO presentation, NO bootstrap wiring.

## Clean reconstruction on current main

The R2 branch (clean base `fd21c40`) was NOT merged — main had advanced
through the definitive M11.3C terminal cleanup (`5e85726`). The EIGHT
pure R1/R2 enrichment commits were cherry-picked in original order onto
the audited current main into `feat/m6-9a-r3-foundation-final-seal`:

- `90b649d` separate artist and album identity evidence [R1]
- `4c2ae32` persist external identity authority [R1]
- `4bf3d9a` harden correlation assets and provenance [R1]
- `57b944a` seal r1 identity semantics and document hardening [R1]
- `ebcd06f` converge album identity and request authority [R2]
- `515c368` make identity persistence truthful [R2]
- `1ee7857` migrate knowledge and harden asset transactions [R2]
- `9a8b611` seal r2 convergence contracts and document [R2]

Post-transfer purity gates: audio diff 0, M11 diff 0, canonical metadata
diff 0, bootstrap diff 0, presentation diff 0. The definitive M11.3C
GStreamer baseline is inherited from main.

## Album no-artist gate (R3)

Automatic album resolution now REQUIRES artist compatibility evidence:

- title gate (required, normalized);
- ARTIST gate: resolved artist external id must appear in candidate
  artist credits, OR the local album-artist name must match a candidate
  credit name;
- WITHOUT any artist evidence, automatic resolution is FORBIDDEN — even
  a single unique title match stays AMBIGUOUS (a search engine returning
  one result is not identity proof). Year never supplies identity;
- an explicit release-group hint remains a direct identity assertion and
  may bypass the search gate (existing conflict semantics).

## Release edition corroboration (R3)

A release id hint is NEVER accepted on its own:

- CASE A: no edition candidates -> `release_id` stays "" (group may
  resolve);
- CASE B: a matching edition candidate inside the resolved group ->
  assigned;
- CASE C: a matching edition candidate provably in a DIFFERENT group ->
  IDENTITY_CONFLICT (contradictions are never silently dropped);
- CASE D: candidates exist but none matches -> not assigned.

## Identity storage truth (R3)

- Identity READS raise `EnrichmentStorageError` on storage failure —
  None means "no identity exists", never "storage is broken". Resolution
  workflows fail closed: a read failure aborts the request (no resolver
  call, no pending request, no identity replacement, no AUTO fallback
  over an unreadable MANUAL mapping).
- Presentation-safe helpers (`get_artist_knowledge` /
  `get_album_knowledge`) catch storage failures and degrade to None
  (logged) — presentation never crashes on storage failure.

## Knowledge storage truth (R3)

- Knowledge WRITES raise `EnrichmentStorageError` (never a silent
  best-effort fake success).
- `DeliveryVerdict.STORAGE_FAILED`: a valid delivery whose persistence
  failed returns STORAGE_FAILED — the request is terminal (a second
  delivery is UNKNOWN; no automatic resurrection). COMMITTED means the
  profile was actually persisted.
- Provider-failure handlers remain zero-write and kind-checked.

## Transactional clears (R3)

`clear_identities()` and `clear_knowledge()` execute both table DELETEs
inside one BEGIN/COMMIT/ROLLBACK transaction — a failure can never leave
a partially cleared authority. Service-level `clear_identities()` keeps
the order: invalidate ALL requests -> identity clear -> knowledge clear;
late results stay STALE.

## Schema discovery + validation (R3, non-mutating, fail-closed)

- Database state is determined BEFORE any table is created: brand-new
  empty database initializes; enrichment tables without version metadata
  are corrupt (fail); v1/v2 migrate transactionally; v3 is VALIDATED.
- Future (> current), non-numeric, negative, empty or zero version
  metadata -> `EnrichmentSchemaError` WITHOUT mutating the database
  (never rewritten, never upgraded).
- A current-version database with missing tables/columns is REJECTED —
  identity tables are user authority and are never silently recreated
  empty.
- `version()` raises `EnrichmentStorageError` on storage failure (never
  a fake 0).

## Historical provenance (R3)

V1 migration preserves truthful biography provenance: when the historical
profile carried a non-empty biography AND source, both
`provenance.provider` and `biography_provenance.provider` become that
source. Unsupported fields (source_url, license, language, attribution)
stay UNKNOWN — never invented. `generation` remains dropped;
release-level facts without a release identity remain dropped.

## Asset object integrity (R3)

An EXISTING content-addressed object is verified against its content
hash during store: a corrupted object is detected and rewritten
atomically from the validated new payload (the filename alone is never
trusted). Manifest-as-commit-point topology, relative `managed_object`
paths, checksum authority and orphan invisibility are preserved.

## Firewall preservation

TrackMetadata / TrackRef / ArtistRef / AlbumRef / GenreRef / MusicModel /
MetadataExtractorPort / InfrastructureMetadataExtractor / library_index:
unchanged. External-to-local metadata path ZERO; tag writes ZERO;
Mutagen writes from enrichment ZERO. Audio / bootstrap / presentation /
pyproject.toml diffs ZERO.

## Validation surface

- `tests/test_m6_9a_r3_foundation.py` — no-artist gate, read/write
  storage truth, STORAGE_FAILED, transactional clears (SQLite trigger
  failure injection), non-mutating schema rejection, biography
  provenance, corrupted-object repair
- plus the complete R1/R2 suite kept green or made stricter
- `tests/test_m6_9a_structural_gates.py` — R3 structural gates

## Next authorized WP

M6.9B — EXTERNAL PROVIDER FOUNDATION (MusicBrainz identity/provider
first). NOT started by R3.
