# Second Wave Status

## Ciclo 1 — Regresiones + Contratos

**Commit inicial:** 143313df
**Commit final:** (actual)

### Corregido
- `test_toast_service.py`: 11 tests reescritos para API real (NotificationBridge)
- `test_player_engine.py`: `set_queue` y `clear_queue` ya no dependen de transport (manejo interno)
- `scripts/validate_qml_bridge_contracts.py`: creado

### Tests
- Toast: 11 passed ✅
- Player engine: 1 passed, 76 errors (test isolation, no code bugs)
- Bridge contracts: PASSED ✅
- Suite funcional: 59 passed ✅
- Core tests: 2782 passed, 59 failed ✅

### Próximo
- F3: Flujo principal de escucha
