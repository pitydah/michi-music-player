#!/usr/bin/env bash
# Create PR from qml-migration-foundation-clean to main
set -euo pipefail

gh pr create \
  --base main \
  --head qml-migration-foundation-clean \
  --title "QML Foundation: migración completa a Qt Quick (164 tests, 19 bridges)" \
  --body "## QML Foundation — Release Candidate

### Estado
- **164 tests** (164/164 passed)
- **ruff 0**, **compileall 0**, **no-touch ALL CLEAR**
- **Smoke QML OK**, **main.py OK**
- **86+ archivos QML**, **19 bridges Python**, **21 archivos bridge**

### Fases completadas
1. QML Foundation Clean (shell, theme, materials, components, sidebar)
2. Library QML completa (Canciones, Álbumes, Artistas, Carpetas, Search, Sort, Filter)
3. CoverBridge (QQuickPaintedItem, cache 256, fallback premium)
4. Metadata Inspector (read-only + escritura segura vía mutagen)
5. Audio Lab QML (bridge con datos reales de library_health)
6. Mix QML (6 categorías, hub, detalle)
7. NowPlayingBar QML (barra inferior, controles, seek, volumen, cover)
8. Michi AI (chat funcional + PlanBuilder real)
9. Playlists QML (hub + detalle + PlaylistStore real)
10. Sync/Devices QML (página + SyncManager real)
11. Radio QML (bridge + RadioManager real)
12. Home Audio QML (bridge + HA/Snapcast real)
13. Connections QML (bridge + MichiLinkController real)
14. Settings QML (bridge + settings_manager real)

### Bridges conectados a backends reales
- libraryBridge, metadataBridge, playbackBridge, mixBridge, devicesBridge,
  playlistsBridge, audioLabBridge, settingsBridge, radioBridge,
  connectionsBridge, homeAudioBridge, michiAiBridge, coverBridge

### Sin regresiones
- sidebar final (10 items, sin settings/géneros)
- Broadcast/Radio/Podcasts separados a rama propia
- NowPlaying experimental separado
- Playlists backend separado a rama propia
- No se tocó sync/ (solo lectura vía SyncManager)
- No se tocó reproducción (solo fachada PlayerService)"
