# Known Issues — Michi Music Player QML

| Issue | Severidad | Módulo | Workaround | Estado |
|---|---|---|---|---|
| NowPlayingBar playbackBridge binding loop (warning no crítico) | Baja | NowPlayingBar QML | Ignorar, no afecta funcionalidad | Conocido |
| Metadata Inspector solo lectura | Media | MetadataBridge | Usar interfaz clásica para escribir tags | Aceptado |
| Playlists bridge usa datos mock | Media | PlaylistsBridge | Conectar a backend real de rama playlists-premium-backend | Pendiente |
| Devices bridge usa datos mock | Media | DevicesBridge | Conectar a SyncManager real | Pendiente |
| Audio Lab cards son placeholders | Media | AudioLabPage | Conectar a servicios reales | Pendiente |
| Settings no conectado a settings_manager | Media | SettingsPage | Conectar a core/settings_manager.py | Pendiente |
| Radio es placeholder informativo | Baja | RadioPage | Migrar desde rama broadcast-radio-podcasts | Pendiente |
| CI no ejecuta tests QML en PR (solo en push) | Baja | CI | Verificar en push a qml-migration-foundation-clean | Conocido |
