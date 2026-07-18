# Functional Traceability — Michi Music Player

**SHA:** 0ada5c2b
**Fecha:** 2026-07-18
**Estado:** DECLARED_ONLY — la mayoría de funciones están declaradas pero no tienen flujo vertical completo.

## Convención de estados

| Estado | Significado |
|--------|-------------|
| DECLARED_ONLY | Existe página/clase pero no hay flujo completo |
| WIRED | Bridge conectado a servicio, pero servicio puede ser None |
| EXECUTED | Flujo produce efecto real |
| PERSISTED | Datos sobreviven reinicio |
| ERROR_TESTED | Errores manejados |
| VERTICALLY_TESTED | Test de integración vertical pasa |
| COMPLETE | Todo lo anterior |

## Matriz funcional

| Dominio | Función | QML | Bridge | Service | Estado real | Bloqueador |
|---------|---------|-----|--------|---------|-------------|------------|
| Playback | Reproducir | ✅ | ✅ | NONE | DECLARED_ONLY | Composition: playback_service=None |
| Queue | Cola | ✅ | ✅ | NONE | DECLARED_ONLY | Composition: queue_service=None |
| Library | Biblioteca | ✅ | ✅ | NONE | DECLARED_ONLY | Composition: library_query_service=None |
| Search | Buscar | ✅ | ✅ | NONE | DECLARED_ONLY | Composition: global_search_service=None |
| Mix | Mixes | ✅ | ✅ | NONE | DECLARED_ONLY | Composition: mix_service=None |
| Lyrics | Letras | ✅ | ✅ | NONE | DECLARED_ONLY | Composition: lyrics_service=None |
| Metadata | Metadatos | ✅ | ✅ | NONE | DECLARED_ONLY | Composition: metadata_service=None |
| EQ | Ecualizador | ✅ | ✅ | NONE | DECLARED_ONLY | Composition: eq no registrado |
| Radio | Radio | ✅ | ✅ | NONE | DECLARED_ONLY | Composition: radio_service=None |
| Playlists | Playlists | ✅ | ✅ | NONE | DECLARED_ONLY | Composition: playlist_service=None |
| History | Historial | ✅ | ✅ | NONE | DECLARED_ONLY | Composition: history_query_service=None |
| Settings | Ajustes | ✅ | ✅ | ✅ | WIRED | Faltan runtime adapters completos |
| Audio Lab | Audio Lab | ✅ | ✅ | NONE | DECLARED_ONLY | Composition: audio_lab_service=None |
| CD Ripper | Ripeo CD | ✅ | ✅ | ✅ | DECLARED_ONLY | Requiere hardware |
| ADC | Grabación ADC | ✅ | ✅ | ✅ | DECLARED_ONLY | Requiere hardware |
| Devices | Dispositivos | ✅ | ✅ | NONE | DECLARED_ONLY | Composition: device_sync_service=None |
| Connections | Conexiones | ✅ | ✅ | NONE | DECLARED_ONLY | Composition: connection_service=None |
| Home Audio | Audio hogar | ✅ | ✅ | NONE | DECLARED_ONLY | Composition: home_audio_service=None |
| Mobile Sync | Sync móvil | ❌ | ❌ | ✅ | DECLARED_ONLY | Sin bridge ni página |
| Micro Server | Micro Server | ❌ | ❌ | NONE | DECLARED_ONLY | Sin integración real |
| Michi AI | Asistente | ✅ | ✅ | NONE | DECLARED_ONLY | Composition: michi_ai_service=None |
| Smart Tagging | Tagging | ✅ | ✅ | NONE | DECLARED_ONLY | Composition: smart_tagging_service=None |
| Library Doctor | Doctor | ✅ | ✅ | NONE | DECLARED_ONLY | Composition: library_doctor_service=None |
| Diagnostics | Diagnóstico | ✅ | ✅ | NONE | DECLARED_ONLY | Composition: diagnostics_service=None |

## Problema crítico

26 de 37 servicios registrados en el composition root son `None`.
Esto significa que los bridges reciben None y cualquier interacción real falla.
La causa es que `core/composition/*.py` intenta construir servicios que dependen de otros servicios que aún no están disponibles, y los atrapa con `except Exception: pass`, registrando None.

**Solución:** Reordenar los builders para que los servicios base se construyan primero,
y eliminar los `except Exception: pass` silenciosos.
