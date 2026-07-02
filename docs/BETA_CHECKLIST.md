# Beta Checklist — Michi Music Player v0.2.0-alpha.1

## Arranque

- [x] `python main.py` arranca sin errores
- [x] `python main.py --qml` arranca sin errores
- [x] Safe mode funciona (`MICHI_SAFE_MODE=1`)
- [x] Smoke startup pasa (1 pre-existing error: `is_smart`)
- [ ] Smoke UI routes pasa
- [x] `ruff check .` sin errores nuevos
- [x] `python -m compileall .` sin errores

## Biblioteca

- [x] Biblioteca abre desde sidebar
- [x] Canciones se muestran
- [x] Álbumes se muestran
- [x] Artistas se muestran
- [x] Géneros se muestran
- [x] Carpetas se muestran
- [x] Búsqueda funciona por sección
- [x] Historial atrás/adelante restaura estado
- [x] Cambiar vista no rompe sección
- [x] CoverFlow solo en álbumes
- [x] Tree solo en carpetas

## Indexer

- [x] Escaneo incremental funciona
- [x] ChangeDetector (size + mtime)
- [x] FTS5 rebuild
- [x] Force reindex preserve play_count/rating
- [x] MediaRecordBuilder unificado

## Reproducción

- [x] Play/Pause
- [x] Next/Previous
- [x] Seek
- [x] Volumen
- [x] Cola
- [x] Gapless
- [x] Crossfade (si activo)
- [x] Radio URL playback
- [x] Subsonic/Navidrome/Jellyfin (si configurado)

## Audio Profiles

- [x] Standard
- [x] Hi-Fi PCM
- [x] Bit-Perfect PCM
- [ ] DSD→PCM
- [ ] DoP (experimental)
- [x] Streaming
- [ ] Pure Audio
- [ ] Studio Monitor
- [ ] Multiroom/Snapcast

## MPD (si configurado)

- [ ] MPD backend arranca
- [ ] MPD playback
- [ ] MPD → GStreamer fallback
- [ ] EQ desactivado en MPD

## NowPlaying

- [x] Portada, título, artista, álbum
- [x] Tiempo/duración
- [x] Volumen
- [x] Formato/calidad/códec
- [x] Sample rate/bit depth/bitrate
- [x] Backend activo visible
- [x] Perfil de audio
- [x] Salida actual
- [x] ReplayGain estado
- [ ] Bit-Perfect estado (verified/intended/disabled)

## Playlists

- [x] Listar playlists
- [x] Crear playlist
- [x] Renombrar
- [x] Eliminar con confirmación
- [x] Ver detalle
- [x] Agregar/quitar canciones
- [x] Reproducir playlist
- [x] Agregar a cola
- [x] Guardar cola como playlist
- [x] Crear desde álbum/artista/género/búsqueda
- [x] Importar M3U
- [x] Exportar M3U
- [ ] Detectar canciones perdidas (tool: "pendiente")
- [ ] Detectar duplicados (tool: "pendiente")

## Audio Lab

- [x] Diagnóstico funcional
- [x] Identificador funcional
- [x] Metadata Doctor funcional
- [x] Artwork funcional
- [x] Lyrics funcional
- [x] Bit-perfect Monitor funcional
- [x] Backup Manifest funcional
- [x] Disc Lab funcional
- [ ] Vinyl Lab experimental
- [ ] Conversión experimental
- [x] Organización funcional
- [ ] Inteligencia local experimental

## Michi Link

- [x] HTTP API funciona
- [x] mDNS funciona
- [x] Sync Manager funciona
- [x] Descubrimiento de servidores
- [ ] Pairing completo
- [ ] Importar a servidor
- [ ] Continue on Server

## Sync

- [x] Servicio de sincronización arranca
- [x] Pares detectados
- [x] Transferencia de archivos
- [x] Android REST API

## Géneros

- [x] Normalización
- [x] Limpieza
- [x] Backfill desde media_items
- [ ] Búsqueda en QML (era NOP, corregido en LibrarySearchService)

## Settings

- [x] General
- [x] Apariencia
- [x] Audio
- [x] Biblioteca
- [x] Atajos de teclado
- [x] Perfiles de salida

## CI

- [ ] GitHub Actions pasa completo
- [x] `ruff check .` pasa
- [x] `compileall` pasa
- [x] QML tests pasan (165)
- [x] Library tests pasan (228+)
- [ ] Full test suite pasa

## Empaquetado

- [ ] Flatpak
- [ ] AUR
- [ ] pip install

## Documentación

- [x] README actualizado
- [x] ESTADO.md actualizado
- [x] AGENTS.md actualizado
- [x] Feature Status actualizado
- [x] Known Issues creado
- [x] Beta Checklist creado
- [x] Beta Product Audit creado
- [x] Release Notes Draft creado
- [x] QML Backend Integration Report creado
- [ ] docs/library_architecture.md completo

---
**Leyenda:** ✅ = verificado | Pendiente = no implementado o no verificado
