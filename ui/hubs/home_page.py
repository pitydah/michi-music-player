"""HomePage — clean dashboard: library status, suggestions, continuity, ecosystem."""
from __future__ import annotations

import logging
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QPushButton, QFileDialog,
)

from ui.central.central_styles import (
    glass_button_qss, glass_chip_button_qss,
    empty_state_qss,
    card_title_qss, card_desc_qss,
)
from ui.effects.michi_glass import AcrylicGlassFrame, apply_card_shadow

logger = logging.getLogger("michi.home_page")


class HomePage(QWidget):
    navigation_requested = Signal(str)
    refresh_requested = Signal()
    add_music_requested = Signal(list)
    add_folder_requested = Signal(str)

    def __init__(self, db=None, playback=None, window=None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("homePage")
        self._db = db
        self._playback = playback
        self._win = window
        self._build_ui()

    def refresh(self, items=None, servers=None, devices=None):
        stats = self._get_stats()
        self._update_library_status(stats)
        self._update_add_music(stats)
        self._update_suggestions(stats)
        self._update_last_session()
        self._update_connections(servers or [], devices or [])

    def _get_stats(self) -> dict:
        stats = {"total_songs": 0, "total_artists": 0, "total_albums": 0,
                 "missing_metadata": 0}

        # Try context service snapshot first
        try:
            from core.context.context_service import ContextService
            svc = ContextService()
            snap = svc.get_home_snapshot()
            if snap and snap.get("library_health"):
                lh = snap["library_health"]
                stats.update({
                    "total_songs": lh.get("track_count", 0),
                    "total_artists": lh.get("artist_count", 0),
                    "total_albums": lh.get("album_count", 0),
                    "missing_metadata": lh.get("missing_metadata_count", 0),
                })
                return stats
        except Exception:
            logger.debug("ContextService snapshot unavailable")

        # Fallback to direct DB queries
        try:
            if self._db and hasattr(self._db, "get_dashboard_stats"):
                ds = self._db.get_dashboard_stats()
                stats.update(ds)
            elif self._db and hasattr(self._db, "get_stats"):
                st = self._db.get_stats()
                stats["total_songs"] = st.get("total", 0)
        except Exception as e:
            logger.debug("Home stats unavailable: %s", e)
        return stats

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

        # ── 1. Library Status ──
        self._lib_card = AcrylicGlassFrame("homeLibCard")
        lc = QVBoxLayout(self._lib_card)
        lc.setContentsMargins(24, 20, 24, 20)
        lc.setSpacing(4)
        self._lib_status_msg = QLabel("Tu biblioteca está lista")
        self._lib_status_msg.setObjectName("libStatusMsg")
        self._lib_status_msg.setStyleSheet(
            card_title_qss() +
            "QLabel { color: rgba(255,255,255,0.92); }")
        lc.addWidget(self._lib_status_msg)
        self._lib_counts = QLabel("")
        self._lib_counts.setStyleSheet(card_desc_qss())
        lc.addWidget(self._lib_counts)
        cl.addWidget(self._lib_card)

        # ── 2. Añadir música (contextual) ──
        self._add_music_card = AcrylicGlassFrame("homeAddMusicCard", hover_shine=True)
        self._add_music_card.setVisible(False)
        amc = QVBoxLayout(self._add_music_card)
        amc.setContentsMargins(24, 16, 24, 16)
        amc.setSpacing(8)

        self._add_music_title = QLabel("Añadir música")
        self._add_music_title.setStyleSheet(card_title_qss())
        amc.addWidget(self._add_music_title)

        self._add_music_desc = QLabel("Agrega archivos o carpetas a tu biblioteca.")
        self._add_music_desc.setStyleSheet(card_desc_qss())
        amc.addWidget(self._add_music_desc)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self._add_folder_btn = QPushButton("📁 Añadir carpeta")
        self._add_folder_btn.setCursor(Qt.PointingHandCursor)
        self._add_folder_btn.setStyleSheet(glass_button_qss("secondary"))
        self._add_folder_btn.clicked.connect(self._on_add_folder_clicked)
        btn_row.addWidget(self._add_folder_btn)

        self._add_files_btn = QPushButton("🎵 Añadir archivos")
        self._add_files_btn.setCursor(Qt.PointingHandCursor)
        self._add_files_btn.setStyleSheet(glass_button_qss("primary"))
        self._add_files_btn.clicked.connect(self._on_add_files_clicked)
        btn_row.addWidget(self._add_files_btn)
        btn_row.addStretch()
        amc.addLayout(btn_row)

        # Preview section
        self._preview_widget = QWidget()
        self._preview_widget.setVisible(False)
        self._preview_widget.setStyleSheet("background: transparent;")
        pw_layout = QVBoxLayout(self._preview_widget)
        pw_layout.setContentsMargins(0, 4, 0, 0)
        pw_layout.setSpacing(6)
        self._preview_label = QLabel("")
        self._preview_label.setWordWrap(True)
        self._preview_label.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.72); font-size: 12px;"
            "  background: transparent; border: none; }")
        pw_layout.addWidget(self._preview_label)

        preview_btn_row = QHBoxLayout()
        preview_btn_row.setSpacing(10)
        self._cancel_preview_btn = QPushButton("✕ Cancelar")
        self._cancel_preview_btn.setCursor(Qt.PointingHandCursor)
        self._cancel_preview_btn.setStyleSheet(glass_chip_button_qss())
        self._cancel_preview_btn.clicked.connect(self._clear_selection)
        preview_btn_row.addWidget(self._cancel_preview_btn)

        self._confirm_btn = QPushButton("✓ Importar")
        self._confirm_btn.setCursor(Qt.PointingHandCursor)
        self._confirm_btn.setStyleSheet(glass_button_qss("primary"))
        self._confirm_btn.clicked.connect(self._on_confirm)
        preview_btn_row.addWidget(self._confirm_btn)
        preview_btn_row.addStretch()
        pw_layout.addLayout(preview_btn_row)
        amc.addWidget(self._preview_widget)
        cl.addWidget(self._add_music_card)

        # ── 3. Sugerencias de Michi ──
        self._sugg_card = AcrylicGlassFrame("homeSuggCard", hover_shine=True)
        sc = QVBoxLayout(self._sugg_card)
        sc.setContentsMargins(24, 16, 24, 16)
        sc.setSpacing(8)
        sugg_title = QLabel("Sugerencias de Michi")
        sugg_title.setStyleSheet(card_title_qss())
        sc.addWidget(sugg_title)
        self._sugg_content = QVBoxLayout()
        self._sugg_content.setSpacing(4)
        sc.addLayout(self._sugg_content)
        cl.addWidget(self._sugg_card)

        # ── 4. Last Session + Connections (side by side) ──
        bottom = QHBoxLayout()
        bottom.setSpacing(16)

        # Last session
        self._session_card = AcrylicGlassFrame("homeSessionCard", hover_shine=True)
        sc2 = QVBoxLayout(self._session_card)
        sc2.setContentsMargins(20, 16, 20, 16)
        sc2.setSpacing(8)
        session_title = QLabel("Última reproducción")
        session_title.setStyleSheet(card_title_qss())
        sc2.addWidget(session_title)
        self._session_track = QLabel("Sin reproducción reciente")
        self._session_track.setStyleSheet(card_desc_qss())
        self._session_track.setWordWrap(True)
        sc2.addWidget(self._session_track)
        sc2.addStretch()
        self._continue_btn = QPushButton("Continuar")
        self._continue_btn.setObjectName("homeContinueBtn")
        self._continue_btn.setCursor(Qt.PointingHandCursor)
        self._continue_btn.setStyleSheet(glass_button_qss("ghost"))
        self._continue_btn.clicked.connect(
            lambda: self.navigation_requested.emit("playback_hub"))
        sc2.addWidget(self._continue_btn)
        bottom.addWidget(self._session_card, 1)

        # Connections
        self._conn_card = AcrylicGlassFrame("homeConnCard", hover_shine=True)
        cc = QVBoxLayout(self._conn_card)
        cc.setContentsMargins(20, 16, 20, 16)
        cc.setSpacing(8)
        conn_title = QLabel("Servidores y conexiones")
        conn_title.setStyleSheet(card_title_qss())
        cc.addWidget(conn_title)
        self._conn_status = QLabel("")
        self._conn_status.setStyleSheet(card_desc_qss())
        self._conn_status.setWordWrap(True)
        cc.addWidget(self._conn_status)
        cc.addSpacing(4)
        self._conn_mms_hint = QLabel("» Michi Micro Server: centraliza tu biblioteca y transmite música")
        self._conn_mms_hint.setStyleSheet(
            "font-size: 11px; color: rgba(143,183,255,0.50);")
        cc.addWidget(self._conn_mms_hint)
        cc.addStretch()
        self._conn_btn = QPushButton("Abrir Conexiones")
        self._conn_btn.setCursor(Qt.PointingHandCursor)
        self._conn_btn.setStyleSheet(glass_button_qss("ghost"))
        self._conn_btn.clicked.connect(
            lambda: self.navigation_requested.emit("connections_hub"))
        cc.addWidget(self._conn_btn)
        bottom.addWidget(self._conn_card, 1)

        cl.addLayout(bottom)
        cl.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)
        self._apply_qss()

        for card in (self._lib_card, self._add_music_card, self._sugg_card,
                     self._session_card, self._conn_card):
            apply_card_shadow(card)

        self._selected_files: list[str] = []

    # ── Add Music handlers ──

    def _on_add_folder_clicked(self):
        path = QFileDialog.getExistingDirectory(
            self, "Añadir carpeta", os.path.expanduser("~"))
        if path:
            self.add_folder_requested.emit(path)

    def _on_add_files_clicked(self):
        from library.library_db import AUDIO_EXTS
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Añadir archivos", os.path.expanduser("~"),
            f"Audio ({' '.join('*' + e for e in AUDIO_EXTS)})")
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

    # ── Update sections ──

    def _update_library_status(self, stats: dict):
        songs = stats.get("total_songs", 0)
        if songs == 0:
            self._lib_status_msg.setText("Tu biblioteca necesita atención")
        else:
            self._lib_status_msg.setText("Tu biblioteca está lista")
        self._lib_counts.setText(
            f"{songs:,} canciones · {stats.get('total_albums', 0):,} álbumes"
            f" · {stats.get('total_artists', 0):,} artistas")

    def _update_add_music(self, stats: dict):
        songs = stats.get("total_songs", 0)
        if songs == 0:
            self._add_music_card.setVisible(True)
            self._add_music_title.setText("Añadir música")
            self._add_music_desc.setText(
                "Tu biblioteca está vacía. Agrega archivos o carpetas para empezar.")
        else:
            self._add_music_card.setVisible(True)
            self._add_music_title.setText("Añadir más música")
            self._add_music_desc.setText(
                "Importa nuevos archivos o carpetas a tu biblioteca.")

    def _update_suggestions(self, stats: dict):
        _clear_layout(self._sugg_content)
        actions = []

        missing = stats.get("missing_metadata", 0)
        if missing > 0:
            actions.append((f"Completar metadatos de {missing} canciones",
                            "metadata_editor", "accent"))

        songs = stats.get("total_songs", 0)
        if songs == 0:
            actions.append(("Añadir carpeta de música",
                            "library_hub", "primary"))

        if not actions:
            no_op = QLabel("No hay tareas importantes pendientes.")
            no_op.setStyleSheet(empty_state_qss() +
                "QLabel { color: rgba(255,255,255,0.56); font-size: 13px;"
                "  background: transparent; border: none; padding: 4px 0; }")
            self._sugg_content.addWidget(no_op)
        else:
            for text, target, kind in actions[:3]:
                btn = QPushButton(text)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setStyleSheet(glass_button_qss(kind))
                btn.clicked.connect(
                    lambda c=None, t=target: self.navigation_requested.emit(t))
                self._sugg_content.addWidget(btn)

        open_asst = QPushButton("Abrir Asistente")
        open_asst.setCursor(Qt.PointingHandCursor)
        open_asst.setStyleSheet(glass_chip_button_qss())
        open_asst.clicked.connect(
            lambda: self.navigation_requested.emit("assistant"))
        self._sugg_content.addWidget(open_asst)

    def _update_last_session(self):
        w = self._win or self.window()
        ref = getattr(w, '_current_ref', None) if w else None
        has_track = ref and (ref.title or ref.uri)
        if has_track:
            name = ref.title or os.path.basename(ref.uri)
            artist = getattr(ref, "artist", "") or ""
            text = f"{artist} — {name}" if artist else name
            self._session_track.setText(text)
            self._continue_btn.setVisible(True)
        else:
            self._session_track.setText("Sin reproducción reciente")
            self._continue_btn.setVisible(False)

    def _update_connections(self, servers: list, devices: list):
        lines = []
        if servers:
            srv = servers[0]
            srv_name = getattr(srv, 'name', None) or getattr(srv, 'server_type', 'Conectado')
            lines.append(f"Servidores: {len(servers)} ({srv_name})")
        else:
            lines.append("Sin servidores configurados")
        if devices:
            lines.append(f"Dispositivos: {len(devices)} detectado(s)")
        else:
            lines.append("Sin dispositivos detectados")
        self._conn_status.setText(" · ".join(lines))

    def _apply_qss(self):
        self.setStyleSheet("""
            QWidget#homePage { background: #090B11; }
            QScrollArea#homeScroll { background: transparent; border: none; }
            QWidget#homeContent { background: transparent; }
        """)


def _clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            _clear_layout(item.layout())
