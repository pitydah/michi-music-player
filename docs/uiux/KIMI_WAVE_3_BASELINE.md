# Kimi Wave 3 — Visual Baseline

## Estado del repositorio

- SHA inicial: `ec6a73fc45df2fa8da9b2a9d4d23b9a3ab7a0584`
- Rama: `refactor/premium-ui-wave-3-kimi` (creada desde wave-2 HEAD)
- Archivos QML: 452
- Componentes: 110 en `ui_qml/components/`
- Páginas: 292 en `ui_qml/pages/`
- Runtime: READY con 49 servicios, 44 context properties, 0 warnings, 0 errors

## Lo que GLM ya resolvió correctamente (NO tocar)

1. **PageStack 2.0** — doble buffer, transiciones 160ms, retry, loading threshold 120ms
2. **Now Playing 2.0** — tres modos (desktop/medium/compact) con alturas via tokens
3. **Visual tokens** — nowPlaying, pageSurfaceInset, controlHeight, tableRowHeight, reducedMotion
4. **P0 runtime** — ReferenceError, Accessible.Panel, Accessible en Dialog, anchors en Layout, deprecated parameter injection
5. **HomeBridge** — loading/ready/errorMessage/hasLibrary properties
6. **CapabilityBridge** — BRIDGE_ALIASES, state() method
7. **AudioBackupPage** — página unificada CD+ADC con progreso y cancel
8. **NotificationCenter** — Timer auto-close, HoverHandler, dedup, dismiss-by-id
9. **Accessible roles** — 25 instancias corregidas a Qt6 válidos
10. **EQ route** — registrado correctamente en route_registry
11. **Home dashboard** — datos reales del bridge, LibraryStatusCard, EcosystemCard
12. **Library** — filtros, multi-selección, menú contextual, SelectionBar
13. **Global search** — debounce, grupos de resultados

## Defectos visuales pendientes (mejora demostrable)

### A. Design System — inconsistencias encontradas
- **GlassCard vs MichiCard**: coexisten como sistemas paralelos. GlassCard tiene 47 archivos/130 instancias. MichiCard tiene 4. Debe mantenerse compatibilidad pero evitar nuevas instancias de GlassCard.
- **GlassMaterial sobre-uso**: usado en HomeHero, loading cards, empty states donde bastaría una superficie simple. Debe reservarse para: sidebar, now playing, popups, overlays, hero.
- **Border luminosos**: demasiados elementos con `border.width: 1` y `border.color` que crean efecto "luminous frame" en superficies que deberían ser limpias.
- **Números mágicos**: muchas páginas usan hardcoded heights/widths/spacing en vez de tokens de MichiTheme.

### B. Shell y navegación — problemas responsive y jerarquía
- **Header breadcrumbs**: sin compactación para rutas profundas (4+ niveles).
- **Sidebar flyouts**: en modo compact, los sub-items no se muestran como flyout sino que quedan ocultos permanentemente.
- **PageStack inset**: el PageSurface tiene `anchors.margins` fijo en desktop pero no respeta `pageSurfaceInset` token.
- **Títulos duplicados**: HomePage y LibraryPage muestran el título de la sección tanto en HeaderBar como en el contenido de la página.
- **Focus restoration**: al volver de una sub-página, el foco no regresa al elemento que activó la navegación.

### C. Now Playing — refinamientos posibles
- **Transporte centrado**: no está centrado respecto al viewport sino respecto al espacio sobrante entre metadata y utilities.
- **Carátula pequeña**: 48px en desktop, debería ser 68-72px.
- **Volumen invasivo**: el control de volumen ocupa mucho espacio horizontal incluso cuando no se usa.
- **Sin pista**: el estado "Sin reproducción" no tiene una acción útil (navegar a biblioteca).
- **Tooltips faltantes**: botones de utilidades sin tooltips explicativos.

### D. Home — secciones genéricas
- **Todas las cards son idénticas**: Recién añadido, Favoritos, Sin reproducir, Mixes usan el mismo componente GlassCard con la misma altura y jerarquía. Debería haber variedad: una card grande para continuar escuchando, shelves horizontales para contenido.
- **Sin contenido dinámico**: las cards de "Recién añadido" y "Favoritos" navegan a rutas pero no muestran contenido real (número de elementos, carátulas).
- **EcosystemCard muy técnico**: muestra estados de servicios en vez de "tu ecosistema está listo" de forma amigable.
- **Empty state muy complejo**: dos CTAs (Añadir carpeta + Conectar servidor) compitiendo por atención.

### E. Biblioteca — pulir densidad y claridad
- **Tabla de canciones**: encabezado de tabla usa `Text` plano sin estilo de columna. Filas no tienen altura consistente (algunas usan hardcoded values).
- **Filtros**: el toolbar de filtros tiene botones que se comprimen demasiado en 1024px.
- **Menú contextual**: usa `MichiMenu` con items que no tienen iconos, solo texto.
- **Card de álbumes**: la vista grid usa `AlbumCard` con información mínima (título + artista). Debería mostrar año y número de pistas.

### F. Hubs y módulos del ecosistema — demasiados placeholders
- **Streaming**: `PodcastsPlaceholderPage.qml` es un placeholder completo sin funcionalidad.
- **Conexiones**: muchas tarjetas de conexión tienen botones "Conectar" que no están conectados a ningún servicio real (la conexión se hace desde Settings).
- **Home Audio**: algunas tarjetas muestran "capacidades" que son placeholders (`ChainPlannerPlaceholderPage.qml`).
- **Sync Suite**: `SyncPlansPlaceholderPage.qml`, `SyncHistoryPlaceholderPage.qml`, `PortablePlayersPlaceholderPage.qml` son placeholders sin backend.

### G. Audio Lab — experiencia técnica sin pulir
- **AudioAnalysisPage**: tiene una barra de progreso inline pero no usa el componente JobProgressCard estándar.
- **AudioConversionPage**: usa `MichiCard` para resultados pero no tiene estado de "conversión completada" claro.
- **ComparisonPanel**: comparación A/B sin estilo visual para diferencias (debería destacar coincidencias/diferencias con color).
- **Resultados**: no hay acción para "guardar resultado" o "exportar reporte".

### H. Playlists — funcionalidad con UI mejorable
- **PlaylistEditorDialog**: el diálogo no tiene scroll para descripciones largas.
- **PlaylistDetailPage**: la lista de pistas no tiene drag-reorder visual (drag indicator).
- **SmartPlaylistEditor**: las reglas visuales son compactas pero no muestran preview en tiempo real.

### I. Responsive — problemas por resolución
- **800x600**: Now Playing overflow, Sidebar demasiado ancho, tabla de canciones corta columnas.
- **1024x768**: Home dashboard con 2 columnas muy anchas, filtros de biblioteca comprimidos.
- **3840x2160**: texto muy pequeño (sin escalado DPI), carátulas pequeñas para pantalla grande.

### J. Microinteracciones — finales pero mejorables
- **Hover**: demasiados elementos con color change pero sin `Behavior` animation.
- **Pressed**: algunos botones no tienen estado pressed visual.
- **Focus**: focus ring existe pero no siempre visible en items de lista.
- **Transitions**: algunas páginas tienen `Loader` sin transición de opacidad.

## Elementos ya correctos por GLM (no necesitan cambio)

- Página de Settings (transacciones completas)
- NavigationBridge (pending settings guard, deep link protection)
- Route registry (98 rutas, aliases correctos, params validation)
- NotificationCenter (Timer, HoverHandler, dedup)
- Home dashboard states (loading/ready/error/empty)
- Library models (TrackListModel, AlbumListModel, filtered queries)
- Bridge DI (home_audio, snapcast, settings, navigation)
- Página de Settings transactional (commit/rollback)
- EQ route registrado
- Runtime warning gate tests

## Funciones realmente pendientes

1. **PodcastsPlaceholderPage** — placeholder sin contenido, debe mostrar estado vacío útil
2. **ChainPlannerPlaceholderPage** — placeholder sin contenido
3. **SyncPlansPlaceholderPage** — placeholder sin contenido
4. **SyncHistoryPlaceholderPage** — placeholder sin contenido
5. **PortablePlayersPlaceholderPage** — placeholder sin contenido
6. **Conexiones Connect buttons** — no conectados a servicio real
7. **ComparisonPanel A/B styling** — sin diferencia visual para coincidencias
8. **Export de resultados Audio Lab** — sin acción de guardar/exportar
9. **Drag reorder playlists** — sin indicador visual de drag

## Acciones para wave 3

1. Pulir design system (deprecar GlassCard en nuevas instancias, reducir GlassMaterial, eliminar números mágicos)
2. Mejorar shell (breadcrumbs compactación, sidebar flyouts, PageSurface inset, títulos no duplicados, focus restoration)
3. Refinar Now Playing (centrado real, carátula más grande, volumen compacto, tooltips, empty state acción)
4. Mejorar Home (shelves horizontales, contenido dinámico, ecosistema amigable)
5. Pulir Biblioteca (tabla con altura consistente, toolbar responsive, menú contextual con iconos)
6. Reemplazar placeholders con estados vacíos útiles (Podcasts, Chain Planner, Sync Suite)
7. Pulir Audio Lab (JobProgressCard estándar, estado completado, comparación visual)
8. Mejorar Playlists (scroll en dialog, drag indicator)
9. Fix responsive (800x600, 1024x768, 3840x2160)
10. Microinteracciones (hover/pressed/focus con Behavior, transitions en Loader)
11. Commit por commit con verificación runtime + tests después de cada cambio
