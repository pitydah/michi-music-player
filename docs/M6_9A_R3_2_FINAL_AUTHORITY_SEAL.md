# M6.9A-R3.2 — Migration + Identity Authority Final Seal

Status: implemented. Scope: the final authority/migration corrective seal
on the M6.9A enrichment foundation. NO network providers, NO tag
extraction, NO presentation, NO bootstrap wiring.

## Clean reconstruction on the definitive M11.3C-R6 main

R3.2 was reconstructed from the pinned definitive audio base
`a02412c` (M11.3C-R6 DEFINITIVELY FROZEN). The 14 pure enrichment
commits (R1 transfer + R2 + R3 + R3.1) were cherry-picked in original
order; the R3.1 branch remains untouched as historical evidence.
Post-replay purity: audio diff 0, metadata canonical diff 0, bootstrap
diff 0, presentation diff 0. The current GStreamer blob (M11.3C-R6) is
inherited from main — NOT the older R3.1 audio snapshot.

## Migration commit gate (P1-02)

Every migration (V1 → 3, V2 → 3) now validates the RESULTING database
against the CURRENT schema INSIDE the transaction, BEFORE COMMIT. A
migration succeeds only if the post-migration database is a valid
current schema; any failure rolls the source database back (version
never advances, no `_v3` temporary tables survive). Missing knowledge
tables in a migration source are rejected before the transaction
starts.

## V2 semantic authority validation (P1-03)

Before migrating, EVERY V2 identity row is decoded through the CURRENT
identity constructors: non-empty/non-whitespace keys and ids,
RESOLVED-only status, valid MatchMethod, string resolved_at. Malformed
authority rows FAIL the migration with ROLLBACK — never skipped,
deleted, or normalized. The legacy `manually_confirmed` column is
ignored for V3 authority (MatchMethod remains the authority since R2).

## SQLite constraint validation (P1-04)

Current-schema validation now compares the FULL canonical PRAGMA
signature (column name, declared type, NOT NULL contract, primary-key
role) for all five tables — computed from the CURRENT canonical DDL
built fresh in-memory (never hand-guessed; robust to SQLite
rowid-table PK quirks). A V3 table missing its primary key, wrong
nullability or wrong declared type is rejected without mutation.

## Release-edition contradiction detection (P1-05)

`resolve_release_hint_for_group`: a specific Release ID identifies ONE
edition identity. Candidates mapping the SAME release id to MULTIPLE
distinct release groups are IDENTITY_CONFLICT — even if one group
equals the resolved group (no `any()` acceptance). Duplicate identical
mappings are duplicate observations, not conflicts. Unrelated edition
candidates are ignored.

## Album EMBEDDED release-hint refinement (P1-07)

The persisted-album EMBEDDED_HINT short-circuit now requires BOTH
current direct-hint sets (release_group_ids AND release_ids) to be
empty. A NEW explicit release_id is direct edition evidence: the
persisted release group stays authoritative (never downgraded to
AUTO), the current release hint is evaluated against it via the
contradiction-aware helper — corroborated → edition refined
(MatchMethod stays EMBEDDED_HINT, stale release-level knowledge
invalidated); uncorroborated → group preserved, release not trusted;
proven in another/multiple groups → IDENTITY_CONFLICT + revocation.

## Album authority parity (P1-06)

Album authority now has the same behavioral regression coverage as
artist authority: MANUAL sticky, EMBEDDED stronger than AUTO,
release-only refinement matrix, AUTO same/different preserved/
transitioned, AUTO revoked on AMBIGUOUS / NO_MATCH /
IDENTITY_CONFLICT, late old results STALE with zero persistence.

## Identity decoding fully fail-closed (P1-08)

- `__post_init__` type-validates `status` BEFORE attribute access (a
  wrong status TYPE raises ValueError, never AttributeError).
- Row decoders catch (KeyError, TypeError, ValueError) and translate to
  `EnrichmentStorageError` — never None, never raw exceptions.
- A single-load key mismatch is corruption: raises, never "no identity
  exists".

## ID hygiene (P2-01)

Persistent identity ids reject whitespace-only values; `release_id`
must not be whitespace-only when non-empty.
`dedupe_identity_ids` strips surrounding whitespace, drops
empty-after-strip values and dedupes stripped ids (first-seen order;
never case-normalized; never across roles).

## version() final truth (P2-02)

`version()` additionally rejects a post-construction FUTURE version
(> CURRENT) with `EnrichmentSchemaError` — never returns an
unsupported integer as if valid.

## Schema remains 3

No persistent-format change; no schema 4. These corrections enforce
the already-intended schema-3 contract.

## Firewalls preserved

Metadata firewall (TrackMetadata / TrackRef / ArtistRef / AlbumRef /
GenreRef / MusicModel / MetadataExtractorPort / InfrastructureMetadataExtractor /
LibraryIndexEntry / library_index) unchanged — blob-verified. Audio
firewall: the M11.3C-R6 GStreamer blob equals the pinned base —
blob-verified. Bootstrap and presentation unchanged. pyproject diff
zero. No network code. No Mutagen in enrichment.

## Validation surface

`tests/test_m6_9a_r3_2_final_authority.py` (45 tests): migration
commit gate (rollback proofs via SQLite + injected post-validation
failure), SQLite constraint matrix, release contradictions, album
authority parity, corruption/version/whitespace hygiene — on top of
the complete R1/R2/R3/R3.1 suite.

## Next authorized WP

M6.9B — EXTERNAL PROVIDER FOUNDATION (only after human audit of
R3.2). NOT started.
