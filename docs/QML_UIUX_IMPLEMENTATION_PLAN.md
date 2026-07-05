# QML UI/UX Implementation Plan

Fecha: 2026-07-05

Objetivo: plan futuro de refinamiento visual y usabilidad para la interfaz QML, dividido en commits pequenos y sin interferir con migracion funcional/backend.

## Principios

- No redisenar desde cero.
- Mantener identidad Michi: moderno, sobrio, KDE/Linux, premium, glass smoked moderado.
- Reutilizar componentes existentes antes de crear nuevos.
- No agregar funciones no respaldadas por bridges/backend.
- No usar colores fuera del theme.
- No usar Unicode/texto como icono principal.
- Priorizar accesibilidad y responsive antes que efectos visuales.

## Orden recomendado

### 1. Design tokens

Commit sugerido: `style(qml): extend design tokens for responsive ui`

Scope:

- `ui_qml/theme/MichiColors.qml`
- `ui_qml/theme/MichiSpacing.qml`
- `ui_qml/theme/MichiTypography.qml`
- `ui_qml/theme/MichiMotion.qml`
- `ui_qml/theme/MichiTheme.qml`

Cambios:

- Agregar `captionSize`, `smallSize`, tokens de table/meta.
- Agregar colores semanticos faltantes: `accent`, `textOnError`, `surfaceHover`, `surfacePressed`, `trackBackground`, `dangerSubtle`.
- Agregar tokens de icon sizes, control heights, hit targets y breakpoints.
- Agregar flag/token `reducedMotion`.

Validacion:

- QML smoke startup.
- `rg 'captionSize|colors\\.accent|onError' ui_qml` sin referencias invalidas.
- Auditoria de hardcoded colors reducida.

Riesgo: bajo.

### 2. Componentes base

Commit sugerido: `refactor(qml): make base controls accessible and canonical`

Scope:

- `MichiButton.qml`
- `MichiIconButton.qml`
- `FilterChip.qml`
- `SearchField.qml`
- `EmptyState.qml`
- `StatusBadge.qml`
- `MichiSlider.qml`
- `ToastHost.qml`

Cambios:

- `Accessible.role/name/description` en controles base.
- Focus ring canonico.
- Keyboard Enter/Space en controles custom.
- `MichiIconButton` con icon-only real, tooltip y disabled description.
- `MichiTextField` si se decide separar search/input.
- Toast con icon button canonico en vez de `[X]`.

Validacion:

- Tests QML de componentes.
- Smoke visual de disabled/focus.
- Sin regresion de imports.

Riesgo: medio, porque toca componentes usados por muchas paginas.

### 3. Navegacion y shell

Commit sugerido: `style(qml): polish shell navigation and compact layout`

Scope:

- `Main.qml`
- `AppShell.qml`
- `HeaderBar.qml`
- `Sidebar.qml`
- `SidebarItem.qml`
- `PageStack.qml`
- `CommandPalette.qml`
- `ShortcutLayer.qml`

Cambios:

- Soporte real de 800x600 o documentar minimo si producto decide no soportarlo.
- Auto-collapse sidebar en compact.
- Header compact sin perdida de acciones.
- Command palette responsive, modal accesible y keyboard selection.
- Loading/error state visible en PageStack.
- Reduced motion en transiciones.

Validacion:

- Smoke routes.
- Capturas 800x600, 1024x768, 1920x1080.
- Keyboard path: Ctrl+K, Esc, sidebar, search.

Riesgo: medio.

### 4. Biblioteca

Commit sugerido: `style(qml): consolidate library lists and album views`

Scope:

- `LibraryPage.qml`
- `SongTable.qml`
- `SongRow.qml`
- `SongContextMenu.qml`
- `AlbumGridView.qml`
- `AlbumCoverFlowView.qml`
- `AlbumVinylWallView.qml`
- `AlbumTimelineView.qml`
- `AlbumMagazineView.qml`
- `AlbumCard.qml`
- `AlbumDetailPage.qml`
- `ArtistDetailPage.qml`

Cambios:

- Toolbar responsive.
- Song table con columnas min/max y compact mode.
- Context menu accesible.
- `AlbumTile`/`CoverImage` canonicos para todas las vistas.
- Empty/loading states con `EmptyState`.
- Foco/teclado en rows y album cards.

Validacion:

- Tests QML library components.
- Capturas library en compact/regular/wide.
- Navegacion album/artist detail.

Riesgo: alto por superficie funcional de biblioteca.

### 5. Playback

Commit sugerido: `style(qml): unify playback controls and states`

Scope:

- `NowPlayingBar.qml`
- `NowPlayingControls.qml`
- `NowPlayingSeekBar.qml`
- `NowPlayingVolume.qml`
- `ExpandedNowPlayingPanel.qml`
- `PlaybackPage.qml`
- `NowPlayingQueuePanel.qml`

Cambios:

- Controles compartidos entre bar, expanded y page.
- Seek/volume focusables y con `Accessible.value`.
- Hit targets minimos.
- Disabled/unavailable states consistentes.
- Queue/history usando componente comun.
- Variante compact de now playing.

Validacion:

- Tests QML NowPlaying.
- Smoke startup/routes.
- Prueba manual play/pause/seek/next/prev/volume si backend esta disponible.

Riesgo: alto por UX central.

### 6. Workflows

Commit sugerido: `style(qml): polish user workflows without adding backend scope`

Scope:

- `PlaylistsPage.qml`
- `PlaylistDetailPage.qml`
- `MetadataInspectorPage.qml`
- `SmartTaggingPage.qml`
- `LyricsPage.qml`
- `LyricsSearchDialog.qml`
- `SyncedLyricsView.qml`
- `RadioPage.qml`
- `MixHubPage.qml`
- `MixDetailPage.qml`

Cambios:

- Inputs canonicos.
- Empty/error/loading/unavailable comun.
- Eliminar botones nativos no estilizados.
- Copy honesto para experimental/simulado.
- Unicode icons reemplazados por iconos canonicos.
- Max widths para formularios y lectura.

Validacion:

- Smoke routes.
- Tests QML workflows.
- Capturas 1024/1920.

Riesgo: medio.

### 7. Herramientas avanzadas

Commit sugerido: `style(qml): organize advanced audio tools`

Scope:

- `AudioLabPage.qml`
- `EqPage.qml`
- `LibraryDoctorPage.qml`
- `DiscLabPage.qml`
- `OutputProfilesPage.qml`
- `DiagnosticsPage.qml`

Cambios:

- Tool grid responsive.
- Status badges no superpuestos.
- Cards de herramienta con estado canonico.
- Separar unavailable vs experimental vs classic-available.

Validacion:

- Smoke routes.
- Capturas compact/wide.

Riesgo: medio.

### 8. Ecosistema

Commit sugerido: `style(qml): consolidate devices and ecosystem cards`

Scope:

- `DevicesPage.qml`
- `ConnectionsPage.qml`
- `HomeAudioPage.qml`
- `DeviceCard.qml`
- `ReceiverCard.qml`
- `AudioZoneCard.qml`
- `ExternalServerCard.qml`
- `DiscoveredServerCard.qml`
- `ConfiguredServerCard.qml`
- `NetworkDiscoveryPanel.qml`
- `HomeAudioModeSelector.qml`

Cambios:

- Card base para device/server/receiver.
- Empty/unavailable states canonicos.
- Mode selector responsive.
- Estados backend no disponible visibles.

Validacion:

- Smoke routes.
- Capturas con listas vacias y datos presentes si existen.

Riesgo: medio.

### 9. Accesibilidad

Commit sugerido: `a11y(qml): add roles names focus and keyboard traversal`

Scope:

- Todos los componentes base.
- Shell.
- Library/playback/workflows prioritarios.

Cambios:

- Roles para botones, tabs, sliders, rows, menu items.
- `Accessible.name` en icon-only.
- `Accessible.description` para disabled/unavailable.
- Orden de tab.
- Focus ring visible.
- Keyboard support para cards y rows.

Validacion:

- Tests QML buscando `Accessible.*` en controles canonicos.
- Smoke manual con Tab/Shift+Tab/Enter/Escape/Space.

Riesgo: medio-alto, porque cambia interaccion.

### 10. Responsive

Commit sugerido: `style(qml): validate responsive breakpoints and hidpi sizing`

Scope:

- Shell.
- Library.
- Playback.
- Workflows.
- Ecosystem pages.

Cambios:

- Breakpoints compact/regular/wide/ultra.
- Grids 1/2/3/4 columnas.
- Max-width para formularios y lectura.
- Now playing compact.
- HiDPI-friendly icon sizes.

Validacion:

- Capturas 800x600, 1024x768, 1280x720, 1366x768, 1920x1080, 2560x1440, 3840x2160.
- Test de no dimensiones negativas.
- Test de textos largos en botones/cards.

Riesgo: alto por layouts.

### 11. Pulido final

Commit sugerido: `style(qml): final visual polish for alpha2 candidate`

Scope:

- Copy final.
- Badges experimentales.
- Tooltips.
- Context menus.
- Async feedback.
- Estados disabled.

Cambios:

- Reducir "Experimental" redundante a zonas donde aporta informacion.
- Tooltips consistentes.
- Context menus accesibles.
- Loading/progress donde haya operaciones asincronas.
- Verificacion de contraste.
- Eliminar restos de Unicode/text icons.

Validacion:

- Auditoria visual final.
- Smoke startup/routes.
- QML tests.
- Checklist manual de UI.

Riesgo: bajo-medio.

## Criterios para considerar alpha.2 visual

- 800x600 decidido y validado: soportado o minimo documentado explicitamente.
- Controles principales de playback focusables y accesibles.
- Biblioteca usable en 1024x768 sin acciones cortadas.
- Sin tokens inexistentes en `MichiTheme`.
- Empty/error/loading/unavailable states canonicos en paginas prioritarias.
- Iconos principales sin Unicode/text fallback visible.
- Reduced motion disponible.
- Capturas desktop y compact revisadas.

## Criterios para beta UI

- Accesibilidad basica completa en shell, library y playback.
- Responsive validado hasta 4K y HiDPI 125/150/200.
- Context menus navegables por teclado.
- Tooltips y disabled descriptions consistentes.
- Visual debt P1 cerrado.
- P2 documentado con issues o plan posterior.
