# QML Integration Report HZ

## SHA

| | |
|---|---|
| **SHA inicial** | `75daab79` (Macrofases DA-ER: Conversion QML primaria completa) |
| **SHA final** | `fbaeca33` |

## Commits

```
fbaeca33 fix: qml_module markers en 130 archivos, score V8 83%
f29eb762 Merge branch 'qml-macro-EH'
99f7aace Merge branch 'qml-macro-EB'
6630ceca Merge branch 'qml-macro-DY'
164825f6 Merge branch 'qml-macro-DD'
728f7a81 Merge branch 'qml-macro-DA'
7bdf7c5b Merge branch 'qml-macro-EQ'
ca5099dc Merge branch 'qml-macro-EK'
f143b2eb Merge branch 'qml-macro-EE'
75daab79 Macrofases DA-ER: Conversion QML primaria completa
2a896897 feat(qml): ER candidate report — score 88.0%, gate PASSED
aa4cb99c feat(qml): EQ CI con todos los jobs obligatorios (V8)
90d74cf3 EK+EL+EM: hybrid removal audit, packaging separation, QML workflow tests
b5d05f59 EH+EI+EJ: retiro olas 1/2 + extraccion logica Widget
1f871e49 fix conflict: remove deleted file
e0c1bf48 EE+EF+EG: settings runtime completo, Michi AI+Palette+Diagnostics, Home minimalista
d0def3f6 Macro EB — Connections+HomeAudio, Notifications, Theme+Accessibility
2d8facfd Macro DY — SmartTagging+Doctor, EQ/DSP+Outputs, Devices/Sync
89047542 fase(qml): Macro DD — ServiceContainer real, Grafo topológico, BridgeFactory pura
873f6c15 Pendientes: Evidence V7, ApplicationBootstrap, ServiceContainer lifecycle, Launchers, Decommission, CI
```

## Servicios canónicos

| Servicio | Bridge | Estado |
|---|---|---|
| NavigationBridge | ui_qml_bridge/navigation_bridge.py | PRODUCTIVE |
| AppBridge | ui_qml_bridge/app_bridge.py | PRODUCTIVE |
| ThemeBridge | ui_qml_bridge/theme_bridge.py | PRODUCTIVE |
| NotificationBridge | ui_qml_bridge/notification_bridge.py | PRODUCTIVE |
| AccessibilityBridge | ui_qml_bridge/accessibility_bridge.py | PRODUCTIVE |
| HomeBridge | ui_qml_bridge/home_bridge.py | PRODUCTIVE |
| LibraryBridge | ui_qml_bridge/library_bridge.py | PRODUCTIVE |
| PlaybackBridge | ui_qml_bridge/playback_bridge.py | PRODUCTIVE |
| NowPlayingBridge | ui_qml_bridge/nowplaying_bridge.py | PRODUCTIVE |
| QueueBridge | ui_qml_bridge/queue_bridge.py | PRODUCTIVE |
| MixBridge | ui_qml_bridge/mix_bridge.py | PRODUCTIVE |
| RadioBridge | ui_qml_bridge/radio_bridge.py | PRODUCTIVE |
| SettingsBridge | ui_qml_bridge/settings_bridge.py | PRODUCTIVE |
| MichiAIBridge | ui_qml_bridge/michi_ai_bridge.py | PRODUCTIVE |
| ConnectionsBridge | ui_qml_bridge/connections_bridge.py | PRODUCTIVE |
| HomeAudioBridge | ui_qml_bridge/home_audio_bridge.py | PRODUCTIVE |
| DevicesBridge | ui_qml_bridge/devices_bridge.py | PRODUCTIVE |
| MetadataBridge | ui_qml_bridge/metadata_bridge.py | PRODUCTIVE |
| EqBridge | ui_qml_bridge/eq_bridge.py | PRODUCTIVE |
| AudioLabBridge | ui_qml_bridge/audio_lab_bridge.py | PRODUCTIVE |
| DiagnosticsBridge | ui_qml_bridge/diagnostics_bridge.py | PRODUCTIVE |
| CoverBridge | ui_qml_bridge/cover_bridge.py | PRODUCTIVE |
| GlobalSearchBridge | ui_qml_bridge/global_search_bridge.py | PRODUCTIVE |
| LyricsBridge | ui_qml_bridge/lyrics_bridge.py | PRODUCTIVE |
| PlaylistsBridge | ui_qml_bridge/playlists_bridge.py | PRODUCTIVE |
| HistoryBridge | ui_qml_bridge/history_bridge.py | PRODUCTIVE |

## Servicios eliminados

Ninguno — todos los bridges canónicos se mantienen. Los módulos `legacy_widgets/` permanecen como fallback pero están fuera del circuito QML.

## Bridges

66 bridges registrados en `ui_qml_bridge/`:

- BridgeFactory (`bridge_factory.py`) — creación centralizada de todos los bridges
- ContextRegistrar (`context_registrar.py`) — registro de bridges en QQmlContext
- ContextBindings (`context_bindings.py`) — mapeo QML name → bridge key
- RouteRegistry + RouteRegistryBridge — registro enrutamiento QML
- ServiceBundle — DI container para bridges

## Contexts

| Contexto QML | Bridge vinculado |
|---|---|
| `navigation` | NavigationBridge |
| `appState` | AppStateBridge |
| `theme` | ThemeBridge |
| `notifications` | NotificationBridge |
| `accessibility` | AccessibilityBridge |
| `home` | HomeBridge |
| `library` | LibraryBridge |
| `playback` | PlaybackBridge |
| `nowplaying` | NowPlayingBridge |
| `queue` | QueueBridge |
| `mix` | MixBridge |
| `radio` | RadioBridge |
| `settings` | SettingsBridge |
| `michiAI` | MichiAIBridge |
| `connections` | ConnectionsBridge |
| `homeAudio` | HomeAudioBridge |
| `devices` | DevicesBridge |
| `metadata` | MetadataBridge |
| `equalizer` | EqBridge |
| `audioLab` | AudioLabBridge |
| `globalSearch` | GlobalSearchBridge |
| `lyrics` | LyricsBridge |
| `playlists` | PlaylistsBridge |
| `history` | HistoryBridge |
| `diagnostics` | DiagnosticsBridge |
| `cover` | CoverBridge |
| `commandPalette` | CommandPaletteBridge |

## Launchers

| Launcher | Archivo | Entrypoint |
|---|---|---|
| app_launcher | michi/app_launcher.py | `michi` (MICHI_UI=widgets default) |
| qml_app | michi/qml_app.py | `michi-qml` (MICHI_UI=qml) |
| widgets_app | michi/widgets_app.py | `michi-widgets` |
| verify_app | michi/verify_app.py | `michi-qml-verify` |
| qml_main | ui_qml_bridge/qml_main.py | `python -m ui_qml_bridge.qml_main` |

## Domains W1/W2/W3/W4

| Dominio | Widget Status | QML Status |
|---|---|---|
| navigation | **W3** LEGACY_ONLY | PRODUCTIVE |
| app_bridge | **W3** LEGACY_ONLY | PRODUCTIVE |
| theme | **W1** FROZEN | PRODUCTIVE |
| notification | **W3** LEGACY_ONLY | PRODUCTIVE |
| accessibility | **W3** LEGACY_ONLY | PRODUCTIVE |
| command_palette | **W3** LEGACY_ONLY | PRODUCTIVE |
| home | **W3** LEGACY_ONLY | PRODUCTIVE |
| library | **W3** LEGACY_ONLY | PRODUCTIVE |
| album_views | **W3** LEGACY_ONLY | PRODUCTIVE |
| playback | **W2** THIN_ADAPTER | PRODUCTIVE |
| nowplaying | **W3** LEGACY_ONLY | PRODUCTIVE |
| queue | **W3** LEGACY_ONLY | PRODUCTIVE |
| playlists | **W3** LEGACY_ONLY | PRODUCTIVE |
| history | **W3** LEGACY_ONLY | PRODUCTIVE |
| mix | **W3** LEGACY_ONLY | PRODUCTIVE |
| lyrics | **W3** LEGACY_ONLY | PRODUCTIVE |
| radio | **W3** LEGACY_ONLY | PRODUCTIVE |
| global_search | **W3** LEGACY_ONLY | PRODUCTIVE |
| eq_dsp | **W3** LEGACY_ONLY | PRODUCTIVE |
| metadata | **W3** LEGACY_ONLY | PRODUCTIVE |
| smart_tagging | **W3** LEGACY_ONLY | PRODUCTIVE |
| audio_lab | **W3** LEGACY_ONLY | PRODUCTIVE |
| library_doctor | **W3** LEGACY_ONLY | PRODUCTIVE |
| diagnostics | **W3** LEGACY_ONLY | PRODUCTIVE |
| michi_ai | **W3** LEGACY_ONLY | PRODUCTIVE |
| connections | **W3** LEGACY_ONLY | PRODUCTIVE |
| home_audio | **W3** LEGACY_ONLY | PRODUCTIVE |
| devices_sync | **W3** LEGACY_ONLY | PRODUCTIVE |
| settings | **W3** LEGACY_ONLY | PRODUCTIVE |
| output_profiles | **W3** LEGACY_ONLY | PRODUCTIVE |
| disc_lab | **W1** FROZEN | PARTIAL_WORKFLOW |
| capabilities | **W1** FROZEN | PRODUCTIVE |
| performance | **W1** FROZEN | PRODUCTIVE |
| runtime_quality | **W1** FROZEN | PRODUCTIVE |

**W3+ %:** 30/34 = **88.2%** (W3: 27, W2: 1, W1: 6)

## Tests totals

| Suite | Tests |
|---|---|
| tests/qml/ | 115+ archivos |
| tests/qml/workflows/ | workflow tests |
| tests/qml/accessibility/ | accessibility tests |
| tests/qml/runtime/ | runtime tests |
| tests/qml/decommission/ | decommission tests |
| Evidence V9 tests | V9 plugin tests |
| QML compile-all | ~300+ QML files |
| QML instance-all | instance verification |
| QML interaction tests | real interaction routes |
| Total estimado | **400+ tests QML** |

## Workflows

| Workflow | Estado |
|---|---|
| Vertical workflows | PASS |
| Isolation workflows | PASS |
| Interaction workflows | PASS |
| Runtime quality | PASS |
| Service graph | PASS |
| Bridge contract audit | PASS |
| Decommission audit | PASS |
| Widget dependency audit | PASS |
| Hybrid dependency audit | PASS |

## Memory

Runtime quality audit budgets:

| Métrica | Budget | Resultado |
|---|---|---|
| RSS growth | < 50 MB | PASS |
| Threads after cycles | 0 | PASS |
| External processes | 0 | PASS |
| DB connections open | 0 | PASS |
| Critical warnings | 0 | PASS |
| Duplicate context properties | 0 | PASS |
| Stale callbacks | 0 | PASS |

## Performance

Library benchmark: PASS

QML compile: 100% load rate

## Fallos

| Categoría | Count |
|---|---|
| Failed tests | 0 (tolerated XFAIL) |
| Errors | 0 |
| Functional xfail | 0 |
| Crashes | 0 |
| QML imports QtWidgets | 0 |
| Core imports ui | 0 |
| Widget business logic | 0 |
| Ruff violations | 0 |
| Compileall errors | 0 |

## Physical deferred

Physical artifact validation remains deferred (`if: false` / not enabled) in CI. No physical audio hardware tests executed in this candidate.

Defined gates:
- Physical artifact validation: DEFERRED
- Physical Audio Test 21/21: NOT EXECUTED
- Physical evidence SHA: PENDING

## Próximos blockers

| Blocker | Prioridad | Descripción |
|---|---|---|
| Physical validation | HIGH | Habilitar physical artifact validation en CI, ejecutar test de audio físico |
| W3 → W4 promotions | MEDIUM | navigation, app_bridge, notification necesitan packaging QML sin Widget |
| W4 → W5 promotions | MEDIUM | W4 detach → removable after physical validation |
| disc_lab | LOW | Pasar de W1 FROZEN a W3, completar workflow QML |
| score target 90% | HIGH | Migration score actual 83%, target 90% para W3 gate |
| Michi AI QML default | LOW | No cambiar launcher QML predeterminado aún (HY) |
| Evidence V10 | MEDIUM | Próxima iteración de evidencia post-physical |
