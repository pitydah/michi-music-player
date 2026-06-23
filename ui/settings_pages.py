"""Settings Pages — all 16 preference categories for Michi Music Player."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFileDialog, QMessageBox,
)

from ui.settings_widgets import (
    SettingsCard, SettingsRow, SettingsSwitch, SettingsCombo,
    SettingsSlider, SettingsActionButton, SettingsPathPicker, SettingsPageHeader,
)
import core.settings_manager as sm

_BG = "#090B11"
_TEXT = "#FFFFFF"
_TEXT2 = "rgba(255,255,255,0.78)"
_TEXT3 = "rgba(255,255,255,0.62)"


def _make_scroll(page: QWidget) -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.NoFrame)
    scroll.setWidget(page)
    scroll.setStyleSheet(f"QScrollArea {{ background: {_BG}; border: none; }} "
                         f"QScrollArea QWidget {{ background: {_BG}; }}"
                         "QScrollBar:vertical { background: rgba(255,255,255,0.02); width: 8px; margin: 2px; border-radius: 4px; }"
                         "QScrollBar::handle:vertical { background: rgba(255,255,255,0.14); min-height: 30px; border-radius: 4px; }"
                         "QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.22); }"
                         "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")
    return scroll


class _Page(QWidget):
    """Base page with header, scroll, and card layout."""

    def __init__(self, title: str, subtitle: str = "", icon: str = ""):
        super().__init__()
        self.setStyleSheet(f"background: {_BG};")
        self._title = title
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(24, 16, 24, 24)
        self._layout.setSpacing(14)
        self._layout.addWidget(SettingsPageHeader(title, subtitle, icon))

    def add_card(self, card: SettingsCard):
        self._layout.addWidget(card)

    def add_stretch(self):
        self._layout.addStretch()

    def apply(self):
        pass


# ═══════════════════════════════════════════
# 1. General
# ═══════════════════════════════════════════

class GeneralPage(_Page):
    def __init__(self):
        super().__init__("General", "Comportamiento básico de Michi", "sidebar_library")

        card = SettingsCard("Inicio")
        self._tray = SettingsSwitch(sm.get("general/start_minimized"))
        self._remember = SettingsSwitch(sm.get("general/remember_session"))
        self._confirm_exit = SettingsSwitch(sm.get("general/confirm_exit"))
        self._close_action = SettingsCombo(
            ["Cerrar aplicación", "Minimizar a bandeja", "Preguntar siempre"],
            "Cerrar aplicación")
        card.add_row(SettingsRow("Iniciar minimizado", "Abre Michi en la bandeja del sistema", self._tray))
        card.add_row(SettingsRow("Recordar sesión", "Restaura la última vista y cola al abrir", self._remember))
        card.add_row(SettingsRow("Confirmar salida", "Pregunta antes de cerrar", self._confirm_exit))
        card.add_row(SettingsRow("Al cerrar ventana", "Qué hacer cuando se cierra la ventana principal", self._close_action))
        self.add_card(card)

        card2 = SettingsCard("Carpetas")
        self._music_folder = SettingsPathPicker(sm.get("general/music_folder"))
        self._downloads = SettingsPathPicker(sm.get("general/download_folder"))
        config_btn = SettingsActionButton("Abrir carpeta de configuración")
        config_btn.clicked.connect(lambda: _open_path("~/.config/Michi"))
        card2.add_row(SettingsRow("Carpeta de música", "Directorio principal de tu biblioteca", self._music_folder))
        card2.add_row(SettingsRow("Carpeta de descargas", "Donde se guardan descargas y streams", self._downloads))
        card2.add_row(SettingsRow("Configuración", "Archivos de configuración y caché", config_btn))
        self.add_card(card2)

        card3 = SettingsCard("Integración Linux/KDE")
        self._tray_icon = SettingsSwitch(True)
        self._notify = SettingsSwitch(True)
        self._mpris = SettingsSwitch(True)
        self._remember_geom = SettingsSwitch(True)
        card3.add_row(SettingsRow("Icono en bandeja", "Mantener Michi accesible desde la bandeja", self._tray_icon))
        card3.add_row(SettingsRow("Notificaciones del sistema", "Alertas de cambio de canción", self._notify))
        card3.add_row(SettingsRow("Integración MPRIS", "Control multimedia del escritorio", self._mpris))
        card3.add_row(SettingsRow("Recordar tamaño y posición", "Restaura la geometría al abrir", self._remember_geom))
        self.add_card(card3)
        self.add_stretch()

        self._controls = [self._tray, self._remember, self._confirm_exit, self._close_action,
                          self._music_folder, self._downloads,
                          self._tray_icon, self._notify, self._mpris, self._remember_geom]

    def apply(self):
        sm.set_("general/start_minimized", self._tray.isChecked())
        sm.set_("general/remember_session", self._remember.isChecked())
        sm.set_("general/confirm_exit", self._confirm_exit.isChecked())
        sm.set_("general/music_folder", self._music_folder.text())
        sm.set_("general/download_folder", self._downloads.text())


# ═══════════════════════════════════════════
# 2. Apariencia
# ═══════════════════════════════════════════

class AppearancePage(_Page):
    def __init__(self):
        super().__init__("Apariencia", "Tema, colores y disposición visual", "sidebar_albums")

        card = SettingsCard("Tema")
        self._theme = SettingsCombo(
            ["Oscuro Glass", "Oscuro Alto Contraste", "Claro", "Sistema"], "Oscuro Glass")
        self._accent = SettingsCombo(
            ["Blanco glass", "Azul", "Morado", "Naranja clásico"], "Blanco glass")
        self._glass_intensity = SettingsCombo(["Baja", "Media", "Alta"], "Media")
        card.add_row(SettingsRow("Tema", "Esquema de color general", self._theme))
        card.add_row(SettingsRow("Acento", "Color de elementos interactivos", self._accent))
        card.add_row(SettingsRow("Intensidad glass", "Opacidad del efecto vidrio", self._glass_intensity))
        self.add_card(card)

        card2 = SettingsCard("Layout")
        self._menubar = SettingsSwitch(sm.get("interface/show_menubar"))
        self._compact = SettingsSwitch(sm.get("interface/compact_mode"))
        self._badge = SettingsSwitch(sm.get("interface/show_quality_badge"))
        card2.add_row(SettingsRow("Mostrar barra de menú", "Barra superior clásica", self._menubar))
        card2.add_row(SettingsRow("Modo compacto", "Reduce espacios y márgenes", self._compact))
        card2.add_row(SettingsRow("Badge de calidad", "Indicador de formato en NowPlaying", self._badge))
        self.add_card(card2)

        card3 = SettingsCard("Carátulas")
        self._cover_size = SettingsSlider(120, 400, sm.get("interface/cover_size"), " px")
        self._rounded = SettingsSwitch(True)
        card3.add_row(SettingsRow("Tamaño de carátula", "En mosaicos y vistas", self._cover_size))
        card3.add_row(SettingsRow("Esquinas redondeadas", "Bordes suaves en portadas", self._rounded))
        self.add_card(card3)

        card4 = SettingsCard("Animaciones")
        self._animations = SettingsSwitch(True)
        self._anim_speed = SettingsCombo(["Rápido (100ms)", "Normal (200ms)", "Lento (400ms)"], "Normal (200ms)")
        card4.add_row(SettingsRow("Activar animaciones", "Transiciones entre vistas", self._animations))
        card4.add_row(SettingsRow("Velocidad", "Duración de las transiciones", self._anim_speed))
        self.add_card(card4)
        self.add_stretch()

    def apply(self):
        sm.set_("interface/show_menubar", self._menubar.isChecked())
        sm.set_("interface/compact_mode", self._compact.isChecked())
        sm.set_("interface/show_quality_badge", self._badge.isChecked())
        sm.set_("interface/cover_size", self._cover_size.value())


# ═══════════════════════════════════════════
# 3. Biblioteca
# ═══════════════════════════════════════════

class LibraryPage(_Page):
    def __init__(self):
        super().__init__("Biblioteca", "Escaneo, formatos y mantenimiento", "sidebar_library")

        card = SettingsCard("Escaneo")
        self._auto = SettingsSwitch(sm.get("library/auto_scan"))
        self._hidden = SettingsSwitch(sm.get("library/exclude_hidden"))
        self._symlinks = SettingsSwitch(False)
        self._interval = SettingsCombo(["1 min", "5 min", "15 min", "30 min", "1 h"], "5 min")
        card.add_row(SettingsRow("Escanear al iniciar", "Buscar archivos nuevos automáticamente", self._auto))
        card.add_row(SettingsRow("Excluir carpetas ocultas", "Ignorar directorios con punto", self._hidden))
        card.add_row(SettingsRow("Seguir enlaces simbólicos", "Incluir accesos directos", self._symlinks))
        card.add_row(SettingsRow("Intervalo de escaneo", "Frecuencia de autoescaneo", self._interval))
        self.add_card(card)

        card2 = SettingsCard("Carátulas y caché")
        self._cache = SettingsSlider(50, 500, sm.get("library/covers_cache_size"), " MB")
        self._clean = SettingsActionButton("Limpiar archivos huérfanos")
        self._rescan = SettingsActionButton("Reescanear carátulas")
        card2.add_row(SettingsRow("Caché de carátulas", "Tamaño máximo en disco", self._cache))
        card2.add_row(SettingsRow("", "Elimina referencias a archivos inexistentes", self._clean))
        card2.add_row(SettingsRow("", "Busca y actualiza todas las carátulas", self._rescan))
        self.add_card(card2)

        card3 = SettingsCard("Mantenimiento")
        self._rebuild_btn = SettingsActionButton("Reconstruir base de datos")
        self._export_btn = SettingsActionButton("Exportar biblioteca")
        self._import_btn = SettingsActionButton("Importar biblioteca")
        card3.add_row(SettingsRow("Reconstruir BD", "Regenera la base de datos desde cero", self._rebuild_btn))
        card3.add_row(SettingsRow("Exportar", "Guarda la biblioteca como JSON", self._export_btn))
        card3.add_row(SettingsRow("Importar", "Carga una biblioteca exportada", self._import_btn))
        self.add_card(card3)
        self.add_stretch()

    def apply(self):
        sm.set_("library/auto_scan", self._auto.isChecked())
        sm.set_("library/exclude_hidden", self._hidden.isChecked())
        sm.set_("library/covers_cache_size", self._cache.value())


# ═══════════════════════════════════════════
# 4. Reproducción
# ═══════════════════════════════════════════

class PlaybackPage(_Page):
    def __init__(self):
        super().__init__("Reproducción", "Control de reproducción, cola y transiciones", "warm_play")

        card = SettingsCard("Comportamiento")
        self._vol = SettingsSlider(0, 100, sm.get("playback/default_volume"), "%")
        self._repeat = SettingsCombo(["none", "all", "one"], sm.get("playback/repeat_mode"))
        self._shuffle = SettingsSwitch(sm.get("playback/shuffle_default"))
        self._resume = SettingsSwitch(True)
        card.add_row(SettingsRow("Volumen inicial", "Nivel al abrir la aplicación", self._vol))
        card.add_row(SettingsRow("Repetición inicial", "Modo de repetición por defecto", self._repeat))
        card.add_row(SettingsRow("Aleatorio inicial", "Activar al iniciar", self._shuffle))
        card.add_row(SettingsRow("Continuar donde quedó", "Reanudar la última canción", self._resume))
        self.add_card(card)

        card2 = SettingsCard("Transiciones")
        self._gapless = SettingsSwitch(sm.get("playback/gapless"))
        self._crossfade = SettingsSlider(0, 12, sm.get("playback/crossfade"), " s")
        card2.add_row(SettingsRow("Gapless", "Sin silencio entre canciones", self._gapless))
        card2.add_row(SettingsRow("Crossfade", "Fundido entre canciones", self._crossfade))
        self.add_card(card2)

        card3 = SettingsCard("ReplayGain")
        self._rg = SettingsSwitch(sm.get("playback/replaygain"))
        self._rg_mode = SettingsCombo(["Track", "Album", "Auto"], "Track")
        self._rg_preamp = SettingsSlider(-12, 12, 0, " dB")
        card3.add_row(SettingsRow("ReplayGain", "Normalización de volumen", self._rg))
        card3.add_row(SettingsRow("Modo", "Track por pista, Album por disco", self._rg_mode))
        card3.add_row(SettingsRow("Pre‑amp", "Ajuste adicional de ganancia", self._rg_preamp))
        self.add_card(card3)
        self.add_stretch()

    def apply(self):
        sm.set_("playback/default_volume", self._vol.value())
        sm.set_("playback/repeat_mode", self._repeat.currentText())
        sm.set_("playback/shuffle_default", self._shuffle.isChecked())
        sm.set_("playback/replaygain", self._rg.isChecked())
        sm.set_("playback/crossfade", self._crossfade.value())
        sm.set_("playback/gapless", self._gapless.isChecked())


# ═══════════════════════════════════════════
# 5. Audio / DAC
# ═══════════════════════════════════════════

class AudioPage(_Page):
    def __init__(self):
        super().__init__("Audio / DAC", "Salida, calidad y modo de reproducción", "warm_eq")

        card = SettingsCard("Perfil")
        self._profile = SettingsCombo(
            ["standard", "hifi_pcm", "bitperfect_pcm",
             "dsd_to_pcm", "dop_experimental",
             "pure_audio", "studio_monitor"],
            sm.get("audio/profile"))
        self._backend = SettingsCombo(
            ["auto", "pipewire", "pulseaudio", "alsa", "jack"],
            sm.get("audio/device_backend"))
        card.add_row(SettingsRow("Perfil de audio", "Standard, Hi-Fi, Bit-Perfect, DSD",
                                  self._profile))
        card.add_row(SettingsRow("Backend", "Motor de salida de audio",
                                  self._backend))
        self.add_card(card)

        card_dev = SettingsCard("Dispositivo")
        self._dev = SettingsCombo(
            self._list_real_devices(), sm.get("audio/output_device_id") or "auto")
        detect_btn = SettingsActionButton("Actualizar dispositivos")
        detect_btn.clicked.connect(self._refresh_devices)
        test_btn = SettingsActionButton("Probar DAC")
        card_dev.add_row(SettingsRow("Dispositivo", "Salida de audio detectada",
                                      self._dev))
        card_dev.add_row(SettingsRow("", "Buscar dispositivos conectados", detect_btn))
        card_dev.add_row(SettingsRow("", "Probar dispositivo seleccionado", test_btn))
        self._detect_btn = detect_btn
        self._test_btn = test_btn
        self.add_card(card_dev)

        card_dsd = SettingsCard("DSD")
        self._dsd_mode = SettingsCombo(
            ["pcm", "dop_experimental"],
            sm.get("audio/dsd_mode"))
        self._dsd_rate = SettingsCombo(
            ["auto", "176400", "352800"],
            str(sm.get("audio/dsd_pcm_rate") or "auto"))
        card_dsd.add_row(SettingsRow("Modo DSD", "DSD to PCM o DoP",
                                      self._dsd_mode))
        card_dsd.add_row(SettingsRow("Rate DSD→PCM", "Sample rate para conversion",
                                      self._dsd_rate))
        self.add_card(card_dsd)

        card_q = SettingsCard("Calidad y buffer")
        self._rate = SettingsCombo(
            ["0 (auto)", "44100", "48000", "88200", "96000", "176400", "192000"],
            str(sm.get("audio/sample_rate")))
        self._buf = SettingsCombo(
            ["50", "100", "200", "500", "1000"], str(sm.get("audio/buffer_ms")))
        self._resample = SettingsSwitch(sm.get("audio/allow_resample"))
        self._fallback = SettingsSwitch(sm.get("audio/allow_fallback"))
        card_q.add_row(SettingsRow("Sample rate", "Frecuencia de muestreo", self._rate))
        card_q.add_row(SettingsRow("Buffer (ms)", "Latencia de reproducción", self._buf))
        card_q.add_row(SettingsRow("Permitir resample", "Convertir sample rate si es necesario",
                                    self._resample))
        card_q.add_row(SettingsRow("Fallback automatico", "Degradar perfil si falla",
                                    self._fallback))
        self.add_card(card_q)

        card_dsp = SettingsCard("DSP")
        self._gapless = SettingsSwitch(sm.get("audio/gapless_enabled"))
        self._rg = SettingsSwitch(sm.get("audio/replaygain_enabled"))
        self._rg_mode = SettingsCombo(
            ["track", "album"], sm.get("audio/replaygain_mode"))
        self._spectrum = SettingsSwitch(sm.get("audio/spectrum_enabled"))
        card_dsp.add_row(SettingsRow("Gapless", "Reproduccion sin pausas",
                                      self._gapless))
        card_dsp.add_row(SettingsRow("ReplayGain", "Normalizar volumen",
                                      self._rg))
        card_dsp.add_row(SettingsRow("Modo RG", "Track o Album",
                                      self._rg_mode))
        card_dsp.add_row(SettingsRow("Spectrum", "Visualizador de espectro",
                                      self._spectrum))
        self.add_card(card_dsp)
        self.add_stretch()

    def _list_real_devices(self) -> list:
        try:
            from audio.output_device_manager import list_devices
            return [d.id for d in list_devices()]
        except Exception:
            return ["auto", "pipewire", "pulseaudio", "alsa_default", "test"]

    def _refresh_devices(self):
        items = self._list_real_devices()
        self._dev.clear()
        self._dev.addItems(items)

    def apply(self):
        sm.set_("audio/profile", self._profile.currentText())
        sm.set_("audio/device_backend", self._backend.currentText())
        sm.set_("audio/output_device_id", self._dev.currentText())
        sm.set_("audio/sample_rate",
                int(self._rate.currentText().split()[0]))
        sm.set_("audio/buffer_ms", int(self._buf.currentText()))
        sm.set_("audio/allow_resample", self._resample.isChecked())
        sm.set_("audio/allow_fallback", self._fallback.isChecked())
        sm.set_("audio/dsd_mode", self._dsd_mode.currentText())
        rate = self._dsd_rate.currentText()
        sm.set_("audio/dsd_pcm_rate", int(rate) if rate.isdigit() else 0)
        sm.set_("audio/gapless_enabled", self._gapless.isChecked())
        sm.set_("audio/replaygain_enabled", self._rg.isChecked())
        sm.set_("audio/replaygain_mode", self._rg_mode.currentText())
        sm.set_("audio/spectrum_enabled", self._spectrum.isChecked())

        # Apply to running services
        try:
            from PySide6.QtWidgets import QApplication
            for w in QApplication.topLevelWidgets():
                if hasattr(w, '_ctx') and hasattr(w._ctx, 'playback'):
                    ps = w._ctx.playback
                    ps.set_gapless_enabled(self._gapless.isChecked())
                    ps.set_replaygain_mode(self._rg_mode.currentText())
                    ps.set_spectrum_enabled(self._spectrum.isChecked())
                    # Apply profile/output device (pipeline restart)
                    dev_id = self._dev.currentText()
                    if dev_id and dev_id != "auto":
                        ps.set_output_device_id(dev_id)
                    break
        except Exception:
            pass


# ═══════════════════════════════════════════
# 6. Ecualizador
# ═══════════════════════════════════════════

class EqualizerPage(_Page):
    def __init__(self):
        super().__init__("Ecualizador", "Ajuste de bandas, presets y espectro", "warm_eq")

        card = SettingsCard("General")
        self._enabled = SettingsSwitch(sm.get("eq/enabled"))
        self._eq_mode = SettingsCombo(["graphic", "parametric", "bypass"], sm.get("eq/mode"))
        self._preamp = SettingsSlider(-12, 12, int(sm.get("eq/preamp")), " dB")
        card.add_row(SettingsRow("EQ activo", "Activar ecualizador", self._enabled))
        card.add_row(SettingsRow("Modo", "Gráfico por bandas o paramétrico", self._eq_mode))
        card.add_row(SettingsRow("Pre‑amp (dB)", "Ganancia previa", self._preamp))
        self.add_card(card)

        card2 = SettingsCard("Presets")
        self._preset = SettingsCombo(
            ["Flat", "Rock", "Pop", "Jazz", "Classical", "Hip-Hop",
             "Electronic", "Bass Boost", "Treble Boost", "Loudness",
             "Night Mode", "Vocal"], sm.get("eq/preset"))
        self._spectrum = SettingsSwitch(sm.get("eq/show_spectrum"))
        card2.add_row(SettingsRow("Preset", "Configuración predefinida", self._preset))
        card2.add_row(SettingsRow("Mostrar espectro", "Visualización en tiempo real", self._spectrum))
        self.add_card(card2)

        card3 = SettingsCard("Avanzado")
        self._save_preset = SettingsActionButton("Guardar preset personalizado")
        self._import_preset = SettingsActionButton("Importar preset")
        self._reset_eq = SettingsActionButton("Reset EQ")
        card3.add_row(SettingsRow("Guardar preset", "", self._save_preset))
        card3.add_row(SettingsRow("Importar", "", self._import_preset))
        card3.add_row(SettingsRow("Reset EQ", "", self._reset_eq))
        self.add_card(card3)
        self.add_stretch()

    def apply(self):
        sm.set_("eq/enabled", self._enabled.isChecked())
        sm.set_("eq/mode", self._eq_mode.currentText())
        sm.set_("eq/preset", self._preset.currentText())
        sm.set_("eq/preamp", float(self._preamp.value()))
        sm.set_("eq/show_spectrum", self._spectrum.isChecked())

        try:
            from PySide6.QtWidgets import QApplication
            for w in QApplication.topLevelWidgets():
                if hasattr(w, '_ctx') and hasattr(w._ctx, 'playback'):
                    ps = w._ctx.playback
                    ps.set_eq_bypass(not self._enabled.isChecked())
                    ps.set_eq_preamp(float(self._preamp.value()))
                    ps.set_spectrum_enabled(self._spectrum.isChecked())
                    break
        except Exception:
            pass


# ═══════════════════════════════════════════
# 7. Metadatos
# ═══════════════════════════════════════════

class MetadataPage(_Page):
    def __init__(self):
        super().__init__("Metadatos", "Editor de tags, carátulas e identificación", "metadata_editor")

        card = SettingsCard("Editor")
        self._confirm_save = SettingsSwitch(True)
        self._backup = SettingsSwitch(True)
        self._warn_empty = SettingsSwitch(True)
        card.add_row(SettingsRow("Confirmar antes de guardar", "Diálogo de resumen", self._confirm_save))
        card.add_row(SettingsRow("Crear backup", "Respalda el archivo original", self._backup))
        card.add_row(SettingsRow("Advertencias", "Alertar sobre campos vacíos", self._warn_empty))
        self.add_card(card)

        card2 = SettingsCard("Carátulas")
        self._art_size = SettingsCombo(
            ["Original", "300", "600", "1000", "1400"], "600")
        self._art_format = SettingsCombo(["JPG", "PNG", "Mantener original"], "JPG")
        self._art_crop = SettingsSwitch(True)
        self._art_quality = SettingsSlider(30, 100, 85, "")
        card2.add_row(SettingsRow("Tamaño por defecto", "Dimensión máxima al incrustar", self._art_size))
        card2.add_row(SettingsRow("Formato", "Tipo de imagen", self._art_format))
        card2.add_row(SettingsRow("Recortar a cuadrado", "Centrar y cortar", self._art_crop))
        card2.add_row(SettingsRow("Calidad JPG", "", self._art_quality))
        self.add_card(card2)

        card3 = SettingsCard("Limpieza")
        self._norm_spaces = SettingsSwitch(True)
        self._norm_genre = SettingsSwitch(False)
        self._detect_missing = SettingsSwitch(True)
        card3.add_row(SettingsRow("Normalizar espacios", "Auto‑limpiar al abrir", self._norm_spaces))
        card3.add_row(SettingsRow("Normalizar géneros", "Unificar nombres de género", self._norm_genre))
        card3.add_row(SettingsRow("Detectar campos vacíos", "Mostrar contadores en diagnóstico", self._detect_missing))
        self.add_card(card3)
        self.add_stretch()

    def apply(self):
        sm.set_("metadata/confirm_save", self._confirm_save.isChecked())
        sm.set_("metadata/create_backup", self._backup.isChecked())
        sm.set_("metadata/warn_empty", self._warn_empty.isChecked())
        sm.set_("metadata/art_size", self._art_size.currentText())
        sm.set_("metadata/art_format", self._art_format.currentText())
        sm.set_("metadata/art_crop", self._art_crop.isChecked())
        sm.set_("metadata/art_quality", self._art_quality.value())
        sm.set_("metadata/norm_spaces", self._norm_spaces.isChecked())
        sm.set_("metadata/norm_genre", self._norm_genre.isChecked())
        sm.set_("metadata/detect_missing", self._detect_missing.isChecked())


# ═══════════════════════════════════════════
# 8. Playlists
# ═══════════════════════════════════════════

class PlaylistPage(_Page):
    def __init__(self):
        super().__init__("Playlists", "Creación, importación y gestión", "sidebar_playlists")

        card = SettingsCard("Comportamiento")
        self._auto_open = SettingsSwitch(True)
        self._confirm_del = SettingsSwitch(True)
        self._allow_dup = SettingsSwitch(False)
        self._detect_lost = SettingsSwitch(True)
        card.add_row(SettingsRow("Abrir al crear", "Mostrar playlist nueva automáticamente", self._auto_open))
        card.add_row(SettingsRow("Confirmar al eliminar", "Evitar borrados accidentales", self._confirm_del))
        card.add_row(SettingsRow("Permitir duplicados", "Canciones repetidas en playlist", self._allow_dup))
        card.add_row(SettingsRow("Detectar archivos perdidos", "Mostrar alerta en playlists", self._detect_lost))
        self.add_card(card)

        card2 = SettingsCard("Importar / Exportar")
        self._m3u_format = SettingsCombo(["M3U", "M3U8"], "M3U8")
        self._encoding = SettingsCombo(["UTF-8", "Sistema"], "UTF-8")
        self._relative = SettingsSwitch(True)
        card2.add_row(SettingsRow("Formato por defecto", "Al exportar", self._m3u_format))
        card2.add_row(SettingsRow("Codificación", "Charset de archivo", self._encoding))
        card2.add_row(SettingsRow("Rutas relativas", "En lugar de absolutas", self._relative))
        self.add_card(card2)
        self.add_stretch()

    def apply(self):
        sm.set_("playlists/auto_open", self._auto_open.isChecked())
        sm.set_("playlists/confirm_delete", self._confirm_del.isChecked())
        sm.set_("playlists/allow_duplicates", self._allow_dup.isChecked())
        sm.set_("playlists/detect_lost", self._detect_lost.isChecked())
        sm.set_("playlists/m3u_format", self._m3u_format.currentText())
        sm.set_("playlists/encoding", self._encoding.currentText())
        sm.set_("playlists/relative_paths", self._relative.isChecked())


# ═══════════════════════════════════════════
# 9. Artistas y álbumes
# ═══════════════════════════════════════════

class ArtistsAlbumsPage(_Page):
    def __init__(self):
        super().__init__("Artistas y álbumes", "Agrupación, visualización y CoverFlow", "sidebar_artist")

        card = SettingsCard("Artistas")
        self._use_albumartist = SettingsSwitch(True)
        self._group_collab = SettingsSwitch(True)
        self._separate_comp = SettingsSwitch(True)
        self._artist_default = SettingsCombo(["Mosaico", "Lista"], "Mosaico")
        card.add_row(SettingsRow("Usar Album Artist", "Preferir albumartist para agrupar", self._use_albumartist))
        card.add_row(SettingsRow("Agrupar colaboraciones", "Feat. como parte del artista", self._group_collab))
        card.add_row(SettingsRow("Separar compilaciones", "\"Various Artists\" aparte", self._separate_comp))
        card.add_row(SettingsRow("Vista por defecto", "", self._artist_default))
        self.add_card(card)

        card2 = SettingsCard("Álbumes")
        self._album_sort = SettingsCombo(
            ["título", "artista", "año", "duración", "canciones"], "título")
        self._album_view = SettingsCombo(["Mosaico", "Lista", "CoverFlow"], "Mosaico")
        card2.add_row(SettingsRow("Orden por defecto", "Criterio de ordenamiento", self._album_sort))
        card2.add_row(SettingsRow("Vista por defecto", "", self._album_view))
        self.add_card(card2)
        self.add_stretch()

    def apply(self):
        sm.set_("artists/use_albumartist", self._use_albumartist.isChecked())
        sm.set_("artists/group_collaborations", self._group_collab.isChecked())
        sm.set_("artists/separate_compilations", self._separate_comp.isChecked())
        sm.set_("artists/default_view", self._artist_default.currentText())
        sm.set_("albums/default_sort", self._album_sort.currentText())
        sm.set_("albums/default_view", self._album_view.currentText())


# ═══════════════════════════════════════════
# 10. Radio
# ═══════════════════════════════════════════

class RadioPage(_Page):
    def __init__(self):
        super().__init__("Radio", "Emisoras, streams y grabaciones", "sidebar_radio")

        card = SettingsCard("General")
        self._auto_update = SettingsSwitch(sm.get("radio/auto_update"))
        self._reconnect = SettingsSwitch(sm.get("radio/auto_reconnect"))
        self._reconn_int = SettingsCombo(["1", "3", "5", "10", "30"], str(sm.get("radio/reconnect_interval")))
        card.add_row(SettingsRow("Actualizar al iniciar", "", self._auto_update))
        card.add_row(SettingsRow("Auto‑reconectar", "", self._reconnect))
        card.add_row(SettingsRow("Intervalo (s)", "", self._reconn_int))
        self.add_card(card)

        card2 = SettingsCard("Grabaciones")
        self._record = SettingsSwitch(sm.get("radio/record_streams"))
        self._rec_folder = SettingsPathPicker(sm.get("radio/record_folder"))
        self._rec_format = SettingsCombo(["mp3", "flac", "ogg"], "mp3")
        card2.add_row(SettingsRow("Grabar streams", "Guardar emisiones", self._record))
        card2.add_row(SettingsRow("Carpeta", "Directorio de grabaciones", self._rec_folder))
        card2.add_row(SettingsRow("Formato", "Codificación de audio", self._rec_format))
        self.add_card(card2)
        self.add_stretch()

    def apply(self):
        sm.set_("radio/auto_update", self._auto_update.isChecked())
        sm.set_("radio/auto_reconnect", self._reconnect.isChecked())
        sm.set_("radio/reconnect_interval", int(self._reconn_int.currentText()))
        sm.set_("radio/record_streams", self._record.isChecked())
        sm.set_("radio/record_folder", self._rec_folder.text())


# ═══════════════════════════════════════════
# 11. Servidores
# ═══════════════════════════════════════════

class ServersPage(_Page):
    def __init__(self):
        super().__init__("Servidores", "Navidrome, Jellyfin y conexiones remotas", "sidebar_servers")

        card = SettingsCard("Conexión")
        self._timeout = SettingsCombo(["5", "10", "15", "30"], "10")
        self._retries = SettingsCombo(["1", "3", "5"], "3")
        self._https = SettingsSwitch(True)
        card.add_row(SettingsRow("Timeout (s)", "Tiempo máximo de espera", self._timeout))
        card.add_row(SettingsRow("Reintentos", "", self._retries))
        card.add_row(SettingsRow("Preferir HTTPS", "", self._https))
        self.add_card(card)

        card2 = SettingsCard("Gestión")
        self._add_btn = SettingsActionButton("Añadir servidor")
        self._cache_btn = SettingsActionButton("Limpiar caché remoto")
        card2.add_row(SettingsRow("Añadir", "", self._add_btn))
        card2.add_row(SettingsRow("Caché", "", self._cache_btn))
        self.add_card(card2)
        self.add_stretch()

    def apply(self):
        sm.set_("servers/timeout", int(self._timeout.currentText()))
        sm.set_("servers/retries", int(self._retries.currentText()))
        sm.set_("servers/prefer_https", self._https.isChecked())


# ═══════════════════════════════════════════
# 12. Dispositivos
# ═══════════════════════════════════════════

class DevicesPage(_Page):
    def __init__(self):
        super().__init__("Dispositivos", "USB, discos externos y sincronización", "sidebar_devices")

        card = SettingsCard("Detección")
        self._auto_detect = SettingsSwitch(True)
        self._show_local = SettingsSwitch(True)
        self._confirm_unmount = SettingsSwitch(True)
        card.add_row(SettingsRow("Detectar USB automáticamente", "", self._auto_detect))
        card.add_row(SettingsRow("Mostrar discos locales", "", self._show_local))
        card.add_row(SettingsRow("Confirmar antes de desmontar", "", self._confirm_unmount))
        self.add_card(card)
        self.add_stretch()

    def apply(self):
        sm.set_("devices/auto_detect", self._auto_detect.isChecked())
        sm.set_("devices/show_local", self._show_local.isChecked())
        sm.set_("devices/confirm_unmount", self._confirm_unmount.isChecked())


# ═══════════════════════════════════════════
# 13. Sincronización
# ═══════════════════════════════════════════

class SyncPage(_Page):
    def __init__(self):
        super().__init__("Sincronización", "Transferencia entre dispositivos", "sidebar_servers")

        card = SettingsCard("Servidor de sincronización")
        self._auto = SettingsSwitch(sm.get("sync/auto_start"))
        self._port = SettingsSlider(1024, 65535, sm.get("sync/port"))
        self._port._slider.setTickInterval(1000)
        self._alias = SettingsPathPicker.__new__(SettingsPathPicker)  # workaround
        self._alias2 = QWidget()
        from PySide6.QtWidgets import QLineEdit
        self._alias_edit = QLineEdit(sm.get("sync/alias"))
        self._alias_edit.setStyleSheet("""
            QLineEdit { background: rgba(255,255,255,0.06); color: #FFFFFF;
              border: 1px solid rgba(255,255,255,0.10); border-radius: 8px;
              padding: 6px 10px; font-size: 11.5px; }
        """)
        self._discovery = SettingsSwitch(sm.get("sync/discovery_enabled"))
        self._interval = SettingsCombo(["1", "5", "10", "30", "60"], str(sm.get("sync/announce_interval")))
        card.add_row(SettingsRow("Iniciar al abrir", "", self._auto))
        card.add_row(SettingsRow("Puerto", "TCP para sincronización", self._port))
        card.add_row(SettingsRow("Alias", "Nombre visible en red", self._alias_edit))
        card.add_row(SettingsRow("Descubrimiento LAN", "", self._discovery))
        card.add_row(SettingsRow("Intervalo (s)", "", self._interval))
        self.add_card(card)
        self.add_stretch()

    def apply(self):
        sm.set_("sync/auto_start", self._auto.isChecked())
        sm.set_("sync/port", self._port.value())
        sm.set_("sync/alias", self._alias_edit.text())
        sm.set_("sync/discovery_enabled", self._discovery.isChecked())
        sm.set_("sync/announce_interval", int(self._interval.currentText()))


# ═══════════════════════════════════════════
# 14. Atajos
# ═══════════════════════════════════════════

class ShortcutsPage(_Page):
    def __init__(self):
        super().__init__("Atajos", "Accesos rápidos de teclado", "sidebar_library")

        card = SettingsCard("General")
        self._global = SettingsSwitch(sm.get("shortcuts/global_enabled"))
        card.add_row(SettingsRow("Atajos globales", "Funcionan aunque Michi no tenga el foco", self._global))
        info = QLabel(
            "Espacio       — Reproducir/Pausa\n"
            "Ctrl + →      — Siguiente\n"
            "Ctrl + ←      — Anterior\n"
            "Ctrl + ↑      — Subir volumen\n"
            "Ctrl + ↓      — Bajar volumen\n"
            "Ctrl + M      — Silencio\n"
            "Ctrl + P      — Preferencias"
        )
        info.setStyleSheet(f"color: {_TEXT3}; font-size: 11px; background: transparent; padding: 4px 8px;")
        card.add_row(info)
        self.add_card(card)
        self.add_stretch()

    def apply(self):
        sm.set_("shortcuts/global_enabled", self._global.isChecked())


# ═══════════════════════════════════════════
# 15. Avanzado
# ═══════════════════════════════════════════

class AdvancedPage(_Page):
    def __init__(self):
        super().__init__("Avanzado", "Debug, logs y configuraciones de desarrollo", "warm_settings")

        card = SettingsCard("Logs")
        self._debug = SettingsSwitch(sm.get("advanced/debug_log"))
        self._level = SettingsCombo(
            ["Error", "Warning", "Info", "Debug"], sm.get("advanced/log_level"))
        self._threads = SettingsCombo(["1", "2", "4", "8", "16"], str(sm.get("advanced/thread_limit")))
        card.add_row(SettingsRow("Debug log", "Registro detallado", self._debug))
        card.add_row(SettingsRow("Nivel de log", "", self._level))
        card.add_row(SettingsRow("Hilos máx.", "Procesamiento paralelo", self._threads))
        self.add_card(card)

        card2 = SettingsCard("Configuración")
        self._export = SettingsActionButton("Exportar configuración")
        self._import = SettingsActionButton("Importar configuración")
        self._open_logs = SettingsActionButton("Abrir carpeta de logs")
        self._open_config = SettingsActionButton("Abrir carpeta de configuración")
        card2.add_row(SettingsRow("Exportar", "", self._export))
        card2.add_row(SettingsRow("Importar", "", self._import))
        card2.add_row(SettingsRow("Logs", "", self._open_logs))
        card2.add_row(SettingsRow("Configuración", "", self._open_config))
        self.add_card(card2)

        card3 = SettingsCard("Peligro")
        self._reset_ui = SettingsActionButton("Resetear UI")
        self._reset_audio = SettingsActionButton("Resetear audio")
        self._reset_all = SettingsActionButton("Resetear toda la app")
        lbl = QLabel("Estas acciones no se pueden deshacer")
        lbl.setStyleSheet("color: #FF6B6B; font-size: 10.5px; background: transparent;")
        card3.add_row(lbl)
        card3.add_row(SettingsRow("Reset UI", "", self._reset_ui))
        card3.add_row(SettingsRow("Reset Audio", "", self._reset_audio))
        card3.add_row(SettingsRow("Reset total", "", self._reset_all))
        self.add_card(card3)
        self.add_stretch()

        self._export.clicked.connect(self._do_export)
        self._import.clicked.connect(self._do_import)
        self._open_logs.clicked.connect(lambda: _open_path("~/.local/share/michi-music-player/"))
        self._open_config.clicked.connect(lambda: _open_path("~/.config/Michi/"))
        self._reset_all.clicked.connect(self._do_reset)

    def _do_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar", "michi_config.json", "JSON (*.json)")
        if path:
            sm.export_to_file(path)

    def _do_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar", "", "JSON (*.json)")
        if path:
            try:
                sm.import_from_file(path)
                QMessageBox.information(self, "Importado", "Configuración importada correctamente.")
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _do_reset(self):
        reply = QMessageBox.question(self, "Reset total",
                                     "¿Restaurar TODAS las preferencias a sus valores por defecto?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            sm.restore_defaults()
            QMessageBox.information(self, "Reset", "Preferencias restauradas. Reinicia Michi.")

    def apply(self):
        sm.set_("advanced/debug_log", self._debug.isChecked())
        sm.set_("advanced/log_level", self._level.currentText())
        sm.set_("advanced/thread_limit", int(self._threads.currentText()))


# ═══════════════════════════════════════════
# 16. Acerca de
# ═══════════════════════════════════════════

class AboutPage(_Page):
    def __init__(self):
        super().__init__("Acerca de", "Información de Michi Music Player", "warm_settings")

        card = SettingsCard()
        # App info
        info_widget = QWidget()
        info_widget.setStyleSheet("background: transparent;")
        iv = QVBoxLayout(info_widget)
        iv.setSpacing(4)

        name = QLabel("Michi Music Player")
        name.setStyleSheet(f"color: {_TEXT}; font-size: 18px; font-weight: 800; background: transparent;")
        iv.addWidget(name)

        ver = QLabel("Versión 1.0.0")
        ver.setStyleSheet(f"color: {_TEXT2}; font-size: 13px; background: transparent;")
        iv.addWidget(ver)

        desc = QLabel("Reproductor de música premium para Linux/KDE con GStreamer, CoverFlow 3D y gestión avanzada de metadatos.")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {_TEXT3}; font-size: 11.5px; background: transparent;")
        iv.addWidget(desc)

        iv.addSpacing(8)
        stack = QLabel("Stack: Python 3 · PySide6 · GStreamer · SQLite · Mutagen")
        stack.setStyleSheet(f"color: {_TEXT3}; font-size: 11px; background: transparent;")
        iv.addWidget(stack)

        lic = QLabel("Licencia: MIT")
        lic.setStyleSheet(f"color: {_TEXT3}; font-size: 11px; background: transparent;")
        iv.addWidget(lic)

        author = QLabel("Autor: Cristian")
        author.setStyleSheet(f"color: {_TEXT3}; font-size: 11px; background: transparent;")
        iv.addWidget(author)

        iv.addSpacing(8)
        gh = SettingsActionButton("GitHub")
        gh.clicked.connect(lambda: _open_path("https://github.com/pitydah/michi-music-player"))
        iv.addWidget(gh)

        card.add_row(info_widget)
        self.add_card(card)
        self.add_stretch()


# ═══════════════════════════════════════════
# 17. Home Audio
# ═══════════════════════════════════════════

class HomeAudioPage(_Page):
    def __init__(self):
        super().__init__("Home Audio", "Audio multiroom, parlantes y Home Assistant",
                         "home_audio")

        # Home Assistant card
        card1 = SettingsCard("Home Assistant")
        self._ha_enabled = SettingsSwitch(sm.get("home_audio/enabled"))
        self._ha_url = _line_edit(sm.get("home_audio/ha_base_url") or "")
        self._ha_token = _line_edit(sm.get("home_audio/ha_token") or "")
        self._ha_token.setEchoMode(_line_edit().EchoMode.Password)
        self._ha_ssl = SettingsSwitch(sm.get("home_audio/ha_verify_ssl"))
        card1.add_row(SettingsRow("Activar Home Audio", "Habilita la integracion con HA",
                                  self._ha_enabled))
        card1.add_row(SettingsRow("URL de Home Assistant", "http://homeassistant.local:8123",
                                  self._ha_url))
        card1.add_row(SettingsRow("Token de acceso", "Token de larga duracion",
                                  self._ha_token))
        card1.add_row(SettingsRow("Verificar SSL", "Validar certificado HTTPS",
                                  self._ha_ssl))
        self.add_card(card1)

        # Snapserver card
        card2 = SettingsCard("Snapserver")
        self._snap_enabled = SettingsSwitch(sm.get("home_audio/snapserver_enabled"))
        self._snap_tcp = SettingsSlider(1024, 65535, sm.get("home_audio/snapserver_tcp_port"))
        self._snap_ctrl = SettingsSlider(1024, 65535, sm.get("home_audio/snapserver_control_port"))
        self._snap_http = SettingsSlider(1024, 65535, sm.get("home_audio/snapserver_http_port"))
        card2.add_row(SettingsRow("Activar Snapserver", "Iniciar al activar multiroom",
                                  self._snap_enabled))
        card2.add_row(SettingsRow("Puerto TCP", "Streaming de audio", self._snap_tcp))
        card2.add_row(SettingsRow("Puerto control", "API de Snapcast", self._snap_ctrl))
        card2.add_row(SettingsRow("Puerto HTTP", "Panel web", self._snap_http))
        self.add_card(card2)

        # API + mDNS card
        card3 = SettingsCard("Michi API + mDNS")
        self._api_enabled = SettingsSwitch(sm.get("home_audio/michi_api_enabled"))
        self._api_port = SettingsSlider(1024, 65535, sm.get("home_audio/michi_api_port"))
        self._api_token = _line_edit(sm.get("home_audio/michi_api_token") or "")
        self._mdns_enabled = SettingsSwitch(sm.get("home_audio/mdns_enabled"))
        card3.add_row(SettingsRow("Activar API Michi", "Control remoto desde HA",
                                  self._api_enabled))
        card3.add_row(SettingsRow("Puerto API", "Puerto HTTP de Michi", self._api_port))
        card3.add_row(SettingsRow("Token API", "Token de autenticacion", self._api_token))
        card3.add_row(SettingsRow("Activar mDNS", "Descubrimiento automatico en red",
                                  self._mdns_enabled))
        self.add_card(card3)

        # Local media server card
        card4 = SettingsCard("Servidor local de medios")
        self._lms_enabled = SettingsSwitch(sm.get("home_audio/local_media_server_enabled"))
        self._lms_port = SettingsSlider(1024, 65535, sm.get("home_audio/local_media_server_port"))
        self._local_mon = SettingsSwitch(sm.get("home_audio/play_local_monitor"))
        card4.add_row(SettingsRow("Activar servidor", "Servir archivos locales a HA/Cast",
                                  self._lms_enabled))
        card4.add_row(SettingsRow("Puerto", "Puerto HTTP del servidor", self._lms_port))
        card4.add_row(SettingsRow("Reproducir localmente", "Audio tambien en este equipo",
                                  self._local_mon))
        self.add_card(card4)

        self.add_stretch()

    def apply(self):
        sm.set_("home_audio/enabled", self._ha_enabled.isChecked())
        sm.set_("home_audio/ha_base_url", self._ha_url.text())
        sm.set_("home_audio/ha_token", self._ha_token.text())
        sm.set_("home_audio/ha_verify_ssl", self._ha_ssl.isChecked())
        sm.set_("home_audio/snapserver_enabled", self._snap_enabled.isChecked())
        sm.set_("home_audio/snapserver_tcp_port", self._snap_tcp.value())
        sm.set_("home_audio/snapserver_control_port", self._snap_ctrl.value())
        sm.set_("home_audio/snapserver_http_port", self._snap_http.value())
        sm.set_("home_audio/michi_api_enabled", self._api_enabled.isChecked())
        sm.set_("home_audio/michi_api_port", self._api_port.value())
        sm.set_("home_audio/michi_api_token", self._api_token.text())
        sm.set_("home_audio/mdns_enabled", self._mdns_enabled.isChecked())
        sm.set_("home_audio/local_media_server_enabled", self._lms_enabled.isChecked())
        sm.set_("home_audio/local_media_server_port", self._lms_port.value())
        sm.set_("home_audio/play_local_monitor", self._local_mon.isChecked())

        # Apply to running services
        try:
            from PySide6.QtWidgets import QApplication
            for w in QApplication.topLevelWidgets():
                if hasattr(w, '_michi_api'):
                    api = w._michi_api
                    api.configure(port=self._api_port.value(),
                                  token=self._api_token.text())
                    if self._api_enabled.isChecked() and not api.is_running:
                        api.start()
                    elif not self._api_enabled.isChecked() and api.is_running:
                        api.stop()
                if hasattr(w, '_mdns'):
                    mdns = w._mdns
                    mdns.configure(port=self._api_port.value())
                    if self._mdns_enabled.isChecked() and not mdns.is_running:
                        mdns.start()
                    elif not self._mdns_enabled.isChecked() and mdns.is_running:
                        mdns.stop()
                if hasattr(w, '_snapserver'):
                    ss = w._snapserver
                    ss.configure(tcp=self._snap_tcp.value(),
                                 ctrl=self._snap_ctrl.value(),
                                 http=self._snap_http.value())
                break
        except Exception:
            pass


# ═══════════════════════════════════════════
# Identificador musical
# ═══════════════════════════════════════════

class IdentifierPage(_Page):
    def __init__(self):
        super().__init__("Identificador musical", "Detección de música en reproducción", "sidebar_identifier")

        card = SettingsCard("General")
        self._auto = SettingsSwitch(sm.get("identifier/auto_enabled"))
        self._provider = SettingsCombo(
            ["none", "shazamio", "audd", "acoustid"],
            sm.get("identifier/provider"))
        self._interval = SettingsSlider(10, 120, sm.get("identifier/interval_seconds"), " s")
        card.add_row(SettingsRow("Activar automático", "Identificar automáticamente al reproducir", self._auto))
        card.add_row(SettingsRow("Proveedor", "ShazamIO, AudD, AcoustID o ninguno", self._provider))
        card.add_row(SettingsRow("Intervalo", "Segundos entre identificaciones", self._interval))
        self.add_card(card)

        card2 = SettingsCard("Fuentes")
        self._radio = SettingsSwitch(sm.get("identifier/listen_radio"))
        self._remote = SettingsSwitch(sm.get("identifier/listen_remote"))
        self._local = SettingsSwitch(sm.get("identifier/listen_local"))
        card2.add_row(SettingsRow("Radio", "Identificar emisoras online", self._radio))
        card2.add_row(SettingsRow("Streaming remoto", "Navidrome, Jellyfin, Subsonic", self._remote))
        card2.add_row(SettingsRow("Archivos locales", "Identificar archivos sin metadatos", self._local))
        self.add_card(card2)

        card3 = SettingsCard("Historial y arte")
        self._history = SettingsSwitch(sm.get("identifier/save_history"))
        self._artwork = SettingsSwitch(sm.get("identifier/download_artwork"))
        card3.add_row(SettingsRow("Guardar historial", "Conservar historial de detecciones", self._history))
        card3.add_row(SettingsRow("Descargar carátulas", "Obtener portada al identificar", self._artwork))
        self.add_card(card3)

        card4 = SettingsCard("API Keys")
        self._audd_key = _line_edit(sm.get("identifier/api_key_audd") or "")
        self._acoustid_key = _line_edit(sm.get("identifier/api_key_acoustid") or "")
        card4.add_row(SettingsRow("AudD API Key", "Clave para proveedor AudD", self._audd_key))
        card4.add_row(SettingsRow("AcoustID Key", "Clave para proveedor AcoustID", self._acoustid_key))
        self.add_card(card4)
        self.add_stretch()

    def apply(self):
        sm.set_("identifier/auto_enabled", self._auto.isChecked())
        sm.set_("identifier/provider", self._provider.currentText())
        sm.set_("identifier/listen_radio", self._radio.isChecked())
        sm.set_("identifier/listen_remote", self._remote.isChecked())
        sm.set_("identifier/listen_local", self._local.isChecked())
        sm.set_("identifier/interval_seconds", self._interval.value())
        sm.set_("identifier/save_history", self._history.isChecked())
        sm.set_("identifier/download_artwork", self._artwork.isChecked())
        sm.set_("identifier/api_key_audd", self._audd_key.text())
        sm.set_("identifier/api_key_acoustid", self._acoustid_key.text())


def _open_path(path: str):
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtCore import QUrl
    import os as _os
    expanded = _os.path.expanduser(path)
    QDesktopServices.openUrl(QUrl.fromLocalFile(expanded) if not path.startswith("http")
                              else QUrl(path))


def _line_edit(text: str = ""):
    from PySide6.QtWidgets import QLineEdit
    return QLineEdit(text)
