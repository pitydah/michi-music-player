# Core Services Lifecycle

## Startup Order

```
1. paths/settings resolution
2. databases/repositories
3. shared runtimes (event_bus, job_service, worker_manager)
4. SettingsService
5. Library services (library_query, playlist, queue)
6. PlaybackService
7. DiagnosticsService
8. MetadataService (if available)
9. LyricsService (if available)
10. RadioService (if available)
11. AssistantCoreService (deferred — built on first access)
12. Bridges created by BridgeFactory
13. QML context properties registered
```

## Shutdown Order

```
1. Reject new operations
2. Assistant core (cancel plans, flush traces)
3. Radio sessions (close streams, cancel reconnect)
4. Lyrics requests (cancel pending lookups)
5. Metadata batches (cancel reviews, complete current write)
6. Remote providers (musicbrainz, cover art, lrclib)
7. Device sync service
8. Worker manager / job service
9. Event bus
10. Database connections
```

## ServiceContainer.shutdown() Implementation

```python
def shutdown(self):
    order = [
        "assistant_core_service",
        "radio_service",
        "lyrics_service",
        "metadata_service",
        "audio_lab_service",
        "assistant_local_model_provider",
        "lrclib_provider",
        "cover_art_provider",
        "musicbrainz_provider",
        "device_sync_service",
    ]
    for name in order:
        svc = self._services.get(name)
        if svc is not None and hasattr(svc, "shutdown"):
            try:
                svc.shutdown()
            except Exception:
                pass
    self._started = False
    self._failures.clear()
```

Shutdown is idempotent and tolerant of partial services.
