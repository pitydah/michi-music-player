# Michi Link — Player Beta Guide

## Status: Beta-ready

Michi Music Player is ready for beta testing as a **Michi Link v1.0.0-alpha** server.

## Server endpoints (ready for Mobile)

| Method | Path | Status | Notes |
|--------|------|--------|-------|
| GET | `/api/v1/server/info` | ✅ Ready | Full contract with auth, roles, features |
| GET | `/api/v1/status` | ✅ Ready | Server status, sync active |
| POST | `/api/v1/pair/start` | ✅ Ready | Returns auth_methods, auth_required |
| POST | `/api/v1/pair/confirm` | ✅ Ready | Returns device_token + permissions |
| GET | `/api/v1/tracks` | ✅ Ready | No filepath exposed |
| GET | `/api/v1/search?q=` | ✅ Ready | No filepath exposed |
| GET | `/api/v1/library/stats` | ✅ Ready | |
| GET | `/api/v1/stream/{track_id}` | ✅ Ready | Range Request (206), full (200), 404 |
| GET | `/api/v1/artwork/{cover_id}` | ✅ Ready | Cache-Control, mime, 404 |
| GET | `/api/v1/sync/manifest` | ✅ Ready | Delegates to existing SyncManifestBuilder |
| GET | `/api/v1/sync/manifest/delta` | ✅ Ready | Accepts cursor, since, manifest_id |
| POST | `/api/v1/sync/state` | ✅ Ready | |
| GET | `/api/v1/playback/state` | ✅ Ready | state, position_ms, volume, shuffle, repeat |
| POST | `/api/v1/playback/control` | ✅ Ready | 12 commands, command field official |
| GET | `/api/v1/queue` | ✅ Ready | No filepath exposed |
| POST | `/api/v1/queue/jump` | ✅ Ready | |
| POST | `/api/v1/queue/items` | ✅ Ready | Accepts uris or track_ids |
| POST | `/api/v1/token/refresh` | 🔒 Future | Returns NOT_IMPLEMENTED |
| GET | `/api/v1/events` | 🔒 Future | Returns NOT_IMPLEMENTED, use polling |

## Client stubs (Player → Micro Server — Phase 2/3)

| Module | File | Status |
|--------|------|--------|
| MichiLinkClient | `integrations/michi_link/client.py` | ✅ Ready — discover, pair, library, control |
| MicroServerClient | `integrations/michi_link/micro_server_client.py` | ✅ Stub with 9 methods |
| ImportClient | `integrations/michi_link/import_client.py` | ✅ Stub — fetch tracks, fetch playlists, import to local |
| RemoteLibraryProvider | `integrations/michi_link/remote_library_provider.py` | ✅ Stub — remote as browsable source |
| ContinueOnServerService | `integrations/michi_link/continue_on_server_service.py` | ✅ Stub — handoff queue to Micro Server |

## Controller stubs (future UI)

| Controller | File | Purpose |
|------------|------|---------|
| MichiServerController | `ui/controllers/michi/server_controller.py` | Server lifecycle, devices, account |
| MichiImportController | `ui/controllers/michi/import_controller.py` | Import remote tracks to local library |
| MichiContinueController | `ui/controllers/michi/continue_controller.py` | Handoff playback to remote server |

No controllers are connected to window.py yet. They are prepared for future UI work.

## How to test Mobile → Player

1. Start Player, enable Sync (Devices → Michi Sync Suite).
2. Create local account (optional, enables password pairing).
3. Mobile discovers Player on LAN.
4. POST `/api/v1/pair/start` → read `auth_required`, `auth_methods`.
5. POST `/api/v1/pair/confirm` with `client_device_id`, `username`, `password`.
6. Store `device_token` + `device_id`.
7. All subsequent requests include:
   ```
   Authorization: Bearer <device_token>
   X-Michi-Device-Id: <device_id>
   ```

## Test summary

```
88 tests in tests/test_michi_link.py
1758 total tests in project
2 pre-existing failures (artist_controller, unrelated)
```

## Conservative features

| Feature | Value | Reason |
|---------|-------|--------|
| `events` | `false` | SSE not implemented, polling works |
| `token_refresh` | `false` | Not implemented yet |
| `receivers` | `false` | No receiver integration yet |
| `rooms` | `false` | No multi-room yet |

## What's next

1. **Mobile integration testing** — validate real device pairing, streaming, control.
2. **Micro Server client implementation** — connect Phase 2 methods to real HTTP.
3. **Controller wiring** — connect MichiServerController to sync_manager in window.py.
4. **UI** — server control panel, paired device list, import dialog.
5. **Events** — SSE for real-time state updates.
6. **Token refresh** — implement when auth infrastructure stabilizes.
7. **Receivers/Rooms** — integrate with Snapcast/Home Audio when ready.
