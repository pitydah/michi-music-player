# Auditoría UI/UX — Michi Music Player (QML)

**Fecha:** 2026-07-30 · **Fase:** TRABAJO B · **Ejecutor:** sdd-explore  
**Alcance:** `ui_qml/` + `ui_qml_bridge/route_registry.py`  
**Modo:** Solo lectura — no se modificó ningún archivo.

---

## 1. Inventario de Rutas (`route_registry.py`)

**Total de rutas registradas:** 99  
**Rutas visibles en sidebar:** 35  
**Archivos QML:** 453 en `ui_qml/`

### Distribución por dominio (top-level)

| Grupo | Rutas | En sidebar | Estado |
|-------|-------|-----------|--------|
| `library` | 23 | 5 | La mayoría `functional` |
| `audio_lab` | 20 | 6 | Mix: `functional`, `experimental` |
| `settings` | 8 | 1 | Todas `functional` |
| `connections` | 7 | 6 | Mix: `functional`, `planned`, `configuration_required` |
| `home_audio` | 7 | 4 | `functional` + `partial` + 1 `removed` |
| `sync` | 5 | 5 | 3 de 5 son `planned` |
| `streaming` | 3 | 3 | 1 `planned` (podcasts) |
| `mix` | 5 (total mix_*) | 1 | `functional` |
| `playlists` | 2 (total playlist_*) | 1 | `functional` |
| **Otros (singleton)** | 19 | 5 | `home`, `michi_ai`, `eq`, `search`, `nowplaying`, `placeholders`, etc. |

### Estados de ruta
- `functional`: amplia mayoría
- `planned`: 6 (big_server, jellyfin, navidrome, podcasts, sync.plans, sync.portable_players, sync.history)
- `partial`: 3 (streaming, home_audio.distribution, home_audio.rooms)
- `experimental`: 2 (audio_lab.adc_recorder, audio_lab.capture)
- `configuration_required`: 1 (home_assistant)
- `removed`: 1 (home_audio.chain_planner)
- `deprecated`: 1 (`placeholder`)

### ⚠️ Rutas duplicadas
- **`nowplaying` y `playback`** apuntan al MISMO source: `../pages/nowplaying/NowPlayingPage.qml`. Dos entradas idénticas.
- **`audio_lab.analysis` y `audio_lab.diagnostics`** ambos usan `AudioAnalysisPage.qml` (mismo source).
- **`audio_lab.identifier` y `audio_lab.metadata`** comparten `MetadataInspectorPage.qml`.
- **`library.track_detail` y `library.songs`** ambos a `TracksPage.qml`.
- **`library.folder_detail` y `library.folders`** ambos a `FolderBrowserPage.qml`.

---

## 2. Detección de Duplicaciones (Componentes UI)

### 2.1 Search Fields — 3 variantes

| Componente | Ubicación | Usos |
|------------|-----------|------|
| `MichiSearchField` | `ui_qml/components/` | ~30 usos en header, radio, settings, library, search |
| `SearchField` | `ui_qml/components/` | 1 uso (`GlobalSearchPage.qml`) |
| `LibrarySearchField` | `ui_qml/pages/library/` | Dominio específico |

**Problema:** `MichiSearchField` y `SearchField` son implementaciones DIFERENTES (distintos imports, distinta API: `controlObjectName` vs `searchRequested`). `SearchField` importa `../materials`, `MichiSearchField` no. Esto es fragmentación innecesaria.

**Acción:** Unificar en `MichiSearchField`. Eliminar `SearchField.qml`. `LibrarySearchField` puede envolver `MichiSearchField` si realmente tiene lógica distinta.

### 2.2 Estados Vacíos / Error / Loading — 3 capas de duplicación

```
ui_qml/components/EmptyState.qml          → wrappea states/MichiEmptyState
ui_qml/components/ErrorState.qml           → wrappea states/MichiErrorState
ui_qml/components/LoadingState.qml         → wrappea states/MichiLoadingState
ui_qml/components/UnavailableState.qml     → wrappea states/MichiUnavailableState

ui_qml/components/states/MichiEmptyState.qml       ← CANÓNICO
ui_qml/components/states/MichiErrorState.qml        ← extiende MichiEmptyState
ui_qml/components/states/MichiLoadingState.qml      ← extiende MichiEmptyState
ui_qml/components/states/MichiUnavailableState.qml  ← extiende MichiEmptyState

ui_qml/components/MichiEmptyStateStandard.qml  ← OTRO componente vacío separado

# Domain-specific (no usan el canónico):
ui_qml/pages/library/LibraryEmptyState.qml
ui_qml/pages/library/LibraryErrorState.qml
ui_qml/pages/library/album/components/AlbumEmptyState.qml
ui_qml/pages/queue/QueueEmptyState.qml
```

**Problema:** Hay wrappers que wrappean wrappers. `EmptyState.qml` (en `components/`) solo existe para re-exportar `states/MichiEmptyState`. Los domain-specific NO heredan del canónico.

**Acción:** 
1. Eliminar wrappers de `components/` (`EmptyState.qml`, `ErrorState.qml`, `LoadingState.qml`, `UnavailableState.qml`)
2. Migrar usos directos a `states/Michi*`
3. Hacer que `LibraryEmptyState`, `QueueEmptyState`, etc. extiendan `states/MichiEmptyState` en lugar de implementar desde cero

### 2.3 Diálogos de Confirmación — 5+ variantes

| Componente | Ubicación |
|------------|-----------|
| `ConfirmationDialog` | `ui_qml/components/` |
| `ConfirmActionDialog` | `ui_qml/components/` |
| `DestructiveActionDialog` | `ui_qml/components/` |
| `BaseDialog` | `ui_qml/components/dialogs/` |
| `ConfirmDialog` | `ui_qml/components/dialogs/` |
| `DestructiveDialog` | `ui_qml/components/dialogs/` |
| `AssistantConfirmationDialog` | `ui_qml/pages/assistant/` |

**Problema:** Dos sistemas de diálogos coexisten: los planos en `components/` y los estructurados en `components/dialogs/`. El sistema `dialogs/` (BaseDialog → ConfirmDialog/DestructiveDialog) es más limpio pero NO se usa en producción (0 usos detectados en páginas reales).

**Acción:** Adoptar `dialogs/` como canónico, migrar todos los usos de `ConfirmationDialog` y `DestructiveActionDialog` a `ConfirmDialog` y `DestructiveDialog`. Eliminar los planos.

### 2.4 Badges de Estado — 3 componentes

| Componente | Dónde se usa |
|------------|-------------|
| `StatusBadge` | `PageHeader`, `DiscoveryResultCard`, `FeatureStatePage`, `NotificationCenter` |
| `ConnectionStatusBadge` | Solo definido, ¿sin uso detectado en páginas? |
| `ServiceHealthBadge` | Solo definido |

**Acción:** Unificar. `StatusBadge` cubre el 90% de los casos con `kind`. `ConnectionStatusBadge` y `ServiceHealthBadge` pueden ser variantes de `StatusBadge`.

### 2.5 Notificaciones — 4 componentes

| Componente | Rol |
|------------|-----|
| `NotificationToast` | Toast flotante |
| `NotificationBanner` | Banner inline |
| `NotificationAnnouncement` | Anuncio accesible (aria) |
| `MichiToast` | Toast alternativo |

`NotificationAnnouncement` es diferente (accesibilidad), está bien. Pero `NotificationToast` y `MichiToast` parecen redundantes.

### 2.6 Cards y Paneles — superposición

| Componente | Dónde |
|------------|-------|
| `GlassCard` | `ui_qml/components/` |
| `GlassPanel` | `ui_qml/components/` |
| `HeroPanel` | `ui_qml/components/` |
| `MichiCard` | `ui_qml/components/` |
| `MichiPanel` | `ui_qml/components/` |
| `MichiFeatureCard` | `ui_qml/components/` |

**Problema:** `GlassCard` y `MichiCard` compiten. `GlassPanel` y `MichiPanel` compiten. Los materiales (`GlassMaterial`, `HeroMaterial`) están en `ui_qml/materials/` pero se usan inconsistentemente.

**Acción:** Deprecar `GlassCard`/`GlassPanel`/`HeroPanel` a favor de `MichiCard`/`MichiPanel`/`MichiFeatureCard` + materiales. O viceversa — pero NO ambos.

### 2.7 NowPlaying — 2 fuentes

| Ruta | Source |
|------|--------|
| `nowplaying` | `pages/nowplaying/NowPlayingPage.qml` |
| `playback` | `pages/nowplaying/NowPlayingPage.qml` (mismo archivo) |

**Acción:** Eliminar la ruta `playback` del registro. Mantener solo `nowplaying`.

---

## 3. Valores Hardcodeados

### 3.1 Colores fuera del theme

```
Total: 41 ocurrencias de Qt.rgba(...) o #XXXXXX fuera de archivos de theme
```

Estos 41 colores están dispersos en ~20 archivos QML de páginas y componentes. La mayoría son fondos, bordes y acentos que deberían ser tokens.

### 3.2 Tamaños en píxeles hardcodeados

Ejemplos detectados (parcial):
- `height: 200`, `height: 180`, `height: 320`, `height: 154`
- `width: 200; height: 200` (MobilePairingPage)
- `sourceSize.height: 320`, `sourceSize.height: 128`

Estos NO usan `MichiTheme.spacing` ni `MichiTheme.breakpoints`.

---

## 4. Propuesta de Arquitectura de Información

### Situación actual: sidebar con 35 ítems, sin agrupación clara

El sidebar actual mezcla:
- Conexiones (6 ítems: big_server, home_assistant, jellyfin, micro_server, navidrome + hub)
- Audio Lab (6 ítems)
- Sync (5 ítems, 3 planned)
- Home Audio (4 ítems)
- Streaming (3 ítems)

Esto viola la ley de Miller (7±2). Un usuario no puede escanear 35 ítems eficientemente.

### Propuesta: 7 secciones lógicas (máximo 2 niveles)

```
🏠 INICIO
  ├── Inicio (home)                          ← Dashboard
  └── Búsqueda global (search)               ← Ctrl+K / atajo

📚 BIBLIOTECA
  ├── Canciones (library.songs)
  ├── Álbumes (library.albums)
  ├── Artistas (library.artists)
  ├── Carpetas (library.folders)
  ├── Colecciones (library.collections)       ← nuevo: NO en sidebar actual
  └── Playlists (playlists)

🎛️ REPRODUCCIÓN
  ├── Reproduciendo (nowplaying)
  ├── Cola (queue)
  ├── Ecualizador (eq)
  ├── Mix inteligente (mix)
  └── Historial (history)

🌐 ECOSISTEMA
  ├── Conexiones (connections)                ← hub, no ítems individuales
  ├── Home Audio (home_audio)                 ← hub
  ├── Sync (sync)                             ← hub
  ├── Streaming / Radio (streaming)           ← hub
  └── Michi AI (michi_ai)

🔧 HERRAMIENTAS
  ├── Audio Lab (audio_lab)                   ← hub central
  ├── Metadata editor (metadata.single)
  ├── Smart Tagging (tagging)
  └── Trabajos (jobs)

⚙️ SISTEMA
  └── Ajustes (settings)

📋 PLACEHOLDERS (ocultos por defecto)
  └── Rutas planned/experimental — visibles solo con feature flag
```

### Reglas de la IA propuesta:
1. **Sidebar: máximo 7 secciones, máximo 5 ítems por sección.**
2. **Hubs como primer nivel:** Conexiones, Home Audio, Sync, Audio Lab, Streaming → cada uno es un hub con navegación interna (tabs o sub-páginas), no ítems de sidebar.
3. **Rutas planned/experimental:** ocultas del sidebar por defecto. Visibles con toggle "Modo avanzado" o feature flags.
4. **Ruta `placeholder`:** eliminar del registro. Reemplazar con `UnavailableState` inline.
5. **Ruta `playback` duplicada:** eliminar.

---

## 5. Auditoría de Design Tokens

### 5.1 MichiColors.qml — 122 propiedades

| Categoría | Cantidad | Ejemplos |
|-----------|----------|----------|
| Fondos (bg/surface) | ~20 | `bgBase`, `bgCanvas`, `surfaceElevation0-5` |
| Texto | ~10 | `textPrimary`, `textSecondary`, `textMuted` |
| Acento (accent) | ~15 | `accentPrimary`, `accentHover`, `accentSoft` |
| Bordes | ~8 | `borderCard`, `borderInput`, `borderFocus` |
| Semánticos | ~15 | `success`, `warning`, `error`, `info` |
| Badges | ~12 | `badgeInfoBg`, `badgeActiveBg`, etc. |
| NowPlaying | ~20 | `nowPlayingBackground`, `nowPlayingThumb`, etc. |
| Sombras | ~4 | `shadowSoft`, `shadowFloating` |
| Skeleton | 2 | `skeletonBase`, `skeletonHighlight` |
| Aliases | ~10 | `surface`, `border`, `accentFaint` → apuntan a otras props |

**Evaluación:** Sistema robusto y bien organizado. Cubre la mayoría de necesidades. Las 41 ocurrencias de colores hardcodeados fuera del theme deberían migrarse a estos tokens.

**⚠️ Problema detectado:** Hay aliases al final (`surface`, `border`, `accentFaint`) que apuntan a otras propiedades. Esto crea dos nombres para el mismo color y confunde. O mantener los aliases Y eliminar los originales, o eliminar los aliases.

### 5.2 MichiTheme.qml — 89 propiedades (agregador)

Agrupa: `colors`, `typography`, `spacing`, `motion`, `radius`, `elevation`, `opacity`, `breakpoints`, `density`.

**Evaluación:** Buen agregador. Las páginas deben usar `MichiTheme.colors.xxx`, no `MichiColors.xxx`.

### 5.3 MichiTypography.qml — 17 propiedades

Fuentes escaladas con `scaled()`. Pesos: 300-700. Bien definido. Sin problemas.

### 5.4 MichiSpacing.qml — 9 propiedades

Escala: `xxs(2) → xs(4) → sm(8) → md(12) → lg(16) → xl(24) → xxl(32) → xxxl(48) → page(40)`.  
**⚠️ Inconsistencia:** `page(40)` es menor que `xxxl(48)` pero está al final. `page` debería ser `40` entre `xxl(32)` y `xxxl(48)`.

### 5.5 MichiMotion.qml — 18 propiedades

Duración: `instant(80) → fast(120) → normal(200) → slow(240)`. Easing curves definidas. Soporta `reducedMotion`. **Bien.**

### 5.6 MichiVisualQuality.qml — 0 propiedades `readonly`

Archivo existe pero sin tokens. Posiblemente placeholder. **Acción:** definir o eliminar.

### 5.7 MichiAccessibility.qml — 3 propiedades

Mínimo: `reduceMotion`, `highContrast`, `fontScale`. **Bien** para lo que necesita.

---

## 6. Componentes Canónicos (lista de referencia)

### Form Controls (✅ unificados bajo `Michi*`)
- `MichiButton` — botón principal
- `MichiIconButton` — botón solo ícono (20 usos en producción)
- `MichiTextField` — campo de texto
- `MichiSearchField` — búsqueda (CANÓNICO, reemplazar `SearchField`)
- `MichiComboBox` — dropdown
- `MichiCheckBox` — checkbox
- `MichiSwitch` — toggle
- `MichiRadioButton` — radio
- `MichiSlider` — slider estándar
- `MichiDoubleSpinBox` — spinner numérico
- `MichiWarmSlider` — slider nowplaying (warm palette)
- `MichiProgressBar` — progreso
- `MonoToggle` — toggle binario

### Superficie / Contenedores
- `MichiCard` (CANÓNICO — deprecar `GlassCard`)
- `MichiPanel` (CANÓNICO — deprecar `GlassPanel`)
- `MichiFeatureCard` — card con feature metadata
- `HeroPanel` — hero section (evaluar si `MichiPanel` con variante basta)
- `MichiDialog` — diálogo base
- `MichiPage` / `PageSurface` — páginas

### Estados (✅ canónicos en `states/`)
- `states/MichiEmptyState` — vacío
- `states/MichiErrorState` — error
- `states/MichiLoadingState` — carga
- `states/MichiUnavailableState` — no disponible
- `states/MichiSkeleton` — skeleton loading

### Diálogos (✅ canónicos en `dialogs/`)
- `dialogs/BaseDialog` → `dialogs/ConfirmDialog` / `dialogs/DestructiveDialog` / `dialogs/InputDialog`

### Navegación / Layout
- `SidebarItem` — ítem de sidebar
- `SidebarSection` — sección de sidebar
- `SectionHeader` — encabezado de sección
- `Breadcrumbs` — migas de pan
- `PageHeader` — encabezado de página
- `MichiPageHeader` — alternativo en `layout/` (⚠️ duplicado conceptual)
- `ResponsivePageLayout` — layout responsivo

### NowPlaying
- `NowPlayingBar` — barra inferior
- `NowPlayingTransport` — controles
- `NowPlayingVolume` — volumen
- `PlaybackProgress` — progreso

### Badges / Indicadores
- `StatusBadge` (CANÓNICO)
- `MichiBadge` (¿difiere de StatusBadge?)
- `ConnectionStatusBadge` → migrar a `StatusBadge`
- `ServiceHealthBadge` → migrar a `StatusBadge`
- `PlaybackQualityBadge`
- `TrackQualityBadge`

### Notificaciones
- `NotificationToast` — toast (CANÓNICO)
- `NotificationBanner` — banner inline
- `NotificationCenter` — centro de notificaciones
- `NotificationAnnouncement` — accesibilidad (correcto, no unificar)

### Feedback / Progreso
- `JobProgressCard` — tarjeta de progreso
- `JobStatusBanner` — banner de estado
- `InlineError` — error inline
- `InlineValidation` — validación inline
- `ErrorAnnouncement` — error accesible
- `CancellationBanner` / `CancellationState`

---

## 7. Orden de Prioridad de Migración

### 🔴 P1 — Crítico (integridad estructural)

| # | Acción | Impacto |
|---|--------|---------|
| 1 | Eliminar ruta `playback` duplicada del route_registry | Evita confusión de navegación |
| 2 | Unificar `MichiSearchField` y `SearchField` — eliminar `SearchField.qml` | 2 APIs distintas para lo mismo |
| 3 | Eliminar wrappers `EmptyState.qml`, `ErrorState.qml`, `LoadingState.qml`, `UnavailableState.qml` de `components/` | 4 archivos que solo wrappean `states/*` |
| 4 | Deprecar `GlassCard`/`GlassPanel` a favor de `MichiCard`/`MichiPanel` | Dos sistemas de superficie compitiendo |
| 5 | Unificar diálogos: migrar a `dialogs/ConfirmDialog` y `dialogs/DestructiveDialog` | 5+ variantes de diálogo |

### 🟡 P2 — Alto (experiencia de usuario)

| # | Acción | Impacto |
|---|--------|---------|
| 6 | Reducir sidebar de 35 a ~15 ítems (adoptar hubs) | Sidebar ilegible actualmente |
| 7 | Migrar 41 colores hardcodeados a tokens `MichiColors` | Consistencia visual |
| 8 | Unificar `StatusBadge` / `ConnectionStatusBadge` / `ServiceHealthBadge` | 3 badges para estados |
| 9 | Hacer que `LibraryEmptyState`, `QueueEmptyState`, `AlbumEmptyState` extiendan `MichiEmptyState` | Reutilización |
| 10 | Eliminar `MichiEmptyStateStandard` si es redundante con `MichiEmptyState` | Simplificación |

### 🟢 P3 — Medio (limpieza)

| # | Acción | Impacto |
|---|--------|---------|
| 11 | Renombrar `ConfirmationDialog` → deprecated, migrar usos a `dialogs/ConfirmDialog` | Legacy cleanup |
| 12 | Revisar `MichiPageHeader` vs `PageHeader` — ¿son duplicados? | Layout consistency |
| 13 | Corregir `MichiSpacing.page(40)` — reordenar entre `xxl(32)` y `xxxl(48)` | Consistencia de escala |
| 14 | Definir o eliminar `MichiVisualQuality.qml` | Placeholder vacío |
| 15 | Ocultar rutas `planned` del sidebar (toggle "Modo avanzado") | No mostrar features inexistentes |

### ⚪ P4 — Bajo (documentación)

| # | Acción | Impacto |
|---|--------|---------|
| 16 | Documentar `qmldir` con comentarios de uso | Onboarding |
| 17 | Agregar checklist de "antes de crear un componente nuevo" en AGENTS.md | Prevenir futura duplicación |

---

## 8. Métricas Clave

| Métrica | Valor Actual | Objetivo |
|---------|-------------|----------|
| Sidebar items visibles | 35 | ≤ 15 |
| Componentes de search | 3 | 1 |
| Componentes de empty state | 11 | 5 (canónicos + domain wrappers) |
| Componentes de diálogo | 7 | 4 (Base + Confirm + Destructive + Input) |
| Componentes de badge | 3 | 1 |
| Colores hardcodeados | 41 | 0 |
| Tokens de color definidos | 122 | 122 (suficiente) |
| Archivos QML totales | 453 | — (no es problema per se) |
| Rutas totales | 99 | — (no es problema, solo visibilidad) |
| Rutas planned en sidebar | 6 | 0 (sin feature flag) |

---

## 9. Notas para Implementación

1. **Cualquier cambio en `route_registry.py` requiere actualizar `NavigationBridge`** (validación de rutas).
2. **Eliminar componentes requiere `grep -rn` global** para asegurar cero usos residuales.
3. **La migración de colores a tokens** debe hacerse archivo por archivo, verificando que el token semántico correcto existe. Si no existe, crear el token ANTES de usarlo.
4. **La reducción del sidebar** es el cambio de mayor impacto visual. Hacerlo en un PR separado con screenshots.
5. **Las rutas `planned`** deben quedarse en el registro (para navegación programática) pero NO en el sidebar.
