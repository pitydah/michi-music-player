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
| **Playlists** | ⚠️ 50% | Hub + detail + bridge | ✅ | Conectar a backend real |
| **Sync/Devices** | ⚠️ 50% | DevicesPage + bridge | ✅ | Conectar a SyncManager real |
| **Settings** | ⚠️ 50% | Foundation 6 categorías | ✅ | Conectar a settings_manager |
| **Radio** | ⚠️ 30% | Hero + cards informativas | ✅ | Desde rama broadcast |
| **Home Audio** | ⚠️ 40% | Foundation + dispositivos | ✅ | Conectar a HA/Snapcast |
| **ContextMenu** | ⚠️ 30% | SongContextMenu básico | ✅ | Expandir |
| **Michi Link UI** | ✅ 80% | ConnectionsPage + MicroServerHero | ✅ | Mejorar estado real |
