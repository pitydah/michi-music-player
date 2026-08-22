# M6.9A — Metadata / Enrichment Firewall

Status: implemented. Scope: structural firewall + fail-closed identity gates.
No network providers, no tag extraction, no UI wiring — those are later WPs.

## Problem

Michi Legacy suffered architectural corruption because local file metadata,
external MusicBrainz/Wikipedia enrichment, caches and asynchronous entity
state crossed authority boundaries. M6.9A makes recurrence **structurally
impossible**.

## Five bounded contexts — never merged

| # | Context | Carrier |
|---|---------|---------|
| 1 | LOCAL FILE METADATA | `TrackMetadata`, `TrackRef`, `AlbumRef`, `ArtistRef`, `MusicModel` (`src/michi/domain/library.py`) — media tags + local technical stream facts ONLY |
| 2 | LOCAL EXTERNAL IDENTITY HINTS | `ExternalIdentityHints` (`src/michi/domain/enrichment.py`) — MBIDs that may exist in local tags; pure evidence, not canonical metadata |
| 3 | RESOLVED EXTERNAL IDENTITY | `IdentityResolution`, `AlbumIdentityResolution` — fail-closed gate verdicts |
| 4 | EXTERNAL KNOWLEDGE | `ArtistKnowledgeProfile`, `AlbumKnowledgeProfile` — enrichment.db EXCLUSIVELY |
| 5 | METADATA EDITING | FUTURE — not implemented; no external→tag-write path exists |

## One-way data flow

```
Canonical Local Library → local evidence → Identity Resolver → External Knowledge
```

Reverse propagation (External Knowledge → TrackMetadata / AlbumRef / ArtistRef /
library_index / audio file tags) is FORBIDDEN and structurally absent: the
enrichment service imports nothing from the canonical library ports and the
canonical metadata modules contain zero external-identity references (enforced
by `tests/test_m6_9a_structural_gates.py`).

## Module map

| Module | Role |
|--------|------|
| `src/michi/domain/enrichment.py` | Hints carrier, knowledge profiles, fail-closed gates (`resolve_artist_identity`, `resolve_album_identity`), immutable `EnrichmentRequest` + `EnrichmentRequestLedger`, profile codecs |
| `src/michi/application/enrichment_ports.py` | `ExternalIdentityResolverPort`, `ArtistKnowledgeProviderPort`, `AlbumKnowledgeProviderPort`, `KnowledgeRepositoryPort`, `EnrichmentAssetStorePort` (+ `EnrichmentProviderError`) — in a NEW module so `ports.py` / `MetadataExtractorPort` stay byte-for-byte unchanged |
| `src/michi/application/enrichment_service.py` | Correlation-checked coordination: `request_*` registers an immutable request; `deliver_*` commits only while it still matches that context |
| `src/michi/infrastructure/enrichment_repository.py` | `SqliteKnowledgeRepository` — enrichment.db, tables `artist_knowledge` / `album_knowledge` / `enrichment_meta`. NEVER touches `library_index` / `library_meta` |
| `src/michi/infrastructure/enrichment_assets.py` | `FilesystemEnrichmentAssetStore` — external artwork authority, own directory, never the local artwork cache |

## Identity gates (fail-closed)

- **Artist homonym gate** — canonical `ArtistRef` identity is the normalized
  local name; identical names can be different artists. Auto-match by name
  alone is FORBIDDEN. Resolution requires supporting evidence (local album
  titles, release years, embedded identity hints). Multiple plausible
  candidates → `AMBIGUOUS`, no profile attached.
- **Identity conflict gate** — conflicting hints/evidence for one canonical
  `ArtistRef` → `IDENTITY_CONFLICT`. Never "first", "majority" or "most
  popular".
- **Album identity gate** — `local_album_key → Release Group MBID` may
  auto-resolve with strong evidence (title + year); the specific Release MBID
  stays `""` unless edition-identifying evidence (an embedded release id hint)
  exists. Downloaded release dates/labels never overwrite local album year.

## Async entity-correlation firewall

No mutable `_active_artist` / `_current_album`-style globals exist. Every
async enrichment operation carries immutable correlation
(`EnrichmentRequest`: request_id, entity_kind, local_entity_key,
external_entity_id, generation). `EnrichmentRequestLedger.deliver()` returns:

- `COMMITTED` — request still current (consumed; second delivery → `UNKNOWN`)
- `STALE` — superseded by a newer request (out-of-order / stale identity)
- `UNKNOWN` — never registered
- `MISMATCHED` — payload entity id / kind / local key does not match the
  request context

A result for Artist A can never mutate Artist B — by routing, by payload
validation and by the absence of shared mutable state.

## Firewalls kept

- **External genres** live only in knowledge profiles — never merge into
  `TrackMetadata.genre` / `AlbumRef.genres` / `GenreRef`.
- **External dates** live only in profiles — never repair local year/date;
  timeline stays on canonical local data.
- **Artwork**: three authorities (LOCAL embedded/folder, USER override,
  EXTERNAL downloads). External assets go only to the enrichment asset store;
  embedded artwork is never overwritten and downloaded bytes are never
  written into audio files.
- **Storage**: enrichment.db is fully independent of library_index /
  library_meta; clearing or rebuilding enrichment.db changes zero canonical
  rows / TrackRefs.
- **Presentation join (future)**: UI will compose
  `ArtistPresentation { local: ArtistRef, knowledge: ArtistKnowledgeProfile | None }`
  — never mutate the local refs.

## Acceptance matrix (M6.9A)

TrackMetadata / MetadataExtractorPort / InfrastructureMetadataExtractor /
library_index schema / LibraryIndexEntry codec / ArtistRef / AlbumRef /
MusicModel / local genres / local dates / local artwork authority — all
**unchanged** (enforced by `tests/test_m6_9a_structural_gates.py`).

External identity and external knowledge stored separately; async request
correlation; artist homonym fail-closed; no external-to-local write path;
metadata tag writes ZERO; canonical library writes during enrichment ZERO
(`tests/test_m6_9a_cross_contamination.py`).
