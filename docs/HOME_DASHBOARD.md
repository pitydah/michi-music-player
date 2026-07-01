# Home Dashboard — Centro de Situación Michi

## 1. Propósito

El apartado Inicio (Home Dashboard) responde tres preguntas:

1. **¿Está todo bien?** — Estado general del sistema.
2. **¿Qué puedo continuar?** — Reproducción activa o reciente.
3. **¿Qué requiere atención?** — Alertas, errores, acciones pendientes.

No es una copia de Biblioteca, Mix, Playlists, Conexiones o Audio Lab.
Es una vista premium, limpia y operativa del estado actual del ecosistema Michi.

## 2. Arquitectura

```
Sidebar "Inicio"
  → HomeController.show()
    → HomeDashboardService.build_snapshot()
      → HomeDashboardSnapshot (dataclass tipada)
    → HomePage.render_snapshot(snapshot)
      → 7 glass cards visuales
```

### Capas

| Capa | Archivo | Responsabilidad |
|------|---------|-----------------|
| Dataclasses | `core/home/home_status.py` | 9 tipos: HomeDashboardSnapshot, LibraryHomeStatus, PlaybackHomeStatus, AudioHomeStatus, EcosystemHomeStatus, HomeAlert, AssistantSuggestion, HomeAction, HomeCardError |
| Servicio | `core/home/home_dashboard_service.py` | Construye el snapshot desde servicios existentes. Tolerancia total a fallos parciales |
| Controlador | `ui/controllers/home_controller.py` | Coordina ciclo de vida, refresh, señales, importación |
| Vista | `ui/hubs/home_page.py` | Renderiza 7 cards desde el snapshot. Sin lógica de negocio |
| Estilos | `ui/central/central_styles.py` | Funciones QSS: home_page_qss, home_headline_qss, home_badge_qss, home_metric_value/label, home_alert_item |

## 3. Fuentes de datos

| Card | Fuente principal | Fallback |
|------|------------------|----------|
| Estado general | `HomeDashboardSnapshot.overall_state` + badges | — |
| Continuar | `PlayerService.state`, `PlayerService.current` | `ContextService.get_home_snapshot()` |
| Biblioteca | `ContextService.get_home_snapshot()` → `library_health` | `LibraryDB.get_dashboard_stats()` |
| Audio | `PlayerService.get_output_device_id()`, `get_eq_state()`, `get_audio_diagnostics()` + settings | Valores por defecto |
| Ecosistema | `MichiLinkController.get_connection_state()` (Micro Server), `SyncManager.get_all_peers()`, settings | `disconnected` / `no_device` |
| Atención | `_build_alerts()` desde library + audio + ecosystem | Lista vacía |
| Assistant | `ContextService.get_assistant_snapshot()` | Fallback inteligente desde library health |

## 4. Estados globales

| overall_state | headline | Cuándo ocurre |
|---------------|----------|---------------|
| `ready` | Michi está listo | Biblioteca sana, sin errores |
| `empty_library` | Agrega música para comenzar | `track_count == 0` |
| `playback_active` | Michi está sonando | `PlayerService.state == "playing"` |
| `needs_attention` | Michi requiere atención | `index_error_count > 0` o `missing_file_count > 0` |
| `safe_mode` | Michi está en modo seguro | `MICHI_SAFE_MODE=1` |
| `limited_services` | Servicios limitados | Micro Server requiere pairing |
| `error` | Error al cargar | Excepción en `build_snapshot()` |

## 5. Cards

### A. Estado general
- Headline grande (26px bold)
- Subtítulo informativo (canciones, indexación, salida audio, Micro Server)
- Badges: Biblioteca OK, DAC activo, Micro conectado, Modo seguro, etc.

### B. Continuar
- Pista actual: título, artista, álbum, estado (playing/paused)
- Última pista si no hay actual
- Cola activa
- Botones: Continuar, Ver cola, Continuar en Micro Server
- Si no hay historial: Explorar biblioteca, Crear mix

### C. Biblioteca
- Métricas: canciones, álbumes, artistas, géneros
- Última indexación
- Errores de índice / archivos faltantes
- Botones: Escanear ahora, Ver biblioteca, Revisar problemas

### D. Audio
- Dispositivo de salida
- Perfil activo
- Estado ReplayGain, EQ, DSP
- Bit-Perfect (verified / not_verified / not_available)
- Botones: Configurar salida, Abrir Audio Lab, Diagnóstico

### E. Ecosistema Michi
- Michi Micro Server (conectado/desconectado/pairing/error)
- Mobile Sync (dispositivos, estado)
- API local (activa/inactiva)
- Home Audio (activo/experimental/desactivado)
- Botones: Conectar servidor, Sincronizar móvil, Diagnóstico

### F. Atención requerida
- Máximo 5 alertas priorizadas: critical > warning > info
- Cada alerta tiene título, mensaje, acción y ruta
- Si hay más de 5, resumen con "Ver todo"

### G. Michi Assistant
- Máximo 3 sugerencias contextuales
- Fallback: limpiar metadata, buscar carátulas, explorar biblioteca
- Botón: Abrir Asistente

## 6. Alertas

Jerarquía:
1. **critical**: errores de indexación, archivos faltantes, safe mode
2. **warning**: metadatos incompletos, carátulas faltantes, sync error, pairing pendiente
3. **info**: Micro Server desconectado, audio features pendientes

Constante: `MAX_HOME_ALERTS = 5`
Si hay más de 5: 4 reales + 1 resumen.

## 7. Assistant

Las sugerencias se obtienen de `ContextService.get_assistant_snapshot()`.
Si no está disponible, se genera un fallback desde `LibraryHomeStatus`:

1. `missing_metadata_count > 0` → "Limpiar metadatos"
2. `missing_cover_count > 0` → "Buscar carátulas"
3. `track_count > 0` y no hay continuación → "Explorar biblioteca"
4. Fallback final → "Añadir música"

Máximo 3 sugerencias.

## 8. Ecosistema Michi

### Michi Micro Server
Estado real vía `MichiLinkController.get_connection_state()`.
No se usa `streaming.subsonic_client` — eso es para servidores Subsonic/Navidrome/Jellyfin.

### Mobile Sync
Vía `SyncManager.get_all_peers()`.
Estados: `no_device`, `paired`, `syncing`, `error`.

### API local
Vía settings `michi_api/enabled`.
Si existe objeto runtime (`MichiLinkController`), se usa estado runtime.

### Home Audio
Settings `home_audio/ha_base_url`.
Estados: `active` (configurado), `experimental` (no configurado pero disponible), `disabled` (safe mode o no disponible).

## 9. Testing

### Tests unitarios
```bash
python -m pytest tests/test_home_dashboard_service.py -q   # 41 tests
python -m pytest tests/test_home_controller.py -q         # 19 tests
python -m pytest tests/test_home_page.py -q               # 24 tests
python -m pytest tests/test_home_routes_contract.py -q    # 3 tests
python -m pytest tests/test_spectral_analysis.py -q       # 18 tests
python -m pytest tests/test_post_refactor_regressions.py -q # 4 tests
```

### Tests de contexto
```bash
python -m pytest tests/test_home_context_snapshot.py -q
python -m pytest tests/test_context_snapshot.py -q
python -m pytest tests/test_assistant_snapshot_contract.py -q
```

### Smoke
```bash
QT_QPA_PLATFORM=offscreen python scripts/smoke_startup.py
QT_QPA_PLATFORM=offscreen python scripts/smoke_ui_routes.py
```

### Suite amplia
```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests -m "not perf" -q
```

## 10. Limitaciones conocidas

- `can_continue_remote` se calcula desde `ecosystem.diagnostics_available` como proxy hasta que exista un servicio dedicado de "continue on server".
- `_dict_to_snapshot()` en HomePage solo resuelve library y playback parcialmente. Usar siempre `HomeDashboardSnapshot` tipado.
- `AudioHomeStatus.bitperfect_state` se deduce del perfil + ausencia de DSP, no de una verificación hardware real.
- `EcosystemHomeStatus.home_audio_state` no puede ser "active" sin configuración — es "experimental" o "disabled".

## 11. Commands de validación rápida

```bash
ruff check . --output-format concise
python -m compileall -q -x '.venv/|\.tmpl\.' .
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_home_dashboard_service.py tests/test_home_controller.py tests/test_home_page.py tests/test_home_routes_contract.py tests/test_spectral_analysis.py -q
```
