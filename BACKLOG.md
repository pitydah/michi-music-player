# Backlog — Michi Music Player

Generado: 2026-07-28
HEAD: 33a8c835

---

## P0 — Bloqueantes funcionales

### P0-HA1: WebSocket nativo para Home Assistant

**Problema:** `HomeAssistantService` usa REST polling síncrono cada 5s. No hay suscripción a eventos, no hay tiempo real, cada estado requiere HTTP round-trip completo.

**Solución:** Implementar `HomeAssistantWebSocketClient` que:
- Conecte a `ws://host:port/api/websocket`
- Autentique con token
- Subscribe a `state_changed` para `media_player.*`
- Emita señales Qt en cada evento delta
- Use REST como fallback cuando WebSocket no esté disponible

**Archivos:**
- `integrations/home_audio_service.py` — nuevo WebSocket client
- `ui_qml_bridge/home_audio_bridge.py` — conectar señal `state_changed`

**Tests:** 5-8 tests de integración con mock WebSocket server

---

### P0-GST1: Gapless con pipeline GStreamer real

**Problema:** `test_queue_gapless_reconciliation.py` prueba el two-phase commit con mocks, no con pipeline GStreamer real. La transición `about-to-finish → STREAM_START` nunca se verificó con audio físico.

**Solución:** Agregar test de integración que:
- Cree pipeline GStreamer real con `audiotestsrc`
- Conecte dos archivos de prueba
- Verifique que no hay silencio entre pistas
- Verifique `_gapless_pending_index` y `_commit_gapless_progress`

**Archivos:**
- `tests/test_gapless_real_pipeline.py`

**Dependencias:** GStreamer con `audiotestsrc`, `wavenc`

---

## P1 — Necesario para declarar completo

### P1-HA2: Política atomic/best_effort para rutas

**Problema:** `update_route()` falla o pasa atómicamente, pero no hay política seleccionable. Para rutas multi-destino, el usuario puede preferir `best_effort` (conservar éxitos parciales).

**Solución:**
```python
class RouteTransaction:
    def __init__(self, mode="atomic"):
        self.mode = mode  # atomic | best_effort
        self._snapshots = []
    
    def commit(self): ...
    def rollback(self): ...
```

**Archivos:**
- `core/home_audio_service.py` — agregar `RouteTransaction`
- `ui_qml_bridge/home_audio_bridge.py` — slot con parámetro `mode`

---

### P1-HA3: Chain Planner — implementar o remover

**Problema:** `home_audio.chain_planner` es placeholder permanente. Si no hay plan de implementarlo, debe removerse del sidebar.

**Opción A — Remover:**
- Cambiar `route_registry.py` a `status: "removed"` y ocultar del sidebar

**Opción B — Implementar (alcance estimado: 5-8 días):**
- `ChainPlannerService` — modelos de componentes (DAC, preamp, crossover, amp, speakers)
- `ChainPlannerBridge` — fachada QML
- `ChainPlannerPage.qml` — grafo interactivo de señal
- Validación de compatibilidad de formatos y conexiones
- Perfiles guardados

---

### P1-TEST1: audio_lab segfault en collection

**Problema:** `ModuleNotFoundError: No module named 'core.audio_lab.audio_lab_contracts'` ocurre cuando tests de audio_lab se ejecutan como suite. `core.audio_lab` se convierte en namespace package en vez de regular package.

**Solución:**
- Verificar que `core/__init__.py` existe y tiene contenido
- Verificar que `core/audio_lab/__init__.py` usa imports diferidos
- Agregar test que importe `core.audio_lab` antes que cualquier sub-módulo

**Archivos:**
- `core/__init__.py`
- `core/audio_lab/__init__.py`

---

## P2 — Mejora continua

### P2-ICON1: Migración completa a Fluent System Icons

**Problema:** ~38 iconos SVG propios mezclados con PNGs. No hay familia unificada.

**Solución:**
- Importar subconjunto mínimo de Fluent System Icons (SVG regular + filled)
- Reemplazar iconos propios uno por uno
- Mantener iconos de marca (Michi logo) como propios
- Actualizar `icon_registry.py` para usar la familia unificada

**Archivos:**
- `icons/` — reemplazar por `ui_qml/assets/icons/fluent/regular/` y `filled/`
- `ui_qml/theme/MichiIcon.qml` — nuevo componente canónico
- `ui/icon_registry.py` — actualizar mapa

---

### P2-ORPHAN1: 30 páginas huérfanas

**Problema:** 30 archivos `*Page.qml` no tienen entrada en `ROUTES`. 7 están realmente muertas (MetadataEditorPage, LatencyPage, StreamRoutingPage, SmartTaggingWorkflowPage, LibrarySourcesPage, CapabilityAwarePage, SettingsCategoryPage). Las otras 23 son cargadas por otras páginas o solo por tests.

**Solución:**
- Eliminar las 7 páginas realmente muertas
- Las 23 cargadas dinámicamente dejar documentación de su mecanismo de carga

---

### P2-VISUAL1: Light mode post-refactor

**Problema:** La refactorización visual P0-UI0 a UI12 se probó principalmente en dark mode. Light mode puede tener regresiones.

**Solución:**
- Ejecutar suite de tests visuales con `MichiTheme.lightMode = true`
- Verificar contraste de textos, bordes, superficies
- Ajustar tokens de light mode donde sea necesario

---

## P3 — Deuda técnica / Dependiente de hardware

### P3-HA4: Calibración de latencia por receptor

**Problema:** No hay forma de medir/ajustar latencia por receptor Snapcast. La UI tiene campo de latencia pero no hay calibración.

**Solución:** Implementar `measureLatency(receiverId)` que emita un tono de prueba y mida el desfase contra la salida local.

**Dependencias:** Altavoz físico + micrófono, o medición manual

---

### P3-HW1: Pruebas con hardware Snapcast real

**Problema:** Toda la integración Snapcast se probó con simulación. No hay verificación con Snapserver + Snapclient reales.

**Requerido:** 
- Snapserver (localhost o remoto)
- Al menos 1 Snapclient (Raspberry Pi, desktop, o snapclient CLI)
- Home Assistant opcional

---

### P3-TEST2: 624 tests pre-existentes

**Problema:** ~624 tests fallan en la suite completa. Son mayoritariamente test pollution, no bugs de implementación. Incluyen:
- audio_lab collection segfault (P1-TEST1)
- keyboard/accessibility tests que buscan strings literales en QML
- workflow tests que pasan individuales pero fallan en suite

**Estrategia:** No priorizar. Son ruido de tests, no afectan funcionalidad productiva.

---

### P3-HW2: Disc Lab eject() físico

**Problema:** `eject()` llama a `subprocess.run(["eject", drive])`. No se probó con unidad CD real.

**Dependencias:** Unidad CD/DVD física

---

## Resumen por prioridad

| Prioridad | Items | Esfuerzo estimado |
|-----------|-------|-------------------|
| **P0** | 2 (WebSocket HA + Gapless real) | 3-4 días |
| **P1** | 3 (atomic policy + Chain Planner + audio_lab) | 5-10 días |
| **P2** | 3 (iconos + orphan pages + light mode) | 3-5 días |
| **P3** | 4 (latencia + HW tests + 624 failures + eject) | Variable |

**Total estimado:** 14-23 días hábiles para cerrar todo el backlog conocido.
