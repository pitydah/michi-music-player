# QML Unmerged Commits Review

**Date:** 2026-07-02  
**Source branch:** `qml-migration-foundation`  
**Target branch:** `main`  
**Commits behind:** 34  
**Shared files with conflicts:** ~115  

## Classification Legend

| Classification | Meaning |
|---|---|
| `necesario` | Corrige bug real o mejora bridge existente |
| `duplicado` | `main` ya contiene equivalente |
| `riesgoso` | Toca core, schema, window.py, audio sin tests |
| `descartable` | Solo documentación inflada o placeholders |
| `requiere revisión manual` | No claro si mejora o duplica; conflictos probables |

## Commit Table

| # | Commit | Mensaje | Áreas | Clasificación | Riesgo | Recomendación |
|---|---|---|---|---|---|---|
| 1 | `85fd282` | audit(qml): fix tilde, add explicit PageStack cases, harden tests, 53 passed | QML tests, PageStack | `necesario` | Bajo | Mergear |
| 2 | `a82f8da` | feat(michi-link): playlist API completa — GET/POST/PATCH/DELETE playlists, tracks, reorder, manifest/delta, 14 tests, permissions, docs | Michi Link API, playlist REST | `requiere revisión manual` | Medio | Revisar si main ya tiene API equivalente |
| 3 | `a8adf79` | feat(playlists): UI wiring completo — context menu detalle, drag-drop persistente, cover studio, smart builder, hub actions reales, 109 tests | Playlists QtWidgets UI | `requiere revisión manual` | Medio | Probable conflicto con hub actual |
| 4 | `d8a800e` | test(qml): sidebar routes, Michi AI label, navigation, PageStack (50 tests) | QML tests | `necesario` | Bajo | Mergear |
| 5 | `ae65c3c` | feat(qml): update sidebar - remove settings, add radio/playlists, Michi AI as label; update routes, remove SettingsPage | QML sidebar, routes | `requiere revisión manual` | Medio | Verificar sidebar actual en main |
| 6 | `db590de` | feat(playlists): premium suite completa — store, import, export, audit, relinker, ordering, smart engine, sync manifest, 52 tests, docs | `library/playlists/` (nuevo), tests | `requiere revisión manual` | Alto | Biblioteca nueva (playlist_store, audit, export, import). Probables conflictos con DB actual |
| 7 | `1fcfaef` | fix(qml): HeaderBar import QtQuick.Layouts, HeroMaterial remove Gradient.Orientation; docs: update RUNTIME_BUDGET, AGENTS.md with current status | QML, docs | `necesario` | Bajo | Mergear (fix QML) |
| 8 | `1114cfb` | docs(qml): update with F15 Nav hardening, F16 cierre final, 41 tests | Docs | `descartable` | Bajo | Docs desactualizadas vs main |
| 9 | `38773ef` | fix(tests): remove unused import, ternary style (ruff 0 errors) | Tests | `necesario` | Bajo | Mergear |
| 10 | `228725d` | test(qml): sidebar forbidden routes, no emoji glyphs, context menu no emoji (41 tests); fix: schema.py indent | QML tests, schema.py | `necesario` | Bajo | Mergear (tests nuevos) |
| 11 | `042affc` | fix(navegacion): historial completo — rutas album:/artist:/genre:, dispatch dinámico, alt+left/right, restoring flag, checkpoint condicional, 23 tests | NavigationController | `requiere revisión manual` | Medio | main ya tiene cambios similares. Verificar duplicación |
| 12 | `5ada799` | fix(nav): harden NavigationHistory dedup, Alt+Left/Right editable guard, context menu sin emojis, toggle_favorite_by_filepath, SongsPremiumPage load_data stale guard | Navigation, Songs, UI | `requiere revisión manual` | Medio | Posible duplicado de fixes en main |
| 13 | `bcdf67b` | fix: syntax error in metadata_extractor (unmatched except) - unblocks test suite | metadata_extractor.py | `necesario` | Bajo | **Urgente**: corrige syntax error |
| 14 | `8b5e50f` | docs(qml): update with Polish Pass, add QML_RUNTIME_BUDGET.md | Docs | `descartable` | Bajo | Docs de rama, no relevantes para main |
| 15 | `9e4490e` | test(qml): add emoji prohibition test + appshell-sidebar route sync test (38 total) | QML tests | `necesario` | Bajo | Mergear |
| 16 | `bd23418` | chore(qml): remove dead routes from header (genres, radio, ecosystem) | QML navigation | `necesario` | Bajo | Mergear |
| 17 | `dbde8e5` | feat(qml): placeholders premium - glyphs, badge 'Interfaz clasica', tono premium | QML UI | `requiere revisión manual` | Bajo | Placeholders, bajo riesgo |
| 18 | `b55d303` | feat(qml): HomeAudio 100% - ModeSelector sin emojis, glyphs HA/MS, active state premium | QML HomeAudio | `necesario` | Bajo | Refinamiento QML |
| 19 | `32099ec` | feat(qml): Connections 100% - externos en grid 2x2, sin console.log como accion final | QML Connections | `necesario` | Bajo | Refinamiento QML |
| 20 | `59857b0` | feat(qml): Home 100% - Hero sin emoji (MM), ContinueCard empty honesto, LibraryStatusCard hasData toggle | QML Home page | `necesario` | Bajo | Refinamiento QML |
| 21 | `18c0f9a` | feat(qml): ActionButton 100% - microinteracciones, scale 0.985, loading spinner, focus ring, minWidth | QML components | `necesario` | Bajo | Refinamiento QML |
| 22 | `b5f3d30` | feat(qml): header premium, MichiGlass 2.0 - +15 tokens, microinteracciones, surfaceHeroGlow, surfaceToolbar, surfaceSidebar | QML theme, shell | `necesario` | Bajo | Refinamiento QML |
| 23 | `3b5cbee` | feat(qml): qmldir for components/materials/shell, sidebar premium - glyphs, microinteractions, rutas autorizadas | QML shell, sidebar | `necesario` | Bajo | Refinamiento QML |
| 24 | `fd0a480` | docs(qml): update migration plan with hardening pass, commands, protected areas | Docs | `descartable` | Bajo | Docs de rama |
| 25 | `002d67f` | test(qml): comprehensive bridge tests + structural smoke tests (36 tests) | QML tests | `necesario` | Bajo | Mergear (tests nuevos) |
| 26 | `b66a6cd` | feat(qml): connect page buttons to bridges (NavigationBridge, ConnectionsBridge, HomeAudioBridge) | QML bridges | `necesario` | Bajo | Mejora bridges |
| 27 | `5bb177d` | feat(qml): connect shell to NavigationBridge with fallback | QML shell | `necesario` | Bajo | Mejora shell |
| 28 | `cce7e74` | fix(qml): harden bridges - Slots, route validation, type hints | QML bridges | `necesario` | Bajo | Hardening bridges |
| 29 | `44ffb96` | fix(qml): add theme/qmldir with singleton declarations | QML theme | `necesario` | Bajo | Fix QML |
| 30 | `6572f2f` | fix(qml): PageStack rutas relativas seguras (../pages/...) | QML PageStack | `necesario` | Bajo | Fix QML |
| 31 | `63c5d41` | fix(nav): quitar botones ← Volver centrales, Alt+Left/Right, tabs en historial, ruta michi_local corregida, 146 tests | Navigation, UI | `requiere revisión manual` | Medio | main ya tiene cambios de navegación similares. Posible duplicación |
| 32 | `f7d77d4` | docs: add MICHI_AI.md with unified architecture documentation | Docs | `descartable` | Bajo | Ya existe en main |
| 33 | `017244d` | feat(audio): Hybrid Audio Engine 100% completo | `audio/`, engine | `riesgoso` | **Alto** | Toca audio core. main ya tiene cambios. No mergear sin pruebas |
| 34 | `56c1f7b` | feat(ui): conectar modulos core a la UI — Health Card, Dependency Button, Metadata Doctor, Backup Manifest, Report Health | UI Audio Lab | `requiere revisión manual` | Medio | main ya tiene Audio Lab UI. Verificar duplicación |

## Summary

| Clasificación | Cantidad |
|---|---|
| `necesario` | 18 |
| `requiere revisión manual` | 8 |
| `descartable` | 4 |
| `riesgoso` | 1 |
| `duplicado` | 0 |

## Decision Recommended

1. **No mergear toda la rama** — 115 archivos compartidos con cambios divergentes garantizan conflictos.
2. **Cherry-pick selectivo** de los 18 commits clasificados como `necesario` (prioridad: fixes de QML, tests, schema fix en `bcdf67b`).
3. **Revisar manualmente** los 8 commits `requiere revisión manual` antes de cherry-pick.
4. **No mergear** el commit `017244d` (Hybrid Audio Engine) — toca audio core sin tests en la rama.
5. **Descartar** los 4 commits `descartable` (documentación de rama ya obsoleta vs main).
6. **Commit prioritario:** `bcdf67b` (syntax error en metadata_extractor) — desbloquea test suite.
