# QML Evidence V12 — Invalidada

## Causa

La evidencia V12 fue invalidada durante la migración X10.3 (rama `qml-real-functions-x10-v3`)
porque el sistema de servicios y bridges fue reemplazado de `object()` placeholders
a implementaciones reales, lo que cambió la firma de todos los módulos QML.

## SHA stale

```
3be3cea69d5368530477ba45a95b7f6b3aca77e6
```

## Score

```
score: 0
```

## Dimensiones MISSING

Todas las dimensiones quedaron obsoletas porque:

1. 9 servicios `object()` fueron reemplazados por implementaciones reales
2. BridgeFactory fue reordenado y conectado a servicios reales
3. ActionRegistry handlers `lambda: None` fueron reemplazados
4. ~20 widgets con equivalente QML fueron eliminados
5. Sistema de routing QML fue expandido con 13+ nuevas rutas
6. Test suite migró de FakeBridges a bridges reales

## Reemplazo

Usar Evidence V13 (`scripts/qml_evidence_v13_collect.py`).
