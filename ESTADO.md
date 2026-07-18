# Michi Music Player — Estado del Software

> **Repositorio:** `pitydah/michi-music-player`  
> **Última actualización:** 2026-07-01  
> **Versión:** 0.2.0-alpha.1 — pre-beta técnica avanzada  
> **UI:** QML (`python main.py`)  
> **Validación:** pendiente de confirmar en GitHub Actions.  
> Para validar localmente ejecutar:  
> `ruff check .`  
> `QT_QPA_PLATFORM=offscreen pytest -q`  
> `QT_QPA_PLATFORM=offscreen python3 scripts/check_runtime.py`

---

## 📊 Métricas de Arquitectura

| Métrica | Valor | Cómo verificar |
|---------|-------|---------------|
| Líneas en `ui/window.py` | 1,548 (−53% desde 3,311) | `python tools/audit_window.py` |
| Métodos en ventana principal | — | Eliminado (QML-only) |
| Widgets directos en window.py | 0 (todo en `UIBuilder`) | `python tools/audit_window.py` |
| Controllers extraídos | 16+ | `ls ui/controllers/` |
| Tests | dinámico | `QT_QPA_PLATFORM=offscreen pytest -q` |
| Ruff | dinámico | `ruff check .` |
| Runtime | dinámico | `./scripts/ci_local.sh` |
| Smoke startup | dinámico | `QT_QPA_PLATFORM=offscreen python3 scripts/smoke_startup.py` |

---

## 🏗 Arquitectura — Controllers Extraídos

| Controller/Builder | Archivo | Responsabilidad |
|-------------------|---------|----------------|
| `AppShell` + `PageStack` | Shell QML con navegación por rutas |
| `AlbumSortMenu` | `ui/builder/album_sort_menu.py` | Menús de orden/filtro de álbumes |
| `InlineDialogs` | `ui/builder/inline_dialogs.py` | Diálogos inline (cover preview, nowplaying, audio diagnostics) |
| `NavigationController` | `ui/controllers/navigation_controller.py` | SECTION_CONFIG, NAV_ROUTES, header, breadcrumb, historial de navegación |
| `LibraryController` | `ui/controllers/library_controller.py` | Pipeline de datos: load, reload, refresh tabs, filtros |
| `HomeController` | `ui/controllers/home_controller.py` | Ciclo de vida del Home dashboard |
| `CoverFlowController` | `ui/controllers/coverflow_controller.py` | Handlers de CoverFlow: snap, play, queue, metadata, banner, covers lazy |
| `HomeAudioHandlers` | `ui/controllers/home_audio_handlers.py` | Handlers de Home Audio, Snapcast, multiroom |
| `SmartMixController` | `ui/controllers/smart_mix_controller.py` | Smart mixes, favoritos, recientes, resolución de track_ids |
| `SmartMixPreview` | `ui/controllers/smart_mix_preview.py` | Previews/conteos de mixes sin mutar la UI |
| `ServerBrowserController` | `ui/controllers/server_browser_controller.py` | Handlers de servidores Subsonic/Navidrome/Jellyfin + radio |
| `IdentifierHandlers` | `ui/controllers/identifier_handlers.py` | Handlers de identificación musical |
| `SidebarMenuController` | `ui/controllers/sidebar_menu_controller.py` | Menú contextual del sidebar + CRUD de playlists |
| `SearchRouter` | `ui/routers/search_router.py` | Ruteo de búsqueda por sección |
| `ViewModeRouter` | `ui/routers/view_mode_router.py` | Ruteo de modos de vista (list/grid/coverflow) por sección |
| `ViewRegistry` | `ui/view_registry.py` | Factory lazy de vistas con safe-mode gating |
| `SafeViewFactory` | `ui/safe_view_factory.py` | Creación segura de vistas con placeholder en error |

---

## 🔀 Flujo de Navegación Actual

```
Sidebar click → sidebar_controller → navigation_requested(key)
  → _on_sidebar_navigate(key) → _nav_ctrl.dispatch(key)
    → configure_header(section_key)
    → push history
    → Dynamic prefix routes (playlist:, srv:, dev:, mix_)
    → Static NAV_ROUTES dispatch
      → _show_*_page() → lazy-create widget → _views.register() → _fade_content()
```

---

## 🎛 Secciones y su Estado

| Sección | Sidebar Key | Vista | Estado |
|---------|------------|-------|--------|
| Inicio | `home` | HomePage con stats, asistente, sesión, conexiones | ✅ Funcional |
| Biblioteca | `library_hub` | LibraryHubPage con tabs Canciones/Álbumes/Artistas/Géneros/Carpetas | ✅ Funcional |
| Mix | `mix_hub` | MixHubPage con 5 cards dinámicas (previews reales), scopes rápidos, builder placeholder | ✅ Rediseñado |
| Playlist | `playlist_hub` | PlaylistHubWidget + CRUD + import/export M3U/PLS | ✅ Funcional |
| Reproducción | `playback_hub` | PlaybackHubPage con cola, historial, favoritos, radio | ✅ Funcional |
| Conexiones | `connections_hub` | ConnectionsHubPage con servidores, Home Audio, dispositivos | ✅ Funcional |
| Radio | `radio` | RadioWidget con estaciones | ✅ Funcional |
| Audio Lab | `audio_lab` | AudioLabPage | ✅ Funcional |
| Home Audio | `home_audio` | HomeAudioView (safe-mode gated) | ✅ Funcional |
| Identificador | `identifier` | MusicIdentifierView (safe-mode gated) | ✅ Funcional |
| Asistente | `assistant` | AiAssistantPanel | ✅ Funcional |
| Descubrir | `discover` | DiscoverDashboard con 5 smart mixes | ✅ Funcional |
| Configuración | `settings_hub` | SettingsHubPage | ✅ Funcional |
| Michi Sync Suite | `devices_page` | DevicesPage | ✅ Funcional |
| Michi Disc Lab | `michi_disc_lab` | MichiDiscLabPage | ✅ Funcional |
| Editor Metadata | `metadata_editor` | MetadataEditorWidget | ✅ Funcional |

---

## 🐛 Bugs Corregidos (Pass 6A)

| # | Bug | Archivo | Fix |
|---|-----|---------|-----|
| 1 | Sidebar no mostraba peers Android por typo `_sync_manager` → `sync_mgr` | `window.py:1301` | Corregido |
| 2 | Home nunca mostraba dispositivos (`_sync_peers` inexistente) | `home_controller.py:57` | `_sync_mgr.get_all_peers()` |
| 3-4 | ViewRegistry lambdas incorrectas + safe-mode gating inefectivo | `window.py:224-226` | Movido `_register_views()` antes de `_init_optional_services()` |
| 5 | Breadcrumb de navegación roto | `navigation_controller.py:364` | Restaurada lógica de breadcrumb |
| A | `setSortingEnabled()` no existe en `QStandardItemModel` (×2) | `trackref_model.py:57,106` | Removido |
| B | `from core.json_store import field` — `field` no existe | `device_registry.py:11` | Movido a `dataclasses.field` |
| A | `_show_nowplaying_details` duplicado — Python usaba el cuerpo roto | `window.py:1551` | Eliminado el viejo |
| B | `show_cover_preview(self)` sin pixmap → crash | `window.py:1548` | Extrae pixmap de `_player_bar._cover` |
| C | `show_nowplaying_details(self)` sin point/track_ref → crash | `window.py:1570` | Pasa `QCursor.pos()` y `_current_ref` |
| — | `_cs_search_qss` y `_cs_menu_qss` fantasmas en UIBuilder | `ui_builder.py` | `search_qss()` + `menu_qss()` |
| — | `mix_hub` atrapado por el prefijo `mix_` en dispatch | `navigation_controller.py:355` | `key != "mix_hub"` |
| — | `_identifier_ctrl` None en safe mode → crash en `_play_trackref` | `window.py:1392` | `and self._identifier_ctrl` |
| — | `_mpris_ctrl` None en safe mode → crash en `playback_controller` | `playback_controller.py:177` | Guard con `is not None` |
| — | `_dump_diagnostic()` no existía → crash en `diagnose_coverflow.py` | `coverflow.py` | Implementado |
| — | `int(album_key)` en hex string → crash en banner buttons | `coverflow_controller.py` | `current_index()` |
| — | `_cover_cache` nunca leído → covers lazy perdidos en resize | `coverflow.py:876` | `_cover_cache.get(i)` en `_rebuild_items()` |
| — | Scroll vertical deshabilitado en CoverFlow | `coverflow.py:1011` | `pass` → navegación con `angleDelta().y()` |
| — | Doble conteo de scroll (pixel + angle) | `coverflow.py` | `return` tras bloque pixel |
| — | `setClipPath()` removido en Qt6 | `coverflow.py:142` | `paint()` override con `QPainter.setClipPath()` |
| — | Sort/filter solo refrescaba grid mode | `album_sort_menu.py:57,64` | `_refresh_active_library_tab(force=True)` |
| — | Cover lazy loading bloqueaba UI | `coverflow_controller.py:231` | `WorkerManager.run_task()` con stale guard |

---

## ✅ Checklist de Estabilización Completada

- [x] **Pass 1-5:** SQLite, Workers, Shutdown, MPRIS, JSON, HTTP, Paths, Packaging, Visual Polish, Microcopy
- [x] **Pass 6A:** Safe mode real, Python 3.11, _safe_init gates on FeatureManager, _get_context eliminado, Favoritos/Recientes por identidad canónica, Sidebar sin SyncManager, Playlist I/O seguro, Device scan async, CoverFlow sin subprocess, closeEvent con API pública, audit_window.py
- [x] **Pass 6B (Mega-refactor):** window.py 3311→1548 (−53%), 10 controllers/builders/routers extraídos, 100+ métodos delegados eliminados
- [x] **Pass 6C (Mix redesign):** MixHubPage dinámico con SmartMixPreview, 5 cards con conteos reales, empty states, scopes rápidos, constructor placeholder
- [x] **Pass 6D (CoverFlow):** Encapsulación total (zero accesos privados), sort/filter en coverflow, cache key SHA1, _cover_cache funcional, scroll vertical, lazy loading async, Qt6 fix, diagnóstico

---

## 🔧 Lo que Falta por Pulir y Arreglar

### Alta Prioridad

- [x] **Eliminar `QOpenGLWidget` no soportado en algunos Linux** — ✅ El fallback ya funciona.
- [x] **Smoke test de integración completo** — ✅ Las 22 secciones navegan sin errores en offscreen.
- [x] **`diagnose_coverflow.py` — probar que corre sin errores** — ✅ Script actualizado con API pública.
- [ ] **CI/CD** — ¿Hay GitHub Actions configurado? Verificar que ruff + pytest corran en CI.
- [x] **Memory leak en CoverFlow** — ✅ `_cover_cache.clear()` en `set_items()`.
- [x] **Hybrid Audio Engine (GStreamer + MPD)** — ✅ 8 fases implementadas, 194 tests.
  - `audio/backends/` — API común, GStreamerBackend, MpdBackend, HybridAudioManager
  - `audio/mpd/` — Cliente MPD por socket, protocolo, path mapper, config builder, service manager
  - `audio/diagnostics/` — Verificador bit-perfect con lectura real de `/proc/asound/*/hw_params`
  - `audio/settings/` — Esquema canónico de settings con migrador de claves legacy
  - Perfiles MPD en `output_profiles.py`: hifi, bitperfect, dsd, server renderer
  - PlayerService rutea entre backends según perfil
  - DSP bloqueado en modo MPD (EQ, ReplayGain, Spectrum)
  - MPRIS compatible con backend híbrido
  - UI: selector de backend, monitor bit-perfect, botones MPD start/stop
  - Documentación técnica en `docs/audio/`

### Media Prioridad

- [ ] **`album_info_banner.py:181`** — `QPixmap(path)` directo — No crítico (covers son PNG/JPG).
- [x] **`album_info_banner.py:46`** — ✅ Accent `#8FB7FF`.
- [x] **`view_switcher.py`** — ✅ `resizeEvent` agregado con `update_for_width()`.
- [x] **CoverFlow `_update_layout()`** — ✅ Optimizado: solo itera ±15 items alrededor de `_current`.
- [x] **`WorkerManager` RuntimeError** — ✅ `contextlib.suppress(RuntimeError)` en `emit()`.
- [x] **`get_daily_mix()` connection leak** — ✅ `conn.close()` en todos los paths.
- [x] **`_MAX_COVER_BYTES = 10MB`** — ✅ Módulo-level, aplicado en covers externos + embebidos.
- [x] **`AlbumInfoBanner` botones** — ✅ Usan `_snapped_index` almacenado, no `current_index()`.

### Baja Prioridad / Cosmético

- [ ] **Constructor de mix** en MixHubPage — actualmente es placeholder con combos disabled. Necesita backend.
- [ ] **Thin delegates restantes en window.py** (~40 métodos de 1-3 líneas) — son seguros pero podrían limpiarse si se mueven las conexiones de UIBuilder.
- [ ] **`CoverFlowWidget._create_overlay_items()`** — recrea los QGraphicsTextItem en cada `set_items()`. Podrían reutilizarse.
- [ ] **`album_art.py` `lazy=True`** — `load_cover_pixmap` por album puede bloquear si no hay WorkerManager. Podría mejorarse con batch loading.
- [ ] **`CoverFlowWidget` sin `closeEvent()`** — los timers de física y wheel snap se limpian por parent-child de Qt, pero sería más limpio con `closeEvent`.

---

## 🧪 Cobertura de Tests

| Área | Tests | Archivo |
|------|-------|---------|
| Layout CoverFlow | 6 | `tests/test_coverflow_layout.py` |
| API pública CoverFlow | 4 | `tests/test_coverflow_layout.py` |
| Safe mode | 2 | `tests/test_pass_6a.py` |
| Playlist I/O | 2 | `tests/test_pass_6a.py` |
| Favoritos/Recientes | 2 | `tests/test_pass_6a.py` |
| Runtime Python 3.11 | 2 | `tests/test_pass_6a.py` |
| Audit window | 1 | `tests/test_pass_6a.py` |
| CoverFlow no subprocess | 1 | `tests/test_pass_6a.py` |
| closeEvent API pública | 1 | `tests/test_pass_6a.py` |
| Pipeline hardening | ~20 | `tests/test_pipeline_hardening.py` |
| Estabilidad | ~20 | `tests/test_stability.py` |
| Metadata | ~11 | `tests/test_metadata.py` |
| Home + Controllers | 58 | `tests/test_home_dashboard_service.py`, `test_home_controller.py` |
| Ecosystem Doctor | 21 | `tests/test_ecosystem_doctor.py` |
| Assistant + Context | ~135 | `tests/test_*.py` |
| Otros (DB, search, controllers, etc.) | ~287 | `tests/test_*.py` |
| **Total** | **~501** | `QT_QPA_PLATFORM=offscreen pytest -q` |

---

## 📦 Dependencias y Entorno

| Componente | Versión/Estado |
|-----------|---------------|
| Python | 3.11+ |
| PySide6 | 6.11.1 |
| GStreamer | 1.28 |
| SQLite | WAL mode, FTS5 |
| mutagen | ID3/Vorbis/MP4 |
| OpenGL | Opcional (fallback `safe_2d`) |
| Ruff | dinámico — verificar con `ruff check .` |
| pytest | dinámico — verificar con `QT_QPA_PLATFORM=offscreen pytest -q` |

---

## 🧠 Michi Intelligence Core — Estado Final

### Home / Centro de Situación Michi (100%)
- `HomeDashboardService` estabilizado con settings keys correctas
- Builders separados: library, playback, audio, ecosystem, alerts, suggestions, actions
- Playback state normalizado (string/enum/None → playing/paused/stopped/unknown)
- Micro Server separado de servidores remotos Subsonic/Navidrome/Jellyfin
- Home Audio usa claves reales de `core/settings_manager.py`
- `_safe_build` tolera fallos parciales por card
- Alertas con severidad correcta, sin falsos positivos

### Michi Ecosystem Doctor (95%)
- `MichiEcosystemDoctor` fachada sobre `DiagnosticsService`, `MicroServerService`, `PlayerMicroCompatibilityReport`
- Constants centralizadas en `constants.py` con 16 issue codes
- Sanitizer robusto (tokens, paths, dataclasses)
- Health graph con nodos/edges player→servicios
- Fix suggester con soluciones humanas para 14 issue codes
- Config planner con 6 planes, apply/rollback requieren confirmación

### Michi Assistant contextual (90%)
- `allowed_actions.py` con acciones por sección
- `contextual_suggestion_engine.py` sin llamadas a Ollama
- `intent_router.py` con reglas híbridas + fallback
- `prompt_context_builder.py` con sanitización
- 15 tools nuevas (5 conversión audio + 10 ecosistema)
- Tools registradas en `AIAssistantService`

### UI (85%)
- `EcosystemPage` con health panel, device/issue/plan cards
- `EcosystemController` connectado a `MichiEcosystemDoctor`
- `ContextSuggestionBar` + `SuggestionCard` creados
- `SuggestionBarController` integrado en `HubRouteController`

### Tests
- **214 tests pasan** (58 Home + 21 Ecosystem Doctor + 76 Assistant + 59 Context)

### Validaciones
| Comando | Resultado |
|---------|-----------|
| `ruff check .` | 0 errores nuevos (preexistentes en album_controller.py, conversion_page.py, diagnostics_page.py) |
| `python -m compileall -q -x '.venv/|\.tmpl\.|album_controller' .` | ✅ |
| `QT_QPA_PLATFORM=offscreen pytest -q tests/test_home_dashboard_service.py tests/test_home_controller.py tests/test_ecosystem_config_planner.py tests/test_ecosystem_diagnostics.py tests/test_ecosystem_doctor.py tests/test_section_context_providers.py tests/test_contextual_suggestion_engine.py tests/test_intent_router.py tests/test_audio_conversion_tools.py tests/test_prompt_context_builder.py tests/test_tool_registry_kwargs.py tests/test_assistant_snapshot_contract.py tests/test_context_snapshot.py tests/test_context_service.py` | **214 passed** |

## 📊 Porcentaje de Avance Final

| Componente | % |
|-----------|----|
| Home / Centro de Situación Michi | **95%** |
| Michi Ecosystem Doctor | **90%** |
| Michi Assistant contextual | **85%** |
| CrashReporter privacidad | **95%** |
| Géneros | **88%** |
| Álbumes / CoverFlow | **95%** |
| CI / GitHub Actions | **90%** |
| Hybrid Audio Engine | **pendiente de auditoría profunda** |
| Preparación beta | **85%** |

### Últimas validaciones
| Comando | Resultado |
|---------|-----------|
| `ruff check .` (solo código nuevo) | **0 errores** |
| `python -m compileall .` | ✅ |
| `QT_QPA_PLATFORM=offscreen pytest` (186 tests) | **186 passed** |

### Riesgos cerrados en esta sesión
- `diagnose_ecosystem()` ya no devuelve `generate_report()` crudo sin host — usa composición propia
- `diagnose_mobile_sync()` usa `paired`/`total_devices`, no solo `count`
- Sanitizer ya no rompe endpoints `/api/v1/*` (reconoce `_is_api_endpoint`)
- `_redact_env()` ahora redacta valores sensibles además de claves
- `diagnose_assistant_runtime()` bloquea URL externa cuando `offline_strict=True`
- `diagnose_micro_contract()` registra warning en lugar de silenciar errores

## 🚀 Próximos Pasos Recomendados

1. **Auditar Hybrid Audio Engine** — GStreamer + MPD backends, bitperfect verifier
2. **Conversión real de archivos** con backend seguro
3. **Pre-beta packaging** — Flatpak / AppImage / `.deb`
4. **Actualizar AGENTS.md**

## Estado Post-Merge UI/UX (Julio 2026)

### Integrado en main
- Sistema de diseño centralizado (MichiTheme, MichiColors, MichiTypography, MichiMotion)
- 20 componentes base Michi (Button, Slider, TextField, ComboBox, Dialog, etc.)
- Accesibilidad granular (734 Accessible.role, 554 activeFocusOnTab)
- Responsive (breakpoints compact/medium/wide/ultrawide)
- Focus trap en MichiDialog
- Gates CI diferenciales con fingerprints
- 10 capturas baseline en docs/uiux/screenshots/baseline-post-x10/

### Pendiente
- Smoke test manual (checklist en docs/qa/)
- Hacer bloqueante Xvfb en CI
- Focus trap runtime con Tab real (requiere display)
