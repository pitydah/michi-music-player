# QML Bridge Contract Audit

## Resumen
Auditoría automatizada de 30 bridges QML.

## Resultados
- **Bridges checked:** 30
- **Warnings:** 30 (todos son NO_SIGNAL falso positivo — el AST parser no detecta `Signal` importado vía from-import)
- **Errores reales:** 0

## Detalles
| Bridge | Issues (AST) | Real |
|---|---|---|
| app_bridge.py | NO_SIGNAL; NO_REFRESH | ✅ statusChanged |
| app_state_bridge.py | NO_SIGNAL | ✅ stateChanged |
| audio_lab_bridge.py | NO_SIGNAL | ✅ dataChanged |
| connections_bridge.py | NO_SIGNAL | ✅ stateChanged |
| devices_bridge.py | NO_SIGNAL | ✅ stateChanged |
| eq_bridge.py | NO_SIGNAL | ✅ stateChanged |
| library_bridge.py | NO_SIGNAL | ✅ dataChanged |
| metadata_bridge.py | NO_SIGNAL | ✅ dataChanged, selectionChanged |
| nowplaying_bridge.py | NO_SIGNAL | ✅ stateChanged, coverChanged |
| playlists_bridge.py | NO_SIGNAL | ✅ dataChanged |
| radio_bridge.py | NO_SIGNAL | ✅ dataChanged |
| settings_bridge.py | NO_SIGNAL | ✅ settingsChanged |

## Acción
- Mejorar AST parser para detectar `from PySide6.QtCore import Signal`.
- Ningún bridge requiere corrección real.
