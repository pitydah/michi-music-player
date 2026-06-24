# Michi Music Player

Reproductor audiófilo premium para Linux · PySide6/Qt6 · GStreamer · 206 tests · ruff 0

[![Tests](https://img.shields.io/badge/tests-206%2F206-brightgreen)]()
[![Ruff](https://img.shields.io/badge/ruff-0-green)]()
[![Python](https://img.shields.io/badge/python-3.11+-blue)]()
[![License](https://img.shields.io/badge/license-GPL--3.0-orange)]()

![Michi](icons/app_icon.png)

## Características

### Audio
- 🎵 **9 perfiles de audio** — Standard, Hi-Fi PCM, Bit-Perfect PCM, DSD→PCM, DoP (experimental), Streaming, Pure Audio, Studio Monitor, Multiroom/Snapcast
- 🔊 **Motor GStreamer/PipeWire/ALSA** — PipelineFactory con AudioRoutePlan + DspState, DAC-aware con 25+ marcas detectadas
- 🎛️ **EQ gráfico 31-bandas + paramétrico real** — Biquads vía `audioiirfilter`, coeficientes calculados en tiempo real, preamp, presets AutoEQ
- 📊 **ReplayGain avanzado** — Modos track/album/auto, preamp, headroom, anti-clipping, ganancia segura computada
- 🏷️ **Quality badge** — 6 categorías (lossy/lossless/hi-res/DSD), tooltip con ruta de audio completa, diálogo de diagnóstico
- 🔄 **Gapless playback + crossfade** — Precarga vía `about-to-finish`, sin stops redundantes
- 📻 **Radio + Streaming** — Subsonic/Navidrome/Jellyfin, emisoras HTTP/ICY

### Biblioteca
- 📚 **Indexer 2.0 incremental** — FileWalker → ChangeDetector (size+mtime) → MetadataExtractor → AlbumKeyBuilder → BatchWriter (100/lote) → Cleanup → FTS5 rebuild
- 🔍 **Search 2.0 FTS5** — Búsqueda full-text con filtros: `artist:Genesis`, `album:"The Lamb"`, `format:flac`, `year:>2000`, `bitrate:>=320`, `rating:>=4`
- 🌀 **Cover Flow visual** — Vista de álbumes 3D implementada de forma independiente, con física de desplazamiento, reflejos, slider premium, backdrop difuminado y modos render
- 🖼️ **AlbumInfoBanner** — Card glass 130-175px, mini cover 88×88, badges Info externa/Caché/Local, botones Reproducir/+Cola/Detalles
- 🎤 **Artistas enriquecidos** — Bio, imágenes (MusicBrainz + Wikipedia), géneros, estilo, display_name búsqueda
- 📋 **Playlists** — Importar/exportar M3U, crear desde carpeta/cola/álbum/artista/género/búsqueda
- 🏗️ **Metadata avanzada** — MusicBrainz IDs, BPM, ReplayGain tags, bit_depth, disc_number/total, albumartist, originaldate

### Multiroom & Home Audio
- 🏠 **Home Assistant** — Cliente REST vía QNetworkAccessManager, estados, media_player, play_media, control de volumen
- 📡 **Snapcast** — SnapServerManager (QProcess), AudioCapture (pactl null-sink), GroupManager (zonas QSettings), SnapClientDiscovery (avahi-browse)
- 🔀 **Cast unificado** — Menú combinando salida local + TransmitManager + Snapcast + Home Assistant
- 🎯 **Transmit desacoplado** — 7 controladores: AudioOutput, Snapcast, HomeAudio, Cast, LocalMediaServer, MiniPlayer, TransmitManager
- 🌐 **Michi HTTP API** — REST en puerto 8124, token Bearer, endpoints player/status/destinations/play_media/library/browse
- 📢 **mDNS advertiser** — `avahi-publish-service` para descubrimiento automático
- 🖥️ **Receiver Wizard** — Guías HTML para Raspberry Pi, ESP32 y Docker Snapclient

### Identificación de música
- 🎧 **3 providers reales** — ShazamIO (`shazamio` async), AudD (HTTP API con audio base64), AcoustID (`fpcalc` + Chromaprint fingerprint)
- 🎙️ **AudioCaptureService** — PyAudio, 22050Hz mono S16LE, captura continua cada 15s, auto-detección de monitor source
- 🔍 **Matching 4-tier** — Exacto title+artist → title+album → fuzzy title ≥0.85 → fuzzy artist+title. Skip automático para fuentes locales
- 📜 **Historial persistente** — DetectionHistoryRepository con SQLite, dedup 24h, filtro por fuente (radio/stream/manual)

### UI & Sistema
- 🪟 **Glassmorphism oscuro unificado** — 14+ vistas con gradiente glass `rgba(20,22,28,0.94)→rgba(8,10,16,0.94)`, style_tokens.py + qss.py centralizados
- 🎨 **Sidebar premium** — Gradiente dark con glow azul, branding mini-card, buscador, headers UPPERCASE con chevrons, scrollbar 3px
- 🎯 **Sistema de iconos** — 38+ iconos SVG nativos, IconSpec dataclass con `render_mode` (native_color/symbolic_tint), render 2x scale-down
- ⌨️ **Atajos de teclado** — Ctrl+O/D/P/Q, atajos globales, multimedia keys
- 🔌 **MPRIS** — Integración DBus con KDE Plasma (play/pause/stop/seek/metadata)
- 📱 **Sincronización Android** — API REST + UDP multicast discovery

### Arquitectura
- 🏛️ **AppContext DI** — Inyección de dependencias centralizada, 0 accesos directos a window desde controladores
- 🧩 **14 controladores** — Transmit, AudioOutput, Snapcast, HomeAudio, Cast, LocalMediaServer, MiniPlayer, PlayerBar, Playlist, Artist, Album, Expanded, MPRIS, Tray
- 🔒 **Encapsulación** — PlayerService como facade único al engine, wrappers públicos para todos los métodos, 0 accesos a atributos privados
- 🧹 **Código activo** — módulos cableados a flujos reales, servicios opcionales con degradación segura

## Instalación

### Arch Linux / CachyOS / Manjaro
```bash
git clone https://github.com/pitydah/michi-music-player.git
cd michi-music-player
./scripts/install_arch.sh
source .venv/bin/activate
michi-music-player
```

### Ubuntu / Debian / Linux Mint
```bash
git clone https://github.com/pitydah/michi-music-player.git
cd michi-music-player
./scripts/install_debian_ubuntu.sh
source .venv/bin/activate
michi-music-player
```

### Fedora
```bash
git clone https://github.com/pitydah/michi-music-player.git
cd michi-music-player
./scripts/install_fedora.sh
source .venv/bin/activate
michi-music-player
```

### openSUSE (Tumbleweed / Leap)
```bash
git clone https://github.com/pitydah/michi-music-player.git
cd michi-music-player
./scripts/install_opensuse.sh
source .venv/bin/activate
michi-music-player
```

### Ejecutar desde fuente (sin instalar al sistema)
```bash
git clone https://github.com/pitydah/michi-music-player.git
cd michi-music-player
./scripts/run_from_source.sh
```

### Activar entorno virtual
```bash
# Bash / Zsh:
source .venv/bin/activate

# Fish:
source .venv/bin/activate.fish
```

### Diagnóstico de dependencias
```bash
python3 scripts/check_runtime.py
```

### Dependencias por funcionalidad

| Funcionalidad | Dependencia | Crítica |
|--------------|-------------|---------|
| Reproducción | GStreamer + plugins base/good/bad/ugly | ✅ |
| UI | PySide6 / Qt6 | ✅ |
| Metadatos | mutagen, numpy | ✅ |
| MPRIS / KDE | dbus-python | Opcional |
| Identificación | shazamio, pyaudio, fpcalc | Opcional |
| Multiroom | snapcast (snapserver + snapclient) | Opcional |
| Home Assistant | (solo red, sin deps extra) | Opcional |
| mDNS / descubrimiento | avahi-utils | Opcional |
| Letras sincronizadas | (solo red, LRCLIB API) | Opcional |

### Problemas comunes

**Error: `from gi.repository import Gst`**
```bash
# Ubuntu/Debian:
sudo apt install python3-gi gir1.2-gstreamer-1.0

# Arch:
sudo pacman -S python-gobject

# Fedora:
sudo dnf install python3-gobject
```

**Error: `No module named 'PySide6'`**
```bash
pip install PySide6
# O usa --system-site-packages al crear el venv
```

**Error: dbus / MPRIS**
```bash
# Ubuntu/Debian:
sudo apt install python3-dbus

# Arch:
sudo pacman -S python-dbus

# Instalar dbus-python por pip puede fallar — preferir paquete del sistema
```

**Fish shell: activar venv**
```fish
source .venv/bin/activate.fish
```

## Instalación desde fuente

```bash
git clone https://github.com/pitydah/michi-music-player
cd michi-music-player
pip install .
michi-music-player
```

| Atajo | Acción |
|-------|--------|
| `Ctrl+O` | Abrir archivo |
| `Ctrl+D` | Añadir carpeta |
| `Ctrl+P` | Preferencias |
| `Ctrl+Q` | Salir |
| `Media Play/Pause` | Reproducir / Pausar |
| `Media Next/Prev` | Siguiente / Anterior |
| `Ctrl+↑/↓` | Volumen +5/-5 |

## Estructura del proyecto

```
michi-music-player/
├── main.py                          # Entry point
├── LICENSE                           # GPL-3.0-or-later
├── NOTICE                            # Miro Player origin credit
├── pyproject.toml                    # Package config
├── requirements.txt                  # Pip dependencies
├── install_arch.sh / install_ubuntu.sh
├── data/michi-music-player.desktop
│
├── audio/                            # Motor de audio (24 archivos)
│   ├── player.py                     # GStreamerEngine — playback central
│   ├── player_service.py             # Facade público entre UI y engine
│   ├── pipeline_factory.py           # Construcción de pipelines por perfil
│   ├── dac_manager.py                # Enrutamiento DAC, detección dispositivos
│   ├── output_profiles.py            # 9 perfiles de audio
│   ├── output_device_manager.py      # Detección ALSA hw/PipeWire/PulseAudio
│   ├── audio_route_plan.py           # AudioRoutePlan dataclass
│   ├── dsp_state.py                  # DspState — estado de procesamiento digital
│   ├── audio_chain.py                # DacConfig + get_quality_label + EQ paramétrico
│   ├── audio_diagnostics.py          # AudioRouteDiagnostics → tooltip
│   ├── audio_capabilities.py         # check_dac_capability, check_bitperfect_possible
│   ├── format_probe.py               # probe_format — detección DSD/DSF/DFF/PCM
│   ├── replaygain.py                 # ReplayGainConfig + apply_full + compute_safe_gain
│   ├── quality_classifier.py         # classify_audio_quality — 6 categorías
│   ├── dsd_controller.py             # DsdController — appsrc backpressure
│   ├── dff_parser.py                 # DFF/DSD header parser
│   ├── eq_biquad.py                  # Cálculo de coeficientes biquad
│   ├── eq_basic.py / eq_advanced.py  # Widgets EQ gráfico/paramétrico
│   ├── eq_curve.py / eq_presets.py   # Curva de respuesta + presets
│   ├── eq_autoeq.py                  # AutoEQ integration
│   ├── eq_convert.py                 # Conversión gráfico ↔ paramétrico
│   └── spectrum.py                   # Spectrum analyzer
│
├── library/                          # Biblioteca + indexer (17 archivos)
│   ├── library_db.py                 # SQLite schema, migraciones, CRUD, search_advanced
│   ├── indexer.py                    # Indexer 2.0 — pipeline de indexación
│   ├── index_state.py                # ScanState dataclass + ScanPhase enum
│   ├── batch_writer.py               # BatchWriter — escritura SQLite en lotes
│   ├── search_engine.py              # SearchEngine — FTS5 + field filters
│   ├── search_index.py               # SearchIndex — FTS5 virtual table management
│   ├── query_parser.py               # parse_query — artist:, album:, year:> etc.
│   ├── media_item.py                 # MediaItem dataclass + from_row/from_dict
│   ├── metadata_extractor.py         # GStreamer + Mutagen metadata extraction
│   ├── metadata_normalizer.py        # Normalización de tags
│   ├── album_key.py                  # make_album_key / make_artist_key SHA1
│   ├── artist_grouping.py            # Agrupación de artistas
│   ├── coverflow.py                  # CoverFlow 3D (1096 líneas)
│   ├── cover_art_service.py          # Servicio de carátulas
│   ├── album_grid.py                 # Grid de álbumes
│   ├── album_art_worker.py           # Worker de extracción de carátulas
│   └── tag_editor.py                 # Editor de tags Mutagen
│
├── recognition/                      # Identificación de música (10 archivos)
│   ├── detection_service.py          # Orquestador — captura + identificación continua
│   ├── identifier_controller.py      # Source-aware: radio/stream sí, local no
│   ├── audio_capture_service.py      # PyAudio — captura 22050Hz mono
│   ├── detection_history_repository.py  # CRUD historial SQLite
│   ├── recognition_matcher.py        # Matching 4-tier con fuzzy
│   ├── deduplication.py              # Dedup por ventana de tiempo
│   ├── models.py                     # DetectedTrack dataclass
│   ├── provider_manager.py           # Selección y configuración de providers
│   ├── base_recognizer.py            # BaseRecognizer abstracto
│   ├── null_recognizer.py            # Fallback Null Object
│   └── providers/                    # Implementaciones reales
│       ├── shazam.py                 # ShazamProvider — shazamio async
│       ├── audd.py                   # AudDProvider — HTTP API + audio base64
│       └── acoustid.py               # AcoustIDProvider — fpcalc + fingerprint
│
├── integrations/                     # Integraciones externas
│   ├── home_assistant/               # Home Assistant
│   │   ├── client.py                 # REST vía QNetworkAccessManager
│   │   ├── local_media_server.py     # Servidor HTTP archivos locales → HA
│   │   └── models.py                 # HomeAssistantConfig, CastRequest, etc.
│   ├── snapcast/                     # Snapcast multiroom
│   │   ├── snapserver_manager.py     # QProcess lifecycle
│   │   ├── audio_capture.py          # pactl null-sink
│   │   ├── discovery.py              # avahi-browse — Snapclient discovery
│   │   ├── group_manager.py          # Zonas CRUD en QSettings
│   │   └── receivers.py              # ReceiverWizard (RPi/ESP32/Docker)
│   ├── http_api/                   # Michi HTTP API
│   │   ├── http_api.py               # REST server (puerto 8124)
│   │   └── mdns_advertiser.py        # avahi-publish-service
│   ├── artist_metadata/              # Enriquecimiento de metadatos externos
│   │   ├── client.py                 # API client
│   │   ├── models.py                 # ArtistExternalInfo (20 campos)
│   │   ├── cache.py                  # SQLite cache + imágenes locales
│   │   ├── artist_enrichment_service.py  # Servicio de enriquecimiento de artistas
│   │   ├── album_enrichment_service.py   # Servicio de enriquecimiento de álbumes
│   │   └── album_cache.py            # Cache de metadatos de álbum
│   └── home_assistant_custom_component/  # Componente HA personalizado
│       ├── manifest.json / config_flow.py / media_player.py / media_source.py / api.py
│
├── ui/                               # Interfaz de usuario (35+ archivos)
│   ├── window.py                     # MainWindow (2825 líneas)
│   ├── nowplaying_bar.py             # Barra de reproducción inferior
│   ├── sidebar_widget.py             # Sidebar colapsable
│   ├── album_info_banner.py          # Banner de info de álbum
│   ├── source_status_badge.py        # Badge de calidad/formato
│   ├── home_audio_view.py            # Dashboard Home Audio
│   ├── music_identifier_view.py      # Dashboard identificación
│   ├── mini_player.py                # Reproductor compacto
│   ├── style_tokens.py               # COLORS/RADIUS/SPACING
│   ├── qss.py                        # Helpers QSS (glass_panel, premium_button, etc.)
│   ├── premium_menus.py              # Estilos de menú premium
│   ├── icon_registry.py              # Registro de 38+ iconos
│   ├── theme.py                      # QPalette + QSS
│   ├── eq_panel.py                   # Diálogo de ecualizador
│   ├── preferences_window.py         # 16 categorías de preferencias
│   ├── settings_pages.py             # Páginas de settings (AudioPage, etc.)
│   ├── controllers/                  # Controladores (14)
│   │   ├── transmit_controller.py    # Dispositivos TransmitManager
│   │   ├── audio_output_controller.py  # Selección de salida de audio local
│   │   ├── snapcast_controller.py    # Ciclo de vida Snapcast
│   │   ├── home_audio_controller.py  # Cast a Home Assistant
│   │   ├── cast_controller.py        # Menú de transmisión unificado
│   │   ├── local_media_server_controller.py  # Servidor HTTP local
│   │   ├── mini_player_controller.py  # Ciclo de vida mini player
│   │   ├── player_bar_controller.py  # NowPlayingBar facade
│   │   ├── playlist_controller.py    # Operaciones de playlists
│   │   ├── album_controller.py       # Operaciones de álbumes
│   │   ├── artist_repository.py      # Repositorio centralizado de artistas
│   │   ├── expanded_controller.py    # Vista expandida
│   │   ├── mpris_controller.py       # MPRIS facade
│   │   └── tray_controller.py        # System tray
│   └── ...
│
├── tests/                            # Tests (180 en 25 archivos)
│   ├── test_replaygain.py (14) / test_search_engine.py (7)
│   ├── test_search_index.py (5) / test_indexer.py (10)
│   ├── test_dac_manager.py (6) / test_pipeline_factory.py (6)
│   ├── test_player_service.py (7) / test_dsp_state.py (8)
│   ├── test_quality_classifier.py (16) / test_playlist_controller.py (6)
│   ├── test_icon_registry.py (7) / test_cover_art_service.py
│   └── ... (15 más)
│
├── core/                             # Infraestructura
│   ├── settings_manager.py           # QSettings wrapper
│   ├── interfaces.py                 # IPlaybackController, IViewController
│   ├── app_context.py                # AppContext DI container
│   ├── playback_controller.py        # Control de reproducción + EQ
│   └── file_actions.py               # Open, scan, drop, folder import
│
├── streaming/                        # Streaming & radio
│   ├── subsonic_client.py / remote_browser.py / server_dialog.py
│   ├── radio_manager.py / radio_widget.py / radio_dialog.py
│   └── transmit_manager.py           # Gestión de dispositivos de transmisión
│
├── sources/                          # Fuentes de música
│   ├── base_source.py                # MusicSource abstracto + TrackRef
│   ├── local_source.py               # LocalSource — FTS5 + SearchEngine
│   ├── radio_source.py               # RadioSource
│   └── subsonic_source.py            # SubsonicSource
│
├── sync/                             # Sincronización Android
│   ├── sync_server.py / sync_protocol.py
│   ├── sync_discovery.py / sync_manager.py
│
├── adapters/                         # Integraciones de sistema
│   └── mpris.py                      # MPRIS DBus adapter
│
├── metadata/                         # Metadatos extendidos
│   ├── album_summary.py              # AlbumSummary NamedTuple
│   ├── album_info_repository.py      # LRU cache 200 + fallback SQLite
│   └── tag_actions.py               # search_replace
│
├── lyrics/                           # Letras
│   └── lrclib_client.py             # LRCLIB API client
│
├── docs/                             # Documentación
│   ├── architecture.md
│   └── roadmap.md
│
└── icons/                            # Iconos SVG + PNG
    └── actions/                      # 38+ iconos
```

## Tecnologías

- **Python 3.11+**
- **PySide6** (Qt 6 — bindings oficiales)
- **GStreamer 1.0** (motor de audio — playbin, decodebin, audioiirfilter, equalizer-nbands, rgvolume, spectrum)
- **SQLite 3** + **FTS5** (full-text search, WAL mode, content= sync)
- **mutagen** (extracción de metadatos: ID3, Vorbis, MP4, MusicBrainz, ReplayGain, BPM, cover art)
- **shazamio** (reconocimiento de música — Shazam API)
- **PyAudio** (captura de audio del sistema — PortAudio bindings)
- **fpcalc** (Chromaprint — huella acústica para AcoustID)
- **dbus-python** (MPRIS — integración KDE Plasma)
- **avahi** (mDNS — descubrimiento de servicios)
- **pactl** (PulseAudio/PipeWire — null-sink para Snapcast)
- **numpy** (procesamiento de señales — EQ, spectrum)

## Estado de funcionalidades

| Funcionalidad | Estado |
|--------------|--------|
| Reproducción local (MP3, FLAC, OGG, Opus, WAV, DSD, AIFF, APE, WV) | ✅ Completo |
| 9 perfiles de audio (Standard → Multiroom) | ✅ Completo |
| PipelineFactory + AudioRoutePlan + DspState | ✅ Completo |
| EQ gráfico 31-bandas + paramétrico biquads reales | ✅ Completo |
| ReplayGain avanzado (track/album/auto + preamp/headroom/anti-clip) | ✅ Completo |
| Biblioteca SQLite + metadatos avanzados (MusicBrainz, BPM, RG, bit_depth) | ✅ Completo |
| Indexer 2.0 incremental + batch writing | ✅ Completo |
| Search 2.0 FTS5 + field filters (`artist:`, `year:>`, `format:`) | ✅ Completo |
| Cover Flow visual (implementación independiente) | ✅ Completo |
| AlbumInfoBanner + enriquecimiento externo | ✅ Completo |
| Artistas (grid premium + ficha detalle + MusicBrainz + Wikipedia) | ✅ Completo |
| Home Audio multiroom (HA + Snapcast + Michi API + mDNS) | ✅ Completo |
| Transmit desacoplado (7 controladores) | ✅ Completo |
| Recognition real (ShazamIO + AudD HTTP API + AcoustID fpcalc) | ✅ Completo |
| AudioCaptureService continuo (PyAudio 22050Hz, loop 15s) | ✅ Completo |
| Quality badge (6 categorías + tooltip + diálogo diagnóstico) | ✅ Completo |
| UI glassmorphism unificada (14+ vistas) | ✅ Completo |
| Sistema de iconos centralizado (38+ iconos, IconSpec) | ✅ Completo |
| Playlist Hub (crear, M3U import/export, crear desde carpeta/cola/artista) | ✅ Completo |
| PlayerService wrappers públicos (7 métodos) · 0 accesos privados | ✅ Completo |
| AppContext DI · 0 accesos directos a window desde controladores | ✅ Completo |
| MPRIS DBus (KDE Plasma) | ✅ Completo |
| Subsonic / Navidrome / Jellyfin | ✅ Completo |
| Radio por Internet (HTTP/ICY) | ✅ Completo |
| Sincronización Android (REST API + UDP discovery) | ✅ Completo |
| DSD/DFF nativo (PCM + DoP experimental vía `MICHI_DOP_EXPERIMENTAL=1`) | ✅ Completo |
| Gapless playback + crossfade | ✅ Completo |
| Mini Player (ventana compacta independiente) | ✅ Completo |
| Fondo adaptativo (gradiente basado en carátula) | ✅ Completo |
| Tag editor (Mutagen ID3/Vorbis/MP4) | ✅ Completo |
| Persistencia de cola entre sesiones | ✅ Completo |
| Flatpak packaging | ✅ Completo |
| Receiver Wizard (Raspberry Pi / ESP32 / Docker Snapclient) | ✅ Completo |

## Métricas

| Métrica | Valor |
|---------|-------|
| Tests | **206** en 25 archivos |
| Archivos `.py` | **171** |
| Ruff | **0** |
| Bugs (F-class) | **0** |
| Stubs | **0** |
| Código muerto | **0** (~320 líneas eliminadas) |
| Perfiles de audio | **9** |
| Controladores | **14** |
| Providers recognition | **3 reales** (ShazamIO, AudD, AcoustID) |
| Vistas con glassmorphism | **14+** |
| Iconos registrados | **38+** |
| Commits recientes | **9** (consolidación completa) |

## Instalación desde fuente

```bash
git clone https://github.com/pitydah/michi-music-player
cd michi-music-player
pip install .
michi-music-player
```

### Flatpak

```bash
flatpak-builder --user --install build-dir data/com.michi.MusicPlayer.yml
flatpak run com.michi.MusicPlayer
```

## Licencia

GPL-3.0-or-later

Ver `NOTICE` y `docs/THIRD_PARTY.md` para declaraciones legales completas, inspiraciones de terceros, dependencias, marcas comerciales y compatibilidad con servicios externos.

---

## Third-party notices, inspirations, and trademarks

Michi Music Player es un reproductor de música independiente para Linux/KDE. No está afiliado, respaldado, patrocinado ni aprobado por ningún proyecto, compañía, fundación, servicio o titular de marca mencionado en este repositorio.

Algunas funciones fueron concebidas a partir de flujos de trabajo comunes en software musical: bibliotecas musicales locales, editores de metadatos, taggers, navegación visual de álbumes, listas inteligentes, búsqueda de metadatos externos, audio multiroom y sincronización local entre dispositivos.

Herramientas open source de metadatos como MusicBrainz Picard, beets, Kid3, puddletag, EasyTAG, Quod Libet, Clementine, Strawberry Music Player, MusicBrainz, AcoustID, Chromaprint y Mutagen se mencionan solo como referencias conceptuales, de flujo de trabajo, de compatibilidad o de dependencia, salvo que un aviso a nivel de archivo indique lo contrario.

Michi Music Player no incluye intencionalmente logos, iconos, screenshots, assets visuales, assets propietarios, bases de datos ni código fuente de esos proyectos, salvo que un aviso específico a nivel de archivo lo indique.

Ver `NOTICE` y `docs/THIRD_PARTY.md` para las declaraciones completas de atribución, inspiración, dependencias, compatibilidad y marcas comerciales.
