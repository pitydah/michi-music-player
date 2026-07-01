"""Folder Browser — premium music explorer with health panel and maintenance features."""

import os
import random
import json
import logging

from PySide6.QtCore import Qt, Signal, QSize, QSettings
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QFileDialog, QHeaderView, QFrame, QMenu,
    QApplication, QMessageBox, QDialog, QFormLayout, QAbstractItemView,
    QDialogButtonBox,
)

from library.folder_index import list_folder_entries, list_audio_files
from library.folder_models import FolderEntry, FolderHealth
from ui.icons import get_qicon
from ui.central.central_styles import glass_button_qss, glass_card_qss
from core.file_manager_service import FileManagerService

logger = logging.getLogger("michi.folder_browser")

COVER_NAMES = frozenset({
    "cover.jpg", "cover.png", "folder.jpg", "folder.png",
    "front.jpg", "front.png", "album.jpg", "album.png",
    "art.jpg", "art.png", "portada.jpg", "portada.png",
})
SETTINGS_KEY_FAVS = "folder_browser/favorites"
SETTINGS_KEY_HIST = "folder_browser/history"

_HEALTH_LABELS = {
    "excellent": "Excelente", "good": "Buena", "attention": "Atención",
    "warning": "Advertencia", "critical": "Crítica",
}
_HEALTH_COLORS = {
    "excellent": "#4CAF50", "good": "#8BC34A", "attention": "#FFC107",
    "warning": "#FF9800", "critical": "#F44336",
}

_KIND_LABELS = {
    "folder": "Carpeta", "audio": "Canción", "unsupported_audio": "Audio no soportado",
    "cover": "Carátula", "playlist": "Playlist", "cue": "CUE", "log": "LOG",
    "text": "Texto", "unknown": "Desconocido", "error": "Error",
}
_KIND_ICONS = {
    "folder": "folder", "audio": "songs", "unsupported_audio": "audio",
    "cover": "sidebar_albums", "playlist": "sidebar_playlists",
    "cue": "sidebar_library", "log": "sidebar_library", "text": "sidebar_library",
}

_STATUS_LABELS = {
    "ok": "OK", "not_indexed": "No indexado", "incomplete": "Sin metadata",
    "missing_cover": "Sin carátula", "unsupported": "No soportado",
    "auxiliar": "Auxiliar", "unknown": "Desconocido", "error": "Error",
    "permission": "Permiso denegado",
}
_STATUS_COLORS = {
    "ok": "rgba(76,175,80,0.78)", "not_indexed": "rgba(255,193,7,0.78)",
    "incomplete": "rgba(255,152,0,0.78)", "error": "rgba(244,67,54,0.78)",
    "permission": "rgba(244,67,54,0.78)",
}


def _kind_icon_key(kind: str) -> str:
    return _KIND_ICONS.get(kind, "sidebar_library")


def _status_for_entry(e: FolderEntry) -> str:
    if e.kind == "error":
        return "error"
    if e.kind == "unsupported_audio":
        return "unsupported"
    if e.kind in ("cover", "playlist", "cue", "log", "text"):
        return "auxiliar"
    if e.kind != "audio":
        return "unknown"
    if not e.is_indexed:
        return "not_indexed"
    if e.problems:
        return "incomplete"
    return "ok"


class FolderBrowserWidget(QWidget):
    folder_selected = Signal(list)
    queue_requested = Signal(list)
    scan_requested = Signal(str)
    create_playlist_requested = Signal(str, list)
    folder_loaded = Signal(str)
    reindex_requested = Signal(str)
    add_library_root_requested = Signal(str)
    integrity_requested = Signal(str, bool)
    integrity_deep_requested = Signal(str)
    open_file_manager_requested = Signal(str)
    reveal_file_requested = Signal(str)
    open_terminal_requested = Signal(str)
    metadata_folder_requested = Signal(str)
    problem_report_requested = Signal(str)
    files_for_metadata = Signal(list)
    show_problem_report = Signal(object)
    safe_rename_requested = Signal(str)
    safe_move_requested = Signal(str)
    safe_rename_dialog = Signal(str)
    safe_move_dialog = Signal(str)
    audio_lab_requested = Signal(str)

    def __init__(self, parent=None, db=None):
        super().__init__(parent)
        self._root = os.path.expanduser("~")
        self._db = db
        self._db_connected = db is not None
        self._health: FolderHealth | None = None
        self._favorites: list[str] = []
        self._history: list[str] = []
        self._view_filter: str = "all"
        self._load_persistent()
        self._fm_name = FileManagerService.preferred_file_manager_name()
        self._health_svc = None

        self.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            " stop:0 rgba(20,22,28,0.94), stop:1 rgba(8,10,16,0.94));")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        self._build_toolbar(main_layout)
        self._build_splitter(main_layout)
        self._load(self._root)
        self._rebuild_favs_menu()
        self._rebuild_history_menu()

    def set_health_service(self, svc):
        self._health_svc = svc

    def _build_toolbar(self, layout):
        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("folderToolbar")
        toolbar_frame.setStyleSheet("""
            QFrame#folderToolbar {
                background: rgba(255,255,255,0.035);
                border: 1px solid rgba(255,255,255,0.075);
                border-radius: 14px;
            }
        """)
        tl = QHBoxLayout(toolbar_frame)
        tl.setContentsMargins(10, 8, 10, 8)
        tl.setSpacing(8)

        self._home_btn = QPushButton("Inicio")
        self._home_btn.setStyleSheet(glass_button_qss("secondary"))
        self._home_btn.clicked.connect(self._go_home)
        tl.addWidget(self._home_btn)

        self._up_btn = QPushButton("Subir")
        self._up_btn.setStyleSheet(glass_button_qss("secondary"))
        self._up_btn.clicked.connect(self._go_up)
        tl.addWidget(self._up_btn)

        self._breadcrumb = QLabel("")
        self._breadcrumb.setObjectName("breadcrumbLabel")
        self._breadcrumb.setStyleSheet(glass_card_qss("breadcrumbLabel") + """
            QLabel#breadcrumbLabel {
                color: rgba(255,255,255,0.86);
                padding: 7px 12px;
                font-size: 12px;
                font-weight: 600;
            }
        """)
        tl.addWidget(self._breadcrumb, 1)

        self._favs_menu = QMenu("Favoritos")
        self._favs_btn = QPushButton("Favoritos ▼")
        self._favs_btn.setStyleSheet(glass_button_qss("accent"))
        self._favs_btn.clicked.connect(lambda: self._favs_menu.exec(
            self._favs_btn.mapToGlobal(self._favs_btn.rect().bottomLeft())))
        tl.addWidget(self._favs_btn)

        self._hist_menu = QMenu("Recientes")
        self._hist_btn = QPushButton("\u231b Recientes ▼")
        self._hist_btn.setStyleSheet(glass_button_qss("secondary"))
        self._hist_btn.clicked.connect(lambda: self._hist_menu.exec(
            self._hist_btn.mapToGlobal(self._hist_btn.rect().bottomLeft())))
        tl.addWidget(self._hist_btn)

        tl.addStretch()

        self._play_btn = QPushButton("\u25b6 Reproducir")
        self._play_btn.setStyleSheet(glass_button_qss("accent"))
        self._play_btn.clicked.connect(self._play_folder)
        tl.addWidget(self._play_btn)

        self._shuffle_btn = QPushButton("\U0001f500 Aleatorio")
        self._shuffle_btn.setStyleSheet(glass_button_qss("secondary"))
        self._shuffle_btn.clicked.connect(self._shuffle_folder)
        tl.addWidget(self._shuffle_btn)

        self._queue_btn = QPushButton("+ Cola")
        self._queue_btn.setStyleSheet(glass_button_qss("secondary"))
        self._queue_btn.clicked.connect(self._queue_folder)
        tl.addWidget(self._queue_btn)

        self._scan_btn = QPushButton("Escanear")
        self._scan_btn.setStyleSheet(glass_button_qss("ghost"))
        self._scan_btn.clicked.connect(lambda: self.scan_requested.emit(self._root))
        self._scan_btn.setToolTip("Escanear carpeta para agregar archivos a la biblioteca")
        tl.addWidget(self._scan_btn)

        self._refresh_btn = QPushButton("Actualizar")
        self._refresh_btn.setStyleSheet(glass_button_qss("ghost"))
        self._refresh_btn.clicked.connect(lambda: self._load(self._root))
        tl.addWidget(self._refresh_btn)

        self._browse_btn = QPushButton("Abrir...")
        self._browse_btn.setStyleSheet(glass_button_qss("secondary"))
        self._browse_btn.clicked.connect(self._browse_folder)
        tl.addWidget(self._browse_btn)

        layout.addWidget(toolbar_frame)

    def _build_splitter(self, layout):
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(
            "QSplitter::handle { background: rgba(255,255,255,0.05); width: 1px; }")

        tree_frame = QFrame()
        tree_layout = QVBoxLayout(tree_frame)
        tree_layout.setContentsMargins(0, 0, 0, 0)

        # Filter bar
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(4)
        self._filter_buttons: dict[str, QPushButton] = {}
        for key, label in [("all", "Todo"), ("problems", "Problemas"),
                           ("not_indexed", "No indexados"), ("no_metadata", "Sin metadata"),
                           ("unsupported", "No soportados"), ("aux", "Auxiliares")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(key == "all")
            btn.setStyleSheet(self._filter_btn_qss(key == "all"))
            btn.clicked.connect(lambda checked, k=key: self._set_view_filter(k))
            self._filter_buttons[key] = btn
            filter_bar.addWidget(btn)
        filter_bar.addStretch()
        tree_layout.addLayout(filter_bar)

        self._tree = QTreeWidget()
        self._tree.setColumnCount(9)
        self._tree.setHeaderLabels(
            ["Nombre", "Estado", "Tipo", "Indexado", "Archivos",
             "M\u00fasica", "Duraci\u00f3n", "Formatos", "Ruta"])
        self._tree.setIndentation(22)
        self._tree.setIconSize(QSize(32, 32))
        self._tree.setFrameShape(QTreeWidget.NoFrame)
        self._tree.setAlternatingRowColors(True)
        self._tree.setAnimated(True)
        self._tree.setUniformRowHeights(True)
        self._tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self._tree.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tree.setAllColumnsShowFocus(True)
        self._tree.setRootIsDecorated(False)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.setStyleSheet("""
            QTreeWidget {
                background: rgba(255,255,255,0.025);
                alternate-background-color: rgba(255,255,255,0.014);
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.065);
                border-radius: 16px;
                outline: none;
                padding: 8px;
            }
            QTreeWidget::item {
                min-height: 42px;
                padding: 7px 10px;
                margin: 1px 4px;
                border-radius: 12px;
                color: rgba(255,255,255,0.86);
                background: transparent;
                border: 1px solid transparent;
            }
            QTreeWidget::item:hover {
                background: rgba(255,255,255,0.075);
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.10);
            }
            QTreeWidget::item:selected {
                background: rgba(255,255,255,0.105);
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.14);
            }
            QHeaderView::section {
                background: rgba(255,255,255,0.035);
                color: rgba(255,255,255,0.78);
                border: none;
                border-bottom: 1px solid rgba(255,255,255,0.06);
                padding: 8px 10px;
                font-size: 11.5px;
                font-weight: 700;
            }
            QScrollBar:vertical {
                background: rgba(255,255,255,0.025);
                width: 10px; margin: 4px; border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.18);
                min-height: 40px; border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255,255,255,0.28);
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px; background: transparent;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)
        hdr = self._tree.header()
        hdr.setStretchLastSection(True)
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 8):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self._tree.itemDoubleClicked.connect(self._on_item)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        tree_layout.addWidget(self._tree)

        bar = QHBoxLayout()
        self._status = QLabel("")
        self._status.setObjectName("folderStatus")
        self._status.setStyleSheet(
            "QLabel#folderStatus { color: rgba(255,255,255,0.62); font-size: 12px;"
            "font-weight: 500; padding: 8px 12px; }")
        bar.addWidget(self._status, 1)

        self._filter_btn = QPushButton("\U0001f50d")
        self._filter_btn.setStyleSheet(glass_button_qss("ghost"))
        self._filter_btn.setFixedWidth(36)
        self._filter_btn.setToolTip("Filtrar archivos")
        self._filter_btn.clicked.connect(self._toggle_filter)
        bar.addWidget(self._filter_btn)
        tree_layout.addLayout(bar)

        splitter.addWidget(tree_frame)
        self._build_health_panel(splitter)
        splitter.setSizes([600, 300])
        layout.addWidget(splitter, 1)

    @staticmethod
    def _filter_btn_qss(active: bool) -> str:
        if active:
            return ("QPushButton { background: rgba(143,183,255,0.22);"
                    " color: #8FB7FF; border: 1px solid rgba(143,183,255,0.35);"
                    " border-radius: 10px; padding: 5px 10px; font-size: 11px; font-weight: 600; }")
        return ("QPushButton { background: rgba(255,255,255,0.04);"
                " color: rgba(255,255,255,0.62); border: 1px solid rgba(255,255,255,0.06);"
                " border-radius: 10px; padding: 5px 10px; font-size: 11px; font-weight: 600; }"
                "QPushButton:hover { background: rgba(255,255,255,0.07); color: #fff; }")

    def _set_view_filter(self, key: str):
        self._view_filter = key
        for k, btn in self._filter_buttons.items():
            active = k == key
            btn.setChecked(active)
            btn.setStyleSheet(self._filter_btn_qss(active))
        self._apply_filters_to_tree()

    def _apply_filters_to_tree(self):
        vf = self._view_filter
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            kind = item.data(0, Qt.UserRole + 1)
            status = item.data(0, Qt.UserRole + 3)
            visible = True
            if vf == "problems":
                visible = status not in ("", "ok")
            elif vf == "not_indexed":
                visible = status == "not_indexed"
            elif vf == "no_metadata":
                visible = status == "incomplete"
            elif vf == "unsupported":
                visible = kind == "unsupported_audio"
            elif vf == "aux":
                visible = kind in ("cover", "playlist", "cue", "log", "text")
            item.setHidden(not visible)

    def _build_health_panel(self, splitter):
        self._details = QFrame()
        self._details.setFixedWidth(280)
        self._details.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.035);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 18px;
            }
        """)
        dl = QVBoxLayout(self._details)
        dl.setContentsMargins(16, 16, 16, 16)
        dl.setSpacing(10)

        self._health_cover = QLabel()
        self._health_cover.setFixedSize(248, 248)
        self._health_cover.setAlignment(Qt.AlignCenter)
        self._health_cover.setStyleSheet(
            "QLabel { background: rgba(255,255,255,0.03); border-radius: 12px; }")
        dl.addWidget(self._health_cover, alignment=Qt.AlignCenter)
        dl.addSpacing(4)

        self._health_name = QLabel("")
        self._health_name.setStyleSheet("font-size:14px;font-weight:650;color:#fff;")
        dl.addWidget(self._health_name)

        self._health_path = QLabel("")
        self._health_path.setWordWrap(True)
        self._health_path.setStyleSheet("font-size:10.5px;color:rgba(255,255,255,0.62);")
        dl.addWidget(self._health_path)

        self._health_score = QLabel("")
        self._health_score.setStyleSheet("font-size:13px;font-weight:700;color:#fff;")
        dl.addWidget(self._health_score)

        self._health_status_lbl = QLabel("")
        self._health_status_lbl.setStyleSheet("font-size:12px;font-weight:600;")
        dl.addWidget(self._health_status_lbl)

        self._health_stats = QLabel("")
        self._health_stats.setWordWrap(True)
        self._health_stats.setStyleSheet("font-size:11px;color:rgba(255,255,255,0.68);")
        dl.addWidget(self._health_stats)

        self._health_recs = QLabel("")
        self._health_recs.setWordWrap(True)
        self._health_recs.setStyleSheet("font-size:10.5px;color:rgba(255,255,255,0.72);"
                                         "padding: 4px 0;")
        dl.addWidget(self._health_recs)

        self._fav_toggle = QPushButton("Favorita")
        self._fav_toggle.setCheckable(True)
        self._fav_toggle.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.72);
              border: 1px solid rgba(255,255,255,0.08); border-radius: 10px;
              padding: 7px; font-size: 12px; font-weight: 600; }
            QPushButton:hover { background: rgba(255,255,255,0.08); color: #fff; }
            QPushButton:checked { color: #fff; background: rgba(255,255,255,0.10); }
        """)
        self._fav_toggle.clicked.connect(self._toggle_favorite)
        dl.addWidget(self._fav_toggle)
        dl.addSpacing(6)

        action_style = """
            QPushButton { background: rgba(255,255,255,0.05);
              border: 1px solid rgba(255,255,255,0.08); border-radius: 10px;
              padding: 6px 12px; font-size: 11px; font-weight: 600;
              color: rgba(255,255,255,0.78); }
            QPushButton:hover { background: rgba(255,255,255,0.08); color: #fff; }
        """
        self._actions_widget = QFrame()
        al = QVBoxLayout(self._actions_widget)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(6)

        r1 = QHBoxLayout()
        self._btn_scan = QPushButton("Escanear")
        self._btn_scan.setStyleSheet(action_style)
        self._btn_scan.clicked.connect(lambda: self.scan_requested.emit(self._root))
        r1.addWidget(self._btn_scan)
        self._btn_reindex = QPushButton("Reindexar")
        self._btn_reindex.setStyleSheet(action_style)
        self._btn_reindex.clicked.connect(lambda: self.reindex_requested.emit(self._root))
        r1.addWidget(self._btn_reindex)
        al.addLayout(r1)

        r2 = QHBoxLayout()
        self._btn_add_root = QPushButton("+ Biblioteca")
        self._btn_add_root.setStyleSheet(action_style)
        self._btn_add_root.clicked.connect(
            lambda: self.add_library_root_requested.emit(self._root))
        r2.addWidget(self._btn_add_root)
        self._btn_verify = QPushButton("Verificar")
        self._btn_verify.setStyleSheet(action_style)
        self._btn_verify.clicked.connect(
            lambda: self.integrity_requested.emit(self._root, False))
        r2.addWidget(self._btn_verify)
        self._btn_verify_deep = QPushButton("Verif. profunda")
        self._btn_verify_deep.setStyleSheet(action_style)
        self._btn_verify_deep.clicked.connect(
            lambda: self.integrity_deep_requested.emit(self._root))
        r2.addWidget(self._btn_verify_deep)
        al.addLayout(r2)

        r3 = QHBoxLayout()
        self._btn_problems = QPushButton("Problemas")
        self._btn_problems.setStyleSheet(action_style)
        self._btn_problems.clicked.connect(
            lambda: self.problem_report_requested.emit(self._root))
        r3.addWidget(self._btn_problems)
        self._btn_metadata = QPushButton("Metadata")
        self._btn_metadata.setStyleSheet(action_style)
        self._btn_metadata.clicked.connect(
            lambda: self.metadata_folder_requested.emit(self._root))
        r3.addWidget(self._btn_metadata)
        self._btn_audio_lab = QPushButton("Audio Lab")
        self._btn_audio_lab.setStyleSheet(action_style)
        self._btn_audio_lab.setVisible(False)
        self._btn_audio_lab.clicked.connect(
            lambda: self.audio_lab_requested.emit(self._root))
        r3.addWidget(self._btn_audio_lab)
        al.addLayout(r3)

        r4 = QHBoxLayout()
        self._btn_open_fm = QPushButton(f"Abrir en {self._fm_name}")
        self._btn_open_fm.setStyleSheet(action_style)
        self._btn_open_fm.clicked.connect(
            lambda: self.open_file_manager_requested.emit(self._root))
        r4.addWidget(self._btn_open_fm)
        self._btn_terminal = QPushButton("Terminal")
        self._btn_terminal.setStyleSheet(action_style)
        self._btn_terminal.clicked.connect(
            lambda: self.open_terminal_requested.emit(self._root))
        r4.addWidget(self._btn_terminal)
        al.addLayout(r4)

        dl.addWidget(self._actions_widget)
        dl.addStretch()
        splitter.addWidget(self._details)

    def update_health(self, health: FolderHealth | None):
        self._health = health
        if not health:
            self._health_score.setText("")
            self._health_status_lbl.setText("")
            self._health_stats.setText("")
            self._health_recs.setText("")
            return
        self._health_score.setText(f"Salud: {health.score}/100")
        color = _HEALTH_COLORS.get(health.status, "#888")
        label = _HEALTH_LABELS.get(health.status, "Desconocido")
        self._health_status_lbl.setText(f"Estado: {label}")
        self._health_status_lbl.setStyleSheet(
            "font-size:12px;font-weight:600;color:{};".format(color))
        stats = []
        if health.audio_count:
            stats.append(f"{health.audio_count} audios")
        if health.indexed_audio_count:
            stats.append(f"{health.indexed_audio_count} indexados")
        if health.unindexed_audio_count:
            stats.append(f"{health.unindexed_audio_count} sin indexar")
        if health.missing_metadata_count:
            stats.append(f"{health.missing_metadata_count} sin metadata")
        if health.subfolder_count:
            stats.append(f"{health.subfolder_count} subcarpetas")
        if health.unsupported_audio_count:
            stats.append(f"{health.unsupported_audio_count} no soportados")
        if health.formats:
            stats.append(f"Formatos: {', '.join(health.formats)}")
        self._health_stats.setText(" \u00b7 ".join(stats))

        # Recommendations inline
        if health.recommended_actions:
            rec_lines = []
            for r in health.recommended_actions[:3]:
                rec_lines.append(f"\u2022 {r.label}: {r.description}")
            self._health_recs.setText("\n".join(rec_lines))
        else:
            self._health_recs.setText("Sin recomendaciones pendientes")

        inside_lib = health.is_inside_library_root or health.is_library_root
        self._btn_add_root.setVisible(health.exists and not inside_lib)
        self._btn_scan.setEnabled(inside_lib)
        self._btn_reindex.setEnabled(inside_lib)

    # ── Persistent storage ──
    def _load_persistent(self):
        s = QSettings("MichiMusicPlayer", "FolderBrowser")
        try:
            self._favorites = json.loads(s.value(SETTINGS_KEY_FAVS, "[]"))
        except Exception:
            self._favorites = []
        try:
            self._history = json.loads(s.value(SETTINGS_KEY_HIST, "[]"))
        except Exception:
            self._history = []

    def _save_favorites(self):
        QSettings("MichiMusicPlayer", "FolderBrowser").setValue(
            SETTINGS_KEY_FAVS, json.dumps(self._favorites))

    def _save_history(self):
        QSettings("MichiMusicPlayer", "FolderBrowser").setValue(
            SETTINGS_KEY_HIST, json.dumps(self._history))

    def _add_to_history(self, path: str):
        if path in self._history:
            self._history.remove(path)
        self._history.insert(0, path)
        self._history = self._history[:15]
        self._save_history()
        self._rebuild_history_menu()

    def _rebuild_favs_menu(self):
        self._favs_menu.clear()
        if not self._favorites:
            a = self._favs_menu.addAction("(vac\u00edo)")
            a.setEnabled(False)
        else:
            for p in list(self._favorites):
                name = os.path.basename(p) or p
                self._favs_menu.addAction(name, lambda path=p: self._load(path))
            self._favs_menu.addSeparator()
            for p in list(self._favorites):
                name = os.path.basename(p) or p
                self._favs_menu.addAction(f"\u2715 {name}",
                    lambda path=p: self._remove_favorite(path))

    def _rebuild_history_menu(self):
        self._hist_menu.clear()
        if not self._history:
            a = self._hist_menu.addAction("(vac\u00edo)")
            a.setEnabled(False)
        else:
            for p in self._history:
                name = os.path.basename(p) or p
                self._hist_menu.addAction(name, lambda path=p: self._load(path))
            self._hist_menu.addSeparator()
            self._hist_menu.addAction("Limpiar historial",
                                       lambda: self._clear_history())

    def _clear_history(self):
        self._history.clear()
        self._save_history()
        self._rebuild_history_menu()

    def _toggle_favorite(self):
        path = self._root
        if path in self._favorites:
            self._favorites.remove(path)
        else:
            self._favorites.append(path)
        self._save_favorites()
        self._fav_toggle.setChecked(path in self._favorites)
        self._rebuild_favs_menu()

    def _remove_favorite(self, path: str):
        if path in self._favorites:
            self._favorites.remove(path)
            self._save_favorites()
            self._rebuild_favs_menu()
            if path == self._root:
                self._fav_toggle.setChecked(False)

    # ── Filter / Search ──
    def set_filter(self, text: str):
        text = text.lower()
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            name = item.text(0).lower()
            path = item.text(8).lower()
            visible = not text or text in name or text in path
            item.setHidden(not visible)

    def _toggle_filter(self):
        from PySide6.QtWidgets import QLineEdit
        dlg = QDialog(self)
        dlg.setWindowTitle("Filtrar archivos")
        dlg.setStyleSheet("""
            QDialog { background: #181C25; border-radius: 14px; }
            QLineEdit {
                background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.12);
                border-radius: 8px; color: #fff; font-size: 14px; padding: 8px 12px;
                min-width: 300px;
            }
        """)
        layout = QVBoxLayout(dlg)
        inp = QLineEdit()
        inp.setPlaceholderText("Filtrar por nombre...")
        layout.addWidget(inp)
        inp.textChanged.connect(self.set_filter)
        inp.returnPressed.connect(dlg.accept)
        dlg.exec()

    # ── Navigation ──
    def _load(self, path: str):
        self._tree.clear()
        self._root = path
        self._breadcrumb.setText(self._format_breadcrumb(path))
        self._add_to_history(path)
        self._fav_toggle.setChecked(path in self._favorites)
        self._health_name.setText(os.path.basename(path) or path)
        self._health_path.setText(path)
        self._load_cover(path)
        self.folder_loaded.emit(path)

        try:
            entries = list_folder_entries(path)
        except Exception:
            entries = []
        self._load_entries(entries)
        audio_count = sum(1 for e in entries if e.kind == "audio")
        folder_count = sum(1 for e in entries if e.kind == "folder")
        self._status.setText(
            f"{folder_count} carpetas \u00b7 {audio_count} canciones"
            f" \u00b7 {len(entries)} entradas")

    def _load_entries(self, entries: list[FolderEntry]):
        for e in entries:
            item = QTreeWidgetItem()
            sv = _status_for_entry(e)

            item.setIcon(0, get_qicon(_kind_icon_key(e.kind), size=24))
            item.setText(0, e.name)
            item.setText(1, _STATUS_LABELS.get(sv, sv))
            item.setText(2, _KIND_LABELS.get(e.kind, e.kind))
            item.setText(3, "S\u00ed" if e.is_indexed else "No" if e.kind == "audio" else "\u2014")
            item.setText(4, "\u2014")
            item.setText(5, "\u2014")
            item.setText(6, self._format_duration(e.duration) if e.duration else "")
            item.setText(7, e.format_label or "")
            item.setText(8, e.path)
            item.setData(0, Qt.UserRole, e.path)
            item.setData(0, Qt.UserRole + 1, e.kind if e.kind == "folder" else "file")
            item.setData(0, Qt.UserRole + 3, sv)
            if e.kind == "folder":
                sub_audio = len(list_audio_files(e.path))
                item.setText(5, str(sub_audio) if sub_audio else "\u2014")
            self._tree.addTopLevelItem(item)
        self._apply_filters_to_tree()

    def _load_cover(self, path: str):
        pix = None
        if self._db and self._db_connected:
            try:
                from library.album_key import make_album_key
                folder_name = os.path.basename(path)
                artist_name = os.path.basename(os.path.dirname(path))
                ak = make_album_key(artist_name, artist_name, folder_name)
                cached = self._db.get_album_art_cache(ak)
                if cached:
                    mime, data = cached
                    tpix = QPixmap()
                    if tpix.loadFromData(data):
                        pix = tpix
            except Exception:
                pass
        if pix is None:
            cover = self._find_cover(path)
            if cover:
                tpix = QPixmap(cover)
                if not tpix.isNull():
                    pix = tpix
        if pix:
            pix = pix.scaled(244, 244, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._health_cover.setPixmap(pix)
        else:
            self._health_cover.setText("\u266a")

    @staticmethod
    def _find_cover(directory: str) -> str | None:
        for name in COVER_NAMES:
            p = os.path.join(directory, name)
            if os.path.isfile(p):
                return p
        return None

    @staticmethod
    def _format_breadcrumb(path: str) -> str:
        home = os.path.expanduser("~")
        if path.startswith(home):
            rel = os.path.relpath(path, home)
            if rel == ".":
                return "Inicio"
            parts = ["Inicio"] + rel.split(os.sep)
        else:
            parts = path.strip(os.sep).split(os.sep)
        if len(parts) > 4:
            parts = ["\u2026"] + parts[-3:]
        return " / ".join(parts)

    @staticmethod
    def _format_duration(seconds: float) -> str:
        if not seconds:
            return ""
        m = int(seconds // 60)
        s = int(seconds % 60)
        if seconds >= 3600:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    def _on_item(self, item, col):
        data_role = item.data(0, Qt.UserRole + 1)
        path = item.data(0, Qt.UserRole)
        if data_role == "folder":
            self._load(path)
        elif data_role == "file":
            self.folder_selected.emit([path])

    # ── Toolbar actions ──
    def _play_folder(self):
        files = list_audio_files(self._root)
        if files:
            self.folder_selected.emit(files)

    def _shuffle_folder(self):
        files = list_audio_files(self._root)
        if files:
            random.shuffle(files)
            self.folder_selected.emit(files)

    def _queue_folder(self):
        files = list_audio_files(self._root)
        if files:
            self.queue_requested.emit(files)

    def _go_up(self):
        parent = os.path.dirname(self._root)
        if parent and parent != self._root:
            self._load(parent)

    def _go_home(self):
        self._load(os.path.expanduser("~"))

    def _browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Abrir carpeta", self._root)
        if path:
            self._load(path)

    # ── Context menu ──
    def _on_context_menu(self, pos):
        item = self._tree.itemAt(pos)
        if not item:
            return
        path = item.data(0, Qt.UserRole)
        data_role = item.data(0, Qt.UserRole + 1)
        kind = item.data(0, Qt.UserRole + 1)
        if data_role == "file":
            kind = item.text(2)
        menu = QMenu(self)

        if kind == "folder" or data_role == "folder":
            menu.addAction("Abrir carpeta", lambda: self._load(path))
            menu.addSeparator()
            menu.addAction("\u25b6 Reproducir carpeta", lambda: self._play_path_folder(path))
            menu.addAction("\U0001f500 Aleatorio", lambda: self._shuffle_path_folder(path))
            menu.addAction("+ A\u00f1adir a cola", lambda: self._queue_path_folder(path))
            menu.addSeparator()
            menu.addAction("Crear playlist", lambda: self._create_playlist(path))
            menu.addAction("Escanear carpeta", lambda: self.scan_requested.emit(path))
            menu.addAction("Reindexar metadata", lambda: self.reindex_requested.emit(path))
            menu.addAction("+ Agregar a biblioteca",
                           lambda: self.add_library_root_requested.emit(path))
            menu.addSeparator()
            menu.addAction("Verificar integridad",
                           lambda: self.integrity_requested.emit(path, False))
            menu.addAction("Ver problemas",
                           lambda: self.problem_report_requested.emit(path))
            menu.addAction("Editar metadata de carpeta",
                           lambda: self.metadata_folder_requested.emit(path))
            menu.addSeparator()
            menu.addAction(f"Abrir en {self._fm_name}",
                           lambda: self.open_file_manager_requested.emit(path))
            menu.addAction("Abrir terminal aqu\u00ed",
                           lambda: self.open_terminal_requested.emit(path))
            menu.addSeparator()
            menu.addAction("\u2605 Favorita", lambda: self._fav_folder(path))
            menu.addAction("Copiar ruta", lambda: QApplication.clipboard().setText(path))

        elif data_role == "file":
            type_label = kind or "Archivo"
            if type_label == "Canci\u00f3n":
                menu.addAction("\u25b6 Reproducir", lambda: self.folder_selected.emit([path]))
                menu.addAction("+ A\u00f1adir a cola", lambda: self.queue_requested.emit([path]))
                menu.addSeparator()
                menu.addAction("Informaci\u00f3n t\u00e9cnica", lambda: self._show_audio_info(path))
            else:
                menu.addAction("Informaci\u00f3n", lambda: self._show_audio_info(path))
            menu.addSeparator()
            menu.addAction(f"Revelar en {self._fm_name}",
                           lambda: self.reveal_file_requested.emit(path))
            menu.addAction("Copiar ruta", lambda: QApplication.clipboard().setText(path))

        menu.exec(self._tree.viewport().mapToGlobal(pos))

    def _play_path_folder(self, path):
        files = list_audio_files(path)
        if files:
            self.folder_selected.emit(files)

    def _shuffle_path_folder(self, path):
        files = list_audio_files(path)
        if files:
            random.shuffle(files)
            self.folder_selected.emit(files)

    def _queue_path_folder(self, path):
        files = list_audio_files(path)
        if files:
            self.queue_requested.emit(files)

    def _create_playlist(self, path):
        name = os.path.basename(path)
        files = list_audio_files(path)
        if files:
            self.create_playlist_requested.emit(name, files)
        else:
            QMessageBox.information(
                self, "Crear playlist",
                "No se encontraron archivos de audio en esta carpeta.")

    def _fav_folder(self, path):
        self._load(path)
        if path not in self._favorites:
            self._favorites.append(path)
            self._save_favorites()
            self._rebuild_favs_menu()
            self._fav_toggle.setChecked(True)

    @staticmethod
    def _show_audio_info(filepath: str):
        from PySide6.QtWidgets import QLineEdit
        dlg = QDialog()
        dlg.setWindowTitle("Informaci\u00f3n de audio")
        dlg.setMinimumWidth(420)
        dlg.setStyleSheet("""
            QDialog { background: #181C25; border-radius: 14px; }
            QLabel { color: rgba(255,255,255,0.55); font-size: 11px; }
            QLineEdit {
                background: rgba(255,255,255,0.04); border: none; border-radius: 6px;
                color: rgba(255,255,255,0.78); font-size: 12px; padding: 6px 10px;
            }
        """)
        layout = QVBoxLayout(dlg)
        form = QFormLayout()

        def add_row(label, value):
            le = QLineEdit(str(value))
            le.setReadOnly(True)
            form.addRow(f"{label}:", le)

        name = os.path.basename(filepath)
        ext = os.path.splitext(filepath)[1]
        add_row("Archivo", name)
        add_row("Formato", ext.upper().lstrip("."))

        try:
            st = os.stat(filepath)
            add_row("Tama\u00f1o", f"{st.st_size / (1024*1024):.2f} MB")
            from datetime import datetime
            mtime = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")
            add_row("Modificado", mtime)
            import stat as stat_mod
            mode = stat_mod.filemode(st.st_mode)
            add_row("Permisos", mode)
        except OSError:
            pass

        add_row("Ruta", filepath)
        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok)
        btns.accepted.connect(dlg.accept)
        layout.addWidget(btns)
        dlg.exec()

    def set_db(self, db):
        self._db = db
        self._db_connected = db is not None

    def set_audio_lab_available(self, available: bool):
        if hasattr(self, '_btn_audio_lab'):
            self._btn_audio_lab.setVisible(available)

    def set_watcher_active(self, active: bool):
        if not hasattr(self, '_scan_btn') or not self._scan_btn:
            return
        if active:
            self._scan_btn.setText("\u25cf Escanear")
            self._scan_btn.setToolTip(
                "Monitoreo en tiempo real activo. Escanear fuerza re-escaneo.")
        else:
            self._scan_btn.setText("Escanear")
            self._scan_btn.setToolTip("Escanear carpeta para agregar archivos a la biblioteca")

    @property
    def visible_count(self):
        count = 0
        for i in range(self._tree.topLevelItemCount()):
            if not self._tree.topLevelItem(i).isHidden():
                count += 1
        return count
