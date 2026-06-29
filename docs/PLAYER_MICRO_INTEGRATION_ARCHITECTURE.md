# Player ↔ Micro Server Integration Architecture

## Overview

Michi Music Player integrates with Michi Micro Server through a clean service layer.
The Player acts as **client** to the Micro Server for discovery, import, and playback handoff.

## Architecture layers

```
┌─────────────────────────────────────────────────────────────┐
│                      UI Controllers                         │
│  (MichiServerController, MichiImportController, ...)       │
├─────────────────────────────────────────────────────────────┤
│                     Service Layer                           │
│  MicroServerService  │  ImportToServerService               │
│  ContinueOnServer    │  RemoteLibraryService                │
│  DiagnosticsService  │                                      │
├─────────────────────────────────────────────────────────────┤
│                     Client Layer                            │
│  MichiLinkClient  │  MicroServerClient                      │
├─────────────────────────────────────────────────────────────┤
│                     HTTP (urllib.request)                   │
├─────────────────────────────────────────────────────────────┤
│              Michi Micro Server (remote)                    │
└─────────────────────────────────────────────────────────────┘
```

## Service contracts

All services return `Result` objects:

```python
@dataclass
class Result:
    ok: bool
    code: str       # machine-readable error code
    message: str    # human-readable description
    data: Any       # payload on success
    error: str | None  # error details on failure
```

## Data flow

### Discovery + Pairing
```
Player → GET /api/v1/server/info (Micro Server)
Player → POST /api/v1/pair/start
Player → POST /api/v1/pair/confirm
Micro → device_token + device_id
```

### Import
```
Player → create_session(track_ids)
Player → upload_track(session_id, track_id)  [Micro streams from Player]
Player → upload_artwork(session_id, cover_id)
Player → upload_playlist(session_id, playlist)
Player → commit(session_id)
(Player → rollback(session_id) on error)
```

### Continue on Server
```
Player → transfer_queue(server, track_ids, position_ms)
Player → pause_local()
Player → start_remote_playback(server)
(Micro streams from Player)
Player → stop_remote_playback(server)
```

## Implementation files

| Layer | File |
|-------|------|
| Result | `integrations/michi_link/services/result.py` |
| MicroServerService | `integrations/michi_link/services/micro_server_service.py` |
| ImportToServerService | `integrations/michi_link/services/import_to_server_service.py` |
| ContinueOnServerService | `integrations/michi_link/services/continue_on_server_service.py` |
| RemoteLibraryService | `integrations/michi_link/services/remote_library_service.py` |
| DiagnosticsService | `integrations/michi_link/services/diagnostics_service.py` |
| MichiLinkClient | `integrations/michi_link/client.py` |

## Key design decisions

1. **No Qt dependencies** — services are pure Python, testable with mocks
2. **Result objects** — never raise exceptions to caller
3. **Session-based import** — supports commit/rollback for atomicity
4. **Hash verification** — local SHA-256 before upload
5. **Progress callbacks** — for UI progress bars
6. **queue_provider/pause_local** — injected callables for decoupling
7. **No window.py** — controllers consume services, not direct HTTP
