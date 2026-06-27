"""Folder Browser — premium music explorer with details panel and advanced features."""

import os
import random
import stat
import subprocess
import json

from PySide6.QtCore import Qt, Signal, QSize, QSettings
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QFileDialog, QHeaderView, QFrame, QMenu,
    QApplication, QMessageBox, QDialog, QFormLayout, QAbstractItemView,
    QDialogButtonBox,
)

from library.folder_index import list_audio_files, list_subfolders
from ui.icons import get_qicon
from ui.central.central_styles import glass_button_qss, glass_card_qss

COVER_NAMES = ("cover.jpg", "cover.png", "folder.jpg", "folder.png",
               "front.jpg", "front.png", "album.jpg", "album.png",
               "art.jpg", "art.png", "portada.jpg", "portada.png")
SETTINGS_KEY_FAVS = "folder_browser/favorites"
SETTINGS_KEY_HIST = "folder_browser/history"


class FolderBrowserWidget(QWidget):
    folder_selected = Signal(list)              # filepaths to play
    queue_requested = Signal(list)              # filepaths to queue
    scan_requested = Signal(str)               # directory to scan
    create_playlist_requested = Signal(str, list)  # name, filepaths

    def __init__(self, parent=None, db=None):
        super().__init__(parent)
        self._root = os.path.expanduser("~")
        self._db = db
        self._db_connected = db is not None
        self._favorites: list[str] = []
        self._history: list[str] = []
        self._load_persistent()
        self.set_watcher_active(False)

        self.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            " stop:0 rgba(20,22,28,0.94), stop:1 rgba(8,10,16,0.94));")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # ── Toolbar ──
        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("folderToolbar")
        toolbar_frame.setStyleSheet("""
            QFrame#folderToolbar {
                background: rgba(255,255,255,0.035);
                border: 1px solid rgba(255,255,255,0.075);
                border-radius: 14px;
            }
        """)
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 8, 10, 8)
        toolbar_layout.setSpacing(8)

        self._home_btn = QPushButton("Inicio")
        self._home_btn.setStyleSheet(glass_button_qss("secondary"))
        self._home_btn.clicked.connect(self._go_home)
        toolbar_layout.addWidget(self._home_btn)

        self._up_btn = QPushButton("Subir")
        self._up_btn.setStyleSheet(glass_button_qss("secondary"))
        self._up_btn.clicked.connect(self._go_up)
        toolbar_layout.addWidget(self._up_btn)

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
        toolbar_layout.addWidget(self._breadcrumb, 1)

        # Favorites dropdown
        self._favs_menu = QMenu("Favoritos")
        self._favs_btn = QPushButton("Favoritos ▼")
        self._favs_btn.setStyleSheet(glass_button_qss("accent"))
        self._favs_btn.clicked.connect(lambda: self._favs_menu.exec(
            self._favs_btn.mapToGlobal(self._favs_btn.rect().bottomLeft())))
        toolbar_layout.addWidget(self._favs_btn)

        # History dropdown
        self._hist_menu = QMenu("Recientes")
        self._hist_btn = QPushButton("⌛ Recientes ▼")
        self._hist_btn.setStyleSheet(glass_button_qss("secondary"))
        self._hist_btn.clicked.connect(lambda: self._hist_menu.exec(
            self._hist_btn.mapToGlobal(self._hist_btn.rect().bottomLeft())))
        toolbar_layout.addWidget(self._hist_btn)

        toolbar_layout.addStretch()

        self._play_btn = QPushButton("▶ Reproducir carpeta")
        self._play_btn.setStyleSheet(glass_button_qss("accent"))
        self._play_btn.clicked.connect(self._play_folder)
        toolbar_layout.addWidget(self._play_btn)

        self._shuffle_btn = QPushButton("🔀 Aleatorio")
        self._shuffle_btn.setStyleSheet(glass_button_qss("secondary"))
        self._shuffle_btn.clicked.connect(self._shuffle_folder)
        toolbar_layout.addWidget(self._shuffle_btn)

        self._queue_btn = QPushButton("+ Añadir a cola")
        self._queue_btn.setStyleSheet(glass_button_qss("secondary"))
        self._queue_btn.clicked.connect(self._queue_folder)
        toolbar_layout.addWidget(self._queue_btn)

        self._scan_btn = QPushButton("Escanear")
        self._scan_btn.setStyleSheet(glass_button_qss("ghost"))
        self._scan_btn.clicked.connect(lambda: self.scan_requested.emit(self._root))
        self._scan_btn.setToolTip("Escanear carpeta para agregar archivos a la biblioteca")
        toolbar_layout.addWidget(self._scan_btn)

        self._refresh_btn = QPushButton("Actualizar")
        self._refresh_btn.setStyleSheet(glass_button_qss("ghost"))
        self._refresh_btn.clicked.connect(lambda: self._load(self._root))
        toolbar_layout.addWidget(self._refresh_btn)

        self._browse_btn = QPushButton("Abrir carpeta...")
        self._browse_btn.setStyleSheet(glass_button_qss("secondary"))
        self._browse_btn.clicked.connect(self._browse_folder)
        toolbar_layout.addWidget(self._browse_btn)

        toolbar_layout.addStretch()

        self._filter_input = QPushButton("🔍")
        self._filter_input.setStyleSheet(glass_button_qss("ghost"))
        self._filter_input.setFixedWidth(36)
        self._filter_input.setToolTip("Filtrar archivos")
        self._filter_input.clicked.connect(self._toggle_filter)
        toolbar_layout.addWidget(self._filter_input)

        main_layout.addWidget(toolbar_frame)

        # ── Splitter: tree + details ──
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(
            "QSplitter::handle { background: rgba(255,255,255,0.05); width: 1px; }")

        # ── Tree ──
        tree_frame = QFrame()
        tree_layout = QVBoxLayout(tree_frame)
        tree_layout.setContentsMargins(0, 0, 0, 0)

        self._tree = QTreeWidget()
        self._tree.setColumnCount(5)
        self._tree.setHeaderLabels(["Nombre", "Tipo", "Canciones", "Duración", "Ruta"])
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
            QTreeWidget::item:selected:hover {
                background: rgba(255,255,255,0.125);
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.16);
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
            QHeaderView::section:hover {
                background: rgba(255,255,255,0.06);
                color: rgba(255,255,255,0.92);
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
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._tree.itemDoubleClicked.connect(self._on_item)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        tree_layout.addWidget(self._tree)

        self._status = QLabel("")
        self._status.setObjectName("folderStatus")
        self._status.setStyleSheet(
            "QLabel#folderStatus { color: rgba(255,255,255,0.62); font-size: 12px;"
            "font-weight: 500; padding: 8px 12px; }")
        tree_layout.addWidget(self._status)

        splitter.addWidget(tree_frame)

        # ── Details panel ──
        self._details = QFrame()
        self._details.setFixedWidth(260)
        self._details.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.035);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 18px;
            }
        """)
        details_layout = QVBoxLayout(self._details)
        details_layout.setContentsMargins(16, 16, 16, 16)
        details_layout.setSpacing(10)

        # Cover
        self._detail_cover = QLabel()
        self._detail_cover.setFixedSize(228, 228)
        self._detail_cover.setAlignment(Qt.AlignCenter)
        self._detail_cover.setStyleSheet(
            "QLabel { background: rgba(255,255,255,0.03); border-radius: 12px; }")
        details_layout.addWidget(self._detail_cover, alignment=Qt.AlignCenter)
        details_layout.addSpacing(4)

        # Favorite toggle
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
        details_layout.addWidget(self._fav_toggle)
        details_layout.addSpacing(6)

        # Stats
        self._detail_name = QLabel("")
        self._detail_name.setStyleSheet("font-size:14px;font-weight:650;color:#fff;")
        details_layout.addWidget(self._detail_name)

        self._detail_path = QLabel("")
        self._detail_path.setWordWrap(True)
        self._detail_path.setStyleSheet("font-size:10.5px;color:rgba(255,255,255,0.62);")
        details_layout.addWidget(self._detail_path)

        self._detail_stats = QLabel("")
        self._detail_stats.setStyleSheet("font-size:11px;color:rgba(255,255,255,0.68);")
        details_layout.addWidget(self._detail_stats)

        details_layout.addStretch()
        splitter.addWidget(self._details)
        splitter.setSizes([600, 260])

        main_layout.addWidget(splitter, 1)

        self._load(self._root)
        self._rebuild_favs_menu()
        self._rebuild_history_menu()

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
            a = self._favs_menu.addAction("(vacío)")
            a.setEnabled(False)
        else:
            for p in list(self._favorites):
                name = os.path.basename(p) or p
                self._favs_menu.addAction(name, lambda path=p: self._load(path))
            self._favs_menu.addSeparator()
            for p in list(self._favorites):
                name = os.path.basename(p) or p
                self._favs_menu.addAction(f"✕ {name}",
                    lambda path=p: self._remove_favorite(path))

    def _rebuild_history_menu(self):
        self._hist_menu.clear()
        if not self._history:
            a = self._hist_menu.addAction("(vacío)")
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
        """Filter tree items by name. Called by search controller."""
        text = text.lower()
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            name = item.text(0).lower()
            path = item.text(4).lower()
            visible = not text or text in name or text in path
            item.setHidden(not visible)

    def _toggle_filter(self):
        from PySide6.QtWidgets import QLineEdit, QDialog, QVBoxLayout
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
        self._update_details()

        try:
            folders_arr = list_subfolders(path)
        except Exception:
            folders_arr = []
        try:
            files_arr = list_audio_files(path)
        except Exception:
            files_arr = []

        self._load_folder_items(folders_arr, files_arr, path)

        self._status.setText(f"{len(folders_arr)} carpetas · {len(files_arr)} canciones")

    def _load_folder_items(self, folders_arr: list[str], files_arr: list[str], path: str):
        folder_durations = {}
        if self._db and folders_arr:
            for f in folders_arr:
                dur = self._db._conn.execute(
                    "SELECT COALESCE(SUM(duration), 0) FROM media_items "
                    "WHERE directory = ? AND deleted_at IS NULL",
                    (f,)).fetchone()
                folder_durations[f] = dur[0] if dur else 0.0

        for folder in folders_arr:
            item = QTreeWidgetItem(self._tree)
            item.setIcon(0, get_qicon("folder", size=24))

            item.setText(0, os.path.basename(folder))
            item.setText(1, "Carpeta")
            item.setText(2, "—")
            dur = folder_durations.get(folder, 0.0)
            item.setText(3, self._format_duration(dur) if dur else "")
            item.setText(4, folder)
            item.setData(0, Qt.UserRole, folder)
            item.setData(0, Qt.UserRole + 1, "folder")

        file_refs = []
        if self._db and files_arr:
            items = self._db.get_all_by_directory(path, exact=True)
            if items:
                indexed = {i.filepath: i for i in items}
                for fp in files_arr:
                    if fp in indexed:
                        file_refs.append((fp, indexed[fp]))
                    else:
                        file_refs.append((fp, None))
            else:
                file_refs = [(fp, None) for fp in files_arr]
        else:
            file_refs = [(fp, None) for fp in files_arr]

        for fp, item_data in file_refs:
            tree_item = QTreeWidgetItem(self._tree)
            tree_item.setIcon(0, get_qicon("songs", size=24) or get_qicon("sidebar_library", size=24))
            if item_data:
                title = (item_data.title
                         or os.path.splitext(os.path.basename(fp))[0])
                artist = item_data.artist or ""
                tree_item.setText(0, f"{title}  —  {artist}" if artist else title)
                tree_item.setText(1, "Canción")
                tree_item.setText(2, "")
                tree_item.setText(3, self._format_duration(item_data.duration) if item_data.duration else "")
                tree_item.setText(4, fp)
            else:
                tree_item.setText(0, os.path.basename(fp))
                tree_item.setText(1, "Canción")
                tree_item.setText(2, "")
                tree_item.setText(3, "")
                tree_item.setText(4, fp)
            tree_item.setData(0, Qt.UserRole, fp)
            tree_item.setData(0, Qt.UserRole + 1, "file")

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

    def _update_details(self):
        self._detail_name.setText(os.path.basename(self._root) or self._root)
        self._detail_path.setText(self._root)

        try:
            files = list_audio_files(self._root)
        except Exception:
            files = []
        try:
            folders = list_subfolders(self._root)
        except Exception:
            folders = []

        total_dur = 0.0
        if self._db and self._db_connected:
            stats = self._db.get_directory_stats(self._root)
            total_dur = stats["total_duration"]
            dur_str = f" · {self._format_duration(total_dur)}" if total_dur else ""
        else:
            dur_str = ""

        self._detail_stats.setText(
            f"Archivos: {len(files)} · Carpetas: {len(folders)}{dur_str}")

        # Cover — try album_art_cache first, then sidecar files
        pix = None
        if self._db and self._db_connected:
            try:
                from library.album_key import make_album_key
                folder_name = os.path.basename(self._root)
                artist_name = os.path.basename(os.path.dirname(self._root))
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
            cover = self._find_cover(self._root)
            if cover:
                tpix = QPixmap(cover)
                if not tpix.isNull():
                    pix = tpix

        if pix:
            pix = pix.scaled(224, 224, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._detail_cover.setPixmap(pix)
        else:
            self._detail_cover.setText("♪")

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
            parts = ["…"] + parts[-3:]
        return " / ".join(parts)

    def _on_item(self, item, col):
        kind = item.data(0, Qt.UserRole + 1)
        path = item.data(0, Qt.UserRole)
        if kind == "folder":
            self._load(path)
        elif kind == "file":
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
        kind = item.data(0, Qt.UserRole + 1)
        menu = QMenu(self)

        if kind == "folder":
            menu.addAction("Abrir carpeta", lambda: self._load(path))
            menu.addSeparator()
            menu.addAction("▶ Reproducir carpeta", lambda: self._play_path_folder(path))
            menu.addAction("🔀 Reproducir aleatoriamente",
                          lambda: self._shuffle_path_folder(path))
            menu.addAction("+ Añadir a cola", lambda: self._queue_path_folder(path))
            menu.addSeparator()
            menu.addAction("Crear playlist", lambda: self._create_playlist(path))
            menu.addAction("📂 Escanear carpeta", lambda: self.scan_requested.emit(path))
            menu.addSeparator()
            menu.addAction("★ Marcar favorita", lambda: self._fav_folder(path))
            menu.addSeparator()
            menu.addAction("Abrir en Dolphin", lambda: self._open_in_file_manager(path))
            menu.addAction("Copiar ruta", lambda: QApplication.clipboard().setText(path))

        elif kind == "file":
            menu.addAction("▶ Reproducir ahora", lambda: self.folder_selected.emit([path]))
            menu.addAction("+ Añadir a cola", lambda: self.queue_requested.emit([path]))
            menu.addSeparator()
            menu.addAction("Información técnica", lambda: self._show_audio_info(path))
            menu.addSeparator()
            menu.addAction("Abrir en Dolphin",
                          lambda: self._open_in_file_manager(os.path.dirname(path)))
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
        dlg.setWindowTitle("Información de audio")
        dlg.setMinimumWidth(420)
        dlg.setStyleSheet("""
            QDialog { background: #181C25; border-radius: 14px; }
            QLabel { color: rgba(255,255,255,0.55); font-size: 11px; }
            QLineEdit {
                background: rgba(255,255,255,0.04); border: none; border-radius: 6px;
                color: rgba(255,255,255,0.78); font-size: 12px; padding: 6px 10px;
                read-only: true;
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
            add_row("Tamaño", f"{st.st_size / (1024*1024):.2f} MB")
            from datetime import datetime
            mtime = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")
            add_row("Modificado", mtime)
            mode = stat.filemode(st.st_mode)
            add_row("Permisos", mode)
        except OSError:
            pass

        add_row("Ruta completa", filepath)

        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok)
        btns.accepted.connect(dlg.accept)
        layout.addWidget(btns)
        dlg.exec()

    def set_db(self, db):
        self._db = db
        self._db_connected = db is not None

    def set_watcher_active(self, active: bool):
        if active:
            self._scan_btn.setText("● Escanear")
            self._scan_btn.setToolTip(
                "Monitoreo en tiempo real activo. Usá Escanear para forzar un re-escaneo completo.")
        else:
            self._scan_btn.setText("Escanear")
            self._scan_btn.setToolTip("Escanear carpeta para agregar archivos a la biblioteca")

    @staticmethod
    def _open_in_file_manager(path: str):
        target = path if os.path.isdir(path) else os.path.dirname(path)
        try:
            subprocess.Popen(["xdg-open", target])
        except Exception:
            import logging
            logging.getLogger("michi").debug("Folder browser: xdg-open failed")
