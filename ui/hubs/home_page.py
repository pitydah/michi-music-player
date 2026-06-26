"""HomePage — clean dashboard: library status, assistant, last session, connections."""

from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QPushButton,
)

from ui.central.central_styles import (
    glass_card_qss, glass_button_qss,
    card_title_qss,
    page_title_qss, page_subtitle_qss,
)


class HomePage(QWidget):
    navigation_requested = Signal(str)
    refresh_requested = Signal()

    def __init__(self, db=None, playback=None, window=None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("homePage")
        self._db = db
        self._playback = playback
        self._win = window
        self._build_ui()

    # ── Public API ──

    def refresh(self, items=None, servers=None, devices=None):
        """Update all sections with fresh data."""
        stats = self._get_stats()
        self._update_library_status(stats)
        self._update_assistant(stats, items or [])
        self._update_last_session()
        self._update_connections(servers or [], devices or [])

    # ── Stats ──

    def _get_stats(self) -> dict:
        stats = {"total_songs": 0, "total_artists": 0, "total_albums": 0}
        try:
            if self._db and hasattr(self._db, "get_stats"):
                st = self._db.get_stats()
                stats["total_songs"] = st.get("total", 0)
            if self._db and hasattr(self._db, "get_all"):
                items = self._db.get_all() or []
                artists = set()
                albums = set()
                for item in items:
                    a = str(getattr(item, "artist", "") or "").strip().lower()
                    artists.add(a or "artista desconocido")
                    al = str(getattr(item, "album", "") or "").strip().lower()
                    albums.add(al or "sin album")
                stats["total_artists"] = len(artists)
                stats["total_albums"] = len(albums)
        except Exception:
            pass
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
        cl.setContentsMargins(40, 32, 40, 40)
        cl.setSpacing(20)

        # Title
        title = QLabel("Inicio")
        title.setObjectName("homeTitle")
        cl.addWidget(title)

        # ── 1. Library Status ──
        self._lib_card = QFrame()
        self._lib_card.setObjectName("homeLibCard")
        lc = QVBoxLayout(self._lib_card)
        lc.setContentsMargins(24, 20, 24, 20)
        lc.setSpacing(4)
        self._lib_status_msg = QLabel("Tu biblioteca está lista")
        self._lib_status_msg.setObjectName("libStatusMsg")
        self._lib_status_msg.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.92); font-size: 15px;"
            "  font-weight: 600; background: transparent; border: none; }")
        lc.addWidget(self._lib_status_msg)
        self._lib_counts = QLabel("")
        self._lib_counts.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.56); font-size: 12px;"
            "  background: transparent; border: none; }")
        lc.addWidget(self._lib_counts)
        self._lib_card.setStyleSheet(glass_card_qss("homeLibCard", "elevated"))
        cl.addWidget(self._lib_card)

        # ── 2. Michi Assistant ──
        self._asst_card = QFrame()
        self._asst_card.setObjectName("homeAsstCard")
        ac = QVBoxLayout(self._asst_card)
        ac.setContentsMargins(24, 16, 24, 16)
        ac.setSpacing(8)
        asst_title = QLabel("Michi Asistente")
        asst_title.setStyleSheet(card_title_qss())
        ac.addWidget(asst_title)
        self._asst_content = QVBoxLayout()
        self._asst_content.setSpacing(4)
        ac.addLayout(self._asst_content)
        self._asst_card.setStyleSheet(glass_card_qss("homeAsstCard", "elevated"))
        cl.addWidget(self._asst_card)

        # ── 3. Last Session + Connections (side by side) ──
        bottom = QHBoxLayout()
        bottom.setSpacing(16)

        # Last session
        self._session_card = QFrame()
        self._session_card.setObjectName("homeSessionCard")
        sc = QVBoxLayout(self._session_card)
        sc.setContentsMargins(20, 16, 20, 16)
        sc.setSpacing(8)
        session_title = QLabel("Última sesión")
        session_title.setStyleSheet(card_title_qss())
        sc.addWidget(session_title)
        self._session_track = QLabel("Sin reproducción reciente")
        self._session_track.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.56); font-size: 12px;"
            "  background: transparent; border: none; }")
        self._session_track.setWordWrap(True)
        sc.addWidget(self._session_track)
        sc.addStretch()
        self._continue_btn = QPushButton("Continuar")
        self._continue_btn.setObjectName("homeContinueBtn")
        self._continue_btn.setCursor(Qt.PointingHandCursor)
        self._continue_btn.setStyleSheet(glass_button_qss("ghost"))
        self._continue_btn.clicked.connect(
            lambda: self.navigation_requested.emit("playback_hub"))
        sc.addWidget(self._continue_btn)
        self._session_card.setStyleSheet(glass_card_qss("homeSessionCard", "elevated"))
        bottom.addWidget(self._session_card, 1)

        # Connections
        self._conn_card = QFrame()
        self._conn_card.setObjectName("homeConnCard")
        cc = QVBoxLayout(self._conn_card)
        cc.setContentsMargins(20, 16, 20, 16)
        cc.setSpacing(8)
        conn_title = QLabel("Conexiones")
        conn_title.setStyleSheet(card_title_qss())
        cc.addWidget(conn_title)
        self._conn_status = QLabel("")
        self._conn_status.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.56); font-size: 12px;"
            "  background: transparent; border: none; }")
        self._conn_status.setWordWrap(True)
        cc.addWidget(self._conn_status)
        cc.addStretch()
        self._conn_btn = QPushButton("Abrir Conexiones")
        self._conn_btn.setCursor(Qt.PointingHandCursor)
        self._conn_btn.setStyleSheet(glass_button_qss("ghost"))
        self._conn_btn.clicked.connect(
            lambda: self.navigation_requested.emit("connections_hub"))
        cc.addWidget(self._conn_btn)
        self._conn_card.setStyleSheet(glass_card_qss("homeConnCard", "elevated"))
        bottom.addWidget(self._conn_card, 1)

        cl.addLayout(bottom)
        cl.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)
        self._apply_qss()

    # ── Update sections ──

    def _update_library_status(self, stats: dict):
        songs = stats.get("total_songs", 0)
        if songs == 0:
            self._lib_status_msg.setText("Tu biblioteca necesita atención")
            self._lib_card.setStyleSheet(glass_card_qss("homeLibCard", "accent"))
        else:
            self._lib_status_msg.setText("Tu biblioteca está lista")
            self._lib_card.setStyleSheet(glass_card_qss("homeLibCard", "elevated"))
        self._lib_counts.setText(
            f"{songs:,} canciones · {stats['total_albums']:,} álbumes"
            f" · {stats['total_artists']:,} artistas")

    def _update_assistant(self, stats: dict, items: list):
        _clear_layout(self._asst_content)
        actions = []

        # Missing metadata
        missing = sum(1 for i in items
            if not getattr(i, "title", "") or getattr(i, "title", "") == getattr(i, "filename", "")
            or not getattr(i, "artist", "") or not getattr(i, "album", ""))
        if missing > 0:
            actions.append((f"Completar metadatos de {missing} canciones",
                            "metadata_editor", "accent"))

        # Missing covers - approximate check
        missing_covers = 0
        if items:
            albums_with_covers = set()
            for i in items:
                al = getattr(i, "album", "") or "Sin álbum"
                if al not in albums_with_covers:
                    albums_with_covers.add(al)
                    if not hasattr(i, "cover_path") or not getattr(i, "cover_path", ""):
                        missing_covers += 1
        if missing_covers > 0:
            actions.append((f"Buscar carátulas para {missing_covers} álbumes",
                            "albums", "secondary"))

        # Scan pending
        songs = stats.get("total_songs", 0)
        if songs == 0:
            actions.append(("Añadir carpeta de música",
                            "library", "primary"))
        elif missing == 0 and missing_covers <= 3:
            pass  # nothing needed

        if not actions:
            no_op = QLabel("No hay tareas importantes pendientes.")
            no_op.setStyleSheet(
                "QLabel { color: rgba(255,255,255,0.42); font-size: 12px;"
                "  background: transparent; border: none; padding: 4px 0; }")
            self._asst_content.addWidget(no_op)
        else:
            for text, target, kind in actions[:3]:
                btn = QPushButton(text)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setStyleSheet(glass_button_qss(kind))
                btn.clicked.connect(
                    lambda c=None, t=target: self.navigation_requested.emit(t))
                self._asst_content.addWidget(btn)

    def _update_last_session(self):
        w = self._win or self.window()
        ref = getattr(w, '_current_ref', None) if w else None
        if ref and (ref.title or ref.uri):
            name = ref.title or os.path.basename(ref.uri)
            artist = getattr(ref, "artist", "") or ""
            text = f"{artist} — {name}" if artist else name
            self._session_track.setText(text)
            self._continue_btn.setVisible(True)
        else:
            self._session_track.setText("Sin reproducción reciente")
            self._continue_btn.setVisible(False)
        if hasattr(self, '_last_playback_state') and self._last_playback_state == "playing":
            self._continue_btn.setText("Continuar")

    def _update_connections(self, servers: list, devices: list):
        lines = []
        if servers:
            lines.append(f"Servidor: {servers[0].name if hasattr(servers[0], 'name') else 'Conectado'}")
        else:
            lines.append("Servidor: no configurado")
        if devices:
            lines.append(f"Dispositivos: {len(devices)} detectado(s)")
        else:
            lines.append("Dispositivos: no detectados")
        self._conn_status.setText("\n".join(lines))

    # ── QSS ──

    def _apply_qss(self):
        self.setStyleSheet(
            page_title_qss() + page_subtitle_qss() + """
            QWidget#homePage { background: #090B11; }
            QScrollArea#homeScroll { background: transparent; border: none; }
            QWidget#homeContent { background: transparent; }
            QLabel#homeTitle { color: rgba(255,255,255,0.92); font-size: 22px; font-weight: 700; }
        """)


def _clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            _clear_layout(item.layout())
