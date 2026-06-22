# Michi Music Player — Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        UI Layer (PySide6)                    │
│  window.py  nowplaying_bar.py  sidebar_widget.py           │
│  expanded_view.py  coverflow.py  preferences_window.py      │
├─────────────────────────────────────────────────────────────┤
│                     Player Engine (GStreamer)               │
│  player.py → audio_chain.py → GStreamer pipeline           │
│  eq_biquad.py  eq_basic.py  eq_advanced.py  spectrum.py     │
├─────────────────────────────────────────────────────────────┤
│                     Data Layer (SQLite + JSON)              │
│  library_db.py  radio_manager.py  transmit_manager.py       │
│  subsonic_client.py  sync_manager.py                        │
├─────────────────────────────────────────────────────────────┤
│                     Integrations                             │
│  adapters/mpris.py (KDE DBus)  sync_*.py (Android)          │
│  transmit_manager.py (Snapcast/HTTP)                        │
└─────────────────────────────────────────────────────────────┘
```

## Key Files

| File | Role |
|------|------|
| `main.py` | Entry point. Sets up QApplication, theme, font. |
| `window.py` | MainWindow. Menus, sidebar, content area, signals. |
| `player.py` | GStreamerEngine. Play/pause/seek/queue/EQ pipeline. |
| `library_db.py` | SQLite schema, scanner, metadata, playlists, history. |
| `nowplaying_bar.py` | Bottom bar: cover, seek, controls, volume. |
| `sidebar_widget.py` | Collapsible section sidebar with search. |
| `theme.py` | QPalette + QSS for glassmorphism dark theme. |
| `audio_chain.py` | DAC config, EQ sink builders. |
| `adapters/mpris.py` | MPRIS DBus service for KDE control. |
| `settings_manager.py` | QSettings wrapper with defaults. |
| `preferences_window.py` | 14-category settings dialog. |

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
| Settings | QSettings | `~/.config/Astra/MusicPlayer.conf` |
| Album art cache | SQLite | (same DB) |
