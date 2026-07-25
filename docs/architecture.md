# Michi Music Player — Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     UI Layer (PySide6 QML)                   │
│  AppShell.qml  Sidebar.qml  NowPlayingBar.qml              │
│  pages/*.qml  components/*.qml                              │
├─────────────────────────────────────────────────────────────┤
│                  QML Bridge Layer (Python)                   │
│  ui_qml_bridge/*.py  bridges/*.py                           │
├─────────────────────────────────────────────────────────────┤
│                     Player Engine (GStreamer)               │
│  audio/player.py → audio/pipeline_factory.py                │
│  audio/eq_*.py  audio/spectrum.py                           │
├─────────────────────────────────────────────────────────────┤
│                  Core Services Layer                         │
│  core/  library/  metadata/  audio/  integrations/          │
├─────────────────────────────────────────────────────────────┤
│                     Data Layer (SQLite + JSON)              │
│  library/library_db.py  library/indexer.py                  │
│  core/radio/  core/sync/  core/playlists/                   │
└─────────────────────────────────────────────────────────────┘
```

## Key Files

| File | Role |
|------|------|
| `main.py` | Entry point. Delegates to michi/qml_app.py. |
| `michi/qml_app.py` | QML runtime: QGuiApplication + QQmlApplicationEngine. |
| `core/application_bootstrap.py` | DI container, builds all services. |
| `core/queue_service.py` | Canonical queue state, navigation, modes, rollback, reconciliation, and session persistence. |
| `audio/player_service.py` | Transport/audio facade and physical queue synchronization adapter. |
| `ui_qml_bridge/*.py` | Python-QML bridges, one per domain. |
| `ui_qml/shell/AppShell.qml` | Root QML shell with sidebar + page stack. |
| `audio/player.py` | GStreamerEngine. Play/pause/seek/queue/EQ pipeline. |
| `library/library_db.py` | SQLite schema, scanner, metadata, playlists, history. |
| `core/settings_manager.py` | QSettings wrapper with defaults. |

## Data Flow

```
User selects tracks → bridge or external adapter
  → QueueService mutates canonical items/index/repeat/shuffle transactionally
    → PlayerService synchronizes the active backend queue
      → HybridAudioManager → GStreamer or MPD
  → QueueService publishes one canonical revision to QML observers
  → backend progression is reconciled by index + filepath + revision

Transport-only commands (pause, stop, seek, volume)
  → PlayerService → active audio backend
```

`QueueService` is the only production queue ingress. QML bridges, MPRIS,
Michi AI, Michi Link, settings, playlists, library actions, and mixes must not
call PlayerService queue APIs. `tests/test_queue_ingress_architecture.py`
enforces this boundary.

## Persistence

| Data | Storage | Path |
|------|---------|------|
| Library | SQLite | `~/.local/share/michi-music-player/library.db` |
| Playlists | SQLite | (same DB) |
| Queue session | Atomic JSON | `~/.local/share/michi-music-player/runtime/queue_state.json` |
| Radio stations | JSON | `~/.local/share/michi-music-player/radio_stations.json` |
| Subsonic servers | JSON | `~/.local/share/michi-music-player/subsonic_servers.json` |
| Transmit devices | JSON | `~/.local/share/michi-music-player/transmit_devices.json` |
| Settings | QSettings | `~/.config/Michi/MusicPlayer.conf` |
| Album art cache | SQLite | (same DB) |
