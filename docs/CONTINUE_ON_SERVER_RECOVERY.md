# Continue on Server — Recovery

## Safety rules

1. **Local playback is NEVER paused before remote confirmation.**
2. If queue transfer fails → return Result.fail + keep playing locally.
3. If auto-import fails → rollback import session + return error.
4. User can always retry.

## Transfer flow (with recovery)

```
1. Read local queue → track_ids, index, position_ms
2. (Optional) Auto-import missing tracks:
   a. For each track: upload → track_id response
   b. Commit → if error, rollback
3. POST /api/v1/queue/transfer → if error, return, keep playing
4. PAUSE LOCAL PLAYBACK ⇐ ONLY HERE
5. POST /api/v1/playback/control { command: "play" }
   → if error, log warning, queue was transferred but not playing
```

## Recovery scenarios

| Failure | Recovery |
|---------|----------|
| Preflight unavailable | Fallback: upload everything |
| Upload fails mid-session | Rollback entire session |
| Queue transfer fails | Keep playing locally, return TRANSFER_FAILED |
| Remote play fails | Queue transferred, Micro has it, start manually |
| Local pause fails | Log warning, continue |

## Diagnostic check

```python
svc = DiagnosticsService()
# Check if continue can work
result = svc.check_continue_readiness(player_service)
# result == {"status": "ready", "has_queue": true, "queue_length": N}
```
