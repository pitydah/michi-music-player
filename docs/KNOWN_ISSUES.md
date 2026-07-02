# Known Issues — Michi Music Player QML

| Issue | Severidad | Módulo | Workaround | Estado |
|---|---|---|---|---|
| NowPlayingBar playbackBridge binding loop (warning no crítico) | Baja | NowPlayingBar QML | Ignorar, no afecta funcionalidad | Conocido |
| Metadata Inspector solo lectura | Media | MetadataBridge | Usar interfaz clásica para escribir tags | Aceptado |
| Playlists bridge usa PlaylistStore pero sin DB real en QML | Media | PlaylistsBridge | Inicializar con conexión DB desde qml_main | Pendiente |
| Devices bridge usa SyncManager pero sin instancia en QML | Media | DevicesBridge | Inicializar con sync_manager desde qml_main | Pendiente |
| Audio Lab cards dependen de DB connection | Media | AudioLabBridge | Inicializar con db_conn desde qml_main | Pendiente |
| CI no ejecuta tests QML en PR (solo en push) | Baja | CI | Verificar en push a qml-migration-foundation-clean | Conocido |
