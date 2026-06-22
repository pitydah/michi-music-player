# Michi Music Player — Roadmap

## v0.1.0-alpha (Current)

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
- [x] 14-category preferences window
- [x] Keyboard shortcuts
- [x] Drag & drop files/folders

## v0.2 (Planned)

- [ ] Crossfade between tracks
- [ ] ReplayGain support
- [ ] Grid view for albums (2D)
- [ ] M3U/PLS playlist import/export
- [ ] System tray icon with controls
- [ ] Desktop notifications on track change
- [ ] Last.fm scrobbling
- [ ] Radio stream recording
- [ ] AutoEQ preset downloader
- [ ] Lyrics display

## v0.3 (Planned)

- [ ] Reorganize code into packages (audio/, library/, ui/, streaming/, sync/)
- [ ] Controller layer separating UI from player engine
- [ ] Unit tests (pytest + pytest-qt)
- [ ] Internationalization (i18n)
- [ ] Flatpak package
- [ ] Multiple library support
- [ ] Smart shuffle (weighted by play history)

## v1.0 (Target)

- [ ] Stable API
- [ ] Full Flatpak on Flathub
- [ ] AUR package
- [ ] Ubuntu PPA
- [ ] User documentation
- [ ] Developer documentation
