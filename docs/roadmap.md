# Michi Music Player — Roadmap

## v0.2.0-alpha.1 (Current)

### QtWidgets (estable — `python main.py`)
- [x] Local playback (MP3, FLAC, OGG, WAV, DSD)
- [x] SQLite library with mutagen metadata
- [x] Album art extraction (embedded + directory)
- [x] 31-band graphic EQ + parametric biquad EQ
- [x] CoverFlow 3D carousel
- [x] Playlists (CRUD)
- [x] Queue persistence between sessions
- [x] Play history + favorites (SQLite)
- [x] Navidrome/Jellyfin streaming (Subsonic API)
- [x] Radio stations (URL playback)
- [x] Audio transmission (HTTP server, Snapcast client)
- [x] Android sync (REST API + UDP discovery)
- [x] MPRIS DBus adapter (KDE integration)
- [x] Dark glassmorphism theme with internal texture
- [x] Adaptive background from album art colors
- [x] Collapsible sidebar with search
- [x] Keyboard shortcuts
- [x] Drag & drop files/folders
- [x] Carpetas — Folder maintenance (104 tests)
- [x] Biblioteca canónica — LibraryState, TrackIdentity, MutationService, OrganizeService
- [x] Library health service — summary, score, alerts

### QML (experimental — `python main.py --qml`)
- [x] QML Foundation — 16+ bridges, theme, materials, sidebar
- [x] Navigation — 12 routes, PageStack, history
- [x] Library QML — songs, albums, artists, folders, search
- [x] NowPlayingBar QML — controls, seek, volume, cover
- [x] Michi AI — chat integration
- [x] Playlists QML — hub + detail
- [ ] Audio Lab QML — placeholders, necesita backend conectado
- [ ] Settings QML — placeholders
- [ ] Radio QML — placeholders
- [ ] Home Audio QML — placeholders

## En validación
- Crossfade between tracks
- ReplayGain support
- Grid view for albums (2D)
- M3U/PLS playlist import/export
- System tray icon with controls
- Desktop notifications on track change
- Last.fm scrobbling
- Radio stream recording
- AutoEQ preset downloader
- Lyrics display

## Pendiente
- Reorganize code into packages
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
