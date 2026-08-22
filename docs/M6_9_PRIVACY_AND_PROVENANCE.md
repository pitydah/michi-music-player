# M6.9 — Privacy & Provenance

## Privacy contract

- Michi does not silently transmit library information.
- `Online Library Enrichment` defaults OFF; every network call is the
  result of an explicit user operation.
- Outbound requests contain ONLY provider query terms and verified
  external ids. Never transmitted: filesystem paths, home directories,
  user names, play history, ratings, playlists, queue, device ids.
- Structural gates keep the canonical scan surface free of any
  enrichment network import.

## Provenance contract

Every provider-derived value is attributable:

- `KnowledgeProvenance` (provider, external_entity_id, source_url,
  retrieved_at, language, license, license_url, attribution) rides on
  every knowledge profile; biography carries its own provenance
  (identity ≠ biography source).
- Asset manifests (`EnrichmentAssetRecord`) carry provider, source URL,
  creator, license, license URL, attribution, checksum and dimensions.
- UNKNOWN stays UNKNOWN: license/attribution are never fabricated.

## Artwork authority

USER artwork > LOCAL embedded/folder artwork > EXTERNAL enrichment
artwork > placeholder. External images never become the canonical local
cover and are never written into audio files.

## Attribution

External biography/image surfaces must expose available provider,
source URL, license and attribution through the (future) attribution
UI — presentation phase is pending UI integration.
