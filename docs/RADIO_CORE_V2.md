# Radio Core V2 — Architecture & Usage

## Overview

Radio Core V2 is a complete rewrite of the radio subsystem in Michi Music Player. It is decoupled from QtWidgets, QML, and UI, designed to be consumed by any frontend through a single `RadioService` facade.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    RadioService                      │
│  (canonical facade — coordinates all operations)     │
├─────────────────────────────────────────────────────┤
│   StationRepo  │  HistoryRepo  │  StreamProbe       │
│   (SQLite)     │  (SQLite)     │  (HTTP probe)      │
├────────────────┼───────────────┼─────────────────────┤
│   ImportSvc    │  ExportSvc    │  StreamSession      │
│   (M3U/PLS)    │  (M3U8/PLS)   │  (state machine)    │
├────────────────┴───────────────┴─────────────────────┤
│   ReconnectPolicy  │  IcyMetadataTracker              │
│   (exponential     │  (header + stream title parser)  │
│    backoff)        │                                   │
├──────────────────────────────────────────────────────┤
│   EventBus (domain events for all consumers)          │
└──────────────────────────────────────────────────────┘
```

## Key Modules

| Module | Path | Responsibility |
|--------|------|----------------|
| Models | `core/radio/models.py` | Typed dataclasses, enums, contracts |
| Events | `core/radio/events.py` | EventBus with generation tracking |
| Interfaces | `core/radio/interfaces.py` | Protocols for dependency injection |
| URL Utils | `core/radio/url_utils.py` | Validation, normalization, dedup |
| ICY Parser | `core/radio/icy_parser.py` | Header + StreamTitle parser |
| Reconnect | `core/radio/reconnect.py` | Exponential backoff + scheduler |
| StreamProbe | `core/radio/stream_probe.py` | Cancellable HTTP stream probing |
| Session | `core/radio/session.py` | State machine (IDLE→PLAYING→FAILED) |
| Service | `core/radio/service.py` | RadioService facade |
| Import/Export | `core/radio/import_export.py` | M3U/PLS/M3U8/JSON import & export |
| SQL Schema | `infrastructure/radio/schema.py` | DB schema + migrations |
| Station Repo | `infrastructure/radio/station_repository.py` | SQLite CRUD with pagination |
| History Repo | `infrastructure/radio/history_repository.py` | Play history with retention |

## Domain Events

All events are emitted via `EventBus`:

- `station_created`
- `station_updated`
- `station_deleted`
- `favorite_changed`
- `probe_started`
- `probe_completed`
- `session_state_changed`
- `metadata_changed`
- `playback_failed`
- `reconnect_scheduled`

## Session States

```
IDLE → CONNECTING → BUFFERING → PLAYING → STOPPING → STOPPED
                  ↘ FAILED ↗           ↘ RECONNECTING → CONNECTING
                    CANCELLED            CANCELLED       CANCELLED
```

## Usage

```python
from core.radio.service import RadioService
from core.radio.models import StationCreateRequest, StationUpdateRequest
from infrastructure.radio.station_repository import SqliteStationRepository
from infrastructure.radio.history_repository import SqliteRadioHistoryRepository

station_repo = SqliteStationRepository("stations.db")
station_repo.initialize()
history_repo = SqliteRadioHistoryRepository("stations.db")
history_repo.initialize()

service = RadioService(station_repo, history_repo)

# Create a station
result = service.create_station(StationCreateRequest(
    name="My Radio", stream_url="https://example.com/stream",
))

# List stations
stations = service.list_stations(page=1, page_size=50)

# Probes the stream (non-blocking if using async)
probe_result = service.probe_station(result.station.id)

# Start playback
service.start_station(result.station.id)

# Stop
service.stop()
```

## Testing

```bash
pytest tests/core/radio -q --timeout=120
pytest tests/integration/radio -q --timeout=300
```

## Dependencies

- Python 3.11+ stdlib only for core logic
- SQLite3 for persistence
- No Qt, GStreamer, or network dependencies in unit tests
