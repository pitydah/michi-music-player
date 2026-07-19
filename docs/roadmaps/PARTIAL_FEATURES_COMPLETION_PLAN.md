# Plan de cierre de funcionalidades parciales

Estado base: `0.10.0-alpha.1`  
Alcance: Michi Music Player, exclusivamente audio.

## Principios obligatorios

1. Una ruta cargable no se considera funcional si solo muestra un hub, datos simulados o una página de estado.
2. Ninguna operación destructiva puede informar éxito sin verificar su resultado.
3. Los trabajos largos deben ser cancelables, observables y recuperables.
4. MSC y MTP son los transportes base para reproductores portátiles. No se implementará sincronización ni conversión de video.
5. Cada promoción `planned -> partial -> functional` exige backend, bridge, QML, pruebas negativas y al menos una prueba de integración.

## Fase 1 — Estabilización y Sync Suite MVP

Implementada en PR #121.

### Mix

Archivos:

- `core/mix_query_service.py`
- `ui_qml_bridge/mix_bridge.py`
- `tests/test_mix_query_service_limits.py`

Entregables:

- corregir el enlace de parámetros en consultas por artista, género, década, año, calidad y redescubrimiento;
- aplicar un único `LIMIT ?` acotado;
- mantener una forma homogénea de pista;
- registrar fallos SQL sin cerrar la aplicación.

Criterio de aceptación:

- las consultas no producen listas vacías por desajuste de parámetros;
- el límite máximo evita cargas accidentales de bibliotecas completas;
- las pruebas verifican SQL y parámetros.

### Ajustes transaccionales

Archivos:

- `ui_qml_bridge/settings_bridge_v2.py`
- `ui_qml/pages/SettingsPage.qml`
- `ui_qml/components/settings/SettingsRow.qml`
- `tests/test_settings_bridge_v2_transactions.py`

Entregables:

- dirty state global y contador de cambios;
- commit individual/global;
- rollback individual/global;
- restauración de valores originales después de `resetAll`;
- barra QML Aplicar/Descartar pendiente de integrar en la fase 2.

### Reproductores portátiles

Archivos:

- `ui_qml/pages/sync/PortablePlayersPlaceholderPage.qml`
- `ui_qml_bridge/devices_bridge.py`
- servicio registrado como `device_sync_service`;
- pruebas QML de rutas y pruebas físicas posteriores.

MVP:

- descubrimiento MSC/MTP;
- identificación y emparejamiento;
- selección de origen y destino;
- validación estricta de audio;
- transferencia y visualización de trabajos.

### Planes e historial

Archivos:

- `ui_qml/pages/sync/SyncPlansPlaceholderPage.qml`
- `ui_qml/pages/sync/SyncHistoryPlaceholderPage.qml`
- `ui_qml/pages/sync/SyncHubPage.qml`

MVP:

- previsualización manual;
- patrón de nombres;
- política de colisiones;
- estimación mediante el servicio disponible;
- ejecución manual;
- historial, búsqueda, cancelación y reintento.

Pendiente para promover las rutas:

- cambiar `route_registry.py` de `planned` a `partial` o `functional`;
- renombrar las páginas eliminando `Placeholder`;
- actualizar `tests/qml/test_placeholder_routes_runtime.py`;
- validar con dispositivos HiBy, FiiO, Ruizu y almacenamiento USB genérico.

## Fase 2 — Ajustes, Home Audio y metadatos

### 2.1 Cierre de Ajustes QML

Implementar en `SettingsPage.qml`:

- `hasChanges()` delegado a `settingsBridgeV2.hasPendingChanges`;
- banner persistente con contador;
- botones `Aplicar cambios` y `Descartar cambios`;
- confirmación al abandonar la página;
- recarga controlada de `SettingsRow` después de commit o rollback;
- indicación de ajustes que requieren reinicio.

Pruebas:

- cambio -> dirty;
- volver al valor inicial -> clean;
- rollback global;
- reset global -> rollback;
- navegación con cambios pendientes.

### 2.2 Distribución de audio

Problema actual: las tarjetas Fuentes, Servidores, Receptores, Destinos y Rutas activas vuelven al mismo hub.

Archivos objetivo:

- `ui_qml/pages/home_audio/DistributionHubPage.qml`
- `ui_qml_bridge/home_audio_bridge.py`
- `core/home_audio/*`
- nuevas páginas de detalle bajo `ui_qml/pages/home_audio/distribution/`.

Contratos:

- `sources`: origen, formato, sample rate, estado;
- `servers`: Snapserver/Michi server, endpoint, salud;
- `receivers`: Snapclient/Michi Music Stream, latencia, volumen;
- `destinations`: salida física o zona;
- `routes`: source_id, destination_ids, estado, latencia y error.

Acciones mínimas:

- crear/detener ruta;
- asignar receptor;
- cambiar destino;
- mostrar pérdida de conexión;
- recuperación sin falso éxito.

### 2.3 Habitaciones y zonas

Completar:

- creación, edición y eliminación de zona;
- agrupación/desagrupación;
- asignación de receptores;
- volumen y mute por zona;
- latencia y estado;
- persistencia y restauración tras reinicio.

### 2.4 Smart Tagging y metadata batch

Backend disponible: escaneo asíncrono, selección por confianza, backup, escritura segura, verificación y rollback.

Falta QML:

- selección múltiple desde biblioteca;
- revisión por pista y por campo;
- aplicar solo sugerencias seleccionadas;
- resumen de lote;
- errores parciales;
- rollback visible;
- actualización inmediata de biblioteca.

Promoción a funcional solo con pruebas sobre MP3, FLAC, OGG/Opus y M4A.

## Fase 3 — Audio Lab productivo

### 3.1 Análisis técnico

- caché por `filepath + mtime + size`;
- invalidación al modificar archivo;
- comprobación de FFmpeg/ffprobe al inicio;
- fallback reducido y mensaje accionable.

### 3.2 Conversión

- estimación de tamaño y espacio libre;
- política explícita de metadatos y carátula;
- archivo temporal + reemplazo atómico;
- reporte automático de fallos;
- progreso agregado e individual;
- pruebas de FLAC, MP3, AAC, Opus y WAV.

### 3.3 Normalización y ReplayGain

- separar visualmente normalización destructiva y ReplayGain;
- track gain y album gain;
- procesamiento por álbum;
- presets descriptivos configurables;
- true peak limit;
- autoanálisis opcional al importar;
- rescaneo selectivo.

### 3.4 Comparación

- reproducción A/B sincronizada;
- igualación de loudness para comparar;
- SNR, rango dinámico y diferencias espectrales;
- comparación de dos archivos en el MVP; N archivos solo después de estabilizar A/B.

### 3.5 Trabajos por lote

- drag and drop;
- selección Shift/Ctrl;
- cancelación por trabajo y global;
- notificación desktop;
- scheduler persistente, no `QTimer.singleShot` como solución definitiva;
- recuperación tras reinicio.

## Fase 4 — Streaming e integraciones

### 4.1 Podcasts

MVP:

- suscripción RSS/Atom;
- actualización condicional HTTP;
- episodios reproducidos/no reproducidos;
- descarga opcional de audio;
- cola y reproducción con el motor normal;
- límites de caché;
- sin video podcasts.

No implementar sincronización de transcripciones ni funciones visuales.

### 4.2 Michi Micro Server

- descubrimiento mDNS;
- pairing autenticado;
- biblioteca remota;
- streaming y playlists;
- transferencia de reproducción;
- manejo offline;
- pruebas E2E Player <-> Micro Server.

### 4.3 Navidrome/Subsonic

- autenticación segura;
- navegación paginada;
- búsqueda;
- streaming;
- playlists compatibles;
- caché de carátulas;
- errores de red diferenciados.

### 4.4 Jellyfin

Alcance exclusivamente musical:

- bibliotecas de música;
- artistas, álbumes y pistas;
- streaming de audio;
- playlists;
- ignorar películas, series y reproducción de video.

### 4.5 Home Assistant

- configuración URL/token;
- prueba de conexión;
- entidades de reproducción;
- zonas y grupos;
- servicios play/pause/volume/route;
- no bloquear el hilo UI.

### 4.6 Michi Big Server

No promover hasta estabilizar el protocolo común con Micro Server. El Player debe consumir una interfaz de servidor compartida y no ramas específicas por producto.

## Fase 5 — Beta y distribución

Bloqueadores:

- elevar coverage gate desde 25 % de forma gradual;
- eliminar o justificar pruebas `.skip`/`xfail` críticas;
- pruebas QML con ventana visible/Xvfb;
- smoke tests de todas las rutas;
- perfiles de rendimiento con biblioteca grande;
- auditoría de memoria y cancelación;
- Flatpak y AppImage reproducibles;
- paquete Windows posterior al cierre de dependencias nativas;
- documentación de usuario y diagnóstico de dependencias.

## Definición de terminado por módulo

Un módulo alcanza `functional` cuando cumple todo lo siguiente:

- servicio productivo sin datos mock;
- bridge con resultados tipados y sin falso éxito;
- estados loading/ready/empty/error;
- cancelación cuando corresponda;
- recuperación o rollback;
- accesibilidad por teclado;
- diseño responsive;
- pruebas unitarias, negativas y de integración;
- documentación mínima;
- ruta y badges coherentes con su estado real.
