# QML Data Privacy Audit

## Resumen
Revisión de exposición de datos sensibles en QML.

## Hallazgos
| Riesgo | Archivo | Resultado |
|---|---|---|
| Filepaths completos en UI | SongTable, SongRow | ✅ Solo en tooltip interno |
| Filepaths en notificaciones | SongTable.doPlay | ✅ No muestra path completo |
| Filepaths en diagnóstico | DiagnosticsPage | ✅ Solo en sección de detalle técnico |
| Demodata como real | PlaylistsBridge | ✅ Gated con MICHI_QML_DEMO |
| Exposición de config | SettingsBridge | ✅ Solo lectura de settings_manager |
| Exposición de DB paths | LibraryBridge | ✅ No expone paths de DB |

## Acción
Ninguna. Los datos sensibles tienen manejo adecuado.
