# Biblioteca QML Premium — diagnóstico consolidado y plan de implementación

## 1. Objetivo

Convertir Biblioteca en uno de los módulos principales de Michi Music Player: rápida con colecciones grandes, visualmente diferenciada, completamente operativa desde teclado y ratón, y capaz de ofrecer distintas formas de explorar una fonoteca sin duplicar lógica de dominio.

La implementación se mantiene exclusivamente orientada a audio. Las vistas son representaciones distintas del mismo catálogo de álbumes; no crean bases de datos paralelas ni alteran la biblioteca.

## 2. Diagnóstico consolidado

La base existente era funcional, pero no tenía paridad de producción. Los problemas principales eran:

1. La selección múltiple dependía de un `id` perteneciente a otro ámbito QML.
2. `ActionRegistry.execute()` se invocaba con argumentos incompatibles.
3. El menú contextual construía identificadores de acción inexistentes.
4. Género, año, compositor, favoritos, no reproducidos y ausentes no llegaban de forma consistente a conteo y paginación.
5. La barra de filtros referenciaba objetos inexistentes.
6. La pestaña rotulada “Géneros” cargaba Carpetas.
7. La máquina de estados Python tenía más estados que la representación QML.
8. `PageStack` no entregaba parámetros de navegación a las páginas de detalle.
9. Detalle de álbum y artista reutilizaban modelos globales y contaminaban el estado de Biblioteca.
10. CoverFlow, Vinyl Wall, Timeline y Magazine existían como prototipos, pero no estaban expuestos mediante un selector visible ni alcanzaban calidad de producto.

## 3. Arquitectura objetivo

```text
LibraryPage
├── MichiLibraryToolbar
├── LibraryFilterBar
├── LibraryStatusHeader
├── StackLayout
│   ├── LibraryTrackTable
│   ├── AlbumViewHost
│   │   ├── AlbumGridView
│   │   ├── AlbumCoverFlowView
│   │   ├── AlbumVinylWallView
│   │   ├── AlbumTimelineView
│   │   └── AlbumMagazineView
│   ├── ArtistGridPage
│   └── FolderBrowserPage
├── LibrarySelectionBar
└── LibraryContextMenu

LibraryBridge
├── TrackListModel
├── AlbumListModel
├── ArtistListModel
├── FolderTreeModel
└── LibraryRefreshCoordinator
```

Principios obligatorios:

- Un solo modelo de álbumes para todas las vistas.
- Ninguna vista ejecuta SQL ni conoce detalles de persistencia.
- Todas las acciones de reproducción pasan por `LibraryBridge` o servicios de dominio.
- Las páginas de detalle cargan datos locales y no cambian los filtros del catálogo principal.
- La paginación usa `loadingMore` y `hasMore`; no temporizadores ni flags locales que se liberen antes de completar la consulta.
- Las vistas permanecen utilizables sin efectos gráficos costosos ni dependencias externas.

## 4. Diseño visual premium

### Lenguaje visual

- Superficies oscuras de baja luminancia con jerarquía por elevación.
- Bordes sutiles y foco visible mediante `borderFocus`.
- Acento azul Michi para selección, reproducción y navegación.
- Esquinas grandes en contenedores; esquinas medias en carátulas.
- Transiciones de 120–220 ms mediante tokens `MichiMotion`.
- Texto principal de alto contraste y metadatos deliberadamente silenciosos.
- Acciones rápidas visibles en hover, pero siempre accesibles por teclado.

### Comportamiento común

- Enter abre el detalle.
- Espacio reproduce.
- Doble clic reproduce.
- Flechas recorren el contenido.
- Ctrl+1…Ctrl+5 cambia la vista de álbumes.
- Cada vista muestra estado vacío y paginación cuando corresponde.
- El cambio de vista no vuelve a consultar la base de datos.

## 5. Vistas implementadas

### 5.1 Grid View

Propósito: exploración general y eficiente.

- Número de columnas adaptativo.
- Carátulas grandes con metadatos legibles.
- Año como badge flotante.
- Acción de reproducción rápida.
- Selección de teclado y foco visible.
- Botón de carga incremental.

### 5.2 CoverFlow / PathView

Propósito: exploración inmersiva de la colección.

- `PathView` real con perspectiva lateral, escala, opacidad y profundidad.
- Entre 5 y 9 elementos visibles según el ancho.
- Elemento central destacado.
- Panel inferior con artista, año, canciones y acciones.
- Navegación por flechas y snapping.
- Ilusión de reflejo sin shaders ni efectos externos costosos.

### 5.3 Vinyl Wall

Propósito: representación física y coleccionista.

- Funda y disco superpuestos.
- Desplazamiento lateral del vinilo en hover/foco.
- Rotación limitada al elemento interactivo.
- Cuadrícula adaptativa y paginada.
- Metadatos de edición visibles sin saturar la composición.

### 5.4 Timeline View

Propósito: lectura histórica de la colección.

- Agrupación por año o década.
- Cabeceras de sección persistentes.
- Línea temporal vertical con nodos.
- Filas con carátula, año, artista y cantidad de canciones.
- Reproducción rápida y navegación por teclado.

### 5.5 Magazine View

Propósito: experiencia editorial y descubrimiento.

- Hero rotatorio basado en álbumes reales.
- Rail horizontal de descubrimiento.
- Archivo editorial con numeración de edición.
- Sin categorías ficticias como “Hi-Res” cuando el modelo no contiene datos de calidad por álbum.
- Acciones de reproducción y detalle visibles.

## 6. Mejoras funcionales incluidas

- Propagación completa de filtros a `TrackListModel`.
- Conteo y página utilizan exactamente los mismos filtros.
- Selección múltiple reactiva y encapsulada mediante señal `selectionChanged`.
- Acciones masivas reales: reproducir, encolar y favorito.
- Menú contextual con identificadores canónicos y llamadas directas válidas.
- Estados QML alineados con `LibraryState`.
- Parámetros de ruta entregados por `PageStack`.
- Detalle de álbum con modelo local, reproducción, mezcla y cola.
- Detalle de artista con modelos locales derivados, reproducción, mezcla y cola.
- Etiqueta de cuarta pestaña corregida a Carpetas.
- Barra de filtros reconstruida con formatos, favoritos, no reproducidos, ausentes, género y año.

## 7. Fases siguientes

### Fase A — estabilización inmediata

- Ejecutar compilación de cada componente QML.
- Corregir cualquier warning `ReferenceError`, `Binding loop` o `Cannot assign`.
- Verificar consultas de filtros con SQLite real.
- Probar navegación Biblioteca → Álbum → Volver y Biblioteca → Artista → Volver.
- Verificar selección con Ctrl, Shift y Ctrl+A.

### Fase B — capacidades premium de catálogo

- Persistir la vista elegida por usuario.
- Añadir densidad Compacta / Cómoda / Galería.
- Añadir orden específico de álbumes: título, artista, año, agregado recientemente y más reproducido.
- Añadir filtros dinámicos obtenidos desde la base de datos, no escritos manualmente.
- Añadir favoritos de álbum y artista en el dominio.
- Añadir menú contextual homogéneo a álbumes y artistas.

### Fase C — inteligencia local

- Colecciones inteligentes basadas en reglas.
- Álbumes incompletos, duplicados y metadatos sospechosos.
- Agrupación configurable de ediciones y remasterizaciones.
- Sugerencias de carátulas y metadatos mediante servicios existentes de Michi.
- Magazine con secciones generadas desde estadísticas reales: recién añadidos, redescubrimientos, aniversarios y escuchas pendientes.

### Fase D — rendimiento extremo

- Medición con 10.000, 50.000 y 150.000 pistas.
- Presupuesto de 16 ms por frame durante scroll.
- Máximo de 9 delegates activos en CoverFlow.
- Caché de carátulas dimensionada según DPI y tamaño visible.
- Cancelación de consultas obsoletas en búsquedas rápidas.
- Cero carga de imágenes originales cuando una miniatura es suficiente.

## 8. Criterios de aceptación

### Funcionalidad

- Todos los filtros cambian resultados y total de forma coherente.
- Ninguna acción visible devuelve `NOT_FOUND` por un identificador incorrecto.
- Las cinco vistas abren detalle y reproducen álbumes.
- Cambiar de vista conserva búsqueda y filtros.
- Volver desde detalles restaura Biblioteca sin alterar el modelo global.
- La selección múltiple permanece sincronizada entre filas y barra contextual.

### UX y accesibilidad

- Todos los elementos interactivos tienen nombre accesible.
- El foco es visible en teclado.
- Los textos largos usan `elide` o wrap controlado.
- La interfaz es utilizable a 800, 1200 y 1600 px.
- No se depende exclusivamente de hover para ejecutar una acción.

### Rendimiento

- Sin consultas nuevas al alternar las cinco vistas.
- Sin `ShaderEffect` de alto costo.
- Animaciones solo en elementos visibles o interactivos.
- Paginación bloqueada correctamente durante `loadingMore`.
- Ningún modelo global se refresca al abrir un detalle.

## 9. Archivos principales

```text
ui_qml/pages/library/LibraryPage.qml
ui_qml/pages/library/LibraryFilterBar.qml
ui_qml/pages/library/LibraryTrackTable.qml
ui_qml/pages/library/LibrarySelectionBar.qml
ui_qml/pages/library/LibraryContextMenu.qml
ui_qml/pages/library/AlbumDetailPage.qml
ui_qml/pages/library/ArtistDetailPage.qml
ui_qml/pages/library/album/AlbumViewHost.qml
ui_qml/pages/library/album/AlbumGridView.qml
ui_qml/pages/library/album/AlbumCoverFlowView.qml
ui_qml/pages/library/album/AlbumVinylWallView.qml
ui_qml/pages/library/album/AlbumTimelineView.qml
ui_qml/pages/library/album/AlbumMagazineView.qml
ui_qml/models/TrackListModel.py
ui_qml_bridge/library_refresh_coordinator.py
ui_qml/shell/PageStack.qml
```
