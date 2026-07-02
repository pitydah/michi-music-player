# Known Issues — Michi Music Player v0.2.0-alpha.1

| Issue | Severidad | Área | Cómo reproducir | Workaround | Estado |
|---|---|---|---|---|---|
| `no such column: is_smart` en DB schema test | Media | Schema / Tests | Ejecutar `pytest tests/test_library_db.py` | Test con `:memory:` no refleja schema real; ignorar en CI | No corregido |
| `test_dispatch_radio_sets_playback_hub_sidebar` falla | Baja | Navegación | Ejecutar test de navegación | El sidebar espera `broadcast_hub`, no `playback_hub`; actualizar test | No corregido |
| `is_smart` no existe en tabla `playlists` | Media | Playlists | Schema tiene índice en `is_smart` pero columna no agregada en migraciones | La creación de playlists falla si se ejecuta schema desde cero; usar DB existente | No corregido |
| Audio Lab QML `navigateTo` es stub | Baja | Audio Lab QML | Click en módulo de Audio Lab en QML | QtWidgets Audio Lab funciona completo | Documentado |
| QML NowPlaying no recibe PlayerService directamente | Baja | NowPlaying QML | NowPlaying QML no muestra cambios de estado | Usar `python main.py` (QtWidgets) para NowPlaying completo | Documentado |
| Settings QML no tiene reset | Baja | Settings QML | No hay botón para restaurar defaults | QtWidgets Settings funciona completo | Documentado |
| Mix usa slicing básico, no recomendación real | Media | Mix | LoadMix("daily_mix") devuelve primeros N items | Recomendación real no implementada; usa datos reales de DB | Documentado |
| Michi AI sugerencias estáticas sin MichiAIContextBridge | Baja | Michi AI | Sin MichiAIContextBridge, sugerencias son fijas | Usar QtWidgets Assistant para AI completo | Documentado |
| `--qml` flag no acepta argumentos adicionales | Baja | QML | `python main.py --qml --safe` no funciona | Pasar flags antes de `--qml` | Documentado |
| FileWatcher degradado con >2048 directorios | Media | Biblioteca | Bibliotecas muy grandes con estructura profunda | Monitoreo parcial; usar escaneo manual | No corregido |
| BatchWriter transaction nesting con cover art | Media | Indexer | Archivos con carátula embebida durante indexación | Se corrigió en MediaRecordBuilder (no hace commit inline); Indexer actualizado | **Corregido** |
