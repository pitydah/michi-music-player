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
| `ui_qml_bridge/*.py` | Python-QML bridges, one per domain. |
| `ui_qml/shell/AppShell.qml` | Root QML shell with sidebar + page stack. |
| `audio/player.py` | GStreamerEngine. Play/pause/seek/queue/EQ pipeline. |
| `library/library_db.py` | SQLite schema, scanner, metadata, playlists, history. |
| `core/settings_manager.py` | QSettings wrapper with defaults. |

## Data Flow

```
User clicks play → window._play_file()
  → player.play(uri)
    → GStreamer pipeline (playbin → audiochain → alsasink)
    → player emits state_changed, position_changed, duration_changed
  → nowplaying_bar updates seek, title, cover
  → mpris adapter emits PropertiesChanged via DBus
  → KDE widget/lockscreen updates
```

## Persistence

| Data | Storage | Path |
|------|---------|------|
| Library | SQLite | `~/.local/share/michi-music-player/library.db` |
| Playlists | SQLite | (same DB) |
| Queue | SQLite | (same DB) |
| Radio stations | JSON | `~/.local/share/michi-music-player/radio_stations.json` |
| Subsonic servers | JSON | `~/.local/share/michi-music-player/subsonic_servers.json` |
| Transmit devices | JSON | `~/.local/share/michi-music-player/transmit_devices.json` |
| Settings | QSettings | `~/.config/Michi/MusicPlayer.conf` |
| Album art cache | SQLite | (same DB) |
