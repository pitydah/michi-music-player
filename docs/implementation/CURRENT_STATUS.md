# Current Status

## Ciclo 1 — F0 Baseline
**Commit inicial:** fc7d847b
**Entry points:** michi, michi-verify (ambos QML-only)

### Completado
- [x] QML-only gate: 0 imports QtWidgets en producción
- [x] Wheel builds (0.10.0a1)
- [x] Entry points: widgets_app eliminado
- [x] Compileall OK
- [x] Diagnostics OK (Qt 6.11.1, GStreamer)
- [x] 61 tests funcionales QML pasan
- [x] legacy_widgets/ archivado y eliminado

### Pendiente inmediato (F0)
- Crear gate CI para QML-only
- Construir wheel, instalar en entorno limpio, verificar entry points
- Verificar que wheel no incluye secretos/legacy
- Línea base de rendimiento
- docs/implementation/ actualizados

### Pendiente (F1+)
- 18 fases de transformación
