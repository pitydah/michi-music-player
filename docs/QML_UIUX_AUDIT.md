# Michi QML UI/UX Audit

Fecha: 2026-07-05

Alcance auditado: `ui_qml/`, `ui_qml/theme/`, `ui_qml/components/`, `ui_qml/materials/`, `ui_qml/pages/` y `ui_qml/shell/`.

No se revisaron ni se proponen cambios en backend, bridges, servicios, scripts ni CI.

## Resumen ejecutivo

La interfaz QML de Michi Music Player ya tiene una direccion visual reconocible: producto musical avanzado para KDE/Linux, oscuro, sobrio, con glass smoked moderado y una densidad media razonable. La base de `MichiTheme`, `GlassMaterial`, `MichiButton`, `MichiIconButton`, `StatusBadge`, `SearchField`, `Sidebar`, `AppShell` y `NowPlayingBar` permite evolucionar sin redisenar desde cero.

El estado actual, sin embargo, todavia no es una UI/UX lista para beta publica. La deuda principal no es de identidad visual sino de sistematizacion: accesibilidad incompleta, responsive insuficiente por debajo de 1024 px, muchos controles custom basados en `MouseArea`, hardcodes de medidas, estados visuales inconsistentes y varias paginas avanzadas con apariencia de prototipo funcional.

Evaluacion global:

| Area | Estado | Nota |
|---|---:|---|
| Madurez visual | 72/100 | Identidad clara, pero con componentes y paginas de madurez desigual. |
| Consistencia | 64/100 | Theme y materiales existen, pero hay variaciones ad hoc en botones, cards, empties y album views. |
| Responsiveness | 55/100 | `Main.qml` bloquea 800x600 con `minimumWidth: 1024`; grids y barras usan medidas fijas. |
| Accesibilidad | 32/100 | Solo se encontraron 4 usos de `Accessible.*`, todos en `NowPlayingVolume.qml`. |
| Interaccion | 66/100 | Shortcuts y comandos existen, pero foco/teclado/context menus son parciales. |
| Preparacion productiva | 67/100 | Buen alpha avanzado; falta pulido sistemico para beta. |

## Fortalezas

| Fortaleza | Evidencia | Impacto |
|---|---|---|
| Identidad visual coherente | `MichiColors.qml`, `GlassMaterial.qml`, `HeroMaterial.qml`, `SidebarMaterial.qml` | La interfaz ya se siente propia y no copia directamente Spotify, Roon o Apple Music. |
| Shell funcional | `AppShell.qml`, `Sidebar.qml`, `HeaderBar.qml`, `PageStack.qml`, `ShortcutLayer.qml` | Navegacion QML clara, con rutas y shortcuts base. |
| Now Playing reconocible | `NowPlayingBar.qml`, `NowPlayingControls.qml`, `NowPlayingSeekBar.qml`, `NowPlayingVolume.qml` | La zona de reproduccion comunica producto musical real. |
| Componentes base reutilizables | `MichiButton`, `MichiIconButton`, `StatusBadge`, `SearchField`, `FilterChip`, `GlassCard` | Hay base para consolidar sin crear una UI nueva. |
| Estados iniciales presentes | Varias paginas muestran empty/error/unavailable/status badges | No parte de cero; la deuda es de consistencia, no ausencia total. |
| Densidad media apropiada | Sidebar 250 px, header 56 px, now playing 100 px, tablas compactas | Encaja con una app KDE/Linux productiva, no con landing page. |

## Hallazgos criticos

| Finding | Severity | Files | Recommendation |
|---|---|---|---|
| 800x600 no esta soportado por la ventana principal | P1 | `ui_qml/Main.qml` | Definir breakpoints reales y reducir `minimumWidth/minimumHeight` o documentar el minimo soportado. La mision pide 800x600. |
| Tokens inexistentes usados por paginas | P1 | `PlaybackPage.qml`, `LyricsPage.qml`, `SyncedLyricsView.qml`, `LyricsSearchDialog.qml` | Agregar tokens o reemplazar referencias a `MichiTheme.colors.onError`, `MichiTheme.colors.accent`, `MichiTheme.typography.captionSize`. |
| Accesibilidad estructural casi ausente | P1 | Shell, componentes, paginas | Crear contrato de `Accessible.name`, `Accessible.description`, `Accessible.role` para botones, sidebar, tabs, listas, cards y controles de reproduccion. |
| Controles custom no son navegables por teclado de forma consistente | P1 | `MichiIconButton.qml`, `SidebarItem.qml`, `SongRow.qml`, album views, cards | Migrar interacciones primarias a controles focusables o agregar foco, teclas Enter/Space y roles accesibles. |
| Iconografia mixta: imagenes, glifos, letras y Unicode | P1 | `Sidebar.qml`, `IconSlot.qml`, `ExpandedNowPlayingPanel.qml`, `ToastHost.qml`, `PlaylistDetailPage.qml`, `SyncedLyricsView.qml` | Establecer iconografia canonica monocromatica y eliminar texto/Unicode como icono principal. |
| Responsive basado en medidas fijas | P1 | `LibraryPage.qml`, album views, `CommandPalette.qml`, `HomePage.qml`, `PlaybackPage.qml` | Introducir breakpoints/tokens de layout y reglas compact/regular/large. |
| Reduced motion no existe como contrato | P2 | `MichiMotion.qml`, `Sidebar.qml`, `PageStack.qml`, `MichiProgressBar.qml`, `SyncedLyricsView.qml` | Agregar token/flag de reduced motion y desactivar animaciones no esenciales. |
| Estados loading/empty/error/unavailable no son canonicos | P2 | `PageStack.qml`, `SongTable.qml`, `AlbumGrid.qml`, `RadioPage.qml`, `SmartTaggingPage.qml`, `PlaybackPage.qml` | Convertir `EmptyState`, error banners y progress/status en componentes canonicos. |
| Hardcoded colors fuera del theme | P2 | Componentes/materials/shell | Mover `Qt.rgba(...)` repetidos a `MichiColors` como tokens semanticos. |
| Context menu custom incompleto | P2 | `SongContextMenu.qml`, `SongTable.qml` | Unificar menu contextual con foco, Escape, dismissal, disabled states y posicionamiento seguro. |

## Problemas globales

| Problema | Severidad | Solucion recomendada | Componentes afectados | Esfuerzo | Riesgo funcional |
|---|---|---|---|---:|---|
| Theme insuficiente para UI productiva | P1 | Agregar tokens de control size, icon size, hit target, focus ring, disabled text, hover layers, breakpoints y density. | `MichiTheme`, `MichiColors`, `MichiSpacing`, `MichiTypography`, `MichiMotion` | M | Bajo |
| 38 usos de `Qt.rgba` fuera de `MichiColors.qml` | P2 | Promoverlos a tokens semanticos: `surfaceHover`, `surfacePressed`, `trackBg`, `dangerSubtle`, `glassHighlight`. | `MichiButton`, `MichiIconButton`, `GlassMaterial`, `ToastHost`, sliders | M | Bajo |
| 294 medidas numericas directas detectadas | P2 | Normalizar medidas repetidas y conservar hardcodes solo cuando sean formato fijo justificado. | Shell, pages, components | L | Medio |
| `MouseArea` usado como control principal en 50 ocurrencias | P1 | Envolver con `Control`/`Button` o agregar `activeFocusOnTab`, `Keys`, `Accessible.role` y estados focus/pressed. | Cards, sidebar, song rows, album views, seek/volume | L | Medio |
| Tooltips parciales | P3 | Hacer que `MichiIconButton`, controles disabled y acciones destructivas expongan tooltip/description consistente. | Now Playing, Assistant, Sidebar, cards | S | Bajo |
| Empty states duplicados | P2 | Reutilizar `EmptyState.qml` con icon source, title, body, primary/secondary action. | Library, AlbumGrid, ArtistList, FolderBrowser, Metadata, Radio, Devices | M | Bajo |
| Badges duplicados | P3 | Elegir `StatusBadge` como canonico y retirar/absorber `MichiBadge` si no aporta variante distinta. | `StatusBadge`, `MichiBadge` | S | Bajo |
| Album views visualmente fragmentadas | P2 | Compartir `AlbumTile`, `AlbumPlaceholder`, `AlbumMetaText` y estados empty/loading. | `AlbumGridView`, `AlbumCoverFlowView`, `AlbumVinylWallView`, `AlbumTimelineView`, `AlbumMagazineView` | M | Medio |
| HiDPI no esta sistematizado | P2 | Definir escala UI o depender explicitamente de Qt scaling, revisar icon assets y hit targets. | Todo QML | M | Medio |

## Inconsistencias especificas

| Categoria | Ejemplos | Severidad | Recomendacion |
|---|---|---|---|
| Botones | `MichiButton`, `MichiIconButton`, `Button` nativo en Lyrics, `MouseArea` sobre rectangulos | P2 | Centralizar variantes y evitar mezclar botones nativos sin estilo Michi. |
| Tipografia | `captionSize` usado pero no definido; `FontWeight.*` mezclado con `MichiTheme.typography.weight*` | P1 | Completar escala tipografica y exigir uso de tokens. |
| Espaciado | `spacing: 2`, `spacing: 3`, `height: 24`, `width: 220`, `height: 140` repetidos | P2 | Mover a tokens o componentes canonicos. |
| Iconos | Glifos de sidebar `IN`, `BL`, `MX`; `[X]`; `\u25C0\u25B6`; `<<`, `>>` | P1 | Usar iconos monocromaticos o `MichiIconButton` con icon source canonico. |
| Glass/smoked | `GlassMaterial`, `GlassCard`, `HeroMaterial` conviven con `Rectangle` directos | P2 | Definir que tipo de superficie usa cada patron: page hero, panel, card, popup, toolbar. |
| Estados backend | `No disponible`, `Safe mode`, `Servicio no disponible`, `Experimental`, `Interfaz clasica disponible` | P2 | Crear lenguaje comun para unavailable/disabled/experimental. |
| Foco | Pocos controles tienen focus ring visible; custom cards no son tab-focusables | P1 | Focus ring canonico y orden de tab por pagina. |

## Problemas por pagina

| Pagina | Estado actual | Problemas | Severidad | Solucion recomendada | Riesgo funcional |
|---|---|---|---|---|---|
| `Main.qml` | Ventana limpia, experimental | Minimo 1024x640 contradice 800x600; titulo sigue diciendo experimental | P1 | Definir matriz responsive real y copy de producto segun canal | Bajo |
| `AppShell.qml` | Shell funcional | Sidebar fijo 250; NowPlaying 100 fijo; drop area invisible sin feedback | P2 | Breakpoints compactos y feedback visual de drag/drop | Medio |
| `HeaderBar.qml` | Sencillo y sobrio | Search width 25%; status "Experimental" permanente; sin responsive compacto | P2 | Header variants: compact, regular, wide | Bajo |
| `Sidebar.qml` | Navegacion clara | Glifos fallback, collapse sin accesibilidad, ancho animado sin reduced motion | P1 | SidebarItem accesible, iconos canonicos, reduced motion | Medio |
| `NowPlayingBar.qml` | Fuerte identidad musical | Distribucion porcentual fragile; boton pequeno 22 px; falta accessible/keyboard | P1 | Convertir controles a canonicos focusables y validar layout compact | Medio |
| `PlaybackPage.qml` | Funcional y bastante completa | Tokens inexistentes; cola/historial densos; controles no accesibles | P1 | Reparar tokens, panelizar queue/history, teclado | Medio |
| `LibraryPage.qml` | Core productivo avanzado | Toolbar apretada en ancho pequeno; tabs custom repetidos; botones no reflow | P1 | Toolbar responsive y tabs canonicas | Medio |
| `SongTable.qml` | Tabla util y densa | Columnas porcentuales no adaptan; context menu custom; empty state duplicado | P1 | Tabla con columnas min/max y menu accesible | Alto |
| `AlbumGridView.qml` | Funcional, basico | Placeholder por iniciales, cell size fijo, no empty/loading | P2 | Usar AlbumTile canonico y responsive grid | Medio |
| `AlbumCoverFlowView.qml` | Visualmente diferenciado | Path fijo, motion sin reduced mode, baja densidad en ventanas pequenas | P2 | Convertir en vista opcional con fallback grid/list | Medio |
| `AlbumVinylWallView.qml` | Concepto atractivo | Vinilo placeholder hardcoded; no caratulas reales en delegate | P2 | Compartir portada/caratula y tokens de album art | Medio |
| `AlbumTimelineView.qml` | Buena idea para discografia | Secciones y filas demasiado basicas; no keyboard selection | P3 | Refinar como vista lista cronologica canonica | Bajo |
| `AlbumMagazineView.qml` | Lista editorial compacta | Alternancia por index; no card semantics; layout fijo | P3 | Unificar con list card canonica | Bajo |
| `AlbumDetailPage.qml` | Detalle simple | Header horizontal no reflow; `SongTable` altura fija 400 | P2 | Header responsive y tabla con fill/available height | Medio |
| `ArtistDetailPage.qml` | Detalle simple | Grid no interactivo, altura calculada por 3 columnas fijas, tabla 300 fija | P2 | Breakpoints y componente detail header compartido | Medio |
| `PlaylistsPage.qml` | Base funcional | `+ Nueva playlist` usa texto como icono; cards Flow sin empty canonico | P2 | Acciones canonicas, empty state y grid responsive | Medio |
| `MetadataInspectorPage.qml` | Flujo real parcial | Empty custom, labels 60 px, TextField nativo sin estilo Michi, copy experimental fuerte | P2 | Form rows canonicas y InputMaterial/MichiTextField | Medio |
| `SmartTaggingPage.qml` | Prototipo funcional | Simulado en apply, filas porcentuales, status disperso | P2 | Estados honestos: unavailable, pending, result; no prometer funcionalidad | Medio |
| `LyricsPage.qml` | Flujo util | Usa `captionSize` inexistente; mezcla `Button` nativo; empty/error custom | P1 | Tokens correctos y MichiButton/EmptyState | Bajo |
| `RadioPage.qml` | Base clara | Add station con SearchField como input generico; ListView height fija 400 | P2 | Input canonico, estados empty/search/loading | Medio |
| `MixHubPage.qml` | Limpio pero corto | Grid de 2 columnas fijo; depende de categorias sin empty | P3 | Empty/loading y responsive 1/2/3 columnas | Bajo |
| `SettingsPage.qml` | Navegacion basica | Parece indice/prototipo; cards duplicadas y status clasico | P3 | Agrupar secciones y diferenciar settings reales vs legacy | Bajo |
| `AudioLabPage.qml` | Bastante completa visualmente | Muchas cards 2 columnas fijas y badges "Funcional" superpuestos | P2 | Tool grid responsive y status placement canonico | Medio |
| `DevicesPage.qml` | Correcta, sobria | Empty text plano; falta unavailable state si bridge no existe | P2 | EmptyState y backend unavailable panel | Bajo |
| `ConnectionsPage.qml` | Coherente con ecosistema | Grid 2 columnas fijo; empty text dentro de Grid puede no mostrarse confiablemente | P2 | Responsive grid y empty externo al repeater/grid | Medio |
| `HomeAudioPage.qml` | Identidad clara | "concept"/experimental visible; modo selector fijo; devices empty plano | P2 | Estados honestos y responsive mode selector | Medio |

## Accesibilidad

Solo se encontraron cuatro usos de `Accessible.*`, todos en `NowPlayingVolume.qml`. No hay un contrato consistente de:

- `Accessible.role` para botones, menu items, tabs, sliders, sidebar items, cards clickeables y rows.
- `Accessible.name` para icon-only buttons.
- `Accessible.description` para disabled/unavailable states.
- Orden de tab y foco visible en listas, cards, album views y sidebar.
- Atajos anunciables para acciones clave.

Accion recomendada: antes del pulido visual fino, convertir `MichiButton`, `MichiIconButton`, `FilterChip`, `SidebarItem`, `SongRow`, album tiles y cards interactivas en componentes focusables con roles y nombres.

## Responsive, 4K y HiDPI

El layout funciona mejor entre 1280x720 y 1920x1080. Por debajo de 1024 px hay bloqueo formal en `Main.qml`. En 2560/3840 px la UI no rompe, pero puede verse demasiado pequena porque la escala tipografica usa `font.pixelSize` fijo y no hay density/scale tokens. En HiDPI, Qt puede escalar la escena, pero la app no declara una estrategia propia para 125%, 150% y 200%.

Acciones recomendadas:

1. Crear breakpoints `compact`, `regular`, `wide`, `ultra`.
2. Definir tokens de hit target: 32, 36, 40, 44 px segun densidad.
3. Definir escala tipografica/density que no dependa del viewport.
4. Revisar icon assets raster (`nowplaying_clean/*.png`) para nitidez en 150%/200%.

## Reduced motion

`MichiMotion.qml` define duraciones, pero no hay flag global de reduced motion. Las animaciones actuales son moderadas, pero deben poder desactivarse:

- `Sidebar.qml`: width animation.
- `PageStack.qml`: opacity transition.
- `GlassMaterial.qml`: color/border animations.
- `ExpandedNowPlayingPanel.qml`: height animation.
- `MichiProgressBar.qml`: indeterminate infinite animation.
- `SyncedLyricsView.qml`: color/font animation y auto-scroll periodico.

## Estado final recomendado

No redisenar desde cero. La ruta correcta es consolidar:

1. Tokens de design system.
2. Componentes base accesibles.
3. Responsive shell.
4. Biblioteca y playback.
5. Workflows avanzados.
6. Estados y pulido final.

Con esa secuencia, la UI puede pasar de alpha visual avanzada a candidata alpha.2 pulida sin interferir con la migracion funcional.
