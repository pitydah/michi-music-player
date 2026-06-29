# Player Diagnostics — Health Check Reference

## Overview

Michi Music Player includes a `DiagnosticsService` that generates a health report
for the entire Michi ecosystem. It checks Player API, sync server, pairing,
stream, playback, queue, and Micro Server connectivity.

## Report structure

```json
{
  "player_api": { "status": "ok", "service": "michi-music-player", ... },
  "sync_server": { "status": "ok", "running": true },
  "pairing": { "status": "ok", "total_devices": 2, "paired": 1, "revoked": 1 },
  "stream": { "status": "ok" },
  "playback": { "status": "ok", "state": "stopped" },
  "queue": { "status": "ok", "queue_length": 10 },
  "micro_server_client": { "status": "ok", "alias": "MicroNAS", ... },
  "micro_import": { "status": "ok", "requires_pairing": true, "import_available": true },
  "continue_readiness": { "status": "ready", "has_queue": true, "queue_length": 10 },
  "errors": []
}
```

## Status values

| Status | Meaning |
|--------|---------|
| `ok` | Working correctly |
| `stopped` | Service exists but not running |
| `no_index` | Stream index not built yet |
| `no_queue` | No active queue for continue |
| `ready` | Ready for continue |
| `unreachable` | Micro Server not reachable |
| `skipped` | Test skipped (no host provided) |
| `error` | Exception occurred |
| `unknown` | Not checked |

## Usage

```python
from integrations.michi_link.services.diagnostics_service import (
    DiagnosticsService,
)

svc = DiagnosticsService()
report = svc.generate_report(
    handler=request_handler,
    registry=device_registry,
    micro_host="192.168.1.100",
    player_service=player_service,
)
```

## Individual checks

| Check | Method | Parameters |
|-------|--------|------------|
| Player API | `check_player_api(handler)` | HTTP request handler |
| Sync server | `check_sync_server(handler)` | HTTP request handler |
| Pairing | `check_pairing(registry)` | DeviceRegistry |
| Stream | `check_stream(handler)` | HTTP request handler |
| Playback | `check_playback(player_service)` | PlayerService |
| Queue | `check_queue(player_service)` | PlayerService |
| Micro Server | `check_remote_micro(host, port)` | host string, port int |
| Import | `check_micro_import(host, port)` | host string, port int |
| Continue | `check_continue_readiness(player_service)` | PlayerService |
