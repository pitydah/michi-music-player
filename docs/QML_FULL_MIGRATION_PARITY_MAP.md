# QML Full Migration Parity Map

## Objetivo

Definir el estado real de paridad funcional entre QtWidgets y QML para preparar la migración completa controlada.

## Resumen ejecutivo

| Área | QtWidgets | QML | Backend real | Tests | Estado | Prioridad |
|---|---|---|---|---|---|---|
| AppShell/Shell | ✅ | ✅ | — | ✅ Shell | COMPLETO | — |
| Sidebar | ✅ | ✅ | NavigationBridge | ✅ | COMPLETO | — |
| HeaderBar | ✅ | ✅ | — | ✅ | COMPLETO | — |
| NowPlayingBar | ✅ | ✅ | NowPlayingBridge | ✅ | COMPLETO | — |
| Inicio | ✅ | ✅ | HomeBridge | Parcial | FUNCIONAL | Alta |
| Biblioteca | ✅ | ✅ | LibraryBridge | ✅ | FUNCIONAL | Alta |
| Reproducción | ✅ | ✅ | PlaybackBridge | ✅ | FUNCIONAL | Alta |
| Playlists | ✅ | ✅ | PlaylistsBridge | ✅ | FUNCIONAL | Media |
| Radio | ✅ | ✅ | RadioBridge | ✅ | FUNCIONAL | Media |
| Mix | ✅ | ✅ | MixBridge | Parcial | FUNCIONAL | Media |
| Assistant | ✅ | ✅ | MichiAIBridge | ✅ | FUNCIONAL | Media |
| Conexiones | ✅ | ✅ | ConnectionsBridge | ✅ | FUNCIONAL | Alta |
| Home Audio | ✅ | ✅ | HomeAudioBridge | Parcial | FUNCIONAL | Baja |
| Dispositivos | ✅ | ✅ | DevicesBridge | Sí | FUNCIONAL | Baja |
| Ajustes | ✅ | ✅ | SettingsBridge | Sí | FUNCIONAL | Baja |
| Metadata | ✅ | ✅ | MetadataBridge | ✅ | FUNCIONAL | Media |
| Audio Lab | ✅ | ✅ | AudioLabBridge | Sí | FUNCIONAL | Baja |
| Disc Lab | ✅ | ❌ (no existe) | — | — | LEGACY_ONLY | Baja |
| Library Doctor | ✅ | ✅ LibraryDoctorPage.qml | — | ✅ | COMPLETO_VISUAL | Baja |
| Smart Tagging | ✅ | ✅ SmartTaggingPage.qml | SmartTaggingBridge | ✅ | PARCIAL | Baja |
| DSP/EQ | ✅ | ✅ EqPage.qml | — | ✅ | COMPLETO_VISUAL | Baja |
| Output Profiles | ✅ | ✅ OutputProfilesPage.qml | SettingsBridge (outputProfiles) | ✅ | FUNCIONAL | Baja |

## Alpha2 Readiness Gate

| Gate | Estado | Observación |
|---|---|---|
| Ruff | ✅ | All checks passed |
| Compileall | ✅ | OK |
| Smoke startup | ✅ | 7/7 |
| Smoke UI routes | ✅ | 2/2 |
| Runtime check | ✅ | OK |
| QML bridge tests | ✅ | 170 passed |
| QML component tests | ✅ | 62 passed |
| Total QML tests | ✅ | 238 passed |
| Schema tests | ✅ | 15 passed |
| Format probe | ✅ | 41 passed |
| Playback controller | ✅ | 6 passed |
| Todas las páginas QML con test | ✅ | 100% cobertura de existencia |
| MichiCover directo en páginas | ✅ | 0 (solo CoverBridgeProxy) |
| Emojis como controles | ✅ | 0 |
| ActionButton en código activo | ✅ | 0 |
| Demo data en QML | ✅ | Eliminado (Connections, HomeAudio) |
| Radius hardcodeados → MichiTheme | ✅ | Corregido (DeviceCard, SyncStatusPanel) |
| Manual visual QML | ⏳ | Pendiente |
| Audio físico real | ⏳ | Pendiente |
| Pre-existing non-QML failure | ⚠️ | album_import_worker.py / test_services_no_qt_dependency (deuda preexistente fuera de alcance QML) |

### Veredicto Alpha2

El gate automatizado está aprobado. El proyecto es candidato fuerte a `0.2.0-alpha.2`, pero no debe declararse listo mientras falte la prueba humana visual con `python main.py --qml` y validación de audio real.

## Matriz por módulo

### 1. AppShell / Navegación

| Elemento | QtWidgets | QML | Bridge/Service | Estado | Acción |
|---|---|---|---|---|---|
| Shell layout | window.py / QStackedWidget | AppShell.qml | — | COMPLETO | — |
| Sidebar | SidebarWidget | Sidebar.qml | NavigationBridge | COMPLETO | — |
| Header | window.py SECTION_CONFIG | HeaderBar.qml | — | COMPLETO | — |
| Route transition | QStackedWidget instant | RouteTransition.qml | — | COMPLETO | — |
| NowPlaying bar | NowPlayingBarWidget | NowPlayingBar.qml | NowPlayingBridge | COMPLETO | — |
| Collapse sidebar | No | Sí (botón collapse) | — | COMPLETO | — |

### 2. Inicio

| Elemento | QtWidgets | QML | Bridge/Service | Estado | Acción |
|---|---|---|---|---|---|
| Hero | HomeHero (QWidget) | HomeHero.qml | HomeBridge | FUNCIONAL | Validar snapshot real |
| Cards | ContinueCard, LibraryCard, etc. | ContinueCard, LibraryStatusCard, etc. | HomeBridge | FUNCIONAL | Tests bridge |
| Sugerencias | — | AssistantCard | HomeBridge | VISUAL | Conectar bridge |

### 3. Biblioteca

| Elemento | QtWidgets | QML | Bridge/Service | Estado | Acción |
|---|---|---|---|---|---|
| Songs | SongsPremiumPage | SongTable.qml | LibraryBridge | FUNCIONAL | Context menu acciones |
| Albums | AlbumGridView | AlbumGrid.qml / AlbumCard | LibraryBridge | FUNCIONAL | — |
| Artists | ArtistGridView | ArtistList.qml / ArtistCard | LibraryBridge | FUNCIONAL | — |
| Folders | FolderBrowser | FolderBrowser.qml | LibraryBridge | FUNCIONAL | — |
| Album detail | AlbumDetailView | AlbumDetailPage.qml | LibraryBridge | FUNCIONAL | Cover bridge |
| Artist detail | ArtistDetailView | ArtistDetailPage.qml | LibraryBridge | FUNCIONAL | Cover bridge |
| Search | SearchController | SearchField (HeaderBar) | LibraryBridge | FUNCIONAL | Bridge search |

### 4. Reproducción / NowPlaying

| Elemento | QtWidgets | QML | Bridge/Service | Estado | Acción |
|---|---|---|---|---|---|
| Controls | NowPlayingBar | NowPlayingControls.qml | NowPlayingBridge | COMPLETO | — |
| Seek bar | NowPlayingBar | NowPlayingSeekBar.qml | NowPlayingBridge | COMPLETO | — |
| Volume | NowPlayingBar | NowPlayingVolume.qml | NowPlayingBridge | COMPLETO | — |
| Cover | NowPlayingBar | NowPlayingCover.qml | CoverBridge | COMPLETO | — |
| Info | NowPlayingBar | NowPlayingInfo.qml | NowPlayingBridge | COMPLETO | — |
| PlaybackPage | PlaybackHubPage | PlaybackPage.qml | PlaybackBridge | FUNCIONAL | Queue/history |

### 5. Playlists

| Elemento | QtWidgets | QML | Bridge/Service | Estado | Acción |
|---|---|---|---|---|---|
| List | PlaylistHub | PlaylistsPage.qml | PlaylistsBridge | PARCIAL | CRUD real |
| Detail | PlaylistDetailView | PlaylistDetailPage.qml | PlaylistsBridge | PARCIAL | Botones acción |
| Card | — | PlaylistCard.qml | PlaylistsBridge | VISUAL | Bridge data |

### 6. Radio

| Elemento | QtWidgets | QML | Bridge/Service | Estado | Acción |
|---|---|---|---|---|---|
| Station list | Radio view | RadioPage.qml | RadioBridge | PARCIAL | Filtros reales |
| Search | SearchController | — | — | PENDIENTE | Migrar search |

### 7. Mix

| Elemento | QtWidgets | QML | Bridge/Service | Estado | Acción |
|---|---|---|---|---|---|
| List | MixHubPage | MixHubPage.qml | MixBridge | PARCIAL | Data bridge |
| Detail | — | MixDetailPage.qml | MixBridge | PARCIAL | Smart mixes |

### 8. Assistant

| Elemento | QtWidgets | QML | Bridge/Service | Estado | Acción |
|---|---|---|---|---|---|
| Chat | AiAssistantPanel | AssistantPage.qml | MichiAIBridge | FUNCIONAL | Visual polish |
| Suggestions | SuggestionBar | SuggestionCard | MichiAIBridge | FUNCIONAL | — |

### 9. Connections

| Elemento | QtWidgets | QML | Bridge/Service | Estado | Acción |
|---|---|---|---|---|---|
| Servers | ConnectionsHubPage | ConnectionsPage.qml | ConnectionsBridge | FUNCIONAL | Validar servers reales |
| Discovery | — | NetworkDiscoveryPanel | — | VISUAL | Bridge discovery |
| Micro Server | — | MicroServerHero | — | VISUAL | Bridge micro |

### 10. Devices / Sync

| Elemento | QtWidgets | QML | Bridge/Service | Estado | Acción |
|---|---|---|---|---|---|
| Device list | DevicesPage | DevicesPage.qml | DevicesBridge | PARCIAL | Sync real |
| Sync status | — | SyncStatusPanel | — | VISUAL | Bridge sync |

### 11. Settings

| Elemento | QtWidgets | QML | Bridge/Service | Estado | Acción |
|---|---|---|---|---|---|
| Sections | SettingsHubPage | SettingsPage.qml | SettingsBridge | PARCIAL | Migrar secciones |

### 12. Metadata Editor

| Elemento | QtWidgets | QML | Bridge/Service | Estado | Acción |
|---|---|---|---|---|---|
| Inspector | MetadataEditor | MetadataInspectorPage.qml | MetadataBridge | PARCIAL | Completar campos |
| Artwork | ArtworkPicker | MetadataArtworkPreview.qml | MetadataBridge | PARCIAL | Cover bridge directo |

### 13. Audio Lab

| Elemento | QtWidgets | QML | Bridge/Service | Estado | Acción |
|---|---|---|---|---|---|
| Dashboard | AudioLabPage | AudioLabPage.qml | AudioLabBridge | PARCIAL | Migrar subpáginas |

### 14-16. Disc Lab / Library Doctor / Smart Tagging

| Elemento | QtWidgets | QML | Bridge/Service | Estado | Acción |
|---|---|---|---|---|---|
| Disc Lab | MichiDiscLabPage | ❌ | — | LEGACY_ONLY | Migrar después de Audio Lab |
| Library Doctor | LibraryDoctorPanel | ❌ | — | LEGACY_ONLY | Migrar después de Metadata |
| Smart Tagging | SmartTaggingPanel | ❌ | — | LEGACY_ONLY | Migrar después de Metadata |

### 17. DSP / EQ / Audio Output

| Elemento | QtWidgets | QML | Bridge/Service | Estado | Acción |
|---|---|---|---|---|---|
| EQ | EqDialog | ❌ | — | LEGACY_ONLY | Migrar después de Settings |
| Output profiles | AudioPage | ❌ | — | LEGACY_ONLY | Migrar después de Settings |

## Gaps críticos

| Gap | Severidad | Módulo | Motivo | Acción propuesta |
|---|---|---|---|---|
| Disc Lab no existe en QML | Media | Disc Lab | Requiere migración completa | PR post-Audio Lab |
| Library Doctor no existe en QML | Media | Library Doctor | Requiere migración completa | PR post-Metadata |
| Smart Tagging no existe en QML | Media | Smart Tagging | Requiere migración completa | PR post-Metadata |
| DSP/EQ no existe en QML | Baja | DSP/EQ | Baja prioridad | Post-Settings |
| Output profiles no existe en QML | Baja | Output Profiles | Baja prioridad | Post-Settings |
| No hay bridge de búsqueda QML | Baja | Search | Se puede resolver con LibraryBridge | PR opcional |
| MetadataArtworkPreview usa MichiCover directo | Baja | Metadata | Reemplazar con CoverImage | PR Metadata |

## Dependencias para migración completa

| Dependencia | Estado | Riesgo | Acción |
|---|---|---|---|
| Prueba humana visual QML | ⏳ Pendiente | Alto | Ejecutar python main.py --qml |
| Audio real físico | ⏳ Pendiente | Alto | Probar reproducción real |
| Playlists CRUD completo | ⚠️ Parcial | Medio | Completar bridge |
| Radio filtros reales | ⚠️ Parcial | Medio | Completar bridge |
| Settings secciones reales | ⚠️ Parcial | Bajo | Completar bridge |
| Devices sync real | ⚠️ Parcial | Bajo | Completar bridge |
| CoverImage en metadata | ⚠️ Parcial | Bajo | Reemplazar MichiCover directo |

## Orden recomendado de PRs

| PR | Objetivo | Riesgo | Estado |
| -- | -------- | ------ | ------ |
| #12 | QML Full Migration Parity Map | Ninguno | ✅ Mergeado |
| #13 | Playlists + Radio functional parity | Medio | ✅ Mergeado |
| #14 | Settings + Devices + Connections parity | Medio | ✅ Mergeado |
| #15 | Metadata QML phase 1 | Medio | ✅ Mergeado |
| #16 | Audio Lab QML tests | Bajo | ✅ Mergeado |
| #17 | Full QML route coverage | Bajo | ✅ Mergeado |
| #18 | Release gate documentation update | Bajo | ✅ Mergeado |
| #19 | EQ page + Library Doctor page | Bajo | ✅ Mergeado |
| #20 | Smart Tagging + Output profiles QML | Alto | ⏳ Pendiente (backend pesado) |
| #21 | QML default behind guarded flag | Alto | ⏳ Pendiente (requiere release gate + prueba humana) |

## Validación del PR

| Comando | Resultado |
|---|---|
| `ruff check .` | ✅ All checks passed |
| `compileall` | ✅ OK |
| `tests/qml/ -q` | ✅ 211 passed |
| `tests/test_schema.py -q` | ✅ 15 passed |

## Veredicto

Este PR es documental y define el mapa maestro de migración. No migra funcionalidad nueva. El gate automatizado para Alpha2 está aprobado. La migración completa requiere seguir el orden de PRs propuesto, empezando por Playlists/Radio parity.
