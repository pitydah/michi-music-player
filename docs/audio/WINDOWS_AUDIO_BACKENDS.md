# Windows Audio Backends — Future Support

## Context

Michi Music Player is developed for Linux/KDE. Windows support is not a
current priority, but the Hybrid Audio Engine architecture is designed to
accommodate future Windows audio backends without breaking the existing API.

## WASAPI (Windows Audio Session API)

- **Status:** Not implemented (Linux-only project)
- **Purpose:** Native Windows audio output
- **Key features for future implementation:**
  - Exclusive mode for bit-perfect playback
  - Shared mode for normal playback
  - Event-driven buffering
  - Sample rate and format negotiation
- **Architecture:** Would implement `AudioBackend` protocol as `WasapiBackend`
  in `audio/backends/wasapi_backend.py`

## ASIO (Audio Stream Input/Output)

- **Status:** Not implemented
- **Purpose:** Professional/low-latency audio on Windows
- **Requirements:**
  - ASIO SDK or third-party driver
  - Proprietary license for distribution
  - Device-specific driver installation
- **Architecture:** Would implement `AudioBackend` protocol as `AsioBackend`
  in `audio/backends/asio_backend.py`

## Capability flags

The `BackendCapabilities` dataclass already includes:
```python
supports_wasapi: bool = False
supports_asio: bool = False
```

## Current status

```text
Linux:     GStreamer (default) + MPD (Hi-Fi)
Windows:   Not supported in this phase
macOS:     Not supported in this phase
```

## Priority for future

1. WASAPI Exclusive mode (bit-perfect on Windows)
2. WASAPI Shared mode (normal playback)
3. ASIO (pro audio)
