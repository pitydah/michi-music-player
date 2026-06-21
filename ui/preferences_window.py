"""Preferences Window — premium 16-category settings dialog with sidebar and search."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem,
    QStackedWidget, QWidget, QLabel, QLineEdit, QPushButton,
    QFrame, QScrollArea, QMessageBox,
)

from ui.settings_pages import (
    GeneralPage, AppearancePage, LibraryPage, PlaybackPage,
    AudioPage, EqualizerPage, MetadataPage, PlaylistPage,
    ArtistsAlbumsPage, RadioPage, ServersPage, DevicesPage,
    SyncPage, ShortcutsPage, AdvancedPage, AboutPage,
    HomeAudioPage,
)
from ui.icons import get_icon
import core.settings_manager as sm

_BG = "#090B11"
_PANEL = "rgba(255,255,255,0.035)"
_HOVER = "rgba(255,255,255,0.075)"
_SELECTED = "rgba(255,255,255,0.115)"
_BORDER = "rgba(255,255,255,0.075)"
_TEXT = "#FFFFFF"
_TEXT2 = "rgba(255,255,255,0.78)"
_TEXT3 = "rgba(255,255,255,0.62)"

PAGE_DEFS = [
    ("General", "general", "sidebar_library"),
    ("Apariencia", "appearance", "sidebar_albums"),
    ("Biblioteca", "library", "sidebar_library"),
    ("Reproducción", "playback", "warm_play"),
    ("Audio / DAC", "audio", "warm_eq"),
    ("Ecualizador", "eq", "warm_eq"),
    ("Metadatos", "metadata", "metadata_editor"),
    ("Playlists", "playlists", "sidebar_playlists"),
    ("Artistas y álbumes", "artists_albums", "sidebar_artist"),
    ("Radio", "radio", "sidebar_radio"),
    ("Servidores", "servers", "sidebar_servers"),
    ("Dispositivos", "devices", "sidebar_devices"),
    ("Sincronización", "sync", "sidebar_servers"),
    ("Home Audio", "home_audio", "home_audio"),
    ("Atajos", "shortcuts", "sidebar_library"),
    ("Avanzado", "advanced", "warm_settings"),
    ("Acerca de", "about", "warm_settings"),
]

_FOOTER_BTN_CSS = f"""
    QPushButton {{
        background: rgba(255,255,255,0.055); color: {_TEXT2};
        border: 1px solid rgba(255,255,255,0.08); border-radius: 10px;
        padding: 7px 16px; font-size: 12px; font-weight: 600;
    }}
    QPushButton:hover {{
        background: rgba(255,255,255,0.090); color: {_TEXT};
        border: 1px solid rgba(255,255,255,0.13);
    }}
    QPushButton#applyBtn {{
        background: rgba(255,255,255,0.11); color: {_TEXT};
        border: 1px solid rgba(255,255,255,0.15);
    }}
    QPushButton#applyBtn:hover {{
        background: rgba(255,255,255,0.16);
    }}
"""


class PreferencesWindow(QDialog):
    settings_applied = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferencias — Astra Music Player")
        self.resize(1020, 700)
        self.setMinimumSize(900, 600)
        self.setModal(True)
        self._pending_changes: set[str] = set()

        self.setStyleSheet("""
            QDialog { background: rgba(15,17,22,0.96);
              border: 1px solid rgba(255,255,255,0.06); border-radius: 18px; }
            QWidget { background: transparent; }
        """)

        # ── Header ──
        header = QHBoxLayout()
        header.setContentsMargins(20, 14, 20, 8)
        title_lbl = QLabel("Preferencias")
        title_lbl.setStyleSheet(f"color: {_TEXT}; font-size: 20px; font-weight: 800; background: transparent;")
        header.addWidget(title_lbl)
        header.addStretch()

        self._search = QLineEdit()
        self._search.setPlaceholderText("Buscar ajustes...")
        self._search.setClearButtonEnabled(True)
        self._search.setFixedWidth(240)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(255,255,255,0.060); color: {_TEXT};
                border: 1px solid rgba(255,255,255,0.10); border-radius: 12px;
                padding: 7px 14px; font-size: 12px;
            }}
            QLineEdit:focus {{ border-color: rgba(255,255,255,0.18); }}
        """)
        header.addWidget(self._search)

        # ── Body: sidebar + stack ──
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)

        self._nav = QListWidget()
        self._nav.setObjectName("settingsNav")
        self._nav.setFixedWidth(220)
        self._nav.setStyleSheet(f"""
            QListWidget#settingsNav {{
                background: rgba(255,255,255,0.018);
                border: none;
                border-right: 1px solid rgba(255,255,255,0.045);
                padding: 8px;
            }}
            QListWidget#settingsNav::item {{
                min-height: 44px; padding: 9px 14px; margin: 2px 4px;
                color: rgba(255,255,255,0.68); font-size: 12.5px; font-weight: 520;
                border-radius: 11px; border: 1px solid transparent;
            }}
            QListWidget#settingsNav::item:hover {{
                background: {_HOVER}; color: {_TEXT};
                border: 1px solid rgba(255,255,255,0.10);
            }}
            QListWidget#settingsNav::item:selected {{
                background: {_SELECTED}; color: {_TEXT}; font-weight: 700;
                border: 1px solid rgba(255,255,255,0.16);
            }}
        """)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet("QStackedWidget { background: transparent; }")

        self._pages: list[tuple[str, QWidget]] = []
        for name, _page_class, icon_name in PAGE_DEFS:
            item = QListWidgetItem(name)
            icon_path = get_icon(icon_name)
            if icon_path:
                from PySide6.QtGui import QIcon
                pix = QPixmap(icon_path)
                if not pix.isNull():
                    item.setIcon(QIcon(pix.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
            self._nav.addItem(item)

        self._nav.currentRowChanged.connect(self._switch_page)

        body.addWidget(self._nav)
        body.addWidget(self._stack, 1)

        # ── Footer ──
        footer = QHBoxLayout()
        footer.setContentsMargins(16, 10, 16, 12)
        footer.setSpacing(8)

        restore_page_btn = QPushButton("Restaurar página")
        restore_page_btn.setStyleSheet(_FOOTER_BTN_CSS)
        restore_page_btn.clicked.connect(self._restore_page)
        footer.addWidget(restore_page_btn)

        restore_all_btn = QPushButton("Restaurar todo")
        restore_all_btn.setStyleSheet(_FOOTER_BTN_CSS)
        restore_all_btn.clicked.connect(self._restore_all)
        footer.addWidget(restore_all_btn)

        footer.addSpacing(8)

        export_btn = QPushButton("Exportar")
        export_btn.setStyleSheet(_FOOTER_BTN_CSS)
        export_btn.clicked.connect(self._do_export)
        footer.addWidget(export_btn)

        import_btn = QPushButton("Importar")
        import_btn.setStyleSheet(_FOOTER_BTN_CSS)
        import_btn.clicked.connect(self._do_import)
        footer.addWidget(import_btn)

        footer.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setStyleSheet(_FOOTER_BTN_CSS)
        cancel_btn.clicked.connect(self._on_cancel)
        footer.addWidget(cancel_btn)

        apply_btn = QPushButton("Aplicar")
        apply_btn.setObjectName("applyBtn")
        apply_btn.setStyleSheet(_FOOTER_BTN_CSS)
        apply_btn.clicked.connect(self._apply_all)
        footer.addWidget(apply_btn)

        save_btn = QPushButton("Guardar")
        save_btn.setObjectName("applyBtn")
        save_btn.setStyleSheet(_FOOTER_BTN_CSS)
        save_btn.clicked.connect(self._on_save)
        footer.addWidget(save_btn)

        # ── Assemble ──
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addLayout(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,0.06);")
        outer.addWidget(sep)

        outer.addLayout(body, 1)
        outer.addWidget(sep)
        outer.addLayout(footer)

        # Build pages lazily on first switch
        self._page_widgets: list[QWidget | None] = [None] * len(PAGE_DEFS)
        self._nav.setCurrentRow(0)

        # Connect search
        self._search.textChanged.connect(self._on_search)

    def _get_or_build_page(self, idx: int) -> QWidget:
        if idx < 0 or idx >= len(PAGE_DEFS):
            return None
        if self._page_widgets[idx] is not None:
            return self._page_widgets[idx]

        name, key, icon = PAGE_DEFS[idx]
        page_classes = {
            "general": GeneralPage, "appearance": AppearancePage,
            "library": LibraryPage, "playback": PlaybackPage,
            "audio": AudioPage, "eq": EqualizerPage,
            "metadata": MetadataPage, "playlists": PlaylistPage,
            "artists_albums": ArtistsAlbumsPage, "radio": RadioPage,
            "servers": ServersPage, "devices": DevicesPage,
            "sync": SyncPage, "shortcuts": ShortcutsPage,
            "advanced": AdvancedPage, "about": AboutPage,
            "home_audio": HomeAudioPage,
        }
        cls = page_classes.get(key, GeneralPage)
        page = cls()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(page)
        scroll.setStyleSheet(f"QScrollArea {{ background: {_BG}; border: none; }} "
                             f"QScrollArea QWidget {{ background: {_BG}; }}")
        self._stack.addWidget(scroll)
        self._page_widgets[idx] = page
        return page

    def _switch_page(self, idx: int):
        if idx < 0:
            return
        self._get_or_build_page(idx)
        self._stack.setCurrentIndex(idx)

    # ── Search ──

    def _on_search(self, text: str):
        text = text.strip().lower()
        for i in range(self._nav.count()):
            item = self._nav.item(i)
            name = PAGE_DEFS[i][0]
            visible = text == "" or text in name.lower()
            item.setHidden(not visible)

        # If current item hidden, jump to first visible
        current = self._nav.currentItem()
        if current and current.isHidden():
            for i in range(self._nav.count()):
                if not self._nav.item(i).isHidden():
                    self._nav.setCurrentRow(i)
                    break

    # ── Apply / Save ──

    def _apply_all(self):
        for pw in self._page_widgets:
            if pw and hasattr(pw, 'apply'):
                pw.apply()
        self._pending_changes.clear()

    def _on_save(self):
        self._apply_all()
        self.accept()

    def _on_cancel(self):
        if self._pending_changes:
            reply = QMessageBox.question(
                self, "Cambios sin guardar",
                "Hay cambios sin aplicar. ¿Descartar cambios?",
                QMessageBox.Discard | QMessageBox.Cancel)
            if reply != QMessageBox.Discard:
                return
        self.reject()

    def _restore_page(self):
        idx = self._nav.currentRow()
        if idx < 0:
            return
        key = PAGE_DEFS[idx][1]
        reply = QMessageBox.question(
            self, "Restaurar página",
            f"¿Restaurar valores por defecto de '{PAGE_DEFS[idx][0]}'?",
            QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        for k in sm.DEFAULTS:
            if k.startswith(key + "/") or k == key:
                sm.set_(k, sm.DEFAULTS[k])
        # Reload page
        self._page_widgets[idx] = None
        self._switch_page(idx)
        self._pending_changes.discard(key)

    def _restore_all(self):
        reply = QMessageBox.question(
            self, "Restaurar todo",
            "Esto restaurará TODAS las preferencias de Astra a sus valores por defecto.\n\n¿Continuar?",
            QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        sm.restore_defaults()
        self._page_widgets = [None] * len(PAGE_DEFS)
        self._switch_page(self._nav.currentRow())
        self._pending_changes.clear()
        QMessageBox.information(self, "Restaurado", "Todas las preferencias han sido restauradas. Reinicia Astra.")

    def _do_export(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Exportar configuración", "astra_config.json", "JSON (*.json)")
        if path:
            sm.export_to_file(path)

    def _do_import(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "Importar configuración", "", "JSON (*.json)")
        if path:
            try:
                sm.import_from_file(path)
                self._page_widgets = [None] * len(PAGE_DEFS)
                self._switch_page(self._nav.currentRow())
                QMessageBox.information(self, "Importado", "Configuración importada. Reinicia Astra para aplicar todos los cambios.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo importar:\n{e}")
