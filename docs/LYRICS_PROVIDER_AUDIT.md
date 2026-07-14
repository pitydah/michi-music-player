# Lyrics Provider Audit

## LRCLIB (lrclib.net)

| Field | Value |
|-------|-------|
| Base URL | https://lrclib.net/api |
| Provider ID | `lrclib` |
| Supports exact lookup | Yes (`GET /api/get?track_name=&artist_name=`) |
| Supports search | Yes (`GET /api/search?q=`) |
| Supports synced | Yes (LRC format) |
| Supports plain | Yes |
| Rate limit | 1 req/sec |
| Authentication | None |
| Attribution required | Source label recommended |
| License | Public API — see lrclib.net/docs |
| Terms reference | https://lrclib.net/docs |
| Implementation status | Implemented in this branch (`infrastructure/lyrics/providers/lrclib_provider.py`) |
| Legacy status | `lyrics/lrclib_client.py` preserved as compatibility wrapper |

## Genius (not implemented)

| Field | Value |
|-------|-------|
| Status | Defined in settings schema, NOT implemented |
| Risk | Scraping may violate ToS |
| Plan | Do not implement in this branch |

## Musixmatch (not implemented)

| Field | Value |
|-------|-------|
| Status | Defined in settings schema, NOT implemented |
| Risk | Requires API key, may have usage restrictions |
| Plan | Do not implement in this branch |

## Attribution Policy

All providers must be displayed with attribution in the UI when their lyrics are shown.
For LRCLIB: "Lyrics provided by lrclib.net".
