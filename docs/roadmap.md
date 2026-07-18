# Michi Music Player — Roadmap

## v0.2.0-alpha.1 (Current)

### QML (único runtime — `python main.py`)
- [x] Local playback (MP3, FLAC, OGG, WAV, DSD)
- [x] SQLite library with mutagen metadata
- [x] Album art extraction (embedded + directory)
- [x] 31-band graphic EQ + parametric biquad EQ
- [x] Playlists (CRUD + smart playlists)
- [x] Queue persistence between sessions
- [x] Play history + favorites (SQLite)
- [x] Navidrome/Jellyfin streaming (Subsonic API)
- [x] Radio stations (URL playback)
- [x] Audio transmission (HTTP server, Snapcast client)
- [x] Android sync (REST API + UDP discovery)
- [x] MPRIS DBus adapter (KDE integration)
- [x] Dark glassmorphism theme
- [x] Adaptive background from album art colors
- [x] Keyboard shortcuts
- [x] Drag & drop files/folders
- [x] Folder maintenance
- [x] Library health service — summary, score, alerts
- [x] QML Foundation — 69+ bridges, theme, materials, sidebar
- [x] Navigation — 50+ routes, PageStack, history
- [x] Library QML — songs, albums, artists, folders, search
- [x] NowPlaying QML — controls, seek, volume, cover, lyrics
- [x] Michi AI — chat integration
- [x] Playlists QML — hub + detail, import/export
- [x] Audio Lab QML — conversion, analysis, comparison
- [x] Settings QML — 8 pages
- [x] Metadata Editor QML — individual + batch
- [x] Equalizer QML — graphic + parametric, presets
- [x] Smart Tagging QML
- [x] Library Doctor QML
- [x] Disc Lab QML
- [x] Radio QML
- [x] Home Audio QML — groups, zones, latency
- [x] Device Sync QML — pairing, transfer, profiles
- [x] Connections QML — discovery, pairing

## En validación
- Crossfade between tracks
- ReplayGain support
- M3U/PLS playlist import/export
- System tray icon with controls
- Desktop notifications on track change
- Last.fm scrobbling
- Radio stream recording
- AutoEQ preset downloader

## Pendiente
- Internationalization (i18n)
- Flatpak package
- Multiple library support
- Smart shuffle (weighted by play history)

## v1.0 (Target)
- [ ] Stable API
- [ ] Full Flatpak on Flathub
- [ ] AUR package
- [ ] Ubuntu PPA
- [ ] User documentation
- [ ] Developer documentation
