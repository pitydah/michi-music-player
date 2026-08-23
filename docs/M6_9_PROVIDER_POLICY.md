# M6.9 — Provider Policy

Authoritative statement of provider roles and boundaries.

## Identity master

**MusicBrainz** is the ONLY identity source. Candidates are strictly
validated; provider score/order never influences identity; first-result
matching is forbidden.

## Field ownership

| Concern | Provider |
|---|---|
| Identity (artist MBID / release group / release) | MusicBrainz |
| Structured facts (dates, genres, area, links) | MusicBrainz, then Wikidata (verified QID only) |
| Biography | Wikipedia (verified sitelink only, bounded extract) |
| Artist image | Wikimedia Commons (verified file claim) |
| Album external cover | Cover Art Archive (release → release-group fallback) |

Wikidata/Wikipedia are NEVER queried by name search — only through
verified MusicBrainz URL relations / Wikidata sitelinks.

## Network policy

- HTTPS only; provider host allowlist; body/redirect validation.
- MusicBrainz: ≤1 request/second, process-wide, serialized.
- Retries: only GET; only 429/502/503/504; max 3 attempts; Retry-After
  honored else 1s/2s backoff.
- No network during library scan; no mandatory startup network; all
  requests run off the UI thread via the enrichment executor.
- `Online Library Enrichment` setting defaults OFF: false ⇒ zero
  provider calls.

## Cache / offline

Provider cache is a separate filesystem authority (never enrichment.db).
Fresh cache serves offline; expired knowledge may be shown as STALE
cache only — identity authority NEVER remaps from stale cached
candidates.

## Excluded

Spotify, Apple Music, Last.fm, Discogs, TheAudioDB, Genius, AllMusic,
Deezer, Tidal, Qobuz. No scraping, no search-engine parsing, no
browser automation.
