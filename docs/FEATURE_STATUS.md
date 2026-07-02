# Feature Status — Michi Music Player QML

| Área | Estado | Ruta | Tests | Acción |
|---|---|---|---|---|
| **Foundation** | ✅ 100% | home, library, mix, playback, connections, radio, playlists, home_audio, assistant, audio_lab | 150 | Mantener |
| **Sidebar** | ✅ 100% | 10 items, sin settings, sin géneros | ✅ | Mantener |
| **NavigationBridge** | ✅ 100% | VALID_ROUTES controladas | ✅ | Mantener |
| **CoverBridge** | ✅ 100% | QQuickPaintedItem, cache 256, paint sin DB | ✅ | Mantener |
| **Library QML** | ✅ 90% | Canciones, Álbumes, Artistas, Carpetas, Search, Sorting, Filtering | ✅ | Pulir |
| **Mix QML** | ✅ 80% | 6 categorías, hub, detalle, bridge | ✅ | Tests reales |
| **Michi AI** | ✅ 75% | Chat funcional, 25 archivos backend | ✅ | Conectar a PlanBuilder |
| **NowPlayingBar** | ✅ 90% | Barra inferior fija, controles, seek, volumen, cover | ✅ | Conectar a PlayerService |
| **Metadata Inspector** | ⚠️ 60% | Read-only con mutagen | ✅ | Agregar escritura |
| **Audio Lab** | ⚠️ 40% | Foundation con cards | ✅ | Conectar servicios |
| **Playlists** | ✅ 80% | Hub + detail + bridge + PlaylistStore real | 164 | Conectar a backend premium |
| **Sync/Devices** | ✅ 70% | DevicesPage + bridge + SyncManager real | 164 | UI pulido |
| **Settings** | ✅ 70% | Bridge + settings_manager real | 164 | UI pulido |
| **Radio** | ✅ 60% | Bridge + RadioManager real | 164 | UI pulido |
| **Home Audio** | ✅ 60% | Bridge + HA/Snapcast real | 164 | UI pulido |
| **ContextMenu** | ✅ 50% | SongContextMenu básico | 164 | Expandir a albums |
| **Michi Link UI** | ✅ 85% | ConnectionsBridge + MichiLinkController real | 164 | UI pulido |
