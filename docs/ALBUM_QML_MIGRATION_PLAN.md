# PLAN MAESTRO: MIGRACIÓN BIBLIOTECA > ÁLBUMES A QML

> **Versión:** 1.0
> **Fecha:** 2026-07-16
> **Autor:** Arquitecto Principal
> **Estado:** Diseño aprobado — pendiente de implementación

---

## ÍNDICE

1. [RESUMEN EJECUTIVO](#1-resumen-ejecutivo)
2. [AUDITORÍA COMPLETA](#2-auditoría-completa)
3. [INVENTARIO DE COMPONENTES](#3-inventario-de-componentes)
4. [CONTRATO AlbumViewContract](#4-contrato-albumviewcontract)
5. [ARQUITECTURA DEFINITIVA](#5-arquitectura-definitiva)
6. [DISEÑO DE VISTAS](#6-diseño-de-vistas)
7. [RENDIMIENTO](#7-rendimiento)
8. [TESTING](#8-testing)
9. [ESTRATEGIA DE MIGRACIÓN](#9-estrategia-de-migración)
10. [ROADMAP COMPLETO](#10-roadmap-completo)
11. [MATRIZ DE RIESGOS](#11-matriz-de-riesgos)
12. [ESTIMACIONES](#12-estimaciones)
13. [INVESTIGACIÓN DE REFERENCIAS](#13-investigación-de-referencias)
    - [13.1 KDE Elisa — GridBrowserDelegate](#131-kde-elisa--gridbrowserdelegate)
    - [13.2 Qt PathView — Documentación Oficial](#132-qt-pathview--documentación-oficial)
    - [13.3 Nemo Mobile qmlmusicplayer — CoverFlow](#133-nemo-mobile-qmlmusicplayer--coverflow)
    - [13.4 KDE AudioTube — Hero y Secciones](#134-kde-audiotube--hero-y-secciones)
    - [13.5 Qt Quick Animations — Microinteracciones](#135-qt-quick-animations--microinteracciones)
    - [13.6 Matriz de Compatibilidad de Licencias](#136-matriz-de-compatibilidad-de-licencias)
    - [13.7 Declaración de Atribuciones por Archivo](#137-declaración-de-atribuciones-por-archivo)

---

## 1. RESUMEN EJECUTIVO

### Problema Detectado

Existen **dos sistemas paralelos e inconexos** para la visualización de álbumes:

| Sistema | Ubicación | Vistas | Estado |
|---------|-----------|--------|--------|
| **Legacy (conectado)** | `LibraryPage.qml` → `AlbumGridPage.qml` | Grid + Lista | ✅ Funcional, usa `CoverImage` real |
| **Nuevo (inconexo)** | `album/AlbumViewHost.qml` | Grid, CoverFlow, Vinyl, Timeline, Magazine | 🧪 Prototipos sin carátulas reales, no conectado a `LibraryPage` |

### Decisión Arquitectónica

**NO** se elimina el sistema legacy hasta que la Fase 3 demuestre paridad funcional.

**NO** se crean nuevos repositorios, modelos, bridges o controladores.

**SÍ** se integra `AlbumViewHost` en `LibraryPage`, reemplazando `AlbumGridPage`.

### Principios Rectores

1. Un único modelo: `AlbumListModel` (ya existe, 7 roles)
2. Una única caché de carátulas: `CoverBridge` + `CoverProviderBridge` (ya existen)
3. Un único bridge: `LibraryBridge` (ya existe, métodos album vía `library_bridge.py:562-620`)
4. Un único sistema de filtros/búsqueda: `LibraryBridge.search()`, `LibraryBridge.setFormatFilter()`, etc.
5. Un único sistema de reproducción: `LibraryBridge.playAlbum()`, `LibraryBridge.enqueueAlbum()`
6. Un único sistema de navegación: `NavigationBridge` + `RouteRegistry`
7. Cero lógica de negocio en QML
8. Cero duplicación de consultas SQL

---

## 2. AUDITORÍA COMPLETA

### 2.1 Modelos

#### `AlbumListModel` (`ui_qml/models/AlbumListModel.py:11`)
- **Tipo:** `BasePagedListModel` (hereda de `QAbstractListModel`)
- **Roles (7):** `albumKey`, `title`, `artist`, `year`, `trackCount`, `duration`, `coverKey`
- **Carga paginada:** `_fetch_count()` → `query_service.count_albums()`, `_fetch_page()` → `query_service.fetch_albums()`
- **Actualización:** `refresh(search, sort, asc)` — resetea el modelo
- **Props QML:** `totalCount`, `count`, `loading`, `error`
- **Uso actual:** Usado por `AlbumGridPage` (legacy conectado) y `AlbumViewHost` (nuevo inconexo)
- **✅ OK — se reutiliza sin cambios**

#### `AlbumDetailModel` (`ui_qml/models/AlbumDetailModel.py:13`)
- **Tipo:** `QAbstractListModel` (no paginado)
- **Roles (14):** trackNumber, title, artist, duration, trackId, trackUid, albumKey, genre, year, discNumber, format, coverKey, albumArtist, trackCount
- **Carga:** `load(album_key)` → `query_service.fetch_album_detail()`
- **✅ OK — se reutiliza sin cambios**

#### `AlbumGroup` (`library/album_repository.py:114`)
- **Propósito:** Agrupación en memoria para CoverFlow legacy
- **Estado:** Reemplazado por lógica SQL en `core/library/repositories/album_repository.py`
- **❌ Se elimina cuando CoverFlow legacy sea retirado**

#### `AlbumSummary` (`metadata/album_summary.py:6`)
- **Propósito:** Metadatos enriquecidos con 27 campos
- **Estado:** Usado por `AlbumInfoRepository` (LRU 200)
- **✅ Se reutiliza — solo para detalle de álbum**

#### `AlbumIdentity` (`library/album_identity.py:213`, `core/library/identity.py:30`)
- **Problema:** Dos definiciones paralelas
- **core/library/identity.py** (3 campos): `album_key`, `album_artist`, `album_title`
- **library/album_identity.py** (9 campos): versión completa con canonical/display, compilación, confidence
- **⚠️ Se unifica: se usa la versión de 9 campos y se elimina `core/library/identity.py`**

#### `AlbumQualitySummary` (`library/album_repository.py:64`)
- **12 campos:** formato dominante, calidad, sample rate, bit depth, mixed quality flags
- **✅ Se reutiliza en badges de vista**

#### `AlbumHealthSummary` (`library/album_repository.py:81`)
- **13 campos:** missing files, disc count, status (ok/warning/danger)
- **✅ Se reutiliza en badges de vista**

### 2.2 Repositorios

| Repositorio | Archivo | Estado | Decisión |
|------------|---------|--------|----------|
| `AlbumRepository` (in-memory) | `library/album_repository.py` | Legacy CoverFlow | ❌ Eliminar con CoverFlow legacy |
| `AlbumRepository` (SQL) | `core/library/repositories/album_repository.py` | Nuevo DI | ✅ REUTILIZAR |
| `LibraryDB.get_all(group_by=album)` | `library/library_db.py:649` | Legacy | ❌ Eliminar |
| `AlbumInfoRepository` (LRU) | `metadata/album_info_repository.py` | Caché metadata | ✅ REUTILIZAR |
| `CoverCache` (QQP) | `integrations/coverart/cover_cache.py` | Remote covers | ✅ REUTILIZAR |
| `ArtworkCache` (disk) | `library/artwork_cache.py` | Local covers | ✅ REUTILIZAR |

### 2.3 Servicios

| Servicio | Archivo | Estado | Decisión |
|----------|---------|--------|----------|
| `AlbumService` | `core/album_service.py` | Nuevo DI | ✅ REUTILIZAR |
| `AlbumQualityService` | `library/album_quality_service.py` | Legacy | ⚠️ Refactorizar si se usa |
| `AlbumDuplicateService` | `library/album_duplicate_service.py` | Legacy | ❌ No migrar |
| `CoverArtService` | `library/cover_art_service.py` | Legacy | ❌ No migrar (usar CoverBridge) |

### 2.4 Controladores

| Controlador | Archivo | Estado | Decisión |
|------------|---------|--------|----------|
| `AlbumController` (legacy) | `legacy_widgets/ui/controllers/album_controller.py` | QtWidgets | ❌ No migrar |
| `CoverFlowController` (legacy) | `legacy_widgets/ui/controllers/coverflow_controller.py` | QtWidgets | ❌ No migrar |
| `ExpandedController` (legacy) | `legacy_widgets/ui/controllers/expanded_controller.py` | QtWidgets | ❌ No migrar |

### 2.5 Bridges

| Bridge | Archivo | Métodos Álbum | Estado | Decisión |
|--------|---------|---------------|--------|----------|
| `LibraryBridge` | `ui_qml_bridge/library_bridge.py` | `getAlbumDetail`, `getAlbumTracks`, `playAlbum`, `enqueueAlbum`, `filterByAlbum`, `getArtistAlbums` | ✅ Funcional | REUTILIZAR, extender si es necesario |
| `CoverBridge` (QQP) | `ui_qml_bridge/cover_bridge.py` | `CoverKey` property, `paint()` | ✅ Funcional | REUTILIZAR |
| `CoverProviderBridge` | `ui_qml_bridge/cover_provider_bridge.py` | `requestCover`, `isCached`, `getFallbackGlyph` | ✅ Funcional | REUTILIZAR |
| `NavigationBridge` | `ui_qml_bridge/navigation_bridge.py` | `navigateWithParams("library.album_detail", ...)` | ✅ Funcional | REUTILIZAR |
| `RouteRegistryBridge` | `ui_qml_bridge/route_registry_bridge.py` | `getSource("library.albums")` | ✅ Funcional | ACTUALIZAR ruta |

### 2.6 Navegación

**Ruta actual para álbumes:** `"library.albums"` → `AlbumGridPage.qml` (legacy, grid+lista)
**Ruta para detalle:** `"library.album_detail"` → `AlbumDetailPage.qml`
**Ruta para artistas:** `"library.artists"` → `ArtistGridPage.qml`

**Flujo actual:**
```
Sidebar → "Biblioteca" → navigationBridge.navigate("library")
  → AppShell → pageStack.loadRoute("library")
  → PageStack Loader → LibraryPage.qml
  → LibraryPage → StackLayout tab[1] → AlbumGridPage (legacy 2 vistas)
```

**Cambio necesario:** `LibraryPage` tab[1] debe cargar `AlbumViewHost` con sus 5 vistas.

### 2.7 Carátulas

**Pipeline completo de carátula en QML:**

```
QML: CoverImage { coverKey: "abc123" }
  → CoverBridgeProxy.qml (Loader async)
  → CoverBridge (QQuickPaintedItem, Python)
  → _load_cover_image(key, size)
    → _COVER_CACHE (dict, max 256) [HIT → QImage]
    → _SHARED_DB → LibraryDB.get_album_art_cache(album_key) [mime, bytes]
    → Fallback: _make_fallback_pixmap() [gradiente + glyph]
  → paint() → QPainter.drawPixmap()
```

**Problema detectado:** `CoverProviderBridge` usa un `_cover_bridge` que es un `QObject()` vacío (bridge_factory.py:578), por lo que `get_cover_data_url()` nunca retorna datos reales. Esto NO afecta a `CoverBridge` (QQP) que funciona independientemente.

### 2.8 CoverFlow Legacy

**Archivo:** `library/coverflow.py` (stub de 3 líneas — reemplazado)
**Código original:** 1181 líneas en commit `ca4ac664`

**Lógica a conservar:**
- Selección de álbum (current_index + signals)
- Snap animation (posicionamiento continuo)
- Lazy loading de carátulas
- Physics timer con fricción (0.92) y spring clamp

**Lógica a reemplazar:**
- Todo el rendering QWidget (paint, QGraphicsView, QGraphicsPixmapItem)
- ReflectiveFloor (se hace con QML ShaderEffect o Rectangle)
- drawBackground con blur (QML FastBlur o GaussianBlur)
- El timer de 16ms se reemplaza por `SmoothedAnimation` de QML

### 2.9 Vistas QML Actuales (album/ subdirectorio)

| Vista | Archivo | Líneas | Delegado | Carátulas reales | Conectada |
|-------|---------|--------|----------|-------------------|-----------|
| Grid | `AlbumGridView.qml` | 80 | Glyph (fallback) | ❌ No | ❌ No |
| CoverFlow | `AlbumCoverFlowView.qml` | 67 | Glyph (fallback) | ❌ No | ❌ No |
| Vinyl Wall | `AlbumVinylWallView.qml` | 73 | Glyph (fallback) | ❌ No | ❌ No |
| Timeline | `AlbumTimelineView.qml` | 85 | Glyph (fallback) | ❌ No | ❌ No |
| Magazine | `AlbumMagazineView.qml` | 93 | Glyph (fallback) | ❌ No | ❌ No |
| Selector | `AlbumViewSelector.qml` | 34 | Botones | N/A | ❌ No |

**TODAS las vistas en `album/` carecen de carátulas reales y NO están conectadas al sistema.**

### 2.10 Vistas Legacy (conectadas)

| Vista | Archivo | Líneas | Delegado | Carátulas reales | Conectada |
|-------|---------|--------|----------|-------------------|-----------|
| Grid | `AlbumGridView.qml` (pages/library/) | 44 | `AlbumCard` | ✅ `CoverImage` | ✅ `LibraryPage tab[1]` |
| List | `AlbumListView.qml` | — | Row | ✅ `CoverImage` | ✅ `LibraryPage tab[1]` |
| Detail | `AlbumDetailPage.qml` | 182 | Cover + TrackList | ✅ `CoverImage` | ✅ `library.album_detail` |
| Card | `AlbumCard.qml` | 75 | Componente | ✅ `CoverImage` | ✅ Usado por grid legacy |

### 2.11 Tests Existentes

| Capa | Archivos | Tests | Cubre |
|------|----------|-------|-------|
| Modelo (AlbumRepository) | 4 | 37 | Build, grouping, identity, compilaciones |
| Servicio (AlbumService) | 6 | 40 | Play, queue, nav, calidad, cover |
| Controlador (AlbumController) | 7 | 65 | Acciones, resolución de identidad, duplicados |
| Vista/Diálogo (AlbumDetailView) | 4 | 32 | Render, señales, track lists, badges |
| Widget (CoverFlow) | 3 | 56 | Layout, API pública, interacción, teclado |
| QML (AlbumListModel) | 3 | 43 | Modelos paginados, roles, cancel/reset |

**NUEVOS tests necesarios:** Ver sección [8. Testing](#8-testing).

---

## 3. INVENTARIO DE COMPONENTES

| Componente | Archivo | Estado | Reutilizar | Reemplazar | Eliminar |
|-----------|---------|--------|------------|------------|----------|
| `AlbumListModel` | `ui_qml/models/AlbumListModel.py` | ✅ | ✅ | — | — |
| `AlbumDetailModel` | `ui_qml/models/AlbumDetailModel.py` | ✅ | ✅ | — | — |
| `BasePagedListModel` | `ui_qml/models/BasePagedListModel.py` | ✅ | ✅ | — | — |
| `AlbumRepository` (SQL) | `core/library/repositories/album_repository.py` | ✅ | ✅ | — | — |
| `AlbumRepository` (mem) | `library/album_repository.py` | 🧪 | — | — | ❌ Fase 4 |
| `AlbumIdentity` (9f) | `library/album_identity.py` | ✅ | ✅ | — | — |
| `AlbumIdentity` (3f) | `core/library/identity.py` | ⚠️ | — | ✅ unificar | ❌ Fase 3 |
| `AlbumSummary` | `metadata/album_summary.py` | ✅ | ✅ | — | — |
| `AlbumGroup` | `library/album_repository.py` | 🧪 | — | — | ❌ Fase 4 |
| `AlbumInfoRepository` | `metadata/album_info_repository.py` | ✅ | ✅ | — | — |
| `AlbumService` | `core/album_service.py` | ✅ | ✅ | — | — |
| `LibraryBridge` | `ui_qml_bridge/library_bridge.py` | ✅ | ✅ | — | — |
| `CoverBridge` | `ui_qml_bridge/cover_bridge.py` | ✅ | ✅ | — | — |
| `CoverProviderBridge` | `ui_qml_bridge/cover_provider_bridge.py` | ✅ | ✅ | — | — |
| `NavigationBridge` | `ui_qml_bridge/navigation_bridge.py` | ✅ | ✅ | — | — |
| `RouteRegistryBridge` | `ui_qml_bridge/route_registry_bridge.py` | ✅ | ✅ | — | — |
| `CoverFlowWidget` (legacy) | `library/coverflow.py` | ❌ Stub | — | ✅ PathView | ❌ Fase 4 |
| `CoverFlowController` | `legacy_widgets/ui/controllers/coverflow_controller.py` | ❌ Stub | — | — | ❌ Fase 4 |
| `AlbumController` (legacy) | `legacy_widgets/ui/controllers/album_controller.py` | ❌ Stub | — | — | ❌ Fase 4 |
| `AlbumGridPage.qml` | `ui_qml/pages/library/AlbumGridPage.qml` | ✅ | — | ✅ AlbumViewHost | ❌ Fase 3 |
| `AlbumGridView.qml` (legacy) | `ui_qml/pages/library/AlbumGridView.qml` | ✅ | — | ✅ album/ version | ❌ Fase 3 |
| `AlbumCard.qml` | `ui_qml/pages/library/AlbumCard.qml` | ✅ | ✅ (como delegate) | — | — |
| `AlbumListView.qml` | `ui_qml/pages/library/AlbumListView.qml` | ✅ | ✅ | — | — |
| `AlbumDetailPage.qml` | `ui_qml/pages/library/AlbumDetailPage.qml` | ✅ | ✅ | — | — |
| `AlbumGridView.qml` (album/) | `ui_qml/pages/library/album/AlbumGridView.qml` | 🧪 | — | ✅ integrar CoverImage | — |
| `AlbumCoverFlowView.qml` | `ui_qml/pages/library/album/AlbumCoverFlowView.qml` | 🧪 | — | ✅ integrar CoverImage+PathView | — |
| `AlbumVinylWallView.qml` | `ui_qml/pages/library/album/AlbumVinylWallView.qml` | 🧪 | — | ✅ integrar CoverImage | — |
| `AlbumTimelineView.qml` | `ui_qml/pages/library/album/AlbumTimelineView.qml` | 🧪 | — | ✅ integrar CoverImage | — |
| `AlbumMagazineView.qml` | `ui_qml/pages/library/album/AlbumMagazineView.qml` | 🧪 | — | ✅ integrar CoverImage | — |
| `AlbumViewHost.qml` | `ui_qml/pages/library/album/AlbumViewHost.qml` | 🧪 | ✅ | — | — |
| `AlbumViewSelector.qml` | `ui_qml/pages/library/album/AlbumViewSelector.qml` | 🧪 | ✅ (rediseñar) | — | — |
| `MichiAlbumTile.qml` | `ui_qml/components/content/MichiAlbumTile.qml` | ✅ | ✅ | — | — |
| `CoverImage.qml` | `ui_qml/components/CoverImage.qml` | ✅ | ✅ | — | — |
| `CoverBridgeProxy.qml` | `ui_qml/components/CoverBridgeProxy.qml` | ✅ | ✅ | — | — |
| `MichiResponsiveGrid` | `ui_qml/components/layouts/MichiResponsiveGrid.qml` | ✅ | ✅ | — | — |

---

## 4. CONTRATO AlbumViewContract

### 4.1 Definición

`AlbumViewContract` es la interfaz común que TODAS las vistas de álbum (Grid, CoverFlow, VinylWall, Timeline, Magazine) deben implementar.

### 4.2 Entradas (Properties)

```qml
// Propiedades requeridas que el host (AlbumViewHost) inyecta
property var albumModel: null      // AlbumListModel (BasePagedListModel)
property var bridge: null          // LibraryBridge
property var coverBridge: null     // CoverProviderBridge (opcional)
property var navigationBridge: null // NavigationBridge (opcional)

// Propiedades de configuración (opcionales, con defaults)
property int coverSize: 140        // Tamaño de carátula en píxeles
property bool showLabels: true     // Mostrar título/artista
property bool compact: false       // Modo compacto
property string filterText: ""     // Texto de filtro activo (para highlight)
```

### 4.3 Eventos (Signals)

```qml
// Evento universal: click en álbum → navegar a detalle
signal albumClicked(string albumKey, string title, string artist, int year)

// Evento: reproducir álbum directamente
signal playAlbum(string albumKey)

// Evento: añadir a cola
signal enqueueAlbum(string albumKey)

// Evento: menú contextual
signal contextMenuRequested(string albumKey, real x, real y)

// Evento: cambio de selección en CoverFlow u otras vistas con selección única
signal selectionChanged(string albumKey)
```

### 4.4 Estados

```qml
// La vista DEBE manejar estos estados (propagados desde AlbumListModel)
// loading:     BusyIndicator o skeleton
// empty:       Mensaje "Sin álbumes" + acción
// error:       Mensaje de error + retry
// ready:       Contenido normal
// filtered:    (opcional) mensaje "Sin resultados" + limpiar filtros

// Implementación esperada (ejemplo):
states: [
    State { name: "loading"; when: albumModel && albumModel.loading },
    State { name: "empty"; when: albumModel && albumModel.count === 0 && !albumModel.loading && !albumModel.error },
    State { name: "error"; when: albumModel && albumModel.error },
    State { name: "ready"; when: albumModel && albumModel.count > 0 }
]
```

### 4.5 Métodos (Functions)

```qml
// Recargar vista (resetear scroll, mantener selección si existe)
function reload() {}

// Scroll a un álbum específico (usado por "buscar y resaltar")
function scrollToAlbum(string albumKey) {}

// Obtener posición de scroll (para preservación de estado)
function scrollPosition(): real { return 0 }
```

### 4.6 Roles del Modelo (AlbumListModel)

| Role | Tipo | Ejemplo | Uso en vistas |
|------|------|---------|---------------|
| `albumKey` | string | `"a1b2c3d4"` | CoverKey, navegación |
| `title` | string | `"Dark Side of the Moon"` | Todas |
| `artist` | string | `"Pink Floyd"` | Todas |
| `year` | int | `1973` | Timeline, ordenación |
| `trackCount` | int | `10` | Grid, Magazine |
| `duration` | int | `4350` | — |
| `coverKey` | string | `"a1b2c3d4"` | CoverImage.coverKey |

---

## 5. ARQUITECTURA DEFINITIVA

### 5.1 Estructura de Directorios

```
ui_qml/pages/library/albums/
├── AlbumViewHost.qml          # ✅ Se MANTIENE (ya existe en album/)
├── AlbumViewSelector.qml      # ✅ Se MANTIENE (ya existe en album/)
├── AlbumGridView.qml          # ✅ Se MANTIENE (ya existe en album/)
├── AlbumCoverFlowView.qml     # ✅ Se MANTIENE (ya existe en album/)
├── AlbumVinylWallView.qml     # ✅ Se MANTIENE (ya existe en album/)
├── AlbumTimelineView.qml      # ✅ Se MANTIENE (ya existe en album/)
├── AlbumMagazineView.qml      # ✅ Se MANTIENE (ya existe en album/)
│
├── delegates/                 # Delegados reutilizables para las vistas
│   ├── AlbumGridDelegate.qml  # Card para GridView (basado en AlbumCard.qml)
│   ├── AlbumCoverDelegate.qml # Delegate para PathView (CoverFlow)
│   ├── AlbumVinylDelegate.qml # Disco de vinilo animado
│   ├── AlbumRowDelegate.qml   # Fila para ListView (Timeline, Magazine)
│   └── AlbumSectionHeader.qml # Cabecera de sección (año/década)
│
├── components/                # Componentes de álbum específicos
│   ├── AlbumContextMenu.qml   # Menú contextual unificado
│   ├── AlbumQualityBadge.qml  # Badge de calidad (Hi-Res, Lossless, DSD)
│   ├── AlbumFavoriteBadge.qml # Badge de favorito
│   └── AlbumEmptyState.qml    # Estado vacío para álbumes
│
└── menus/                     # (reservado para futuros menús contextuales)
```

### 5.2 Diagrama de Flujo de Datos

```
┌─────────────────────────────────────────────────────────────────┐
│                        LibraryPage.qml                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  LibraryNavigationBar (búsqueda)                          │  │
│  │  LibraryFilterBar (formato, género, año)                  │  │
│  │  LibraryStatusHeader (songCount, albumCount, artistCount) │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  StackLayout {                                            │  │
│  │    tab[0]: LibraryTrackTable (tracks)                     │  │
│  │    tab[1]: AlbumViewHost ←── NUEVA CONEXIÓN               │  │
│  │    tab[2]: ArtistGridPage (artists)                       │  │
│  │    tab[3]: FolderBrowserPage (folders)                    │  │
│  │  }                                                        │  │
│  └───────────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────────┘
                        │ albumModel=lib.albumModel
                        │ bridge=lib (LibraryBridge)
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  AlbumViewHost.qml (Loader router)                              │
│  ├── AlbumViewSelector.qml (selector de 5 vistas)               │
│  └── Loader → source según currentView:                         │
│       0 → AlbumGridView.qml      (GridView + AlbumGridDelegate) │
│       1 → AlbumCoverFlowView.qml (PathView + AlbumCoverDelegate)│
│       2 → AlbumVinylWallView.qml (GridView + AlbumVinylDelegate)│
│       3 → AlbumTimelineView.qml  (ListView + AlbumRowDelegate)  │
│       4 → AlbumMagazineView.qml  (ListView + AlbumRowDelegate)  │
└─────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  QML → Python Bridge Layer                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  LibraryBridge (library_bridge.py)                        │  │
│  │  ├── getAlbumDetail(album_key) → dict                     │  │
│  │  ├── playAlbum(album_key) → dict                          │  │
│  │  ├── enqueueAlbum(album_key) → dict                       │  │
│  │  └── albumModel → AlbumListModel (paginado)               │  │
│  │                                                           │  │
│  │  CoverBridge (cover_bridge.py) QQuickPaintedItem          │  │
│  │  └── coverKey → paint() → QPixmap (cached)               │  │
│  │                                                           │  │
│  │  CoverProviderBridge (cover_provider_bridge.py)            │  │
│  │  └── requestCover(coverKey, size) → data URL             │  │
│  │                                                           │  │
│  │  NavigationBridge (navigation_bridge.py)                  │  │
│  │  └── navigateWithParams("library.album_detail", params)   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  Python Service Layer                                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  AlbumListModel → BasePagedListModel                      │  │
│  │  └── QueryService.fetch_albums()                          │  │
│  │      └── AlbumRepository.get_page() / search() / filter() │  │
│  │          └── SQLite (media_items table, GROUP BY album_key)│  │
│  │                                                           │  │
│  │  AlbumDetailModel                                         │  │
│  │  └── QueryService.fetch_album_detail()                    │  │
│  │      └── AlbumRepository.get_by_key() + tracks_for_album()│  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 Contrato de Comunicación

```
┌───────────┐    albumModel (AlbumListModel)    ┌──────────────┐
│  View     │◄══════════════════════════════════│  LibraryBridge│
│  (.qml)   │                                   │  (bridge)     │
│           │    bridge.playAlbum(albumKey)     │              │
│           │══════════════════════════════════►│              │
│           │    bridge.enqueueAlbum(albumKey)  │              │
│           │══════════════════════════════════►│              │
│           │                                   │              │
│           │    albumClicked(key,t,a,y)         │              │
│           │────(conectado a NavigationBridge)──│              │
└───────────┘                                   └──────────────┘
```

### 5.4 Integración en RouteRegistry

```python
# Ruta actual (se actualiza para usar AlbumViewHost)
"library.albums": {
    "title": "Álbumes",
    "source": "../pages/library/AlbumViewHost.qml",  # ← Cambio aquí
    "category": "library",
    "status": "functional"
}
```

---

## 6. DISEÑO DE VISTAS

### 6.1 Grid View

**Propósito:** Navegación visual por álbumes en cuadrícula (vista principal)

**Tecnología:** `GridView` + reutilización de items

**Delegado:** `AlbumGridDelegate.qml` (basado en `AlbumCard.qml`)
- `CoverImage` 140×140 (o tamaño adaptable vía `MichiResponsive`)
- Título (1 línea, elide right)
- Artista (1 línea, elide right, muted)
- Año · N canciones (muted, meta size)
- Hover highlight (semi-transparente)
- Click → `albumClicked(key, title, artist, year)`
- Doble click → `playAlbum(key)`
- Context menu → `contextMenuRequested(key, x, y)`

**Rendimiento:**
- `cellWidth`/`cellHeight`: adaptativo según ancho del contenedor
- `cacheBuffer`: 2000px
- `rebound`/`OverShoot`: desactivado (StopAtBounds)
- ScrollBar vertical as-needed

**Estados:**
- `loading`: esqueleto gris shimmer
- `empty`: `AlbumEmptyState` con mensaje "No hay álbumes en tu biblioteca"
- `error`: mensaje de error + botón "Reintentar"
- `ready`: grid normal

### 6.2 CoverFlow (PathView)

**Propósito:** Navegación visual 3D tipo carrusel

**Tecnología:** `PathView` (soporte nativo Qt Quick)

**Path:**
```
PathAttribute { name: "rotate"; value: -25 }
PathLine → midpoint → PathAttribute { name: "rotate"; value: 0 }
PathLine → end → PathAttribute { name: "rotate"; value: 25 }
```

**Delegado:** `AlbumCoverDelegate.qml`
- `CoverImage` con `transform: Rotation { axis.y: 1; angle: PathView.rotate }`
- Escala: item actual 1.15, otros 0.80 (con transición suave)
- Opacidad: item actual 1.0, otros 0.5
- Sombra inferior: `RectangularGlow` o `DropShadow` sutiles
- Título/artista: visibles solo en item actual (o siempre con baja opacidad)
- Click (solo item central): `albumClicked`
- Doble click (item central): `playAlbum`

**Rendimiento:**
- `preferredHighlightBegin: 0.5; preferredHighlightEnd: 0.5`
- `highlightRangeMode: PathView.StrictlyEnforceRange`
- `cacheItemCount: 4` (precarga 4 items extra por lado)
- `snapMode: PathView.NoSnap` (movimiento libre con snapping natural)

**Lógica preservada del CoverFlow legacy:**
- Selección continua (no discreta) para animación suave
- Snapping al centro via highlight range mode
- Lazy loading de carátulas (ya lo hace CoverBridge)

### 6.3 Vinyl Wall

**Propósito:** Visualización inmersiva tipo discos de vinilo

**Tecnología:** `GridView` con delegates circulares

**Delegado:** `AlbumVinylDelegate.qml`
- Círculo exterior (disco): gradiente concéntrico oscuro → claro
- `CoverImage` centrada como etiqueta del vinilo (60×60)
- Círculo interior (label hole): 12px, color superficie
- Animación de rotación lenta al hacer hover (PropertyAnimation)
- Título debajo del vinilo, centrado
- Click → `albumClicked`
- Context menu → larga presión

**Badges:**
- Calidad: pequeño círculo de color en esquina superior derecha
  - Verde: Hi-Res / DSD
  - Azul: Lossless
  - Gris: Lossy
- Favorito: corazón pequeño

**Rendimiento:**
- `cellWidth: 150`, `cellHeight: 180`
- Delegado optimizado (pocos elementos anidados)
- Animaciones condicionales (solo en hover)

### 6.4 Timeline View

**Propósito:** Exploración cronológica de álbumes por año/década

**Tecnología:** `ListView` con secciones

**Agrupación:** 3 modos (seleccionables por botón o automáticos):
1. **Por año** (`section.property: "year"`) — cada año es una sección
2. **Por década** — agrupa años en décadas (1990, 2000, 2010...)
3. **Por fecha de agregación** — Hoy, Esta semana, Este mes, Este año, Anterior

**Delegado de sección:** `AlbumSectionHeader.qml`
- Fondo sutil (glass panel)
- Texto: "1990" o "90s" o "Esta semana"
- Contador: "12 álbumes"

**Delegado de fila:** `AlbumRowDelegate.qml`
- `CoverImage` pequeña (40×40)
- Título + Artista + Año
- Click → `albumClicked`

**Modelo:** Reutiliza `AlbumListModel`. Para década, se necesita propiedad calculada.

**Alternativa evaluada — Modelo agrupado:**
Se consideró crear un `QSortFilterProxyModel` que agrupe por década. Se descarta porque:
- `QSortFilterProxyModel` no soporta agrupación nativa
- `QML` `section.property` funciona con el modelo plano existente
- Para décadas, se añade propiedad `decade` via `role` en el modelo o como computed en QML

**Decisión:** Usar `section.property: "year"` (nativo QML). Para décadas, añadir role `decade` a `AlbumListModel` (`Qt.UserRole + 8`) calculado como `Math.floor(year / 10) * 10` en Python.

### 6.5 Magazine View

**Propósito:** Dashboard visual con secciones curadas

**Tecnología:** `ListView` (o `Flow`) con secciones temáticas

**Secciones:**
1. **Destacado (Hero):** Álbum más reciente o aleatorio de alta calidad
2. **Recientes:** Últimos 6 álbumes agregados
3. **Favoritos:** Álbumes marcados como favoritos (top 6)
4. **Hi-Res:** Álbumes con calidad ≥ 96kHz / 24bit
5. **No escuchados:** Álbumes con `lastPlayed IS NULL`

**Origen de datos:**
- **NO** consultas SQL separadas por vista
- Se obtienen del `AlbumListModel` con filtros específicos vía `LibraryBridge`
- Alternativa: `AlbumRepository.filter(year, genre, artist)` (SQL) para obtener subconjuntos

**Deduplicación:** Cada álbum aparece una sola vez (por `album_key`). Si un álbum cumple múltiples criterios, aparece en la primera sección que lo contenga.

**Virtualización:** `ListView` virtualiza verticalmente. Cada sección tiene un `Flow` horizontal interno con sus propios items.

**Actualización:** Se refresca al cambiar de pestaña (via `PageStateManager`). No hay polling.

**Delegado:** `MichiAlbumTile.qml` (ya existe, usa `CoverImage`)

---

## 7. RENDIMIENTO

### 7.1 Análisis de Carga

| Escenario | Álbumes | Items en memoria | RAM estimada | Tiempo carga inicial |
|-----------|---------|-----------------|-------------|---------------------|
| Pequeño | 100 | 100 | ~2 MB | < 100ms |
| Mediano | 1,000 | 1,000 | ~20 MB | ~200ms |
| Grande | 5,000 | 5,000 | ~100 MB | ~800ms |
| Extremo | 10,000 | 10,000 | ~200 MB | ~1.5s |

### 7.2 Estrategia de Virtualización

| Vista | Componente | Virtualización nativa | cacheBuffer | recomendado |
|-------|-----------|----------------------|-------------|-------------|
| Grid | `GridView` | ✅ Sí | 2000px | 1000-2000 items visibles |
| CoverFlow | `PathView` | ✅ Sí | 4 items | 4-8 items visibles |
| Vinyl Wall | `GridView` | ✅ Sí | 2000px | similar a Grid |
| Timeline | `ListView` | ✅ Sí | 2000px | 500-1000 items visibles |
| Magazine | `ListView` + `Flow` | ✅ Sí (externo) | 1000px | 50-100 items visibles |

### 7.3 Carga de Carátulas

**Problema:** 10,000 álbumes × ~100KB por carátula = ~1GB de carátulas sin virtualizar.

**Solución:**
1. `CoverBridge` con caché LRU de 256 imágenes en RAM (max ~25MB)
2. `CoverProviderBridge` con caché LRU de 500 data URLs (max ~50MB)
3. Las vistas virtualizadas solo solicitan carátulas de items visibles + cacheBuffer
4. Las carátulas se cargan de forma asíncrona (`Loader.asynchronous: true`, `CoverBridgeProxy`)
5. Fallback inmediato (gradiente + glyph) mientras se carga la carátula real

### 7.4 Scroll

| Vista | Scroll | ReuseItems | BoundBehavior |
|-------|--------|------------|---------------|
| Grid | `GridView` flickable | ✅ automático | `StopAtBounds` |
| Vinyl Wall | `GridView` flickable | ✅ automático | `StopAtBounds` |
| Timeline | `ListView` flickable | ✅ automático | `StopAtBounds` |
| Magazine | `ListView` flickable | ✅ automático | `StopAtBounds` |

### 7.5 GPU

- **PathView (CoverFlow):** requiere GPU para transformaciones 3D (Rotation, scale, opacity). Funciona con OpenGL/Qt Quick Renderer.
- **GridView/ListView:** sin GPU significativa (solo texturas para carátulas)
- **ShaderEffect para Vinyl:** rotación de vinilo usa GPU, pero es condicional (solo hover)

### 7.6 Delegados

Cada delegado debe ser lo más plano posible (mínima anidación). Recomendaciones:

**Optimizado:**
```qml
// Plano, mínimo anidamiento
Item {
    CoverImage { }  // Un solo elemento visual pesado
    Text { }
    Text { }
    MouseArea { }
}
```

**Evitar:**
```qml
// Anidamiento excesivo — cada Rectangle/Column/Item cuesta memoria
Item {
    Column {
        Rectangle {
            Row {
                Rectangle { CoverImage {} }
                Column { Text {} Text {} }
            }
        }
    }
}
```

---

## 8. TESTING

### 8.1 Estrategia General

| Tipo | Framework | Cobertura objetivo | Ubicación |
|------|-----------|-------------------|-----------|
| Unitarias | pytest | 90%+ modelos y servicios | `tests/test_album_list_model.py`, etc. |
| Integración | pytest | 80%+ bridges | `tests/qml/albums/` |
| QML | pytest + pytest-qt | 70%+ vistas (states) | `tests/qml/albums/test_*_view.py` |
| E2E | pytest | Flujos críticos | `tests/e2e/` |
| Rendimiento | pytest + time | Benchmarks | `tests/perf/` |

### 8.2 Tests Nuevos Requeridos

#### Tests Unitarios

| Test | Archivo | Pruebas | Prioridad |
|------|---------|---------|-----------|
| `AlbumListModel` roles | `tests/test_album_list_model.py` | 13 (existen) | ✅ |
| `AlbumViewHost` contract | `tests/test_album_view_host.py` | 5 | Alta |
| `AlbumGridDelegate` | `tests/test_album_grid_delegate.py` | 3 | Media |
| `AlbumCoverDelegate` | `tests/test_album_cover_delegate.py` | 3 | Media |
| `AlbumRowDelegate` | `tests/test_album_row_delegate.py` | 3 | Media |
| `AlbumSectionHeader` | `tests/test_album_section_header.py` | 2 | Baja |

#### Tests de Integración

| Test | Archivo | Pruebas | Prioridad |
|------|---------|---------|-----------|
| `AlbumViewHost` + `AlbumListModel` | `tests/integration/test_album_host_model.py` | 5 | Alta |
| View switching preservation | `tests/integration/test_view_switch.py` | 3 | Alta |
| Filter propagation a vistas | `tests/integration/test_filter_propagation.py` | 3 | Alta |
| Cover loading in delegates | `tests/integration/test_cover_in_delegates.py` | 3 | Media |

#### Tests QML

| Test | Archivo | Pruebas | Prioridad |
|------|---------|---------|-----------|
| `AlbumGridView` estados | `tests/qml/albums/test_grid_view_states.py` | 4 | Alta |
| `AlbumCoverFlowView` path | `tests/qml/albums/test_coverflow_view.py` | 4 | Alta |
| `AlbumTimelineView` sections | `tests/qml/albums/test_timeline_view.py` | 3 | Media |
| `AlbumMagazineView` sections | `tests/qml/albums/test_magazine_view.py` | 3 | Media |
| `AlbumVinylWallView` delegates | `tests/qml/albums/test_vinyl_view.py` | 2 | Baja |

#### Tests de Preservación

| Test | Archivo | Pruebas | Prioridad |
|------|---------|---------|-----------|
| Preservar selección al cambiar vista | `tests/qml/albums/test_selection_preservation.py` | 3 | Alta |
| Preservar filtros al cambiar vista | `tests/qml/albums/test_filter_preservation.py` | 3 | Alta |
| Preservar scroll al cambiar tab | `tests/qml/albums/test_scroll_preservation.py` | 2 | Media |

#### Tests de Rendimiento

| Test | Archivo | Pruebas | Prioridad |
|------|---------|---------|-----------|
| Grid 10,000 álbumes | `tests/perf/test_grid_10k.py` | 3 | Media |
| PathView 5,000 álbumes | `tests/perf/test_pathview_5k.py` | 3 | Media |
| Cover cache miss storm | `tests/perf/test_cover_storm.py` | 2 | Baja |

### 8.3 Criterios de Aceptación por Fase

| Fase | Criterio |
|------|----------|
| Fase 0 | Auditoría documentada y aprobada |
| Fase 1 | `AlbumViewHost` conectado a `LibraryPage`, 5 vistas funcionales con carátulas |
| Fase 2 | CoverFlow PathView con análogos funcionales del legacy |
| Fase 3 | Paridad funcional con legacy (Grid+Lista). Legacy desactivado por feature flag |
| Fase 4 | Código legacy eliminado. Sin regresiones. Tests 100% verdes |

---

## 9. ESTRATEGIA DE MIGRACIÓN

### 9.1 Convivencia Legacy ↔ Nuevo

**Feature flag:** `settings.library/album_view_mode` con valores:
- `"legacy"` (default durante Fase 1 y 2) — usa `AlbumGridPage`
- `"modern"` — usa `AlbumViewHost`

**Implementación en LibraryPage.qml:**
```qml
// Tab[1] actual:
AlbumGridPage { ... }  // legacy

// Reemplazo condicional:
Loader {
    source: libraryViewMode === "modern"
        ? "album/AlbumViewHost.qml"
        : "AlbumGridPage.qml"
}
```

### 9.2 Rollback

Si una vista moderna falla:
1. `AlbumViewHost` detecta error en Loader (`Loader.status === Loader.Error`)
2. Muestra mensaje "Error al cargar vista" + botón "Volver a vista anterior"
3. Al hacer clic, cambia `currentView` a la vista anterior
4. Si todas las vistas fallan, el feature flag se desactiva automáticamente

### 9.3 Eliminación Gradual

| Fase | Acción | Riesgo |
|------|--------|--------|
| Fase 1+2 | Legacy y nuevo coexisten. Feature flag `"legacy"` por defecto | Bajo |
| Fase 3 | Feature flag cambia a `"modern"` por defecto. Legacy aún disponible | Medio |
| Fase 4 | Se elimina `AlbumGridPage.qml`, `AlbumGridView.qml` (legacy), `AlbumListView.qml` | Alto — requiere tests completos |

### 9.4 CoverFlow Legacy → PathView

**Estrategia:** No tocar `library/coverflow.py` (stub). No tocar `coverflow_controller.py`.
El nuevo PathView en QML reemplaza funcionalmente al legacy.

**Paridad funcional requerida (Fase 2):**
- [ ] Navegación por click/drag
- [ ] Snap al centro
- [ ] Doble click → reproducir
- [ ] Scroll con rueda
- [ ] Teclado (flechas izquierda/derecha)
- [ ] Menú contextual en item
- [ ] Lazy loading de carátulas
- [ ] Preservación de selección al cambiar de vista

---

## 10. ROADMAP COMPLETO

### Fase 0: Auditoría y Diseño (Completada ✓)

**Objetivo:** Documentar todo el sistema actual, diseñar la arquitectura definitiva.

**Archivos afectados:** `docs/ALBUM_QML_MIGRATION_PLAN.md` (este documento)

**Dependencias:** Ninguna

**Riesgos:** Ninguno (solo documentación)

**Pruebas:** Ninguna

**Criterio de aceptación:** Documento aprobado con todas las secciones completas

**Duración estimada:** Ya completado

**Deuda técnica eliminada:** N/A

---

### Fase 1: Integración de AlbumViewHost + Carátulas Reales (5-7 días)

**Objetivo:** Conectar `AlbumViewHost` a `LibraryPage`, integrar `CoverImage` en todas las vistas.

**Archivos afectados:**

| Archivo | Acción |
|---------|--------|
| `ui_qml/pages/library/LibraryPage.qml` | Tab[1]: reemplazar `AlbumGridPage` por `AlbumViewHost` (con feature flag) |
| `ui_qml/pages/library/album/AlbumGridView.qml` | Reemplazar Rectangle fallback por `CoverImage` + `AlbumCard` delegate |
| `ui_qml/pages/library/album/AlbumCoverFlowView.qml` | Reemplazar Rectangle fallback por `CoverImage` en delegate |
| `ui_qml/pages/library/album/AlbumVinylWallView.qml` | Reemplazar Rectangle fallback por `CoverImage` en delegate |
| `ui_qml/pages/library/album/AlbumTimelineView.qml` | Reemplazar Rectangle fallback por `CoverImage` en delegate |
| `ui_qml/pages/library/album/AlbumMagazineView.qml` | Reemplazar Rectangle fallback por `CoverImage` en delegate |
| `ui_qml/pages/library/album/AlbumViewSelector.qml` | Usar iconos SVG reales (no Unicode) |
| `ui_qml/pages/library/album/delegates/AlbumGridDelegate.qml` | **NUEVO** — basado en `AlbumCard.qml` |
| `ui_qml/pages/library/album/delegates/AlbumCoverDelegate.qml` | **NUEVO** — delegate para PathView |
| `ui_qml/pages/library/album/delegates/AlbumVinylDelegate.qml` | **NUEVO** — vinilo con CoverImage |
| `ui_qml/pages/library/album/delegates/AlbumRowDelegate.qml` | **NUEVO** — fila compacta con CoverImage |
| `ui_qml/pages/library/album/delegates/AlbumSectionHeader.qml` | **NUEVO** — cabecera de sección |
| `ui_qml/models/AlbumListModel.py` | Añadir role `decade` (`Qt.UserRole + 8`) |
| `ui_qml_bridge/library_bridge.py` | Verificar que `albumModel` se expone correctamente |
| `ui_qml_bridge/route_registry.py` | Actualizar `"library.albums"` source (opcional, depende de integración) |

**Dependencias:** Fase 0 completada

**Riesgos:**
- **Medio:** Al cambiar `LibraryPage` tab[1], puede afectar la preservación de estado (`PageStateManager`)
- **Bajo:** Las vistas en `album/` actualmente son prototipos sin carátulas — integrar `CoverImage` requiere probar que el pipeline de carátulas funciona con `AlbumViewHost`

**Pruebas:**
- `tests/qml/albums/test_grid_view_states.py`
- `tests/qml/albums/test_selection_preservation.py`
- `tests/qml/albums/test_filter_preservation.py`

**Criterio de aceptación:**
- `AlbumViewHost` se ve en `LibraryPage` tab[1] cuando feature flag está en `"modern"`
- Las 5 vistas muestran carátulas reales (no fallbacks de glyph)
- Búsqueda y filtros funcionan en todas las vistas
- Click en álbum navega a `AlbumDetailPage`
- Preservación de scroll al cambiar tabs
- Tests nuevos pasan al 100%

**Duración estimada:** 5-7 días

**Deuda técnica eliminada:**
- Elimina el sistema de 5 prototipos inconexos
- Unifica todas las vistas bajo un solo contrato
- Conecta carátulas a vistas que nunca las tuvieron

---

### Fase 2: CoverFlow PathView + Vinyl Wall Animado (3-5 días)

**Objetivo:** Implementar PathView completo con análogos del CoverFlow legacy. Implementar animación de vinilo.

**Archivos afectados:**

| Archivo | Acción |
|---------|--------|
| `ui_qml/pages/library/album/AlbumCoverFlowView.qml` | PathView completo con path 3D, Rotation, scale, opacity, snap |
| `ui_qml/pages/library/album/delegates/AlbumCoverDelegate.qml` | Transformaciones 3D, DropShadow, lazy loading |
| `ui_qml/pages/library/album/AlbumVinylWallView.qml` | Grid con rotación en hover, badges de calidad |
| `ui_qml/pages/library/album/delegates/AlbumVinylDelegate.qml` | Animation de rotación |
| `ui_qml/theme/MichiTheme.qml` | Verificar que existan colores para badges de calidad |

**Dependencias:** Fase 1 completada

**Riesgos:**
- **Alto:** PathView puede tener problemas de rendimiento con 10,000+ items si no se configura correctamente
- **Medio:** Las transformaciones 3D (Rotation) requieren Qt Quick Renderer con OpenGL
- **Bajo:** La rotación de vinilo puede ser costosa si hay demasiados items visibles

**Mitigación:**
- `cacheItemCount: 4` en PathView
- Animaciones solo en items visibles (opacity/scale condicional)
- Rotation de vinilo solo en hover (no animación perpetua)

**Pruebas:**
- `tests/qml/albums/test_coverflow_view.py`
- `tests/qml/albums/test_vinyl_view.py`
- `tests/perf/test_pathview_5k.py`

**Criterio de aceptación:**
- PathView muestra carátulas con perspectiva 3D
- Snap al centro funciona correctamente
- Doble click reproduce álbum
- Rueda del mouse navega entre álbumes
- Vinilo rota al hacer hover
- Badges de calidad visibles
- Rendimiento aceptable con 5,000 álbumes (< 60fps en PathView)

**Duración estimada:** 3-5 días

---

### Fase 3: Timeline + Magazine + Paridad Funcional (3-5 días)

**Objetivo:** Implementar Timeline con agrupación por año/década. Implementar Magazine con secciones curadas. Alcanzar paridad funcional con el legacy.

**Archivos afectados:**

| Archivo | Acción |
|---------|--------|
| `ui_qml/pages/library/album/AlbumTimelineView.qml` | Sections por año, toggle década/año, scrollToAlbum |
| `ui_qml/pages/library/album/AlbumMagazineView.qml` | Secciones Hero, Recientes, Favoritos, Hi-Res, No escuchados |
| `ui_qml/pages/library/album/delegates/AlbumSectionHeader.qml` | Año/década con contador |
| `ui_qml/pages/library/album/delegates/AlbumRowDelegate.qml` | Fila con CoverImage 40×40 |
| `ui_qml/models/AlbumListModel.py` | Role `decade` (si no se añadió en Fase 1) |
| `ui_qml/pages/library/album/AlbumViewSelector.qml` | Iconos SVG reales (vista activa resaltada) |
| `ui_qml/pages/library/album/components/AlbumContextMenu.qml` | **NUEVO** — menú contextual unificado |
| `ui_qml/pages/library/album/components/AlbumQualityBadge.qml` | **NUEVO** — badge de calidad |
| `ui_qml/pages/library/album/components/AlbumFavoriteBadge.qml` | **NUEVO** — badge de favorito |
| `ui_qml/pages/library/album/components/AlbumEmptyState.qml` | **NUEVO** — estado vacío |
| `ui_qml/pages/library/LibraryPage.qml` | Feature flag `"modern"` pasa a default |

**Dependencias:** Fase 1 y 2 completadas

**Riesgos:**
- **Medio:** `AlbumMagazineView` requiere datos de "favoritos" y "última reproducción" — verificar que `AlbumRepository` los soporte
- **Bajo:** Timeline con 10,000 items + secciones puede tener overhead de layout
- **Bajo:** El feature flag cambiando a `"modern"` por defecto puede causar regresiones si no se prueba adecuadamente

**Pruebas:**
- `tests/qml/albums/test_timeline_view.py`
- `tests/qml/albums/test_magazine_view.py`
- `tests/e2e/test_album_workflow.py` (flujo completo: navegar → filtrar → seleccionar → reproducir)

**Criterio de aceptación:**
- Timeline agrupa por año correctamente
- Timeline agrupa por década (con toggle)
- Magazine muestra 5 secciones con datos reales (sin duplicación)
- Menú contextual funcional en todas las vistas
- Badge de calidad visible en Vinyl Wall
- Feature flag `"modern"` es default
- Legacy sigue disponible con `"legacy"`
- Todos los tests pasan

**Duración estimada:** 3-5 días

---

### Fase 4: Limpieza y Eliminación de Legacy (2-3 días)

**Objetivo:** Eliminar código legacy de álbumes. Unificar identidades. Código limpio sin paralelismos.

**Archivos afectados:**

| Archivo | Acción |
|---------|--------|
| `ui_qml/pages/library/AlbumGridPage.qml` | **ELIMINAR** |
| `ui_qml/pages/library/AlbumGridView.qml` | **ELIMINAR** (versión legacy) |
| `ui_qml/pages/library/AlbumListView.qml` | **ELIMINAR** |
| `ui_qml/pages/library/LibraryViewSelector.qml` | **ELIMINAR** (reemplazado por `AlbumViewSelector`) |
| `library/album_repository.py` | **ELIMINAR** (repositorio in-memory) |
| `library/coverflow.py` | **ELIMINAR** (stub) |
| `legacy_widgets/ui/controllers/album_controller.py` | **ELIMINAR** si no hay otros usos |
| `legacy_widgets/ui/controllers/coverflow_controller.py` | **ELIMINAR** |
| `core/library/identity.py` | **ELIMINAR** (unificar con `library/album_identity.py`) |
| `library/album_duplicate_service.py` | **ELIMINAR** (no migrado) |
| `library/album_quality_service.py` | **ELIMINAR** (no migrado, reemplazar por `core/album_service.py`) |
| `library/cover_art_service.py` | **ELIMINAR** (reemplazado por CoverBridge) |
| `library/album_art.py` | **ELIMINAR** (CoverFlowItem, group_by_album) |
| `library/album_art_worker.py` | **ELIMINAR** (reemplazado por CoverBridge) |
| `tests/test_album_controller.py` | **ELIMINAR** (legacy) |
| `tests/test_coverflow_api.py` | **ELIMINAR** |
| `tests/test_coverflow_layout.py` | **ELIMINAR** |
| `tests/test_coverflow_controller.py` | **ELIMINAR** |
| `tests/test_album_repository.py` | **ELIMINAR** (in-memory) |
| `tests/test_album_repository_grouping_hard.py` | **ELIMINAR** |
| `tests/test_album_duplicate_service.py` | **ELIMINAR** |
| `tests/test_album_quality_service.py` | **ELIMINAR** |
| `tests/test_album_detail_view.py` | **ELIMINAR** (QtWidgets legacy) |
| `tests/test_album_detail_dialog.py` | **ELIMINAR** |
| `tests/test_album_info_banner.py` | **ELIMINAR** |
| `tests/test_album_detail_identity_resolution.py` | **ELIMINAR** |
| `tests/test_album_micro_server_cancel_rollback.py` | **ELIMINAR** |
| `tests/test_album_mobile_sync_visibility.py` | **ELIMINAR** |
| `tests/test_album_server_import_dialog.py` | **ELIMINAR** |
| `tests/test_album_artist_genre_context.py` | **ELIMINAR** |
| `tests/test_album_controller_actions.py` | **ELIMINAR** |
| `tests/test_album_final_closure.py` | **ELIMINAR** |
| `tests/test_album_premium_end_to_end.py` | **ELIMINAR** |
| `tests/test_album_enrichment.py` | **ELIMINAR** |
| `tests/test_album_cache.py` | **ELIMINAR** |
| `tests/test_album_cover_service.py` | **ELIMINAR** |
| `tests/test_album_play_next_semantics.py` | **ELIMINAR** |
| `tests/test_pass_6a.py` | **ELIMINAR** (CoverFlow test) |
| `tests/test_view_context_consistency.py` | **ELIMINAR** (CoverFlow section) |
| `tests/test_library_controller.py` | **ELIMINAR** o migrar |

**Dependencias:** Fase 3 completada + verificación de que ningún otro módulo importa los archivos a eliminar

**Riesgos:**
- **Alto:** Eliminar archivos puede romper imports no detectados. Requiere búsqueda exhaustiva de imports
- **Medio:** Tests legacy pueden estar referenciados en conftest.py o configuraciones CI
- **Medio:** `AlbumCard.qml` se conserva (es usado por `AlbumGridView.qml` legacy, que se elimina — verificar si otros módulos lo usan)

**Mitigación:**
- Antes de eliminar: `grep -r "from library.album_repository"` etc.
- Antes de eliminar: `python -c "from library import album_repository"` para detectar imports rotos
- Eliminar archivos en PRs separados por grupo (modelos → vistas → tests)

**Pruebas:**
- `ruff check .` — 0 errores
- `python -m compileall -q .` — 0 errores
- `python -m pytest tests/ -q` — 100% verde (excluyendo tests eliminados)
- Feature flag `"modern"` funciona sin el legacy

**Criterio de aceptación:**
- Cero archivos legacy de álbumes en el código base
- Cero importaciones rotas
- 100% de tests pasando
- `AlbumViewHost` funciona sin dependencias legacy
- Feature flag `"legacy"` eliminado (ya no es necesario)

**Duración estimada:** 2-3 días

**Deuda técnica eliminada:**
- `core/library/identity.py` duplicado eliminado (3 campos)
- `library/album_repository.py` in-memory eliminado (388 líneas)
- `library/coverflow.py` stub eliminado
- 24+ archivos legacy eliminados (~3,000+ líneas de código muerto)

---

## 11. MATRIZ DE RIESGOS

| # | Riesgo | Probabilidad | Impacto | Mitigación | Fase |
|---|--------|-------------|---------|------------|------|
| 1 | PathView lento con 10,000 items | Media | Alto | `cacheItemCount: 4`, delegados planos | 2 |
| 2 | Feature flag rompe preservación de estado | Media | Alto | Probar `PageStateManager` con ambas ramas del flag | 1 |
| 3 | CoverImage no funciona en album/ vistas | Baja | Alto | Verificar pipeline `CoverBridge` → `CoverBridgeProxy` → `QQuickPaintedItem` | 0 (ya verificado) |
| 4 | Eliminar archivos legacy rompe imports | Media | Alto | `grep` + `compileall` antes de eliminar | 4 |
| 5 | `AlbumMagazineView` sin datos de favoritos | Baja | Medio | Verificar que `LibraryDB` tenga campo `favorite` | 3 |
| 6 | Timeline con décadas requiere role nuevo | Baja | Bajo | Añadir role `decade` a `AlbumListModel` | 1 |
| 7 | Rotation 3D en PathView sin GPU | Baja | Medio | Documentar requisito OpenGL; fallback a 2D | 2 |
| 8 | AlbumContextMenu duplica lógica existente | Media | Medio | Reutilizar `LibraryContextMenu` de `LibraryPage.qml` | 3 |

---

## 12. ESTIMACIONES

### 12.1 Complejidad por Componente

| Componente | Líneas estimadas | Complejidad | Dependencias externas |
|-----------|-----------------|-------------|----------------------|
| `AlbumGridDelegate.qml` | ~60 | Baja | `CoverImage`, `MichiTheme` |
| `AlbumCoverDelegate.qml` | ~80 | Media | `CoverImage`, `PathView`, `Rotation` |
| `AlbumVinylDelegate.qml` | ~70 | Media | `CoverImage`, `PropertyAnimation` |
| `AlbumRowDelegate.qml` | ~50 | Baja | `CoverImage` |
| `AlbumSectionHeader.qml` | ~40 | Baja | `MichiTheme` |
| `AlbumContextMenu.qml` | ~60 | Media | `LibraryContextMenu` existente |
| `AlbumQualityBadge.qml` | ~30 | Baja | `MichiTheme` |
| `AlbumFavoriteBadge.qml` | ~25 | Baja | `MichiTheme` |
| `AlbumEmptyState.qml` | ~35 | Baja | `MichiTheme` |
| `AlbumListModel.py` (+role decade) | ~5 | Baja | `BasePagedListModel` |
| `LibraryPage.qml` (cambio tab[1]) | ~5 | Baja | Feature flag |

**Total líneas nuevas:** ~460 QML + ~5 Python = ~465 líneas
**Total archivos nuevos:** 9 QML
**Total archivos modificados:** ~8 (5 vistas + 2 modelos + 1 page)

### 12.2 Deuda Técnica Eliminada

| Componente | Líneas eliminadas | Archivos eliminados |
|-----------|------------------|--------------------|
| Album repositories (in-memory) | ~388 | 1 |
| CoverFlow legacy | ~1,181 | 1 |
| Album controllers legacy | ~561 | 1 |
| CoverFlow controller legacy | ~435 | 1 |
| Album art services | ~282 + 47 + 70 | 3 |
| Album duplicate/quality services | ~200 | 2 |
| Duplicate identity | ~33 | 1 |
| Vista legacy (AlbumGridPage) | ~71 | 1 |
| Vista legacy (AlbumGridView) | ~44 | 1 |
| Vista legacy (AlbumListView) | ~50 | 1 |
| Vista legacy (LibraryViewSelector) | ~46 | 1 |
| Tests legacy (~20 archivos) | ~1,000+ | ~20 |

**Total líneas eliminadas:** ~4,408
**Total archivos eliminados:** ~34

**Deuda neta:** ~465 (nuevo) - ~4,408 (eliminado) = **~3,943 líneas de deuda técnica eliminada**

### 12.3 Estimación Total

| Fase | Días | Archivos nuevos | Archivos modificados | Archivos eliminados |
|------|------|----------------|---------------------|-------------------|
| Fase 0 | 0 (completado) | 1 (doc) | 0 | 0 |
| Fase 1 | 5-7 | 5 | 8 | 0 |
| Fase 2 | 3-5 | 0 | 4 | 0 |
| Fase 3 | 3-5 | 4 | 3 | 0 |
| Fase 4 | 2-3 | 0 | 0 | ~34 |
| **Total** | **13-20** | **9 + 1 doc** | **15** | **~34** |

---

## APÉNDICE A: Verificación de Contrato en Vistas Actuales

Todas las vistas en `album/` ya implementan parcialmente el contrato:

| Propiedad/Señal | AlbumGridView | AlbumCoverFlowView | AlbumVinylWallView | AlbumTimelineView | AlbumMagazineView |
|----------------|---------------|-------------------|-------------------|-------------------|-------------------|
| `albumModel` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `bridge` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `albumClicked(key,t,a,y)` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Maneja `loading` | ❌ | ❌ | ❌ | ❌ | ❌ |
| Maneja `empty` | ❌ | ❌ | ❌ | ❌ | ❌ |
| Maneja `error` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `CoverImage` real | ❌ (glyph) | ❌ (glyph) | ❌ (glyph) | ❌ (glyph) | ❌ (glyph) |

**Trabajo pendiente por vista:**
- Añadir manejadores de estado (loading, empty, error) → 5 vistas × 3 estados = 15 bloques condicionales
- Reemplazar Rectangle fallback por `CoverImage` → 5 vistas × 1 cambio = 5 cambios
- Conectar señales de reproducción (playAlbum, enqueueAlbum) → 5 vistas × 2 señales = 10 conexiones

---

## APÉNDICE B: Dependencias entre Archivos

```
LibraryPage.qml
  └── AlbumViewHost.qml (Fase 1)
        ├── AlbumViewSelector.qml (Fase 1 — iconos SVG)
        ├── AlbumGridView.qml (Fase 1 — CoverImage)
        │     └── delegates/AlbumGridDelegate.qml (NUEVO Fase 1)
        ├── AlbumCoverFlowView.qml (Fase 2 — PathView 3D)
        │     └── delegates/AlbumCoverDelegate.qml (NUEVO Fase 1)
        ├── AlbumVinylWallView.qml (Fase 2 — animación)
        │     └── delegates/AlbumVinylDelegate.qml (NUEVO Fase 1)
        │     └── components/AlbumQualityBadge.qml (NUEVO Fase 3)
        ├── AlbumTimelineView.qml (Fase 3 — secciones)
        │     └── delegates/AlbumRowDelegate.qml (NUEVO Fase 1)
        │     └── delegates/AlbumSectionHeader.qml (NUEVO Fase 1)
        └── AlbumMagazineView.qml (Fase 3 — secciones curadas)
              └── delegates/AlbumRowDelegate.qml (reutilizado)
              └── components/AlbumEmptyState.qml (NUEVO Fase 3)

dependencias de componentes:
AlbumGridDelegate.qml → CoverImage.qml → CoverBridgeProxy.qml → CoverBridge (Python)
AlbumListModel.py → BasePagedListModel.py → QueryService.fetch_albums()
AlbumContextMenu.qml → LibraryBridge.playAlbum() / enqueueAlbum()
```

---

## APÉNDICE C: Criterios de Decisión

### ¿Por qué NO se usa QSortFilterProxyModel para Timeline?

1. `section.property` de QML ListView funciona con datos planos — no necesita proxy
2. `QSortFilterProxyModel` no soporta agrupación; solo filtrado y ordenación
3. Añadir un proxy model es overhead innecesario cuando el modelo plano ya funciona
4. Para décadas, basta con añadir un role computado en Python

### ¿Por qué NO se crea un AlbumGroupedModel?

1. `AlbumListModel` ya es paginado y funciona con todas las vistas
2. Cada vista procesa los datos de forma diferente (GridView indexa, PathView posiciona, ListView secciona)
3. Un modelo agrupado rompería la paginación y requeriría lógica de agrupación duplicada

### ¿Por qué Magazine NO usa consultas SQL separadas?

1. Las consultas separadas duplicarían lógica de `AlbumRepository`
2. El modelo `AlbumListModel` ya proporciona todos los datos necesarios
3. La selección de "álbumes destacados" puede hacerse con una sola consulta `ORDER BY RANDOM() LIMIT 1`
4. "Recientes" es simplemente `ORDER BY created_at DESC LIMIT 6`
5. "Favoritos" requiere un filtro adicional (`favorite = 1`)
6. Se añaden métodos específicos a `LibraryBridge` si es necesario, no repositorios nuevos

### ¿Por qué CoverFlow usa PathView en lugar de SwipeView?

1. `PathView` permite path 3D personalizado (Rotation, scale, opacity variables por posición)
2. `SwipeView` solo permite navegación lineal sin perspectiva
3. `PathView` es el componente nativo de Qt Quick para carruseles 3D
4. El CoverFlow legacy usaba posicionamiento continuo (no discreto) — `PathView` lo soporta nativamente

---

## 13. INVESTIGACIÓN DE REFERENCIAS

> **Política:** Inspirarse es preferible a copiar. Copiar solo componentes claramente licenciados. Registrar archivo original, autor, licencia y modificaciones. No copiar componentes GPL dentro de Michi sin comprobar compatibilidad con la licencia GPL-3.0 de Michi.

### 13.1 KDE Elisa — GridBrowserDelegate

**Archivo original:** `src/qml/GridBrowserDelegate.qml`
**Autor:** Matthieu Gallien & Devin Lin
**Licencia:** LGPL-3.0-or-later
**Compatibilidad con Michi (GPL-3.0):** ✅ Compatible. LGPL-3.0 es un subconjunto permisivo de GPL-3.0. El código LGPL puede incorporarse en proyectos GPL-3.0.
**Estado:** Inspiración + patrón de diseño. Sin código copiado.

**Patrones tomados:**

| Patrón | Descripción | Uso en Michi |
|--------|-------------|-------------|
| **Loader condicional para hover/focus** | Loader que se activa con `active: hasActiveFocus \|\| hovered` para mostrar indicadores visuales | ✅ Se adapta: en lugar de botones de acción, Michi mostrará badges de calidad, favorito y duración al hacer hover |
| **FocusScope como contenedor del delegate** | Uso de `FocusScope` interno para manejar correctamente el foco del teclado en el delegate | ✅ Se reescribe con `MichiFocusRing` y `activeFocusOnTab` |
| **CoverImage como componente separado** | Componente interno con `asynchronous: true` y capa de sombra vía `layer.effect` | ✅ Michi tiene su propio `CoverImage.qml` con `CoverBridgeProxy` — no se necesita tomar nada |

**Qué NO se tomó:**
- No se copió ninguna línea de código.
- No se usó `ImageWithFallback`, `Kirigami.Theme`, `LabelWithToolTip`, `FlatButtonWithToolTip`, ni ninguna dependencia de Kirigami.
- No se usó el sistema de `multipleImageUrls` (cuatro carátulas en cuadrícula para álbumes recopilatorios).
- Todo se reescribe con `MichiTheme`, `MichiFocusRing` y `CoverImage.qml` (Michi propio).

**Atribución requerida:** Sí. Se añadirá en `delegates/AlbumGridDelegate.qml`:

```qml
// SPDX-FileCopyrightText: 2016 Matthieu Gallien <matthieu_gallien@yahoo.fr>
//   Patrón: Grid delegate con cover + hover indicators (adaptado de KDE Elisa)
// SPDX-License-Identifier: GPL-3.0-or-later
```

---

### 13.2 Qt PathView — Documentación Oficial

**Fuente:** `doc.qt.io/qt-6/qml-qtquick-pathview.html`
**Autor:** The Qt Company
**Licencia:** GFDL 1.3 (documentación), LGPL-3.0/GPL-3.0 (código del módulo Qt Quick)
**Compatibilidad:** ✅ La API pública de Qt Quick se usa según su licencia. Sin restricciones para proyectos GPL-3.0.
**Estado:** API pública estándar. No requiere atribución.

**Propiedades PathView usadas (configuración estándar):**

| Propiedad | Valor | Propósito |
|-----------|-------|-----------|
| `preferredHighlightBegin` | `0.5` | Item actual centrado en el path |
| `preferredHighlightEnd` | `0.5` | Item actual centrado (mismo valor = punto único) |
| `highlightRangeMode` | `PathView.StrictlyEnforceRange` | El item SIEMPRE está en el centro |
| `snapMode` | `PathView.SnapToItem` | Los items encajan en posiciones discretas |
| `cacheItemCount` | `4` | Precarga 4 items extra por lado (asíncrono) |
| `pathItemCount` | `5` | Muestra 5 items visibles simultáneamente |
| `dragMargin` | `100` | Permite arrastrar desde fuera de los items |

**PathAttribute usados (patrón estándar de documentación):**

```qml
Path {
    startX: -ancho; startY: alto/2
    PathAttribute { name: "itemScale"; value: 0.7 }
    PathAttribute { name: "itemOpacity"; value: 0.5 }
    PathAttribute { name: "itemAngle"; value: -25 }
    PathAttribute { name: "zValue"; value: 1 }

    PathLine { x: centro; y: alto/2 }
    PathAttribute { name: "itemScale"; value: 1.15 }
    PathAttribute { name: "itemOpacity"; value: 1.0 }
    PathAttribute { name: "itemAngle"; value: 0 }
    PathAttribute { name: "zValue"; value: 10 }

    PathLine { x: ancho+100; y: alto/2 }
    PathAttribute { name: "itemScale"; value: 0.7 }
    PathAttribute { name: "itemOpacity"; value: 0.5 }
    PathAttribute { name: "itemAngle"; value: 25 }
    PathAttribute { name: "zValue"; value: 1 }
}
```

**Señales y métodos clave:**

| Señal/Método | Uso |
|--------------|-----|
| `incrementCurrentIndex()` / `decrementCurrentIndex()` | Navegación por teclado (flechas izquierda/derecha) |
| `positionViewAtIndex(index, PathView.Center)` | Posicionamiento programático (scroll a álbum) |
| `movementStarted` / `movementEnded` | Sincronizar UI con el movimiento del path |
| `currentItem` | Obtener el delegate del item actual |
| `PathView.isCurrentItem` (attached) | Propiedad attached para estilizar el item activo |

**Qué NO se tomó:**
- No se copió ningún ejemplo concreto de la documentación.
- No se usaron paths complejos (PathQuad, PathCubic) — se usa PathLine simple de 3 segmentos.

**Atribución requerida:** No. La API de PathView es pública y distribuida bajo licencia LGPL-3.0/GPL-3.0 por The Qt Company.

---

### 13.3 Nemo Mobile qmlmusicplayer — CoverFlow

**Archivo original:** `qml/CoverFlow.qml` y `qml/Cover.qml`
**Autor:** Martin Grimme (basado en Music Shelf)
**Licencia:** GPL-2.0-or-later
**Compatibilidad:** ⚠️ GPL-2.0 y GPL-3.0 son compatibles unidireccionalmente. GPL-3.0 puede incorporar código GPL-2.0, pero requiere mantener el aviso de copyright GPL-2.0. **Decisión: NO copiar código. Solo inspirarse en patrones conceptuales.**
**Estado:** Inspiración conceptual. NO se copió código.

**Conceptos tomados:**

| Concepto | Original (Nemo) | Adaptación (Michi) |
|----------|----------------|-------------------|
| **Dimming de items laterales** | `PathAttribute { name: "dimming"; value: 1.0 }` oscurece items no centrales | Mismo mecanismo via `PathAttribute { name: "itemOpacity" }` — patrón estándar de Qt |
| **Reflection especular** | `Image` duplicado con `Rotation { axis.x: 1; angle: 180 }` + gradiente de desvanecimiento | Se implementa como `ShaderEffect` opcional (más eficiente). Desactivado por defecto. Solo en CoverFlow. |
| **pathItemCount ~6** | `pathItemCount: 6` para mostrar 6 items | Michi usa `pathItemCount: 5` (menos solapamiento, mejor para el ancho típico desktop) |

**Qué NO se tomó:**
- No se copió el sistema de 3 paths alternativos (3D, circular, simple). Michi usa un path único de 3 segmentos.
- No se copió la lógica de `MouseArea` con click-to-center manual (PathView con `StrictlyEnforceRange` lo maneja automáticamente).
- No se copió el `Cover.qml` delegate con `Image` duplicado para reflection.
- No se copió ninguna variable, nombre de propiedad, o estructura de control.
- No se usó el archivo `config.js` ni sus constantes.

**Atribución requerida:** Sí, por el diseño conceptual del dimming + reflection. Se añadirá en `AlbumCoverFlowView.qml`:

```qml
// SPDX-FileCopyrightText: 2011 Martin Grimme <martin.grimme _AT_ gmail.com>
//   Patrón: PathAttribute dimming + reflection para CoverFlow
//   (inspirado en Nemo Mobile qmlmusicplayer / Music Shelf)
// SPDX-License-Identifier: GPL-3.0-or-later
```

---

### 13.4 KDE AudioTube — Hero y Secciones

**Fuente:** `invent.kde.org/multimedia/audiotube`
**Autor:** KDE Multimedia Team
**Licencia:** GPL-3.0-or-later (estándar KDE multimedia)
**Compatibilidad:** ✅ Misma licencia que Michi.
**Estado:** Inspiración conceptual. Sin código (repositorio no accesible por 403, pero estructura conocida por ser proyecto KDE Kirigami).

**Conceptos tomados:**

| Concepto | Descripción | Uso en Michi |
|----------|-------------|-------------|
| **Hero content** | Tarjeta grande visualmente destacada al inicio de la página, con carátula grande y metadatos principales | ✅ Se adapta en `AlbumMagazineView`: álbum destacado del momento (aleatorio o el más reciente) con carátula 200×200, título en heroTitleSize, artista, año, badge de calidad |
| **Secciones horizontales** | Filas de ítems desplazables horizontalmente agrupadas por criterio | ✅ Se adapta en `AlbumMagazineView`: secciones "Recientes", "Favoritos", "Hi-Res", "No escuchados". Implementado con `ListView` horizontal nativo. |
| **Diseño responsive** | Adaptación de columnas al ancho de ventana | ⚠️ Michi ya tiene `MichiResponsive` en `AGENTS.md`. Se aplica a todas las vistas. |

**Qué NO se tomó:**
- No se usó Kirigami, `Kirigami.CardGrid`, ni ninguna dependencia de KDE.
- No se copió ninguna línea de código.
- No se usó `ScrollView` de Qt (Michi usa `ListView` horizontal nativo con `orientation: ListView.Horizontal`).

**Atribución requerida:** No. El patrón hero + secciones horizontales es común en múltiples reproductores. La implementación de Michi es original.

---

### 13.5 Qt Quick Animations — Microinteracciones

**Fuente:** `doc.qt.io/qt-6/qml-qtquick-propertyanimation.html`, `doc.qt.io/qt-6/qml-qtquick-behavior.html`, `doc.qt.io/qt-6/qml-qtquick-smoothedanimation.html`
**Autor:** The Qt Company
**Licencia:** GFDL 1.3 (documentación), LGPL-3.0/GPL-3.0 (módulo Qt Quick)
**Compatibilidad:** ✅ API pública estándar.
**Estado:** API pública estándar. No requiere atribución.

**Parámetros definidos para Michi:**

| Microinteracción | Propiedad | Duración | Easing | Destino |
|-----------------|-----------|----------|--------|---------|
| **Hover en Grid/Vinyl** | `scale: 1.0 → 1.05` | 150ms | `OutCubic` | `delegates/AlbumGridDelegate`, `AlbumVinylDelegate` |
| **Hover color de fondo** | `color` | 100ms | `OutQuad` | Todos los delegates |
| **Enter de items nuevos** | `opacity: 0 → 1` + `scale: 0.9 → 1.0` | 250ms | `OutCubic` | `GridView`, `ListView` (via `add: Transition`) |
| **PathView snap** | highlightMoveDuration | 300ms | nativo PathView | `AlbumCoverFlowView` |
| **Rotación de vinilo (hover)** | `rotation: 0 → 360` | 4000ms (continua) | `Linear` | `AlbumVinylDelegate` |
| **Loader page transition** | `opacity: 0 → 1` | 300ms | `OutQuad` | `PageStack` |
| **Badge appear** | `opacity: 0 → 1` | 200ms | `OutQuad` | `AlbumQualityBadge`, `AlbumFavoriteBadge` |

**Reglas:**
- Respetar `reduced motion` (desactivar animaciones no esenciales) — requerido por `AGENTS.md`
- No animaciones perpetuas (la rotación de vinilo es la única excepción, y se desactiva con reduced motion)
- No usar `OutBack` (rebote exagerado, no profesional)
- `Behavior` solo en propiedades que cambian frecuentemente (scale, opacity). Usar `State + Transition` para cambios de visibilidad.
- Duración máxima para hover: 200ms. Para transiciones de página: 300ms.

**Atribución requerida:** No. API pública de Qt Quick.

---

### 13.6 Matriz de Compatibilidad de Licencias

| Fuente | Archivo | Licencia | ¿Copiar código? | ¿Inspirarse? | Atribución |
|--------|---------|----------|----------------|--------------|------------|
| KDE Elisa | `GridBrowserDelegate.qml` | LGPL-3.0 | ✅ Sí (compatible) | ✅ Sí | `Matthieu Gallien` |
| Qt PathView | `qml-qtquick-pathview.html` | LGPL-3.0 (API) | ✅ Sí (API estándar) | ✅ Sí | No requiere |
| Nemo qmlmusicplayer | `CoverFlow.qml`, `Cover.qml` | GPL-2.0 | ❌ NO | ✅ Sí (conceptual) | `Martin Grimme` |
| KDE AudioTube | `AlbumPage.qml` (estructural) | GPL-3.0 | ✅ Sí (compatible) | ✅ Sí | No requiere |
| Qt Animations | Documentación Qt | GFDL 1.3 / LGPL-3.0 | ✅ Sí (API estándar) | ✅ Sí | No requiere |

**Regla final:** NO se copia código de Nemo (GPL-2.0). Sí se copian patrones estructurales de Elisa (LGPL-3.0). La API de PathView y animaciones son estándar Qt. La implementación de animaciones es código original Michi.

---

### 13.7 Declaración de Atribuciones por Archivo

Cada archivo nuevo DEBE llevar su atribución SPDX específica en el encabezado, indicando qué se tomó y de dónde. Archivos sin influencia directa NO deben añadir atribuciones falsas.

| Archivo QML | Atribución | Razón |
|------------|------------|-------|
| `delegates/AlbumGridDelegate.qml` | `SPDX-FileCopyrightText: 2016 Matthieu Gallien <matthieu_gallien@yahoo.fr>` — patrón de delegate grid con cover + hover indicators | Adaptado del `GridBrowserDelegate.qml` de KDE Elisa |
| `AlbumCoverFlowView.qml` | `SPDX-FileCopyrightText: 2011 Martin Grimme <martin.grimme _AT_ gmail.com>` — patrón de PathAttribute dimming + reflection | Inspirado en `CoverFlow.qml` de Nemo Mobile qmlmusicplayer |
| `AlbumMagazineView.qml` | Sin atribución específica | Patrón común de UX musical (hero + secciones horizontales). Implementación original Michi. |
| `AlbumVinylWallView.qml` | Sin atribución específica | Diseño original Michi. |
| `AlbumTimelineView.qml` | Sin atribución específica | Patrón estándar ListView + sections. Implementación original. |
| `delegates/AlbumCoverDelegate.qml` | Sin atribución específica | PathView delegate estándar de Qt, con influencia conceptual de dimming de Nemo (ya atribuido en `AlbumCoverFlowView.qml`). |
| `delegates/AlbumVinylDelegate.qml` | Sin atribución específica | Diseño original Michi. |
| `delegates/AlbumRowDelegate.qml` | Sin atribución específica | Patrón estándar de fila de lista. |
| `delegates/AlbumSectionHeader.qml` | Sin atribución específica | Cabecera de sección estándar. |
| `components/AlbumQualityBadge.qml` | Sin atribución específica | Diseño original Michi. |
| `components/AlbumFavoriteBadge.qml` | Sin atribución específica | Diseño original Michi. |
| `components/AlbumEmptyState.qml` | Sin atribución específica | Diseño original Michi. |
| `components/AlbumContextMenu.qml` | Sin atribución específica | Basado en `LibraryContextMenu` existente de Michi. |

**Formato estándar del encabezado SPDX:**

```qml
// SPDX-FileCopyrightText: YYYY Autor <email>
//   Patrón: Descripción del patrón tomado (adaptado de NombreProyecto)
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls
// ...
```

**Validación:** Antes de cada commit, verificar que todos los archivos nuevos tengan SPDX correcto:
```bash
grep -rl "SPDX-License-Identifier" ui_qml/pages/library/album/*.qml ui_qml/pages/library/album/delegates/*.qml ui_qml/pages/library/album/components/*.qml | wc -l
# Debe coincidir con el número total de archivos nuevos
```
