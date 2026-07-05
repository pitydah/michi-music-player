# QML Visual Debt Map

Fecha: 2026-07-05

Escala: 1 = bajo/fragil, 5 = alto/listo. Prioridad: P1 bloquea pulido alpha/beta, P2 importante, P3 refinamiento.

| Pagina | Madurez visual | Responsive | Accesibilidad | Estados | Prioridad |
|---|---:|---:|---:|---:|---|
| `Main.qml` | 3 | 1 | 2 | 2 | P1 |
| `AppShell.qml` | 4 | 2 | 2 | 3 | P2 |
| `HeaderBar.qml` | 4 | 2 | 2 | 2 | P2 |
| `Sidebar.qml` | 4 | 3 | 1 | 3 | P1 |
| `PageStack.qml` | 3 | 3 | 2 | 1 | P2 |
| `ShortcutLayer.qml` | 3 | 4 | 2 | 2 | P2 |
| `NowPlayingBar.qml` | 4 | 3 | 1 | 3 | P1 |
| `ExpandedNowPlayingPanel.qml` | 3 | 2 | 1 | 3 | P2 |
| `PlaybackPage.qml` | 4 | 3 | 1 | 4 | P1 |
| `LibraryPage.qml` | 4 | 2 | 2 | 3 | P1 |
| `SongTable.qml` | 4 | 2 | 1 | 3 | P1 |
| `AlbumGridView.qml` | 3 | 2 | 1 | 1 | P2 |
| `AlbumCoverFlowView.qml` | 3 | 2 | 1 | 1 | P2 |
| `AlbumVinylWallView.qml` | 3 | 2 | 1 | 1 | P2 |
| `AlbumTimelineView.qml` | 3 | 3 | 1 | 1 | P3 |
| `AlbumMagazineView.qml` | 3 | 3 | 1 | 1 | P3 |
| `AlbumDetailPage.qml` | 3 | 2 | 1 | 2 | P2 |
| `ArtistDetailPage.qml` | 3 | 2 | 1 | 2 | P2 |
| `PlaylistsPage.qml` | 3 | 3 | 2 | 3 | P2 |
| `PlaylistDetailPage.qml` | 2 | 2 | 1 | 3 | P2 |
| `MetadataInspectorPage.qml` | 3 | 2 | 2 | 3 | P2 |
| `SmartTaggingPage.qml` | 3 | 2 | 2 | 4 | P2 |
| `LyricsPage.qml` | 3 | 3 | 2 | 4 | P1 |
| `RadioPage.qml` | 3 | 3 | 2 | 3 | P2 |
| `MixHubPage.qml` | 3 | 3 | 2 | 2 | P3 |
| `MixDetailPage.qml` | 2 | 2 | 1 | 2 | P3 |
| `SettingsPage.qml` | 2 | 3 | 2 | 2 | P3 |
| `AudioLabPage.qml` | 3 | 2 | 2 | 3 | P2 |
| `DevicesPage.qml` | 3 | 3 | 2 | 3 | P2 |
| `ConnectionsPage.qml` | 3 | 2 | 2 | 3 | P2 |
| `HomeAudioPage.qml` | 3 | 2 | 2 | 3 | P2 |
| `HomePage.qml` | 4 | 2 | 2 | 3 | P2 |

## Lectura por zonas

| Zona | Diagnostico | Siguiente accion |
|---|---|---|
| Shell | Visualmente maduro, falta responsive compacto y accesibilidad. | Breakpoints + focus/roles en Sidebar/Header/CommandPalette. |
| Playback | La identidad mas fuerte de la app. | Hacer controles canonicos, focusables y con hit targets de 36-44 px. |
| Biblioteca | Funcional, densa y valiosa. | Resolver toolbar responsive, tabla y context menu. |
| Album views | Ricas como concepto, dispares como sistema. | Unificar album tile/placeholder/empty. |
| Workflows | SmartTagging, Metadata, Radio, AudioLab comunican funcionalidad pero se sienten alpha. | Estados honestos, inputs canonicos y grids responsive. |
| Ecosistema | Connections/HomeAudio/Devices tienen buen tono, pero patrones repetidos. | Card base para device/server/receiver. |
| Accesibilidad | Debil transversal. | Sprint especifico antes de llamar beta. |

## Paginas que parecen mas terminadas

| Pagina | Por que |
|---|---|
| `AppShell.qml` | Estructura limpia, rutas y now playing integrados. |
| `Sidebar.qml` | Navegacion completa y visualmente consistente. |
| `NowPlayingBar.qml` | Buena jerarquia y controles reconocibles. |
| `PlaybackPage.qml` | Tiene track info, quality, controls, queue, history y error handling. |
| `LibraryPage.qml` + `SongTable.qml` | Alto valor funcional, filtros, busqueda, menu contextual. |
| `HomePage.qml` | No esta sobrecargada y respeta una entrada sobria. |

## Paginas que parecen prototipo o alpha funcional

| Pagina | Senal |
|---|---|
| `AlbumCoverFlowView.qml` | Path fijo y placeholders; necesita fallback/reduced motion. |
| `AlbumVinylWallView.qml` | Concepto visual sin caratulas reales en el delegate. |
| `SmartTaggingPage.qml` | Tiene flujo, pero una accion declara aplicacion simulada. |
| `SettingsPage.qml` | Mas indice de rutas que experiencia de ajustes. |
| `MixHubPage.qml` | Correcta pero muy corta y sin empty/loading robusto. |
| `AudioLabPage.qml` | Muchas cards/status badges; necesita orden visual y responsive. |
| `PlaylistDetailPage.qml` | Rows y delete icon por texto `[X]`; falta polish. |

## Deuda transversal por severidad

| Severidad | Deuda | Paginas/componentes afectados |
|---|---|---|
| P1 | Soporte 800x600 incumplido | `Main.qml`, shell, library toolbar, now playing |
| P1 | Tokens inexistentes | `PlaybackPage.qml`, `LyricsPage.qml`, `SyncedLyricsView.qml`, `LyricsSearchDialog.qml` |
| P1 | Accesibilidad/foco incompletos | Casi todo `ui_qml/`; solo `NowPlayingVolume` expone Accessible parcialmente |
| P1 | Iconos por texto/Unicode | Sidebar fallbacks, expanded controls, toasts, playlists, synced lyrics |
| P2 | Hardcoded sizes y grids | Library, album views, AudioLab, Connections, HomeAudio |
| P2 | Estados no canonicos | PageStack, Library, Radio, SmartTagging, Devices |
| P2 | Reduced motion ausente | Shell, panels, progress, lyrics |
| P3 | Copy "Experimental"/"Interfaz clasica" excesivo | Header, Sidebar, Settings, SmartTagging, AudioLab, Playlists |
