# QML Runtime Display Blockers Fix Report

## Base
- Branch: `qml-runtime-display-blockers-fix`
- Base commit: `5cad57b`
- Motivo: Corregir bloqueos P1/P2 detectados al ejecutar `python main.py --qml` en display real

## Errores corregidos

| Error | Archivo | Severidad | Corrección |
|---|---|---|---|
| StackLayout is not a type | LibraryPage.qml, HomeAudioPage.qml | P1 | Agregado `import QtQuick.Layouts` |
| GlassCard.interactive inexistente | RadioPage.qml (via GlassCard.qml) | P1 | Agregada property `interactive` a GlassCard |
| placeholderText en TextInput | AssistantPage.qml | P1 | Eliminado, el Text hijo ya hace de placeholder |
| Property value set multiple times | MetadataInspectorPage.qml | P1 | Eliminado `width` duplicado en emptyComponent |
| Binding loop bridges (4 archivos) | PlaybackPage, ConnectionsPage, PlaylistsPage, AudioLabPage | P2 | Renombradas propiedades locales para evitar self-reference |
| Binding loop bridges (11 archivos restantes) | DevicesPage, MixHubPage, MixDetailPage, RadioPage, SettingsPage, OutputProfilesPage, SmartTaggingPage, AssistantPage, HomeAudioPage, LibraryPage, MetadataInspectorPage | P2 | Renombradas propiedades locales |
| Icon paths resuelven a ui_qml/icons/ | PlaybackPage, AssistantPage | P2 | Cambiado de `../icons/` a `../../icons/` |
| MichiIconButton enabled override | MichiIconButton.qml | P3 | Eliminada property `enabled` (heredada de Item) |

## Validación posterior

| Comando | Resultado |
|---|---|
| `ruff check .` | ✅ All checks passed |
| `compileall` | ✅ OK |
| `smoke_startup` | ✅ 7/7 |
| `smoke_ui_routes` | ✅ 2/2 |
| `check_runtime.py` | ✅ Todo listo |
| `tests/qml/ -q` | ✅ 246 passed |
| `tests/test_schema.py` | ✅ 15 passed |
| `tests/test_format_probe.py` | ✅ 41 passed |
| `tests/test_playback_controller.py` | ✅ 6 passed |

## Tests de regresión agregados
1. LibraryPage tiene import QtQuick.Layouts
2. HomeAudioPage tiene import QtQuick.Layouts
3. No hay `property var XBridge: typeof XBridge` en ninguna página
4. No hay `placeholderText` sobre `TextInput`
5. MichiIconButton no declara `property bool enabled`
6. GlassCard tiene `property bool interactive`
7. MetadataInspectorPage emptyComponent no duplica width
8. No hay referencias a `ui_qml/icons` como ruta objetivo

## Veredicto
Todos los bloqueos P1/P2 de runtime QML en display real han sido corregidos. El display runtime está estable. Alpha2 final sigue pendiente de prueba de audio físico real.
