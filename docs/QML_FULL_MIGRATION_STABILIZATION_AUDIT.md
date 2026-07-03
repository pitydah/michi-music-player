# QML Full Migration Stabilization Audit

## Base
- Branch: `qml-full-migration-stabilization-audit`
- Base commit: `58526a5`
- Objetivo: Revisar, estabilizar y corregir riesgos introducidos entre PR #12 y PR #22

## PRs revisados
| PR | Área | Estado esperado | Riesgo principal |
|---|---|---|---|
| #13 | Playlists + Radio | FUNCIONAL | Delete sin confirmación |
| #14 | Settings + Devices + Connections | FUNCIONAL | — |
| #15 | Metadata phase 1 | FUNCIONAL | — |
| #17 | Full route coverage | COMPLETO | — |
| #19 | EQ + Library Doctor | COMPLETO_VISUAL | Placeholder sin funcionalidad real |
| #22 | Output Profiles + Smart Tagging | FUNCIONAL / PARCIAL | Path fake en SmartTagging |

## Hallazgos

| Hallazgo | Severidad | Archivo | Acción |
|---|---|---|---|
| Path fake `/example/track.mp3` como flujo funcional | Alta | `SmartTaggingPage.qml:55` | Reemplazado por mensaje informativo |
| `deletePlaylist()` sin confirmación | Alta | `PlaylistDetailPage.qml:65-68` | Implementado confirmación en 2 pasos |
| Rename automático con `" (editada)"` | Media | `PlaylistDetailPage.qml:59` | Botón Editar deshabilitado con tooltip |
| `SmartTaggingPage` no permitía selección real de archivo | Media | `SmartTaggingPage.qml` | Funcionalidad gated hasta tener selector |
| Mapa de paridad no reflejaba SmartTagging + Output Profiles | Baja | `QML_FULL_MIGRATION_PARITY_MAP.md` | Actualizado |

## Correcciones aplicadas

| Archivo | Cambio | Motivo |
|---|---|---|
| `ui_qml/pages/SmartTaggingPage.qml` | Eliminado path fake, card ahora muestra mensaje informativo | No ejecutar paths fake en modo normal |
| `ui_qml/pages/playlists/PlaylistDetailPage.qml` | Delete con confirmación en 2 pasos, Edit deshabilitado con tooltip | Acciones destructivas requieren confirmación; no renombrar automáticamente |
| `docs/QML_FULL_MIGRATION_PARITY_MAP.md` | Actualizado estados: SmartTagging → PARCIAL, Output Profiles → FUNCIONAL | Reflejar paridad real post-PR #22 |

## Paridad real vs cobertura visual

| Ruta | Estado anterior | Estado corregido | Motivo |
|---|---|---|---|
| Smart Tagging | LEGACY_ONLY | PARCIAL | Bridge y página existen, sin selector de archivo desde UI |
| Output Profiles | LEGACY_ONLY | FUNCIONAL | Conectado a SettingsBridge → output_profiles reales |
| EQ | LEGACY_ONLY | COMPLETO_VISUAL | Página visual sin EQ real (requiere backend DSP) |
| Library Doctor | LEGACY_ONLY | COMPLETO_VISUAL | Página visual sin escaneo real (requiere bridge) |

## Acciones destructivas

| Acción | Confirmación | Estado |
|---|---|---|
| deletePlaylist | 2 pasos (click → "Confirmar eliminación" → ejecuta) | ✅ Corregido |
| createPlaylist | Inmediato (no destructivo) | ✅ Aceptable |
| renamePlaylist | Deshabilitado (tooltip: "Edición disponible en interfaz clásica") | ✅ Gated |

## Placeholders

| Placeholder | Estado |
|---|---|
| `/example/track.mp3` en SmartTaggingPage | ✅ Eliminado |
| EQ sin backend real | ⚠️ Documentado como COMPLETO_VISUAL |
| Library Doctor sin bridge | ⚠️ Documentado como COMPLETO_VISUAL |
| Smart Tagging sin selector de archivo | ⚠️ Documentado como PARCIAL |

## Validación

| Comando | Resultado |
|---|---|
| `ruff check .` | ✅ All checks passed |
| `compileall` | ✅ OK |
| `smoke_startup` | ✅ 7/7 |
| `smoke_ui_routes` | ✅ 2/2 |
| `check_runtime.py` | ✅ Todo listo |
| `tests/qml/ -q` | ✅ 238 passed |
| `tests/test_schema.py -q` | ✅ 15 passed |
| `tests/test_format_probe.py -q` | ✅ 41 passed |
| `tests/test_playback_controller.py -q` | ✅ 6 passed |

## Veredicto

Riesgos de PR #12–#22 mitigados: path fake eliminado, delete con confirmación, rename deshabilitado, paridad documentada honestamente. No se requiere acción urgente. Próximo paso recomendado: prueba humana visual con `python main.py --qml`.
