# Lyrics Integration Contract

This document describes how future branches should integrate `LyricsService` into QML, QtWidgets, and other subsystems.

## Service Container Integration

Future branch should add to `ServiceContainer`:

```python
# In core/service_container.py or equivalent:
from core.lyrics.service import LyricsService
from core.lyrics.resolver import LyricsResolver
from core.lyrics.registry import LyricsProviderRegistry
from infrastructure.lyrics.cache_repository import SqliteLyricsCacheRepository
from infrastructure.lyrics.providers.lrclib_provider import LrcLibProvider
from core.paths import lyrics_cache_db_path  # needs to be added

def _init_lyrics(self) -> LyricsService:
    cache = SqliteLyricsCacheRepository(lyrics_cache_db_path())
    cache.initialize()
    registry = LyricsProviderRegistry()
    registry.register(LrcLibProvider(cache=cache))
    resolver = LyricsResolver(registry, cache_repo=cache)
    return LyricsService(resolver, registry, cache_repo=cache)
```

## Settings Keys (future)

Add to `core/settings_schema.py`:

- `lyrics/enabled` (bool, default True)
- `lyrics/provider_order` (list[str], default ["lrclib"])
- `lyrics/remote_enabled` (bool, default True)
- `lyrics/offline_mode` (bool, default False)
- `lyrics/prefer_synced` (bool, default True)
- `lyrics/allow_plain` (bool, default True)
- `lyrics/preferred_language` (str, default "")
- `lyrics/request_timeout` (int, default 10000)
- `lyrics/negative_cache_ttl` (int, default 3600)
- `lyrics/positive_cache_ttl` (int, default 86400)
- `lyrics/cache_size_mb` (int, default 50)
- `lyrics/auto_search_current_track` (bool, default True)
- `lyrics/save_remote_to_cache` (bool, default True)

## Paths (future)

Add to `core/paths.py`:

```python
def lyrics_cache_db_path() -> str:
    return os.path.join(app_cache_dir(), "lyrics_cache.sqlite")
```

## LyricsBridge (future QML integration)

Constructor should be:

```python
LyricsBridge(
    lyrics_service: LyricsService,
    playback_context: PlaybackContext,
    parent: QObject = None,
)
```

The bridge should:
- Convert `LyricsDocument` models to QVariantMap for QML
- Expose properties: `lyrics`, `syncedLyrics`, `source`, `status`, `activeLine`
- Emit signals on domain events
- NOT contain HTTP, parsing, cache, matching, filesystem, editing, or persistence logic

## Metadata Integration (future)

- `EmbeddedLyricsReader` protocol implementation in `metadata/tag_reader.py`
- `EmbeddedLyricsWriter` protocol implementation in `metadata/tag_writer.py`
