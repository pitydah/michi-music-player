# M6.9A-R3.1 — Final Identity Invariants + External Asset Safety Seal

Status: implemented. Scope: the LAST corrective pass on the M6.9A
enrichment foundation. NO network providers, NO tag extraction, NO
presentation, NO bootstrap wiring. Child branch of
`feat/m6-9a-r3-foundation-final-seal`.

## Persistent identity invariants

`ArtistExternalIdentity` / `AlbumExternalIdentity` enforce via
`__post_init__`:

- non-empty local key and external id (album: non-empty release group;
  `release_id` MAY be empty — Release Group is the minimum album
  identity);
- `status == IdentityStatus.RESOLVED` ONLY — AMBIGUOUS /
  IDENTITY_CONFLICT / NOT_FOUND are resolution OUTCOMES, never
  persistent records;
- valid `MatchMethod`.

Impossible constructions raise ValueError. The persistent identity
tables contain RESOLVED mappings only.

## Duplicate hint normalization

Same-role hints are deduplicated BEFORE cardinality tests
(`dedupe_identity_ids`): ("A", "A") is ONE identity, never a conflict;
("A", "B") and ("A", "A", "B") are IDENTITY_CONFLICT. Roles are never
merged: track artist ids and album artist ids dedupe WITHIN their role
only.

## Match authority precedence (explicit)

MANUAL > EMBEDDED_HINT > AUTO

- MANUAL: sticky user authority — short-circuits resolution entirely;
  survives ambiguous/conflicting/no-match automatic evidence; only
  reset/confirm may change it.
- EMBEDDED_HINT: direct local identity evidence — a persisted embedded
  mapping is reused when the current request carries NO new explicit
  same-role hint (weaker AUTO evidence can never replace it). New
  explicit embedded hints decide via the normal gates: same -> retained;
  different -> direct transition (old knowledge invalidated); multiple
  distinct -> IDENTITY_CONFLICT + revocation of the old non-manual
  mapping.
- AUTO: inference from structural evidence — REVOCABLE. A fresh
  resolution that becomes AMBIGUOUS / IDENTITY_CONFLICT / NO_MATCH
  revokes the old AUTO identity: ledger invalidation first, then durable
  identity deletion, then knowledge deletion. No new request. A late
  old result is STALE.

Albums follow the same policy (EMBEDDED_HINT = persisted release-group
hint authority).

## Identity corruption truth

Malformed persistent identity rows (invalid status/match method enum,
empty required ids, impossible non-RESOLVED persistent status) raise
`EnrichmentStorageError` — NEVER None ("no identity exists"), never a
partial bulk result, never an AUTO fallback. None means absence ONLY.

## Migration shape hardening (schema stays 3)

- V1: identity tables must be ABSENT — any present table is a corrupt V1
  and raises without mutation.
- V2: BOTH identity tables must exist in the EXACT V2 column shape
  (including the legacy `manually_confirmed`). Partial/wrong-shape V2 is
  rejected transactionally.
- V3: identity table column sets are validated EXACTLY — a V3 database
  still carrying the legacy boolean is a mislabeled V2 and rejected
  (no silent acceptance).
- `version()` is truthful: missing/malformed/zero/negative version rows
  raise `EnrichmentSchemaError`; operational SQLite failures raise
  `EnrichmentStorageError`; never a fake 0.

## External image decode-bomb protection

Beyond the existing byte bound, external artwork now enforces:

- `MAX_EXTERNAL_IMAGE_WIDTH = 8192`
- `MAX_EXTERNAL_IMAGE_HEIGHT = 8192`
- `MAX_EXTERNAL_IMAGE_PIXELS = 20_000_000`

The QImageReader HEADER geometry is validated BEFORE the full decode
(rejecting unreasonable images without allocating them); the decoded
geometry is rechecked after `read()`. A pure `_dimensions_allowed`
helper keeps the policy testable without giant test images.

## Documentation reconciliation

`SqliteEnrichmentRepository`, `EnrichmentStorageError` and
`EnrichmentSchemaError` docstrings now describe the R3 truth: storage
failures vs schema contract violations, truthful reads/writes, and
identity corruption semantics.

## Firewalls preserved

- Metadata firewall: TrackMetadata / TrackRef / ArtistRef / AlbumRef /
  GenreRef / ComposerRef / MusicModel / MetadataExtractorPort /
  InfrastructureMetadataExtractor / LibraryIndexEntry / library_index
  schema — unchanged (blob-verified).
- Audio firewall: audio_engines, AudioTransportRouter, PlaybackService,
  QueueService, Coordinator, bootstrap — unchanged (blob-verified).
- Presentation: zero changes. pyproject.toml: zero changes. No network
  code. No Mutagen in enrichment.

## Validation surface

`tests/test_m6_9a_r3_1_final_invariants.py` (54 tests): identity
invariants matrix, duplicate-hint normalization, authority precedence
(short-circuit call-count proofs, revocation flows), malformed identity
reads, V1/V2/V3 migration shape fail-closed cases, version truth, image
dimension policy + pre-decode rejection seam, normal PNG regression —
on top of the complete R1/R2/R3 suite.

## Next authorized WP

M6.9B — EXTERNAL PROVIDER FOUNDATION (only after audit acceptance of
R3.1). NOT started.
