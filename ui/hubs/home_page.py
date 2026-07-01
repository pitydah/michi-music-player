"""HomePage — Centre de Situation Michi: 7 glass cards, rendered from snapshot."""
from __future__ import annotations

import logging
import os
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

from core.home.home_status import (
    AssistantSuggestion,
    AudioHomeStatus,
    EcosystemHomeStatus,
    HomeAlert,
    HomeCardError,
    HomeDashboardSnapshot,
    LibraryHomeStatus,
    PlaybackHomeStatus,
)
from ui.central.central_styles import (
    card_title_qss,
    glass_button_qss,
    glass_chip_button_qss,
    home_alert_item_qss,
    home_badge_qss,
    home_headline_qss,
    home_metric_label_qss,
    home_metric_value_qss,
    home_page_qss,
    home_subtitle_qss,
)
from ui.effects.michi_glass import AcrylicGlassFrame, apply_card_shadow

logger = logging.getLogger("michi.home_page")


class HomePage(QWidget):
    navigation_requested = Signal(str)
    refresh_requested = Signal()
    add_music_requested = Signal(list)
    add_folder_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("homePage")
        self._selected_files: list[str] = []
        self._cards: dict[str, QWidget] = {}
        self._build_ui()

    # ── Public entry point ──

    def render_snapshot(self, snapshot: HomeDashboardSnapshot | dict | Any):
        if isinstance(snapshot, dict):
            snapshot = self._dict_to_snapshot(snapshot)
        self._snapshot = snapshot
        self._render_all(snapshot)

    # ── Build UI ──

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("homeScroll")

        content = QWidget()
        content.setObjectName("homeContent")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(40, 16, 40, 40)
        cl.setSpacing(20)

        self._cl = cl

        # A. Estado General
        self._card_status = AcrylicGlassFrame("homeStatusCard")
        self._status_layout = QVBoxLayout(self._card_status)
        self._status_layout.setContentsMargins(28, 24, 28, 24)
        self._status_layout.setSpacing(6)
        cl.addWidget(self._card_status)
        self._cards["status"] = self._card_status

        # B. Continuar
        self._card_playback = AcrylicGlassFrame("homePlaybackCard", hover_shine=True)
        self._pb_layout = QVBoxLayout(self._card_playback)
        self._pb_layout.setContentsMargins(24, 16, 24, 16)
        self._pb_layout.setSpacing(8)
        cl.addWidget(self._card_playback)
        self._cards["playback"] = self._card_playback

        # C. Biblioteca
        self._card_library = AcrylicGlassFrame("homeLibCard", hover_shine=True)
        self._lib_layout = QVBoxLayout(self._card_library)
        self._lib_layout.setContentsMargins(24, 16, 24, 16)
        self._lib_layout.setSpacing(8)
        cl.addWidget(self._card_library)
        self._cards["library"] = self._card_library

        # D. Audio
        self._card_audio = AcrylicGlassFrame("homeAudioCard", hover_shine=True)
        self._audio_layout = QVBoxLayout(self._card_audio)
        self._audio_layout.setContentsMargins(24, 16, 24, 16)
        self._audio_layout.setSpacing(8)
        cl.addWidget(self._card_audio)
        self._cards["audio"] = self._card_audio

        # E. Ecosistema Michi
        self._card_eco = AcrylicGlassFrame("homeEcoCard", hover_shine=True)
        self._eco_layout = QVBoxLayout(self._card_eco)
        self._eco_layout.setContentsMargins(24, 16, 24, 16)
        self._eco_layout.setSpacing(8)
        cl.addWidget(self._card_eco)
        self._cards["ecosystem"] = self._card_eco

        # F. Atención requerida
        self._card_alerts = AcrylicGlassFrame("homeAlertsCard", hover_shine=True)
        self._alerts_layout = QVBoxLayout(self._card_alerts)
        self._alerts_layout.setContentsMargins(24, 16, 24, 16)
        self._alerts_layout.setSpacing(8)
        cl.addWidget(self._card_alerts)
        self._cards["alerts"] = self._card_alerts

        # G. Michi Assistant
        self._card_asst = AcrylicGlassFrame("homeAsstCard", hover_shine=True)
        self._asst_layout = QVBoxLayout(self._card_asst)
        self._asst_layout.setContentsMargins(24, 16, 24, 16)
        self._asst_layout.setSpacing(8)
        cl.addWidget(self._card_asst)
        self._cards["assistant"] = self._card_asst

        # Add music card (contextual, always at bottom)
        self._add_music_card = AcrylicGlassFrame("homeAddMusicCard", hover_shine=True)
        self._add_music_card.setVisible(False)
        self._build_add_music_ui()
        cl.addWidget(self._add_music_card)
        self._cards["add_music"] = self._add_music_card

        cl.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.setStyleSheet(home_page_qss())

        for _name, card in self._cards.items():
            apply_card_shadow(card)

    def _build_add_music_ui(self):
        amc = QVBoxLayout(self._add_music_card)
        amc.setContentsMargins(24, 16, 24, 16)
        amc.setSpacing(8)
        self._add_music_title = QLabel("Añadir música")
        self._add_music_title.setStyleSheet(card_title_qss())
        amc.addWidget(self._add_music_title)
        self._add_music_desc = QLabel("")
        self._add_music_desc.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.56); font-size: 12px; "
            "font-weight: 500; background: transparent; border: none; }"
        )
        amc.addWidget(self._add_music_desc)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self._add_folder_btn = QPushButton("📁 Añadir carpeta")
        self._add_folder_btn.setObjectName("homeAddFolderButton")
        self._add_folder_btn.setCursor(Qt.PointingHandCursor)
        self._add_folder_btn.setStyleSheet(glass_button_qss("secondary"))
        self._add_folder_btn.clicked.connect(self._on_add_folder_clicked)
        btn_row.addWidget(self._add_folder_btn)

        self._add_files_btn = QPushButton("🎵 Añadir archivos")
        self._add_files_btn.setObjectName("homeAddFilesButton")
        self._add_files_btn.setCursor(Qt.PointingHandCursor)
        self._add_files_btn.setStyleSheet(glass_button_qss("primary"))
        self._add_files_btn.clicked.connect(self._on_add_files_clicked)
        btn_row.addWidget(self._add_files_btn)
        btn_row.addStretch()
        amc.addLayout(btn_row)

        self._preview_widget = QWidget()
        self._preview_widget.setVisible(False)
        self._preview_widget.setStyleSheet("background: transparent;")
        pw = QVBoxLayout(self._preview_widget)
        pw.setContentsMargins(0, 4, 0, 0)
        pw.setSpacing(6)
        self._preview_label = QLabel("")
        self._preview_label.setWordWrap(True)
        self._preview_label.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.72); font-size: 12px; "
            "background: transparent; border: none; }"
        )
        pw.addWidget(self._preview_label)

        pbr = QHBoxLayout()
        pbr.setSpacing(10)
        self._cancel_preview_btn = QPushButton("✕ Cancelar")
        self._cancel_preview_btn.setCursor(Qt.PointingHandCursor)
        self._cancel_preview_btn.setStyleSheet(glass_chip_button_qss())
        self._cancel_preview_btn.clicked.connect(self._clear_selection)
        pbr.addWidget(self._cancel_preview_btn)
        self._confirm_btn = QPushButton("✓ Importar")
        self._confirm_btn.setObjectName("homeConfirmImportButton")
        self._confirm_btn.setCursor(Qt.PointingHandCursor)
        self._confirm_btn.setStyleSheet(glass_button_qss("primary"))
        self._confirm_btn.clicked.connect(self._on_confirm)
        pbr.addWidget(self._confirm_btn)
        pbr.addStretch()
        pw.addLayout(pbr)
        amc.addWidget(self._preview_widget)

    # ── Render logic ──

    def _render_all(self, s: HomeDashboardSnapshot):
        self._render_status(s)
        self._render_playback(s.playback)
        self._render_library(s.library)
        self._render_audio(s.audio)
        self._render_ecosystem(s.ecosystem)
        self._render_alerts(s.alerts)
        self._render_assistant(s.assistant_suggestions)
        self._render_add_music(s.library, s.overall_state)
        self._render_errors(s.errors)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _badge(self, text: str, kind: str = "ok") -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(home_badge_qss(kind))
        return lbl

    # ── A. Estado General ──

    def _render_status(self, s: HomeDashboardSnapshot):
        self._clear_layout(self._status_layout)

        self._headline = QLabel(s.headline)
        self._headline.setStyleSheet(home_headline_qss())
        self._status_layout.addWidget(self._headline)

        if s.subtitle:
            sub = QLabel(s.subtitle)
            sub.setStyleSheet(home_subtitle_qss())
            sub.setWordWrap(True)
            self._status_layout.addWidget(sub)

        badges = QHBoxLayout()
        badges.setSpacing(8)

        lib = s.library
        if not lib.is_empty and lib.is_healthy:
            badges.addWidget(self._badge("Biblioteca OK", "ok"))
        elif lib.index_error_count > 0:
            badges.addWidget(self._badge("Errores de índice", "critical"))
        elif not lib.is_healthy:
            badges.addWidget(self._badge("Requiere atención", "warning"))

        if s.audio.dac_active:
            badges.addWidget(self._badge("DAC activo", "ok"))
        elif s.audio.output_device and s.audio.output_device != "Predeterminado":
            badges.addWidget(self._badge("Salida configurada", "info"))

        if s.audio.warnings:
            badges.addWidget(self._badge("Audio requiere atención", "warning"))

        if s.ecosystem.micro_server_state == "connected":
            badges.addWidget(self._badge("Micro conectado", "ok"))
        elif s.ecosystem.micro_server_state == "requires_pairing":
            badges.addWidget(self._badge("Requiere pairing", "warning"))

        if lib.is_empty:
            badges.addWidget(self._badge("Biblioteca vacía", "info"))

        safe_mode = os.environ.get("MICHI_SAFE_MODE") == "1"
        if safe_mode:
            badges.addWidget(self._badge("Modo seguro", "warning"))

        if s.overall_state == "error":
            badges.addWidget(self._badge("Error", "critical"))

        badges.addStretch()
        self._status_layout.addLayout(badges)

    # ── B. Continuar ──

    def _render_playback(self, pb: PlaybackHomeStatus):
        self._clear_layout(self._pb_layout)
        title = QLabel("Continuar")
        title.setStyleSheet(card_title_qss())
        self._pb_layout.addWidget(title)

        if pb.has_current_track:
            info = f"{pb.current_artist} — {pb.current_title}" if pb.current_artist else pb.current_title
            track = QLabel(info)
            track.setStyleSheet(
                "QLabel { color: rgba(255,255,255,0.82); font-size: 14px; "
                "font-weight: 600; background: transparent; border: none; }"
            )
            track.setWordWrap(True)
            self._pb_layout.addWidget(track)

            if pb.current_album:
                alb = QLabel(pb.current_album)
                alb.setStyleSheet(
                    "QLabel { color: rgba(255,255,255,0.50); font-size: 12px; "
                    "background: transparent; border: none; }"
                )
                self._pb_layout.addWidget(alb)

            state_label = "Reproduciendo" if pb.state == "playing" else "En pausa"
            state = QLabel(state_label)
            state.setStyleSheet(
                "QLabel { color: rgba(143,183,255,0.70); font-size: 11px; "
                "font-weight: 600; background: transparent; border: none; }"
            )
            self._pb_layout.addWidget(state)

        elif pb.last_track_title:
            info = f"{pb.last_track_artist} — {pb.last_track_title}" if pb.last_track_artist else pb.last_track_title
            track = QLabel(f"Continuar escuchando: {info}")
            track.setStyleSheet(
                "QLabel { color: rgba(255,255,255,0.72); font-size: 13px; "
                "background: transparent; border: none; }"
            )
            track.setWordWrap(True)
            self._pb_layout.addWidget(track)

        if pb.queue_active:
            ql = QLabel(f"Cola activa: {pb.queue_count} canciones")
            ql.setStyleSheet(
                "QLabel { color: rgba(255,255,255,0.52); font-size: 11px; "
                "background: transparent; border: none; }"
            )
            self._pb_layout.addWidget(ql)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        if pb.can_continue:
            cont = QPushButton("▶ Continuar")
            cont.setObjectName("homeContinueButton")
            cont.setCursor(Qt.PointingHandCursor)
            cont.setStyleSheet(glass_button_qss("primary"))
            cont.clicked.connect(lambda: self.navigation_requested.emit("playback_hub"))
            btn_row.addWidget(cont)

        if pb.queue_active:
            queue_btn = QPushButton("Ver cola")
            queue_btn.setObjectName("homeQueueButton")
            queue_btn.setCursor(Qt.PointingHandCursor)
            queue_btn.setStyleSheet(glass_button_qss("ghost"))
            queue_btn.clicked.connect(lambda: self.navigation_requested.emit("playback_hub"))
            btn_row.addWidget(queue_btn)

        if pb.can_continue_remote:
            remote = QPushButton("Continuar en Micro Server")
            remote.setCursor(Qt.PointingHandCursor)
            remote.setStyleSheet(glass_chip_button_qss())
            remote.clicked.connect(lambda: self.navigation_requested.emit("playback_hub"))
            btn_row.addWidget(remote)

        if not pb.can_continue and not pb.queue_active:
            explore = QPushButton("Explorar biblioteca")
            explore.setObjectName("homeExploreLibraryButton")
            explore.setCursor(Qt.PointingHandCursor)
            explore.setStyleSheet(glass_button_qss("ghost"))
            explore.clicked.connect(lambda: self.navigation_requested.emit("library_hub"))
            btn_row.addWidget(explore)

            mix = QPushButton("Crear mix")
            mix.setObjectName("homeCreateMixButton")
            mix.setCursor(Qt.PointingHandCursor)
            mix.setStyleSheet(glass_chip_button_qss())
            mix.clicked.connect(lambda: self.navigation_requested.emit("mix_hub"))
            btn_row.addWidget(mix)

        btn_row.addStretch()
        self._pb_layout.addLayout(btn_row)
        self._pb_layout.addStretch()
        self._card_playback.setVisible(True)

    # ── C. Biblioteca ──

    def _render_library(self, lib: LibraryHomeStatus):
        self._clear_layout(self._lib_layout)
        title = QLabel("Biblioteca")
        title.setStyleSheet(card_title_qss())
        self._lib_layout.addWidget(title)

        if lib.is_empty:
            empty = QLabel("Aún no hay canciones en tu biblioteca")
            empty.setStyleSheet(
                "QLabel { color: rgba(255,255,255,0.50); font-size: 12px; "
                "background: transparent; border: none; }"
            )
            self._lib_layout.addWidget(empty)
            self._card_library.setVisible(True)
            return

        metrics = QHBoxLayout()
        metrics.setSpacing(24)
        for val, label in [
            (f"{lib.track_count:,}", "Canciones"),
            (f"{lib.album_count:,}", "Álbumes"),
            (f"{lib.artist_count:,}", "Artistas"),
            (f"{lib.genre_count:,}", "Géneros"),
        ]:
            col = QVBoxLayout()
            col.setSpacing(0)
            v = QLabel(val)
            v.setStyleSheet(home_metric_value_qss())
            col.addWidget(v)
            label = QLabel(label)
            label.setStyleSheet(home_metric_label_qss())
            col.addWidget(label)
            metrics.addLayout(col)
        metrics.addStretch()
        self._lib_layout.addLayout(metrics)

        if lib.last_scan:
            ls = QLabel(f"Última indexación: {lib.last_scan}")
            ls.setStyleSheet(
                "QLabel { color: rgba(255,255,255,0.42); font-size: 11px; "
                "background: transparent; border: none; }"
            )
            self._lib_layout.addWidget(ls)

        if lib.active_roots_count:
            roots = QLabel(f"{lib.active_roots_count} carpetas activas")
            roots.setStyleSheet(
                "QLabel { color: rgba(255,255,255,0.42); font-size: 11px; "
                "background: transparent; border: none; }"
            )
            self._lib_layout.addWidget(roots)

        if lib.index_error_count > 0 or lib.missing_file_count > 0:
            errs = QLabel(
                f"{lib.index_error_count} errores · {lib.missing_file_count} archivos faltantes"
            )
            errs.setStyleSheet(
                "QLabel { color: rgba(255,82,82,0.60); font-size: 11px; "
                "font-weight: 600; background: transparent; border: none; }"
            )
            self._lib_layout.addWidget(errs)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        scan = QPushButton("Escanear ahora")
        scan.setObjectName("homeScanNowButton")
        scan.setCursor(Qt.PointingHandCursor)
        scan.setStyleSheet(glass_button_qss("ghost"))
        scan.clicked.connect(self.refresh_requested.emit)
        btn_row.addWidget(scan)

        view = QPushButton("Ver biblioteca")
        view.setObjectName("homeViewLibraryButton")
        view.setCursor(Qt.PointingHandCursor)
        view.setStyleSheet(glass_button_qss("primary"))
        view.clicked.connect(lambda: self.navigation_requested.emit("library_hub"))
        btn_row.addWidget(view)

        if lib.index_error_count > 0 or lib.missing_file_count > 0:
            problems = QPushButton("Revisar problemas")
            problems.setObjectName("homeReviewProblemsButton")
            problems.setCursor(Qt.PointingHandCursor)
            problems.setStyleSheet(glass_chip_button_qss())
            problems.clicked.connect(
                lambda: self.navigation_requested.emit("audio_lab_diagnostics")
            )
            btn_row.addWidget(problems)

        btn_row.addStretch()
        self._lib_layout.addLayout(btn_row)
        self._card_library.setVisible(True)

    # ── D. Audio ──

    def _render_audio(self, audio: AudioHomeStatus):
        self._clear_layout(self._audio_layout)
        title = QLabel("Audio")
        title.setStyleSheet(card_title_qss())
        self._audio_layout.addWidget(title)

        if not audio.output_device and audio.bitperfect_state == "not_available":
            muted = QLabel("Información de audio no disponible")
            muted.setStyleSheet(
                "QLabel { color: rgba(255,255,255,0.50); font-size: 12px; "
                "background: transparent; border: none; }"
            )
            self._audio_layout.addWidget(muted)
            self._card_audio.setVisible(True)
            return

        items = QVBoxLayout()
        items.setSpacing(2)
        if audio.output_device:
            items.addWidget(QLabel(f"Salida: {audio.output_device}"))
        if audio.output_profile:
            items.addWidget(QLabel(f"Perfil: {audio.output_profile}"))
        if audio.replaygain_enabled:
            items.addWidget(QLabel("ReplayGain activo"))
        if audio.eq_enabled:
            items.addWidget(QLabel("Ecualizador activo"))
        if audio.dsp_active:
            items.addWidget(QLabel("Procesamiento DSP activo"))
        if audio.bitperfect_state == "verified":
            items.addWidget(QLabel("Bit-Perfect verificado"))
        elif audio.bitperfect_state != "not_available":
            items.addWidget(QLabel("Bit-Perfect no verificado"))

        for i in range(items.count()):
            w = items.itemAt(i).widget()
            if w:
                w.setStyleSheet(
                    "QLabel { color: rgba(255,255,255,0.68); font-size: 12px; "
                    "background: transparent; border: none; }"
                )
        self._audio_layout.addLayout(items)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        config = QPushButton("Configurar salida")
        config.setObjectName("homeAudioOutputButton")
        config.setCursor(Qt.PointingHandCursor)
        config.setStyleSheet(glass_button_qss("ghost"))
        config.clicked.connect(
            lambda: self.navigation_requested.emit("audio_lab_output")
        )
        btn_row.addWidget(config)

        lab = QPushButton("Abrir Audio Lab")
        lab.setObjectName("homeAudioLabButton")
        lab.setCursor(Qt.PointingHandCursor)
        lab.setStyleSheet(glass_button_qss("primary"))
        lab.clicked.connect(lambda: self.navigation_requested.emit("audio_lab"))
        btn_row.addWidget(lab)

        diag = QPushButton("Diagnóstico")
        diag.setCursor(Qt.PointingHandCursor)
        diag.setStyleSheet(glass_chip_button_qss())
        diag.clicked.connect(
            lambda: self.navigation_requested.emit("audio_lab_diagnostics")
        )
        btn_row.addWidget(diag)

        btn_row.addStretch()
        self._audio_layout.addLayout(btn_row)
        self._card_audio.setVisible(True)

    # ── E. Ecosistema Michi ──

    def _render_ecosystem(self, eco: EcosystemHomeStatus):
        self._clear_layout(self._eco_layout)
        title = QLabel("Ecosistema Michi")
        title.setStyleSheet(card_title_qss())
        self._eco_layout.addWidget(title)

        lines = []

        if eco.micro_server_state == "connected":
            name = eco.micro_server_name or "Conectado"
            lines.append(f"Micro Server: {name}")
        elif eco.micro_server_state == "disconnected":
            lines.append("Micro Server: No conectado")
        elif eco.micro_server_state == "requires_pairing":
            lines.append("Micro Server: Requiere pairing")
        elif eco.micro_server_state == "contract_error":
            lines.append("Micro Server: Contrato incompatible")
        else:
            lines.append("Micro Server: Desconocido")

        if eco.mobile_sync_state == "no_device":
            lines.append("Sync móvil: Sin dispositivos")
        elif eco.mobile_sync_state == "paired":
            lines.append(f"Sync móvil: {eco.mobile_device_count} dispositivo(s)")
        elif eco.mobile_sync_state == "syncing":
            lines.append(f"Sync móvil: Sincronizando ({eco.mobile_device_count})")
        elif eco.mobile_sync_state == "error":
            lines.append("Sync móvil: Error")
        else:
            lines.append("Sync móvil: Desconocido")

        if eco.api_state == "active":
            lines.append("API local: Activa")
        else:
            lines.append("API local: Inactiva")

        if eco.home_audio_state == "active":
            lines.append("Home Audio: Activo")
        elif eco.home_audio_state == "experimental":
            lines.append("Home Audio: Experimental")
        elif eco.home_audio_state == "disabled":
            lines.append("Home Audio: Desactivado")

        if eco.last_sync:
            lines.append(f"Última sincronización: {eco.last_sync}")

        for line in lines:
            lbl = QLabel(line)
            lbl.setStyleSheet(
                "QLabel { color: rgba(255,255,255,0.62); font-size: 12px; "
                "background: transparent; border: none; }"
            )
            self._eco_layout.addWidget(lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        if eco.micro_server_state == "disconnected":
            conn = QPushButton("Conectar servidor")
            conn.setObjectName("homeConnectServerButton")
            conn.setCursor(Qt.PointingHandCursor)
            conn.setStyleSheet(glass_button_qss("primary"))
            conn.clicked.connect(
                lambda: self.navigation_requested.emit("connections_hub")
            )
            btn_row.addWidget(conn)

        sync_btn = QPushButton("Sincronizar móvil")
        sync_btn.setObjectName("homeSyncMobileButton")
        sync_btn.setCursor(Qt.PointingHandCursor)
        sync_btn.setStyleSheet(glass_button_qss("ghost"))
        sync_btn.clicked.connect(lambda: self.navigation_requested.emit("devices_page"))
        btn_row.addWidget(sync_btn)

        if eco.diagnostics_available:
            diag = QPushButton("Diagnóstico")
            diag.setObjectName("homeConnectionDiagnosticsButton")
            diag.setCursor(Qt.PointingHandCursor)
            diag.setStyleSheet(glass_chip_button_qss())
            diag.clicked.connect(
                lambda: self.navigation_requested.emit("connections_hub")
            )
            btn_row.addWidget(diag)

        btn_row.addStretch()
        self._eco_layout.addLayout(btn_row)
        self._card_eco.setVisible(True)

    # ── F. Atención requerida ──

    def _render_alerts(self, alerts: list[HomeAlert]):
        self._clear_layout(self._alerts_layout)
        title = QLabel("Atención requerida")
        title.setStyleSheet(card_title_qss())
        self._alerts_layout.addWidget(title)

        if not alerts:
            noop = QLabel("No hay tareas importantes pendientes.")
            noop.setStyleSheet(
                "QLabel { color: rgba(255,255,255,0.50); font-size: 12px; "
                "background: transparent; border: none; }"
            )
            self._alerts_layout.addWidget(noop)
            self._card_alerts.setVisible(True)
            return

        for alert in alerts:
            frame = QFrame()
            frame.setObjectName("alertItem")
            frame.setStyleSheet(home_alert_item_qss(alert.severity))
            f_layout = QVBoxLayout(frame)
            f_layout.setContentsMargins(0, 0, 0, 0)
            f_layout.setSpacing(2)

            alert_title = QLabel(alert.title)
            alert_title.setObjectName("alertTitle")
            f_layout.addWidget(alert_title)

            if alert.message:
                alert_msg = QLabel(alert.message)
                alert_msg.setObjectName("alertMsg")
                alert_msg.setWordWrap(True)
                f_layout.addWidget(alert_msg)

            if alert.target_route and alert.action_label:
                action = QPushButton(alert.action_label)
                action.setCursor(Qt.PointingHandCursor)
                action.setStyleSheet(
                    "QPushButton { color: rgba(143,183,255,0.80); font-size: 11px; "
                    "font-weight: 600; background: transparent; border: none; "
                    "padding: 2px 0; text-align: left; }"
                    "QPushButton:hover { color: rgba(143,183,255,1.0); }"
                )
                action.clicked.connect(
                    lambda c=None, r=alert.target_route: self.navigation_requested.emit(r)
                )
                f_layout.addWidget(action)

            self._alerts_layout.addWidget(frame)

        self._card_alerts.setVisible(True)

    # ── G. Michi Assistant ──

    def _render_assistant(self, suggestions: list[AssistantSuggestion]):
        self._clear_layout(self._asst_layout)
        title = QLabel("Michi Assistant")
        title.setStyleSheet(card_title_qss())
        self._asst_layout.addWidget(title)

        if not suggestions:
            noop = QLabel("No hay sugerencias en este momento.")
            noop.setStyleSheet(
                "QLabel { color: rgba(255,255,255,0.50); font-size: 12px; "
                "background: transparent; border: none; }"
            )
            self._asst_layout.addWidget(noop)

        for sug in suggestions[:3]:
            sug_frame = QFrame()
            sug_frame.setStyleSheet(
                "QFrame { background: rgba(255,255,255,0.02); "
                "border-radius: 6px; padding: 8px 12px; }"
            )
            sg = QVBoxLayout(sug_frame)
            sg.setContentsMargins(12, 8, 12, 8)
            sg.setSpacing(2)
            sg_title = QLabel(sug.title)
            sg_title.setStyleSheet(
                "QLabel { color: rgba(255,255,255,0.82); font-size: 13px; "
                "font-weight: 600; background: transparent; border: none; }"
            )
            sg.addWidget(sg_title)
            if sug.message:
                sg_msg = QLabel(sug.message)
                sg_msg.setStyleSheet(
                    "QLabel { color: rgba(255,255,255,0.48); font-size: 11px; "
                    "background: transparent; border: none; }"
                )
                sg_msg.setWordWrap(True)
                sg.addWidget(sg_msg)
            if sug.target_route:
                sg_btn = QPushButton("Ir")
                sg_btn.setCursor(Qt.PointingHandCursor)
                sg_btn.setStyleSheet(
                    "QPushButton { color: rgba(143,183,255,0.80); font-size: 11px; "
                    "font-weight: 600; background: transparent; border: none; "
                    "padding: 2px 0; text-align: left; }"
                    "QPushButton:hover { color: rgba(143,183,255,1.0); }"
                )
                sg_btn.clicked.connect(
                    lambda c=None, r=sug.target_route: self.navigation_requested.emit(r)
                )
                sg.addWidget(sg_btn)
            self._asst_layout.addWidget(sug_frame)

        open_btn = QPushButton("Abrir Asistente")
        open_btn.setObjectName("homeAssistantOpenButton")
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.setStyleSheet(glass_button_qss("ghost"))
        open_btn.clicked.connect(
            lambda: self.navigation_requested.emit("assistant")
        )
        self._asst_layout.addWidget(open_btn)
        self._card_asst.setVisible(True)

    # ── Add music contextual ──

    def _render_add_music(self, lib: LibraryHomeStatus, overall_state: str):
        if lib.is_empty or overall_state == "empty_library":
            self._add_music_card.setVisible(True)
            self._add_music_title.setText("Añadir música")
            self._add_music_desc.setText(
                "Tu biblioteca está vacía. Agrega archivos o carpetas para empezar."
            )
        else:
            self._add_music_card.setVisible(False)

    # ── Error cards ──

    def _render_errors(self, errors: list[HomeCardError]):
        for err in errors:
            logger.warning("Home card '%s' error: %s", err.card_name, err.error_message)

    # ── Add Music handlers (kept from original) ──

    def _on_add_folder_clicked(self):
        path = QFileDialog.getExistingDirectory(
            self, "Añadir carpeta", os.path.expanduser("~")
        )
        if path:
            self.add_folder_requested.emit(path)

    def _on_add_files_clicked(self):
        from library.library_db import AUDIO_EXTS

        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Añadir archivos",
            os.path.expanduser("~"),
            f"Audio ({' '.join('*' + e for e in AUDIO_EXTS)})",
        )
        if paths:
            self._selected_files = paths
            self._update_preview()
            self._preview_widget.setVisible(True)

    def _clear_selection(self):
        self._selected_files = []
        self._preview_widget.setVisible(False)

    def _on_confirm(self):
        if self._selected_files:
            self.add_music_requested.emit(self._selected_files)
            self._clear_selection()

    def _update_preview(self):
        n = len(self._selected_files)
        if n == 0:
            self._preview_label.setText("")
            self._confirm_btn.setText("✓ Importar")
            return
        lines = [f"{n} archivos seleccionados:"]
        for fp in self._selected_files[:3]:
            lines.append(f"  • {os.path.basename(fp)}")
        if n > 3:
            lines.append(f"  ... y {n - 3} más")
        self._preview_label.setText("\n".join(lines))
        self._confirm_btn.setText(f"✓ Importar {n} canciones")

    # ── Deprecated compat ──

    def refresh(self, items=None, servers=None, devices=None):
        logger.warning("HomePage.refresh() deprecated — use render_snapshot()")
        if hasattr(self, "_snapshot") and self._snapshot is not None:
            self.render_snapshot(self._snapshot)

    @staticmethod
    def _dict_to_snapshot(d: dict) -> HomeDashboardSnapshot:
        lib = d.get("library_health", d.get("library", {}))
        pb = d.get("playback", {})
        return HomeDashboardSnapshot(
            overall_state=d.get("overall_state", "ready"),
            headline=d.get("headline", ""),
            subtitle=d.get("subtitle", ""),
            library=LibraryHomeStatus(
                track_count=lib.get("track_count", 0),
                album_count=lib.get("album_count", 0),
                artist_count=lib.get("artist_count", 0),
                genre_count=lib.get("genre_count", 0),
                last_scan=lib.get("last_scan"),
                index_error_count=lib.get("index_error_count", 0),
                missing_metadata_count=lib.get("missing_metadata_count", 0),
                missing_cover_count=lib.get("missing_cover_count", 0),
                is_empty=lib.get("track_count", 0) == 0,
                is_healthy=lib.get("index_error_count", 0) == 0,
            ),
            playback=PlaybackHomeStatus(
                has_current_track=bool(pb.get("now_playing")),
                current_title=pb.get("now_playing", {}).get("title", ""),
                current_artist=pb.get("now_playing", {}).get("artist", ""),
                queue_active=pb.get("queue_length", 0) > 0,
                queue_count=pb.get("queue_length", 0),
                state="playing" if pb.get("now_playing") else "stopped",
            ),
        )
