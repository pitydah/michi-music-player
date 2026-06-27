# Michi Music Player v0.1.0-rc1 — Release Candidate

**Fecha:** 2026-06-26
**Estado:** Release Candidate 1
**Licencia:** GPL-3.0-or-later

---

## 🎵 ¿Qué es Michi?

Reproductor de música audiófilo para Linux (KDE Plasma) con widgets nativos Qt 6, motor GStreamer,
biblioteca SQLite FTS5, y 425+ archivos Python.

## 📦 Archivos del Release

| Archivo | Descripción |
|---------|-------------|
| `michi-music-player-0.1.0-rc1.tar.gz` | Código fuente completo (git archive) |
| `michi-music-player-0.1.0-rc1.zip` | Código fuente (ZIP) |
| `michi_music_player-0.1.0rc1-py3-none-any.whl` | Wheel instalable vía pip |
| `SHA256SUMS` | Checksums SHA256 de todos los archivos |

## 🚀 Instalación Rápida

```bash
# Opción A: Instalador unificado (recomendado)
tar xzf michi-music-player-0.1.0-rc1.tar.gz
cd michi-music-player-0.1.0-rc1
./install.sh

# Opción B: Flatpak
flatpak-builder --user --install --force-clean build-dir data/com.michi.MusicPlayer.yml

# Opción C: Solo Python (sin desktop integration)
pip install michi_music_player-0.1.0rc1-py3-none-any.whl
```

## ✨ Features en RC1

### Audio
- 9 perfiles de audio (Standard, Hi-Fi PCM, Bit-Perfect PCM, DSD→PCM, DoP, Streaming, Pure Audio, Studio Monitor, Multiroom)
- Motor GStreamer/PipeWire/ALSA con PipelineFactory + AudioRoutePlan + DspState
- EQ gráfico 31-bandas + paramétrico biquad real
- ReplayGain avanzado (track/album/auto, preamp, headroom, anti-clipping)
- Quality badge con 6 categorías y tooltip de ruta de audio
- Gapless playback + crossfade

### Biblioteca
- Indexer 2.0 incremental (walk → change detection → metadata → batch writer → FTS5)
- Search 2.0 FTS5 con filtros: `artist:`, `album:`, `format:`, `year:`, `bitrate:`, `rating:`
- Cover Flow 3D con física de desplazamiento y backdrop difuminado
- AlbumInfoBanner glass con badges
- Artistas enriquecidos (MusicBrainz + Wikipedia)
- Playlists M3U (import/export)

### Streaming & Multi-room
- Subsonic/Navidrome/Jellyfin
- Radio HTTP/ICY
- Home Assistant integration
- Snapcast multi-room
- Michi HTTP API (REST en puerto 8124)

### Reconocimiento de Música
- 3 providers: ShazamIO, AudD, AcoustID (fpcalc + Chromaprint)
- Captura continua de audio (PyAudio, 22050Hz mono)
- Matching 4-tier con historial persistente

### UI
- Glassmorphism oscuro unificado (14+ vistas)
- Sidebar premium con gradiente y glow
- 38+ iconos SVG nativos con render alpha-safe
- Sistema de temas centralizado (QSS functions, no inline styles)

## 🔧 Requisitos del Sistema

| Dependencia | Propósito |
|-------------|-----------|
| Python 3.11+ | Runtime |
| PySide6 ≥ 6.7 | UI toolkit (Qt 6) |
| GStreamer 1.0 + plugins | Motor de audio |
| PyGObject (python3-gi) | Bindings GStreamer |
| mutagen ≥ 1.47 | Metadatos |
| numpy ≥ 1.24 | DSP / EQ |
| dbus-python ≥ 1.3 | MPRIS |
| chromaprint (fpcalc) | AcoustID fingerprint |
| avahi-utils | mDNS discovery |

## 📊 Métricas de Calidad

| Métrica | Valor |
|---------|-------|
| Tests | 359 passed, 2 skipped |
| Ruff | 0 violaciones |
| Archivos Python | 425 |
| Controladores | 29 |
| Perfiles de audio | 9 |
| Providers reconocimiento | 3 reales |

## 🐛 Issues Conocidos

- Flatpak: las features de reconocimiento requieren permisos adicionales de sandbox
- DoP (DSD over PCM) es experimental — depende del DAC
- El análisis de audio (librosa) es opcional y pesado (~200MB)

## 📝 Changelog desde alpha

- **bfce2b1** fix(core): Pass 5 final — cache, tag writer, sqlite utils, audio analysis
- **0182c89** fix(core): Pass 5 cont — README honesty, icon_path robust
- **cb005b2** fix(core): Pass 5 — packaging, XDG paths, dashboard stats, logger robust
- **4c5c795** fix(ui): Visual Polish Phase 4 — metadata editor + dim interactive text
- **b91fbc2** fix(ui): Visual Polish Pass — Phase 1-3 (19 changes)

## 🔮 Próximos Pasos (Road to 0.1.0)

- [ ] Flatpak en Flathub
- [ ] Paquete AUR
- [ ] Cobertura de tests >80%
- [ ] Modo oscuro/claro toggle
- [ ] Lyrics sincronizadas (LRCLIB)
- [ ] Android sync vía Michi API
- [ ] AutoEQ database integration
