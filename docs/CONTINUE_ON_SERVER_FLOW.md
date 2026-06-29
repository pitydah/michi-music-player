# Continue on Server — Playback Handoff Flow

## Overview

The "Continue on Server" feature allows Michi Music Player to hand off its current
playback queue to a paired Michi Micro Server. The Micro Server then streams tracks
from the Player's `/api/v1/stream/{track_id}` endpoint and continues playback.

## Flow

```
1. User is listening on Player
2. User selects "Continue on [Server Name]"
3. Player reads current queue (via queue_provider)
   → track_ids, current_index, position_ms
4. Player resolves internal IDs to API track_ids
5. Player calls POST /api/v1/queue/transfer on Micro Server
   Body: { track_ids, current_index, position_ms, source }
6. If Micro Server confirms (200):
   → Player pauses local playback
   → Player calls POST /api/v1/playback/control { command: "play" }
   → Micro Server starts streaming from Player
7. User can stop remote playback at any time
   → Player calls POST /api/v1/playback/control { command: "stop" }
```

## Service API

### ContinueOnServerService

```python
class ContinueOnServerService:
    def __init__(self, queue_provider=None, pause_local=None, resolve_track=None):
        ...

    def transfer_queue(self, server, track_ids=None, position_ms=0.0) -> Result:
        """Send queue to Micro Server. Pauses local on success."""

    def start_remote_playback(self, server) -> Result:
        """Start playing on Micro Server."""

    def stop_remote_playback(self, server) -> Result:
        """Stop playing on Micro Server."""
```

### queue_provider callable signature

```python
def queue_provider() -> tuple[list[str], int, float]:
    """Returns (track_ids, current_index, position_ms)"""
```

### pause_local callable signature

```python
def pause_local() -> None:
    """Pause local playback."""
```

## Micro Server API requirements

The Micro Server must implement:

```
POST /api/v1/queue/transfer
  Body: { track_ids: [...], current_index: int, position_ms: float, source: str }
  Response: { ok: true }
```

## Error handling

- If queue transfer fails → return Result.fail("TRANSFER_FAILED")
- Player does NOT pause local playback
- User can retry
- If start_remote_playback fails → queue was transferred but not playing
  → User can manually start from Micro Server UI
