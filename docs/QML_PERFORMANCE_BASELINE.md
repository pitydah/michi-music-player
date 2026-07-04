# QML Performance Baseline

## Entorno
- Python: 3.11.15
- Qt: PySide6
- OS: Linux (x86_64)
- Safe mode: No
- QML mode: Sí

## Startup
| Métrica | Resultado |
|---|---|
| Python imports | 0.00s |
| Route registry loaded | 0.00s |

## Route load (registry lookup, no QML engine)
| Ruta | Tiempo | Estado | Categoría |
|---|---|---|---|
| home | 0.0ms | functional | core |
| library | 0.0ms | functional | core |
| playlists | 0.0ms | functional | core |
| radio | 0.0ms | functional | core |
| settings | 0.0ms | functional | core |
| audio_lab | 0.0ms | functional | tools |
| diagnostics | 0.0ms | experimental | system |

## Memoria
| Métrica | Resultado |
|---|---|
| RSS (script mode) | 65.0 MB |

## Hallazgos
| Hallazgo | Severidad | Acción |
|---|---|---|
| Medición inicial sin QML engine full load | Baja | Mejorar probe para medir startup QML real |
| Memoria 65MB en modo script | Baja | Aceptable para modo experimental |

## Veredicto
Performance baseline creado. Medición en modo script sin carga completa de QML engine.
