# Legacy Functional Preservation — Michi Music Player

## Purpose

This document preserves all functional knowledge from the QtWidgets frontend (`legacy_widgets/`) before its final removal.
Each section describes one functional domain: what it does, how it works, what QML/bridge/core replaces it, and what
exclusive logic must not be lost.

---

## Table of Contents

1. [Metadata Editor](#1-metadata-editor)
2. [Equalizer & DSP](#2-equalizer--dsp)
3. [Global Search](#3-global-search)
4. [Smart Tagging](#4-smart-tagging)
5. [Library Doctor](#5-library-doctor)
6. [Audio Lab — Conversion](#6-audio-lab--conversion)
7. [Audio Lab — CD Ripper](#7-audio-lab--cd-ripper)
8. [Audio Lab — ADC Recorder](#8-audio-lab--adc-recorder)
9. [Audio Lab — Analysis](#9-audio-lab--analysis)
10. [Audio Lab — Diagnostics](#10-audio-lab--diagnostics)
11. [Device Sync](#11-device-sync)
12. [Home Audio](#12-home-audio)
13. [Playlists](#13-playlists)
14. [Smart Mixes](#14-smart-mixes)
15. [Now Playing](#15-now-playing)
16. [Queue](#16-queue)
17. [Radio](#17-radio)
18. [Lyrics](#18-lyrics)
19. [Connections & Discovery](#19-connections--discovery)
20. [Settings](#20-settings)
21. [Home Dashboard](#21-home-dashboard)
22. [Artwork Management](#22-artwork-management)
23. [Controllers (legacy)](#23-controllers-legacy)
24. [Sync Services (legacy)](#24-sync-services-legacy)
25. [Audio Lab Services (legacy)](#25-audio-lab-services-legacy)

---

## 1. Metadata Editor

### Identification
- **ID:** metadata_editor
- **Domain:** metadata
- **Criticidad:** HIGH
- **Estado legacy:** FROZEN
- **Estado QML:** PARTIAL
- **Nivel de riesgo:** MEDIUM — legacy has richer batch editing, diff view, conflict resolution, and undo that QML partially exposes

### Archivos relacionados
- **Legacy:** `legacy_widgets/ui/metadata_editor` (imported, source deleted — only pyc remains)
- **QML:** `ui_qml/pages/metadata/MetadataEditorPage.qml`, `MetadataInspectorPage.qml`, `MetadataSingleEditor.qml`, `MetadataBatchEditor.qml`, `MetadataDiffView.qml`, `MetadataConflictView.qml`, `MetadataFieldRow.qml`, `MetadataFieldGrid.qml`, `MetadataPreview.qml`, `MetadataArtworkEditor.qml`, `MetadataArtworkPreview.qml`, `MetadataWriteProgress.qml`
- **Bridge:** `ui_qml_bridge/metadata_bridge.py` (585 lines)
- **Core:** `core/metadata_service.py` (465 lines), `metadata/tag_writer.py` (203 lines), `metadata/tag_reader.py` (281 lines)

### Propósito funcional
Editar metadatos de archivos de audio (tags ID3, Vorbis, MP4) individualmente o en lote. Incluye artwork embedding, diff preview, conflict resolution, y undo.

### Workflow del usuario (legacy)
1. Usuario selecciona canción(es) en la biblioteca
2. Click derecho → "Editar metadatos" o atajo de teclado
3. Se abre ventana con campos: título, artista, álbum, artista álbum, género, año, #pista, #total pistas, #disco, compositor, BPM, comentario, letras
4. Usuario modifica campos
5. Preview de cambios (diff view)
6. Confirmar → escribe tags via `metadata/tag_writer.py`
7. Si hay conflictos (edición múltiple), muestra `MetadataConflictView`
8. Undo disponible tras escritura

### Capacidades visibles (legacy)
- Grid de campos editables en lote
- Diff preview de cambios vs original
- Conflict resolution para edición múltiple
- Artwork preview y reemplazo
- Indicador de progreso en escritura batch
- Undo tras escritura

### Reglas de negocio
- `TrackTags.TEXT_FIELDS` define qué campos se escriben
- `dirty_fields` tracking: solo se escriben campos modificados
- `use_all` fallback: si no hay dirty_fields, escribe todos (backward compat)
- Artwork: soporta JPEG y PNG, embedding específico por formato (APIC para MP3, Pictures para FLAC, covr para MP4)
- Errores de escritura capturados en `tags.error`

### Conocimiento exclusivo del legacy
- Batch editing diff view con resaltado de cambios
- Undo stack para revertir escrituras
- Conflicto de edición concurrente (varios usuarios/ventanas)

### Defectos que no deben replicarse
- Escritura directa sin backup (ya corregido en `metadata/tag_writer.py`)
- `errors='ignore'` en normalización de álbum (ya corregido en `album_identity.py`)
- Sin encoding fallback en tag_reader — Mutagen maneja encoding internamente

### Estado de paridad

| Capacidad | Legacy | QML actual | Backend actual | Estado |
|-----------|--------|------------|----------------|--------|
| Edición título | ✅ | ✅ | ✅ | PARITY |
| Edición artista | ✅ | ✅ | ✅ | PARITY |
| Edición álbum | ✅ | ✅ | ✅ | PARITY |
| Edición género | ✅ | ✅ | ✅ | PARITY |
| Edición año | ✅ | ✅ | ✅ | PARITY |
| Edición #pista | ✅ | ✅ | ✅ | PARITY |
| Edición compositor | ✅ | ✅ | ✅ | PARITY |
| Edición BPM | ✅ | ✅ | ⚠️ | PARITY |
| Batch editing | ✅ | ✅ | ✅ | PARITY |
| Artwork embedding | ✅ | ✅ | ✅ | PARITY |
| Diff preview | ✅ | ✅ | ✅ | PARITY |
| Conflict resolution | ✅ | ✅ | ✅ | PARITY |
| Write undo | ✅ | ⚠️ Missing | ✅ | BACKEND_AVAILABLE_UI_MISSING |
| Write progress | ✅ | ✅ | ✅ | PARITY |

---

## 2. Equalizer & DSP

### Identification
- **ID:** equalizer
- **Domain:** audio
- **Criticidad:** HIGH
- **Estado legacy:** FROZEN
- **Estado QML:** PARITY
- **Nivel de riesgo:** LOW — QML equalizer is fully functional with bridge

### Archivos relacionados
- **Legacy:** `legacy_widgets/ui/controllers/audio_output_controller.py`
- **QML:** `ui_qml/pages/equalizer/EqualizerPage.qml`, `EqualizerGraph.qml`, `EqualizerBandControl.qml`, `EqualizerPresetBrowser.qml`, `DSPChainPage.qml`, `DSPModuleCard.qml`, `DSPConflictWarning.qml`
- **Bridge:** `ui_qml_bridge/eq_bridge.py` (348 lines)
- **Core:** `core/equalizer_service.py`, `audio/eq_*.py`, `audio/dsp_state.py`, `audio/eq_presets.py`, `audio/eq_biquad.py`, `audio/eq_convert.py`

### Propósito funcional
Control gráfico y paramétrico del ecualizador, presets, cadena DSP, bypass, preamp, gestión de conflictos con modo bit-perfect.

### Capacidades QML verificadas
- Graphic EQ (10 bandas) y Parametric EQ (6 bandas)
- Preamp slider (-24 a +24 dB)
- Presets: cargar, guardar, importar, exportar
- Bypass toggle con badge de estado
- Detección de conflicto bit-perfect (EQ bloqueado en modo MPD)
- Persistencia de estado

### Reglas de negocio
- MPD backend bloquea EQ digital → muestra "No disponible"
- Bypass no disponible durante conflicto bit-perfect
- Presets se persisten en `audio.eq_presets` + `core.settings_manager`

### Estado de paridad

| Capacidad | Legacy | QML actual | Backend | Estado |
|-----------|--------|------------|---------|--------|
| Graphic EQ 10 bandas | ✅ | ✅ | ✅ | PARITY |
| Parametric EQ | ✅ | ✅ | ✅ | PARITY |
| Preamp | ✅ | ✅ | ✅ | PARITY |
| Presets | ✅ | ✅ | ✅ | PARITY |
| Bypass | ✅ | ✅ | ✅ | PARITY |
| DSP chain | ✅ | ✅ | ✅ | PARITY |
| MPD conflict | ✅ | ✅ | ✅ | PARITY |
| Import/export presets | ✅ | ✅ | ✅ | PARITY |

---

## 3. Global Search

### Identification
- **ID:** global_search
- **Domain:** library
- **Criticidad:** HIGH
- **Estado legacy:** FROZEN
- **Estado QML:** PARTIAL
- **Nivel de riesgo:** MEDIUM — `ui/search_controller.py` source deleted, bridge exists but QML search is simpler than legacy

### Archivos relacionados
- **Legacy:** `legacy_widgets/ui/controllers/navigation_controller.py` (search route config)
- **QML:** `ui_qml/pages/search/GlobalSearchPage.qml`, `SearchFiltersDrawer.qml`, `SearchSuggestions.qml`, `SearchResultRow.qml`, `SearchResultGroup.qml`, `SearchResultSection.qml`, `SearchResultDelegate.qml`, `SearchResultItem.qml`, `SearchRecentQueries.qml`, `GlobalSearchOverlay.qml`
- **Bridge:** `ui_qml_bridge/global_search_bridge.py`
- **Core:** `core/global_search_service.py`, `library/search_engine.py`, `library/search_index.py`

### NOTA SOBRE SEARCH CONTROLLER
`ui/search_controller.py` source file has been **deleted** (only `.pyc` remains in `legacy_widgets/ui/__pycache__/`).
`legacy_widgets/ui/window.py` imports it (`from ui.search_controller import SearchController`) but this import
would fail at runtime since `ui/` does not exist outside legacy_widgets. The `.pyc` cache may still allow execution
if the working directory is `legacy_widgets/`.

The QML replacement uses `GlobalSearchBridge` + `GlobalSearchService` + `SearchEngine` (FTS5). This is architecturally
superior (search logic in `library/`, bridge in `ui_qml_bridge/`). However, the legacy search controller filtered by
multiple criteria (type, year, quality) with AND/OR logic which the QML version may not fully match.

### Capacidades QML verificadas
- Debounced text search (300ms)
- Type filters, year range, quality filter
- Grouped results (tracks, albums, artists)
- Recent queries
- Stale result guard with request generation counter

### Reglas de negocio
- FTS5 MATCH para búsqueda rápida (<10ms)
- LIKE fallback si FTS5 da 0 resultados (~200ms)
- Filtros de campo: `artist:`, `album:`, `year:>`, `bitrate:>=`
- Cancelación de búsqueda anterior al escribir nuevo término

### Estado de paridad

| Capacidad | Legacy | QML actual | Backend | Estado |
|-----------|--------|------------|---------|--------|
| Text search | ✅ | ✅ | ✅ | PARITY |
| Type filters | ✅ | ✅ | ✅ | PARITY |
| Advanced field filters | ✅ | ⚠️ | ✅ | BACKEND_AVAILABLE_UI_MISSING |
| Recent queries | ✅ | ✅ | ✅ | PARITY |
| Result navigation | ✅ | ✅ | ✅ | PARITY |
| Cancel previous search | ✅ | ✅ | ✅ | PARITY |

---

## 4. Smart Tagging

### Identification
- **ID:** smart_tagging
- **Domain:** metadata
- **Criticidad:** MEDIUM
- **Estado legacy:** FROZEN
- **Estado QML:** PARTIAL
- **Nivel de riesgo:** LOW

### Archivos relacionados
- **Legacy:** `legacy_widgets/ui/audio_lab/services/smart_tagging_service.py` (199 lines)
- **QML:** `ui_qml/pages/SmartTaggingPage.qml`, `ui_qml/pages/metadata/SmartTaggingWorkflowPage.qml`
- **Bridge:** `ui_qml_bridge/smart_tagging_bridge.py`
- **Core:** `core/smart_tagging_service.py` (52 lines)

### Conocimiento exclusivo del legacy
Legacy `smart_tagging_service.py` has richer model classes (`TagSuggestion`, `TrackMetadata`) with confidence scoring, multiple source tracking, and batch status management that `core/smart_tagging_service.py` (52 lines) lacks.

### Estado de paridad

| Capacidad | Legacy | QML actual | Backend | Estado |
|-----------|--------|------------|---------|--------|
| Scan single track | ✅ | ✅ | ✅ | PARITY |
| Scan batch | ✅ | ✅ | ⚠️ | PARTIAL |
| Confidence display | ✅ | ⚠️ | ⚠️ | UI_PRESENT_WORKFLOW_INCOMPLETE |
| Accept/reject suggestions | ✅ | ✅ | ✅ | PARITY |
| Rollback batch | ✅ | ⚠️ | ⚠️ | BACKEND_AVAILABLE_UI_MISSING |

---

## 5. Library Doctor

### Identification
- **ID:** library_doctor
- **Domain:** library
- **Criticidad:** MEDIUM
- **Estado legacy:** FROZEN
- **Estado QML:** PARITY
- **Nivel de riesgo:** LOW

### Archivos relacionados
- **Legacy:** `legacy_widgets/ui/audio_lab/services/library_doctor.py` (247 lines)
- **QML:** `ui_qml/pages/library_doctor/LibraryDoctorPage.qml`, `LibraryDoctorIssueList.qml`, `LibraryDoctorIssueDetail.qml`, `LibraryDoctorScanPage.qml`, `LibraryDoctorReport.qml`, `LibraryDoctorProgress.qml`, `DoctorDryRunPage.qml`, `DoctorReportPage.qml`, `DoctorRepairProgress.qml`, `DoctorIssueList.qml`, `DoctorIssueDetail.qml`, `LibraryDoctorFixPreview.qml`
- **Bridge:** `ui_qml_bridge/library_doctor_bridge.py`
- **Core:** `core/library_doctor_service.py`, `core/library_doctor/` (repositories, scan, repair)

### Estado de paridad

| Capacidad | Legacy | QML actual | Backend | Estado |
|-----------|--------|------------|---------|--------|
| Scan for issues | ✅ | ✅ | ✅ | PARITY |
| Issue categories | ✅ | ✅ | ✅ | PARITY |
| Dry run | ✅ | ✅ | ✅ | PARITY |
| Repair selected/all | ✅ | ✅ | ✅ | PARITY |
| Progress feedback | ✅ | ✅ | ✅ | PARITY |
| Report generation | ✅ | ✅ | ✅ | PARITY |

---

## 6. Audio Lab — Conversion

### Identification
- **ID:** audio_conversion
- **Domain:** audio_lab
- **Criticidad:** HIGH
- **Estado legacy:** FROZEN
- **Estado QML:** PARITY (with bugs)
- **Nivel de riesgo:** MEDIUM — conversion page works but progress is fake

### Archivos relacionados
- **Legacy:** `legacy_widgets/ui/audio_lab/services/encoder_service.py` (143 lines, uses `QProcess`)
- **QML:** `ui_qml/pages/audio_lab/AudioConversionPage.qml` (571 lines), `AudioConversionProfileEditor.qml`, `AudioInputSelection.qml`
- **Bridge:** `ui_qml_bridge/audio_lab_bridge.py`
- **Core:** `core/audio_lab/audio_conversion_service.py`

### Defectos conocidos (no replicar)
- Progress falso: `proc.communicate()` bloquea sin emitir progreso (bug P1)
- Legacy `encoder_service.py` usa `QProcess` (Qt-specific) — core usa `subprocess.Popen` (correcto)

### Estado de paridad

| Capacidad | Legacy | QML actual | Backend | Estado |
|-----------|--------|------------|---------|--------|
| Format selection | ✅ | ✅ | ✅ | PARITY |
| Codec/bitrate options | ✅ | ✅ | ✅ | PARITY |
| Sample rate / bit depth | ✅ | ✅ | ✅ | PARITY |
| Output directory | ✅ | ✅ | ✅ | PARITY |
| Collision policy | ✅ | ✅ | ✅ | PARITY |
| Naming template | ✅ | ✅ | ✅ | PARITY |
| Progress feedback | ✅ | ⚠️ Fake | ⚠️ | UI_PRESENT_WORKFLOW_INCOMPLETE |
| Cancellation | ✅ | ✅ | ✅ | PARITY |
| Batch conversion | ✅ | ✅ | ✅ | PARITY |

---

## 7. Audio Lab — CD Ripper

### Identification
- **ID:** cd_ripper
- **Domain:** audio_lab
- **Criticidad:** HIGH
- **Estado legacy:** FROZEN
- **Estado QML:** PARTIAL
- **Nivel de riesgo:** MEDIUM — QML page exists but uses some simulated values

### Archivos relacionados
- **Legacy:** `legacy_widgets/ui/audio_lab/services/rip_job_manager.py` (120), `rip_worker.py` (176, QProcess+cdparanoia), `disc_detection_service.py` (176)
- **QML:** `ui_qml/pages/audio_lab/CDRipperPage.qml` (368 lines)
- **Bridge:** `ui_qml_bridge/audio_lab_bridge.py`, `ui_qml_bridge/disc_lab_bridge.py`
- **Core:** `core/audio_lab/cd_ripper_service.py`

### Conocimiento exclusivo del legacy
- `rip_worker.py`: Progress parsing from `cdparanoia` stderr output (real-time %)
- `rip_job_manager.py`: Full job lifecycle with retry, cancellation, error recovery
- `disc_detection_service.py`: Optical drive detection via `cdparanoia -V` and `udisksctl`

### Estado de paridad

| Capacidad | Legacy | QML actual | Backend | Estado |
|-----------|--------|------------|---------|--------|
| Drive detection | ✅ | ✅ | ✅ | PARITY |
| CD info loading | ✅ | ✅ | ✅ | PARITY |
| Track selection | ✅ | ✅ | ✅ | PARITY |
| Format selection | ✅ | ✅ | ✅ | PARITY |
| Output folder | ✅ | ✅ | ⚠️ fixed path | PARTIAL |
| Progress feedback | ✅ | ⚠️ | ⚠️ Simulated | UI_PRESENT_WORKFLOW_INCOMPLETE |
| Cancellation | ✅ | ✅ | ✅ | PARITY |
| Per-track size estimation | ✅ | ⚠️ Simulated | ⚠️ | PARTIAL |

---

## 8. Audio Lab — ADC Recorder

### Identification
- **ID:** adc_recorder
- **Domain:** audio_lab
- **Criticidad:** MEDIUM
- **Estado legacy:** FROZEN
- **Estado QML:** PARTIAL
- **Nivel de riesgo:** MEDIUM — VU meter is simulated, core service has thread leak (fix applied)

### Archivos relacionados
- **Legacy:** `legacy_widgets/ui/audio_lab/vinyl_lab_page.py` (660 lines, full vinyl workflow)
- **QML:** `ui_qml/pages/audio_lab/ADCRecorderPage.qml` (526 lines)
- **Bridge:** `ui_qml_bridge/audio_lab_bridge.py`
- **Core:** `core/audio_lab/adc_recorder_service.py`

### Capacidades QML
- USB turntable auto-detection
- Audio device listing
- Recording level meter
- Start/stop/pause recording
- Track markers/cue points
- Output path selection

### Conocimiento exclusivo del legacy
- `vinyl_lab_page.py` (660 lines): Full vinyl digitization workflow — source selection, calibration, recording, waveform review, track splitting, export. This is a complete workflow not replicated in QML.

### Estado de paridad

| Capacidad | Legacy | QML actual | Backend | Estado |
|-----------|--------|------------|---------|--------|
| Device detection | ✅ | ✅ | ✅ | PARITY |
| Recording | ✅ | ✅ | ✅ | PARITY |
| VU meter | ✅ | ⚠️ Simulated (-60) | ⚠️ | PARTIAL |
| Pause/resume | ✅ | ✅ | ✅ | PARITY |
| Markers/cue points | ✅ | ✅ | ✅ | PARITY |
| Waveform review | ✅ | ❌ Missing | ❌ | NOT_STARTED |
| Track splitting | ✅ | ❌ Missing | ⚠️ | NOT_STARTED |
| Calibration | ✅ | ❌ Missing | ❌ | NOT_STARTED |
| Vinyl workflow (full) | ✅ | ❌ Missing | ❌ | NOT_STARTED |

---

## 9. Audio Lab — Analysis

### Identification
- **ID:** audio_analysis
- **Domain:** audio_lab
- **Criticidad:** MEDIUM
- **Estado legacy:** FROZEN
- **Estado QML:** PARITY

### Archivos relacionados
- **Legacy:** None specific — analysis is in core
- **QML:** `ui_qml/pages/audio_lab/AudioAnalysisPage.qml` (229 lines)
- **Bridge:** `ui_qml_bridge/audio_lab_bridge.py` + `audio_analysis_bridge.py`
- **Core:** `core/audio_lab/`, `audio/audio_analysis/`

### Estado de paridad

| Capacidad | Legacy | QML actual | Backend | Estado |
|-----------|--------|------------|---------|--------|
| Codec analysis | ✅ | ✅ | ✅ | PARITY |
| Loudness analysis | ✅ | ✅ | ✅ | PARITY |
| Clipping detection | ✅ | ✅ | ✅ | PARITY |
| Silence detection | ✅ | ✅ | ✅ | PARITY |
| BPM detection | ✅ | ✅ | ✅ | PARITY |
| File comparison | ✅ | ✅ | ✅ | PARITY |
| Batch analysis | ✅ | ✅ | ✅ | PARITY |

---

## 10. Audio Lab — Diagnostics

### Identification
- **ID:** audio_diagnostics
- **Domain:** audio_lab
- **Criticidad:** MEDIUM
- **Estado legacy:** FROZEN
- **Estado QML:** PARITY

### Archivos relacionados
- **Legacy:** `legacy_widgets/ui/audio_lab/diagnostics_service.py` (32 lines, re-exports from core)
- **QML:** `ui_qml/pages/DiagnosticsPage.qml`
- **Bridge:** `ui_qml_bridge/diagnostics_bridge.py`
- **Core:** `core/audio_lab/diagnostics_service.py` (904 lines)

### NOTA
Legacy diagnostics_service.py is already a thin re-export wrapper. Core version is 904 lines — fully migrated.

---

## 11. Device Sync

### Identification
- **ID:** device_sync
- **Domain:** devices
- **Criticidad:** HIGH
- **Estado legacy:** FROZEN
- **Estado QML:** PARTIAL
- **Nivel de riesgo:** HIGH — 7 legacy sync service files have no core equivalents

### Archivos relacionados
- **Legacy:** `legacy_widgets/ui/services/device_registry.py`, `device_sync_controller.py`, `sync_manifest_builder.py`, `sync_manifest_store.py`, `sync_queue.py`, `transcode_service.py`, `transfer_backends.py`
- **QML:** `ui_qml/pages/devices/DevicesPage.qml`, `DeviceDetailPage.qml`, `DevicePairingPage.qml`, `DeviceSyncProfileEditor.qml`, `DeviceTransferPanel.qml`, `DeviceTransferQueue.qml`, `DeviceTransferJob.qml`, `DeviceStoragePanel.qml`, `DeviceSyncHistory.qml`, `DeviceStorageView.qml`, `DeviceCompatibilityView.qml`, `DeviceCard.qml`
- **Bridge:** `ui_qml_bridge/devices_bridge.py`
- **Core:** `core/device_sync_service.py`, `core/sync/` (7 files)

### Conocimiento exclusivo del legacy
The legacy `ui/services/` sync files contain orchestration logic (controller patterns) that was never extracted to `core/sync/`. The core sync package has the low-level implementations, but the legacy layer adds job management, pairing flow, and UI state coordination.

### Estado de paridad

| Capacidad | Legacy | QML actual | Backend | Estado |
|-----------|--------|------------|---------|--------|
| Device discovery | ✅ | ✅ | ✅ | PARITY |
| Pairing | ✅ | ✅ | ✅ | PARITY |
| Transfer management | ✅ | ✅ | ⚠️ | PARTIAL |
| Manifest generation | ✅ | ⚠️ | ✅ | BACKEND_AVAILABLE_UI_MISSING |
| Transcoding | ✅ | ⚠️ | ✅ | BACKEND_AVAILABLE_UI_MISSING |
| Sync history | ✅ | ✅ | ✅ | PARITY |
| Cancellation | ✅ | ✅ | ✅ | PARITY |
| Retry | ✅ | ⚠️ | ✅ | BACKEND_AVAILABLE_UI_MISSING |

---

## 12. Home Audio

### Identification
- **ID:** home_audio
- **Domain:** multiroom
- **Criticidad:** MEDIUM
- **Estado legacy:** FROZEN
- **Estado QML:** PARITY

### Archivos relacionados
- **Legacy:** `legacy_widgets/ui/controllers/home_audio_controller.py`, `home_audio_handlers.py`
- **QML:** `ui_qml/pages/home_audio/HomeAudioPage.qml`, `GroupEditorPage.qml`, `ZoneDetailPage.qml`, `LatencyControl.qml`, `PlaybackTransferDialog.qml`, `MultiroomStatus.qml`, `ReceiverCard.qml`, `StreamRoutingPage.qml`, `HomeAudioModeSelector.qml`, `MichiMusicStreamPanel.qml`, `HomeAssistantPanel.qml`, `AudioZoneCard.qml`, `LatencyPage.qml`, `ZoneCard.qml`
- **Bridge:** `ui_qml_bridge/home_audio_bridge.py`
- **Core:** `integrations/home_audio_service.py`, `integrations/home_assistant/`

### Estado de paridad

| Capacidad | Legacy | QML actual | Backend | Estado |
|-----------|--------|------------|---------|--------|
| Group management | ✅ | ✅ | ✅ | PARITY |
| Zone control | ✅ | ✅ | ✅ | PARITY |
| Playback transfer | ✅ | ✅ | ✅ | PARITY |
| Latency control | ✅ | ✅ | ✅ | PARITY |
| HA receiver management | ✅ | ✅ | ✅ | PARITY |

---

## 13. Playlists

### Identification
- **ID:** playlists
- **Domain:** playlists
- **Criticidad:** MEDIUM
- **Estado legacy:** FROZEN
- **Estado QML:** PARITY

### Archivos relacionados
- **Legacy:** `legacy_widgets/ui/controllers/playlist_controller.py` (562 lines)
- **QML:** `ui_qml/pages/playlists/PlaylistsPage.qml`, `PlaylistDetailPage.qml`, `PlaylistTrackList.qml`, `PlaylistCard.qml`, `PlaylistEditorDialog.qml`, `SmartPlaylistEditorPage.qml`, `PlaylistImportDialog.qml`, `PlaylistExportDialog.qml`, `PlaylistCard.qml`
- **Bridge:** `ui_qml_bridge/playlists_bridge.py`
- **Core:** `core/playlist_service.py`, `core/smart_playlist_service.py`

---

## 14. Smart Mixes

### Identification
- **ID:** smart_mixes
- **Domain:** mixes
- **Criticidad:** LOW
- **Estado legacy:** FROZEN
- **Estado QML:** PARITY

### Archivos relacionados
- **Legacy:** `legacy_widgets/ui/controllers/smart_mix_controller.py`, `smart_mix_preview.py`
- **QML:** `ui_qml/pages/mix/MixHubPage.qml`, `MixRuleEditorPage.qml`, `MixRuleEditor.qml`, `MixResultPage.qml`, `MixGeneratorPage.qml`, `MixGenerationProgress.qml`, `MixDetailPage.qml`, `MixExplanationPanel.qml`, `MixExplanationDrawer.qml`, `MixFeedbackControls.qml`
- **Bridge:** `ui_qml_bridge/mix_bridge.py`
- **Core:** `core/mix_service.py`

---

## 15. Now Playing

### Identification
- **ID:** now_playing
- **Domain:** playback
- **Criticidad:** HIGH
- **Estado legacy:** FROZEN
- **Estado QML:** PARITY

### Archivos relacionados
- **Legacy:** `legacy_widgets/ui/nowplaying_bar.py` (1297 lines)
- **QML:** `ui_qml/pages/nowplaying/NowPlayingPage.qml`, `NowPlayingControls.qml`, `NowPlayingProgress.qml`, `NowPlayingArtwork.qml`, `NowPlayingMetadata.qml`, `NowPlayingHeader.qml`, `NowPlayingOutputSelector.qml`, `NowPlayingLyricsPane.qml`, `NowPlayingTechnicalInfo.qml`, `NowPlayingQueuePreview.qml`, plus `ui_qml/components/NowPlayingBar.qml`
- **Bridge:** `ui_qml_bridge/nowplaying_bridge.py` (1099 lines)

### Conocimiento exclusivo del legacy
Legacy nowplaying_bar.py has custom `QPainter`-drawn widgets (gradient sliders, rounded covers, source badges) that QML doesn't replicate. These are visual polish, not functional gaps.

---

## 16. Queue

### Identification
- **ID:** queue
- **Domain:** playback
- **Criticidad:** MEDIUM
- **Estado legacy:** FROZEN
- **Estado QML:** PARITY

### Archivos relacionados
- **QML:** `ui_qml/pages/queue/QueuePage.qml`, `QueueListView.qml`, `QueueItem.qml`, `QueueHistorySection.qml`
- **Bridge:** `ui_qml_bridge/queue_bridge.py`
- **Core:** `core/queue_service.py` (308 lines — RLock applied)

---

## 17. Radio

### Identification
- **ID:** radio
- **Domain:** streaming
- **Criticidad:** LOW
- **Estado legacy:** FROZEN
- **Estado QML:** PARITY

### Archivos relacionados
- **QML:** `ui_qml/pages/radio/RadioPage.qml`, `RadioSearchView.qml`, `RadioStationDetail.qml`, `RadioImportDialog.qml`, `RadioEditorDialog.qml`, `RadioImportExportPanel.qml`
- **Bridge:** `ui_qml_bridge/radio_bridge.py`
- **Core:** `core/radio/`

---

## 18. Lyrics

### Identification
- **ID:** lyrics
- **Domain:** lyrics
- **Criticidad:** LOW
- **Estado legacy:** FROZEN
- **Estado QML:** PARITY

### Archivos relacionados
- **QML:** `ui_qml/pages/lyrics/LyricsPage.qml`, `LyricsEditDialog.qml`
- **Bridge:** `ui_qml_bridge/lyrics_bridge.py`
- **Core:** `core/lyrics/`, `infrastructure/lyrics/`

---

## 19. Connections & Discovery

### Identification
- **ID:** connections
- **Domain:** network
- **Criticidad:** MEDIUM
- **Estado legacy:** FROZEN
- **Estado QML:** PARITY

### Archivos relacionados
- **QML:** `ui_qml/pages/connections/ConnectionsPage.qml`, `ConnectionSetupWizard.qml`, `ManualConnectionDialog.qml`, `ConnectionDiscoveryPage.qml`, `ConnectionDetailPage.qml`, `ConnectionCard.qml`, `DiscoveredServerCard.qml`, `ConfiguredServerCard.qml`, etc. (16 files)
- **Bridge:** `ui_qml_bridge/connections_bridge.py`
- **Core:** `integrations/connections/`

---

## 20. Settings

### Identification
- **ID:** settings
- **Domain:** config
- **Criticidad:** MEDIUM
- **Estado legacy:** FROZEN
- **Estado QML:** PARITY

### Archivos relacionados
- **QML:** `ui_qml/pages/settings/SettingsGeneralPage.qml`, `SettingsAudioPage.qml`, `SettingsAppearancePage.qml`, `SettingsPlaybackPage.qml`, `SettingsLibraryPage.qml`, `SettingsAccessibilityPage.qml`, `SettingsAboutPage.qml`, `LibrarySourcesPage.qml`, plus `ui_qml/pages/SettingsPage.qml`
- **Bridge:** `ui_qml_bridge/settings_bridge_v2.py`, `accessibility_bridge.py`, `theme_bridge.py`
- **Core:** `core/settings_manager.py`

---

## 21. Home Dashboard

### Identification
- **ID:** home_dashboard
- **Domain:** home
- **Criticidad:** LOW
- **Estado legacy:** FROZEN
- **Estado QML:** PARITY

### Archivos relacionados
- **QML:** `ui_qml/pages/home/HomePage.qml`, `HomeHero.qml`, `ContinueCard.qml`, `LibraryStatusCard.qml`, `EcosystemCard.qml`, `AssistantCard.qml`
- **Bridge:** `ui_qml_bridge/home_bridge.py`
- **Core:** `core/home/home_dashboard_service.py`

---

## 22. Artwork Management

### Identification
- **ID:** artwork
- **Domain:** metadata
- **Criticidad:** LOW
- **Estado legacy:** FROZEN
- **Estado QML:** PARTIAL
- **Nivel de riesgo:** LOW

### Archivos relacionados
- **Legacy:** `legacy_widgets/ui/artwork_picker.py` (274 lines) — preview, crop, resize dialog
- **QML:** `ui_qml/pages/metadata/MetadataArtworkEditor.qml`, `MetadataArtworkPreview.qml`
- **Bridge:** `ui_qml_bridge/cover_bridge.py`, `cover_provider_bridge.py`
- **Core:** `core/cover_art_service.py`, `library/artwork_cache.py`, `library/album_art.py`

### Conocimiento exclusivo del legacy
Artwork picker dialog (`artwork_picker.py`) provides preview, resize, and crop functionality not available in QML. QML can replace/embed artwork but lacks the crop/resize dialog.

---

## 23. Controllers (legacy)

All 39 controllers in `legacy_widgets/ui/controllers/` are marked as replaced by `ui_qml_bridge`.
They coordinate window widgets with backend services. Since the window widgets are gone,
these controllers serve only as behavioral documentation.

### Key controllers (notable for exclusive logic):

| Controller | Lines | Exclusive logic |
|------------|-------|-----------------|
| `navigation_controller.py` | 665 | Route dispatch dictionary (50+ routes), SECTION_CONFIG (40+ entries), nav history |
| `playlist_controller.py` | 562 | M3U import/export, CRUD from all sources |
| `album_controller.py` | 561 | Album detail with 3 fallback priorities |
| `artist_controller.py` | 460 | Artist grid/detail, enrichment, aliases |
| `library_controller.py` | 358 | Tab refresh coordination |
| `folder_controller.py` | 353 | Health/integrity workers with QThread |
| `songs_controller.py` | 319 | Bulk song actions, audio lab badges |
| `genre_controller.py` | 310 | Genre hub/detail, cleanup |
| `audio_lab_controller.py` | 247 | Lazy-init for 13 sub-pages |
| `home_audio_handlers.py` | 333 | All home assistant signal handlers |

---

## 24. Sync Services (legacy)

7 files in `legacy_widgets/ui/services/` have NO core equivalent. These are the primary blockers
for legacy_widgets removal:

| File | Lines | Function |
|------|-------|----------|
| `device_registry.py` | 145 | Persistent paired device storage, token hashing |
| `device_sync_controller.py` | 128 | Pairing flow, manifest coordination |
| `playlist_cover_service.py` | 110 | Mosaic cover generation (Qt-specific QPainter) |
| `sync_manifest_builder.py` | 249 | Android-compatible transfer manifests |
| `sync_manifest_store.py` | 73 | Persistent manifest storage with history |
| `sync_queue.py` | 99 | Transfer job management with progress/cancel |
| `transcode_service.py` | 171 | ffmpeg mobile transcoding (flac_mobile, opus_*) |
| `transfer_backends.py` | 104 | Wireless/MTP/Filesystem backends |

---

## 25. Audio Lab Services (legacy)

10 files in `legacy_widgets/ui/audio_lab/services/` with unique functionality:

| File | Lines | Function | Core equivalent |
|------|-------|----------|-----------------|
| `artwork_resolver.py` | 210 | Local cover search & ranking | None (uses Qt QPixmap) |
| `disc_detection_service.py` | 176 | Optical drive + ISO detection | Duplicate of `core/audio_lab/cd_ripper_service.py` |
| `encoder_service.py` | 143 | Real encoding via QProcess | Replaced by `core/audio_lab/audio_conversion_service.py` |
| `external_tools.py` | 52 | System tool diagnostics | None — extract to `core/audio_lab/dependencies.py` |
| `library_doctor.py` | 247 | Metadata diagnostics | Replaceable by `core/library_doctor_service.py` |
| `library_importer.py` | 148 | File copy + DB registration | None — extract to `core/library/importer.py` |
| `metadata_resolver.py` | 188 | Disc TOC album identification | None (local only) |
| `rip_job_manager.py` | 120 | CD rip job lifecycle | Duplicate of `core/audio_lab/cd_ripper_service.py` |
| `rip_worker.py` | 176 | cdparanoia wrapper + progress | Partially in `core/audio_lab/cd_ripper_service.py` (without QProcess) |
| `smart_tagging_service.py` | 199 | MusicBrainz suggestions | Partially in `core/smart_tagging_service.py` (52 lines — less rich) |
