# Core Services Convergence Baseline

**Rama:** convergence/core-services-v1
**HEAD:** aa085fd1eaf34db3f5e03ed1a93dc9d8a2e9a8bb

## ServiceContainer (pre-convergence)

| Service | Status |
|---------|--------|
| metadata_service | Declared REQUIRED but not registered |
| radio_service | Not declared |
| lyrics_service | Not declared |
| assistant_core_service | Not declared |
| confirmation_service | Not declared |

## BridgeFactory (pre-convergence)

- Creates bridges with only `worker_manager`
- No MetadataService, LyricsService, RadioService injected
- MichiAIBridge created with AIController legacy

## Capabilities (pre-convergence)

- No dynamic capability propagation
- No `metadata.read`, `metadata.modify`, `lyrics.read`, `radio.control`, `assistant.execute`

## Code Check

| Check | Result |
|-------|--------|
| Radio Core V2 files | ✅ Loaded (core/radio/, infrastructure/radio/) |
| Radio tests | ✅ Loaded (tests/core/radio/, tests/integration/radio/) |
| Lyrics Core V2 files | ✅ Loaded (core/lyrics/, infrastructure/lyrics/, lyrics/) |
| Lyrics tests | ✅ Loaded (tests/core/lyrics/, tests/integration/lyrics/, tests/perf/lyrics/) |
| Metadata Core files | ✅ Loaded (core/metadata_service.py, confirmation_service.py, metadata_init.py) |
| Michi AI Core V2 files | ✅ Loaded (michi_ai/v2/, tests/ai/) |
