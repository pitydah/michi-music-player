# Lyrics Core V2 — Architecture & Usage

## Overview

Canonical lyrics subsystem for Michi Music Player. Multi-source resolution (embedded, sidecar, cache, remote), synced (LRC) and plain lyrics, persistent SQLite cache, editor with undo/redo, cancellation, attribution tracking.

## Architecture

```
LyricsService
├── LyricsResolver        (multi-source resolution order)
├── LyricsProviderRegistry (pluggable providers)
├── LyricsCacheRepository  (SQLite, positive + negative cache)
├── LyricsStorageService   (atomic sidecar writes)
├── LyricsEditorService    (undo/redo, offset, insert/delete/split/merge)
├── LyricsTimeline         (binary-search active line lookup)
├── LyricsTraceRecorder    (per-request tracing)
├── LyricsAttributionPolicy (provider attribution)
└── LyricEventBus          (domain events)
```

## Source Resolution Order

1. Manual (preferred)
2. Embedded (USLT/SYLT via protocols)
3. Sidecar LRC
4. Sidecar TXT
5. Cache (SQLite, persistent)
6. Remote Provider (e.g. LRCLIB)

Order is configurable via `LyricsSettings`.

## Key Modules

| Module | Responsibility |
|--------|---------------|
| `core/lyrics/models.py` | Typed dataclasses: TrackIdentity, LyricsDocument, LyricsLine, enums |
| `core/lyrics/parser.py` | Canonical LRC parser/serializer (supports offset, enhanced LRC, BOM, Unicode) |
| `core/lyrics/timeline.py` | Binary-search active line lookup (p95 < 1ms) |
| `core/lyrics/normalizer.py` | TrackIdentity normalization (feat., live, remix, Unicode, punctuation) |
| `core/lyrics/matcher.py` | Multi-factor matching (title, artist, duration, MBID, ISRC) |
| `core/lyrics/registry.py` | Provider registration, priority ordering |
| `core/lyrics/cancellation.py` | CancellationToken, CancellationSource, RequestTracker |
| `core/lyrics/resolver.py` | Orchestrates multi-source resolution with cancellation |
| `core/lyrics/editor.py` | Full editor: shift, insert, delete, split, merge, undo, redo |
| `core/lyrics/storage.py` | Atomic sidecar writes, embedded write gateway |
| `core/lyrics/service.py` | Canonical LyricsService facade |
| `core/lyrics/attribution.py` | Per-provider attribution policy |
| `core/lyrics/trace.py` | Request tracing for diagnostics |
| `infrastructure/lyrics/cache_repository.py` | SQLite cache with TTL, stale-while-revalidate |
| `infrastructure/lyrics/sidecar_provider.py` | File-based .lrc/.txt read/write, path security |
| `infrastructure/lyrics/providers/lrclib_provider.py` | LRCLIB API provider with rate limiting |

## Providers

| ID | Name | Synced | Plain | Network | Priority |
|----|------|--------|-------|---------|----------|
| lrclib | LRCLIB | Yes | Yes | Yes | 10 |

## Domain Events

- `lyrics_resolution_started`
- `lyrics_source_checked`
- `lyrics_resolved`
- `lyrics_not_found`
- `lyrics_resolution_cancelled`
- `lyrics_cache_updated`

## Quick Start

```python
from core.lyrics.service import LyricsService
from core.lyrics.resolver import LyricsResolver
from core.lyrics.registry import LyricsProviderRegistry
from core.lyrics.models import TrackIdentity
from infrastructure.lyrics.cache_repository import SqliteLyricsCacheRepository
from infrastructure.lyrics.providers.lrclib_provider import LrcLibProvider

cache = SqliteLyricsCacheRepository("lyrics.db")
cache.initialize()

registry = LyricsProviderRegistry()
registry.register(LrcLibProvider(cache=cache))

resolver = LyricsResolver(registry, cache_repo=cache)
service = LyricsService(resolver, registry, cache_repo=cache)

identity = TrackIdentity(title="Song", artist="Artist", duration_ms=240000)
result = service.resolve(identity)
if result.ok and result.document:
    print(result.document.plain_text)
```
