# QML Route Migration Status

## Objetivo

Mapa de rutas QML, bridges y estado de paridad frente a QtWidgets.

## Rutas

| Ruta | Página QML | Existe en QtWidgets | Bridge | Backend real | Tests | Estado | Acción siguiente |
|---|---|---|---|---|---|---|---|
| home | ✅ HomePage.qml | ✅ HomePage (QWidget) | HomeBridge | Sí | Parcial | FUNCIONAL_REAL | Validar snapshot bridge |
| library | ✅ LibraryPage.qml | ✅ LibraryHubPage | LibraryBridge | Sí | Sí | FUNCIONAL_REAL | Songs table bridge |
| playback | ✅ PlaybackPage.qml | ✅ PlaybackHubPage | PlaybackBridge | Sí | Sí | FUNCIONAL_REAL | Sincronizar con cola |
| playlists | ✅ PlaylistsPage.qml | ✅ PlaylistHubPage | PlaylistsBridge | Sí | Sí | PARCIAL | Migrar CRUD completo |
| playlist_detail | ✅ PlaylistDetailPage.qml | ✅ PlaylistDetailView | PlaylistsBridge | Sí | Sí | PARCIAL | Conectar botones acción |
| radio | ✅ RadioPage.qml | ✅ Radio view | RadioBridge | Sí | Sí | PARCIAL | Migrar filtros reales |
| mix | ✅ MixHubPage.qml | ✅ MixHubPage | MixBridge | Sí | Parcial | PARCIAL | Completar smart mixes |
| mix_detail | ✅ MixDetailPage.qml | — | MixBridge | Sí | Parcial | PARCIAL | Detalle completo |
| assistant | ✅ AssistantPage.qml | ✅ AiAssistantPanel | MichiAIBridge | Sí | Sí | FUNCIONAL_REAL | Chat visual polish |
| audio_lab | ✅ AudioLabPage.qml | ✅ AudioLabPage | AudioLabBridge | Sí | No | PARCIAL | Migrar subpáginas |
| connections | ✅ ConnectionsPage.qml | ✅ ConnectionsHubPage | ConnectionsBridge | Sí | Sí | FUNCIONAL_REAL | Validar servers reales |
| home_audio | ✅ HomeAudioPage.qml | ✅ HomeAudioView | HomeAudioBridge | Sí | No | FUNCIONAL_REAL | Tests bridge |
| devices | ✅ DevicesPage.qml | ✅ DevicesPage | DevicesBridge | Sí | No | PARCIAL | Conectar sync real |
| settings | ✅ SettingsPage.qml | ✅ SettingsHubPage | SettingsBridge | Sí | No | PARCIAL | Migrar secciones |
| metadata | ✅ MetadataInspectorPage.qml | ✅ MetadataEditor | MetadataBridge | Sí | Sí | PARCIAL | Completar campos |
| dev_page | ✅ PlaceholderPage.qml | — | — | — | — | PLACEHOLDER | Migrar desde widgets |
| radio | ✅ PlaceholderPage.qml | — | — | — | — | PLACEHOLDER | Migrar desde widgets |

## Leyenda de estados

- `FUNCIONAL_REAL`: conectado a backend real y probado.
- `COMPLETO_VISUAL`: UI avanzada, pero funcionalidad parcial o no validada completamente.
- `PARCIAL`: tiene piezas reales, pero faltan contratos, tests o navegación.
- `PLACEHOLDER`: existe visualmente, pero no implementa flujo real.
- `PENDIENTE`: falta QML o falta bridge.
- `RIESGOSO`: depende de backend pesado o de flujo crítico.
- `LEGACY_ONLY`: solo existe en QtWidgets.
