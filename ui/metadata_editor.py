"""Metadata Editor — premium 3-panel tag editor with drag-drop, table, inspector, and rename."""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QColor, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel, QLineEdit, QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFileDialog, QMessageBox,
    QComboBox, QSpinBox, QTabWidget, QListWidget, QListWidgetItem,
    QInputDialog,
)

from metadata.tag_model import TrackTags
from metadata.tag_reader import read_tags, AUDIO_EXTS
from metadata.tag_writer import write_tags
from metadata import tag_actions as ta
from metadata.metadata_diagnostics import diagnose_items, NAV_CATEGORIES
from metadata.rename_engine import preview_rename, apply_rename
from metadata.artwork_utils import (
    _pillow_available,
)

# ═══════════════════════════════════════════════════════════
# Style tokens
# ═══════════════════════════════════════════════════════════
_BG        = "#090B11"
_PANEL     = "rgba(255,255,255,0.040)"
_HOVER     = "rgba(255,255,255,0.065)"
_SELECTED  = "rgba(255,255,255,0.105)"
_BORDER    = "rgba(255,255,255,0.06)"
_TEXT      = "rgba(255,255,255,0.96)"
_TEXT2     = "rgba(255,255,255,0.72)"
_TEXT3     = "rgba(255,255,255,0.56)"
_TEXT_DIM  = "rgba(255,255,255,0.42)"


_BTN_CSS = f"""
    QPushButton {{
        background: rgba(255,255,255,0.045); color: {_TEXT};
        border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;
        padding: 8px 13px; font-size: 12.5px; font-weight: 600;
    }}
    QPushButton:hover {{
        background: rgba(255,255,255,0.085);
        border: 1px solid rgba(255,255,255,0.14);
    }}
    QPushButton:pressed {{ background: rgba(255,255,255,0.11); }}
    QPushButton:disabled {{ color: {_TEXT_DIM}; background: rgba(255,255,255,0.020); }}
"""

_FIELD_CSS = f"""
    background: rgba(255,255,255,0.060); color: {_TEXT};
    border: 1px solid rgba(255,255,255,0.10); border-radius: 10px;
    padding: 7px 10px;
    selection-background-color: rgba(255,255,255,0.18); selection-color: {_TEXT};
"""


def _panel_frame(name: str) -> str:
    return f"QFrame#{name} {{ background: {_PANEL}; border: 1px solid {_BORDER}; border-radius: 18px; }}"

# ═══════════════════════════════════════════════════════════
# MetadataEditorWidget
# ═══════════════════════════════════════════════════════════

class MetadataEditorWidget(QWidget):
    files_saved = Signal(list)
    request_library_refresh = Signal()
    metadata_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("metadataEditor")
        self.setStyleSheet(f"QWidget#metadataEditor {{ background: {_BG}; }}")
        self.setAcceptDrops(True)

        self._tags: list[TrackTags] = []
        self._selected_indices: list[int] = []
        self._dirty_count = 0
        self._field_widgets: dict[str, QLineEdit | QSpinBox] = {}
        self._filter_key = -1

        # ── Header ──
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(10)

        icons_path = Path(__file__).parent.parent / "icons/sidebar/metadata.svg"
        if icons_path.exists():
            icon_lbl = QLabel()
            icon_pix = QPixmap(str(icons_path))
            if not icon_pix.isNull():
                icon_pix = icon_pix.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                icon_lbl.setPixmap(icon_pix)
            icon_lbl.setFixedSize(40, 40)
            icon_lbl.setStyleSheet("background: transparent; border: none;")
            header_row.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        t = QLabel("Editor de metadatos")
        t.setStyleSheet(f"color: {_TEXT}; font-size: 24px; font-weight: 700; background: transparent; border: none;")
        title_box.addWidget(t)
        s = QLabel("Limpia, completa y normaliza la información de tus archivos")
        s.setStyleSheet(f"color: {_TEXT2}; font-size: 13px; font-weight: 500; background: transparent; border: none;")
        title_box.addWidget(s)
        header_row.addLayout(title_box)
        header_row.addStretch()

        for label, slot in [
            ("Abrir archivos", self._open_files),
            ("Abrir carpeta", self._open_folder),
            ("Identificar", self._identify),
            ("Renombrar", self._show_rename_dialog),
            ("Deshacer", self._revert_all),
            ("Guardar", self._save_all),
            ("Smart Tag", self._toggle_smart_tagging),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_BTN_CSS)
            btn.clicked.connect(slot)
            header_row.addWidget(btn)

        header = QFrame()
        header.setObjectName("metadataHero")
        header.setStyleSheet(
            "QFrame#metadataHero {"
            "  background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "    stop:0 rgba(255,255,255,0.065),"
            "    stop:0.55 rgba(255,255,255,0.045),"
            "    stop:1 rgba(143,183,255,0.030));"
            "  border: 1px solid rgba(255,255,255,0.050);"
            "  border-radius: 22px; }")
        header.setContentsMargins(24, 20, 24, 20)
        header.setLayout(header_row)

        # ── Splitter (3 panels) ──
        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.setStyleSheet("QSplitter::handle { background: rgba(255,255,255,0.04); width: 2px; }")

        self._left_panel = self._build_left_panel()
        self._center_panel = self._build_center_panel()
        self._right_panel = self._build_right_panel()

        self._splitter.addWidget(self._left_panel)
        self._splitter.addWidget(self._center_panel)
        self._splitter.addWidget(self._right_panel)
        self._splitter.setSizes([200, 500, 320])

        # ── Main layout ──
        main = QVBoxLayout(self)
        main.setContentsMargins(24, 20, 24, 20)
        main.setSpacing(16)
        main.addWidget(header)
        main.addWidget(self._splitter)

        # ── Smart Tagging + Library Doctor tools ──
        from ui.audio_lab.smart_tagging_panel import SmartTaggingPanel
        from ui.audio_lab.library_doctor_panel import LibraryDoctorPanel
        from ui.audio_lab.services.smart_tagging_service import SmartTaggingService
        self._st_service = SmartTaggingService()
        self._st_panel = SmartTaggingPanel()
        self._st_panel.suggestions_accepted.connect(self._on_st_suggestions_accepted)
        self._doctor_panel = LibraryDoctorPanel()
        self._doctor_panel.scan_requested.connect(self._on_scan_library)
        self._tools_tabs = QTabWidget()
        self._tools_tabs.setObjectName("metadataEditorTools")
        self._tools_tabs.addTab(self._st_panel, "Smart Tagging")
        self._tools_tabs.addTab(self._doctor_panel, "Library Doctor")
        self._tools_tabs.setVisible(False)
        self._tools_tabs.setStyleSheet("""
            QTabWidget#metadataEditorTools::pane { border: none; background: transparent; }
            QTabBar::tab {
                background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);
                border-radius: 8px; padding: 6px 16px; color: rgba(255,255,255,0.52);
                font-size: 12px; margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: rgba(143,183,255,0.08); border: 1px solid rgba(143,183,255,0.12);
                color: rgba(143,183,255,0.85);
            }
        """)
        main.addWidget(self._tools_tabs)

        self._rebuild_navigator()
        self._show_empty_dashboard()

    # ═══════════════════════════════════════════════════════
    # Left Panel: Diagnostics / Navigator
    # ═══════════════════════════════════════════════════════

    def _build_left_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("leftPanel")
        panel.setStyleSheet(_panel_frame("leftPanel"))
        v = QVBoxLayout(panel)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(8)

        title = QLabel("Diagnóstico")
        title.setStyleSheet(f"color: {_TEXT}; font-size: 14px; font-weight: 700; background: transparent; border: none;")
        v.addWidget(title)

        self._nav_list = QListWidget()
        self._nav_list.setStyleSheet(f"""
            QListWidget {{ background: transparent; border: none; color: {_TEXT2}; font-size: 12px; }}
            QListWidget::item {{ padding: 5px 8px; border-radius: 8px; }}
            QListWidget::item:hover {{ background: {_HOVER}; color: {_TEXT}; }}
            QListWidget::item:selected {{ background: {_SELECTED}; color: {_TEXT}; }}
        """)
        self._nav_list.currentRowChanged.connect(self._on_nav_filter)
        v.addWidget(self._nav_list)

        self._diag_label = QLabel("0 archivos cargados")
        self._diag_label.setStyleSheet(f"color: {_TEXT3}; font-size: 10.5px; background: transparent; border: none;")
        v.addWidget(self._diag_label)

        return panel

    def _rebuild_navigator(self):
        self._nav_list.blockSignals(True)
        self._nav_list.clear()
        diag = diagnose_items(self._tags) if self._tags else {}

        for key, label, diag_key in NAV_CATEGORIES:
            count = diag.get(diag_key, 0)
            it = QListWidgetItem(f"{label} ({count})")
            it.setData(Qt.UserRole, key)
            self._nav_list.addItem(it)

        self._nav_list.setCurrentRow(0)
        self._nav_list.blockSignals(False)
        self._diag_label.setText(f"{len(self._tags)} archivos · {self._dirty_count} modificados")

    def _on_nav_filter(self, row: int):
        item = self._nav_list.item(row)
        if not item:
            return
        key = item.data(Qt.UserRole)
        self._filter_key = key
        self._populate_table()

    # ═══════════════════════════════════════════════════════
    # Empty dashboard
    # ═══════════════════════════════════════════════════════

    def _show_empty_dashboard(self):
        if self._tags:
            return
        self._table.setRowCount(0)
        self._table.hide()

    # ═══════════════════════════════════════════════════════
    # Center Panel: Table
    # ═══════════════════════════════════════════════════════

    _TABLE_COLS = ["Estado", "Título", "Artista", "Álbum", "Artista álbum", "Nº", "Disco", "Año", "Género", "Formato"]

    def _build_center_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("centerPanel")
        panel.setStyleSheet(_panel_frame("centerPanel"))
        v = QVBoxLayout(panel)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)

        bar = QHBoxLayout()
        bar.setSpacing(6)
        for label, slot in [
            ("Aplicar a todos", self._batch_apply_all),
            ("Numerar pistas", self._batch_number_tracks),
            ("Normalizar", self._batch_normalize),
            ("Mayúsculas", self._batch_title_case),
            ("Limpiar campo", self._batch_clear_field),
            ("Buscar/reemplazar", self._batch_search_replace),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_BTN_CSS.replace("8px 13px", "5px 10px").replace("12.5px", "11px"))
            btn.clicked.connect(slot)
            bar.addWidget(btn)
        bar.addStretch()
        v.addLayout(bar)

        self._table = QTableWidget()
        self._table.setColumnCount(len(self._TABLE_COLS))
        self._table.setHorizontalHeaderLabels(self._TABLE_COLS)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._table.setShowGrid(False)
        self._table.setFrameShape(QFrame.NoFrame)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._table.setSortingEnabled(False)

        self._table.setStyleSheet(f"""
            QTableWidget {{
                background: transparent; color: {_TEXT}; border: none;
                gridline-color: transparent;
                selection-background-color: {_SELECTED}; selection-color: {_TEXT};
                alternate-background-color: rgba(255,255,255,0.018);
            }}
            QTableWidget::item {{ color: {_TEXT}; padding: 6px; }}
            QTableWidget::item:hover {{ background: {_HOVER}; }}
            QHeaderView::section {{
                background: rgba(255,255,255,0.045); color: rgba(255,255,255,0.86);
                border: none; border-bottom: 1px solid rgba(255,255,255,0.03);
                padding: 8px 10px; font-size: 11.5px; font-weight: 700;
            }}
        """)

        self._table.itemSelectionChanged.connect(self._on_table_selection)
        self._table.setColumnWidth(0, 85)
        self._table.setColumnWidth(1, 160)
        self._table.setColumnWidth(2, 140)
        self._table.setColumnWidth(3, 150)
        self._table.setColumnWidth(4, 150)
        self._table.setColumnWidth(5, 50)
        self._table.setColumnWidth(6, 55)
        self._table.setColumnWidth(7, 55)
        self._table.setColumnWidth(8, 100)
        self._table.setColumnWidth(9, 60)
        v.addWidget(self._table)

        return panel

    def _populate_table(self):
        self._table.setRowCount(0)

        filter_key = self._filter_key

        if not self._tags:
            self._show_empty_dashboard()
            return
        else:
            self._table.show()

        rows = self._tags
        if filter_key and filter_key != "all":
            if filter_key == "dirty":
                rows = [t for t in rows if t.dirty]
            elif filter_key == "no_cover":
                rows = [t for t in rows if not t.has_artwork]
            elif filter_key == "no_artist":
                rows = [t for t in rows if not t.artist]
            elif filter_key == "no_album":
                rows = [t for t in rows if not t.album]
            elif filter_key == "no_albumartist":
                rows = [t for t in rows if not t.albumartist]
            elif filter_key == "no_tracknumber":
                rows = [t for t in rows if not t.tracknumber]
            elif filter_key == "no_year":
                rows = [t for t in rows if not t.date]
            elif filter_key == "no_genre":
                rows = [t for t in rows if not t.genre]
            elif filter_key == "errors":
                rows = [t for t in rows if t.error]

        self._table.setRowCount(len(rows))
        for i, tag in enumerate(rows):
            real_idx = self._tags.index(tag)

            if tag.error:
                status = "Error"
                status_color = QColor("#FF6B6B")
            elif tag.dirty:
                status = "Modificado"
                status_color = QColor("#FFE066")
            elif not tag.has_artwork:
                status = "Sin carátula"
                status_color = QColor(_TEXT3.replace("rgba(", "").replace(")", "").split(",")[-1].strip() if "rgba" in _TEXT3 else _TEXT3)
            else:
                status = "OK"
                status_color = QColor("#80FF80")

            row_data = [
                status, tag.title, tag.artist, tag.album, tag.albumartist,
                tag.tracknumber, tag.discnumber, tag.date, tag.genre, tag.kind,
            ]
            for j, val in enumerate(row_data):
                it = QTableWidgetItem(str(val))
                if j == 0:
                    it.setForeground(status_color)
                elif tag.dirty:
                    it.setForeground(QColor("#FFE066"))
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                it.setData(Qt.UserRole, real_idx)
                self._table.setItem(i, j, it)

    def _on_table_selection(self):
        indices = set()
        for item in self._table.selectedItems():
            real_idx = item.data(Qt.UserRole)
            if real_idx is not None:
                indices.add(int(real_idx))
        self._selected_indices = sorted(indices)
        self._update_inspector()

    # ═══════════════════════════════════════════════════════
    # Right Panel: Inspector
    # ═══════════════════════════════════════════════════════

    def _build_right_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("rightPanel")
        panel.setStyleSheet(_panel_frame("rightPanel"))
        v = QVBoxLayout(panel)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)

        title = QLabel("Inspector")
        title.setStyleSheet(f"color: {_TEXT}; font-size: 14px; font-weight: 700; background: transparent; border: none;")
        v.addWidget(title)

        # Artwork
        self._artwork_label = QLabel()
        self._artwork_label.setFixedSize(180, 180)
        self._artwork_label.setAlignment(Qt.AlignCenter)
        self._artwork_label.setStyleSheet(f"background: rgba(255,255,255,0.050); border: 1px solid {_BORDER}; border-radius: 12px;")
        v.addWidget(self._artwork_label, alignment=Qt.AlignCenter)

        art_btns = QHBoxLayout()
        art_btns.setSpacing(5)
        for label, slot in [
            ("Cambiar", self._change_artwork),
            ("Redimensionar", self._resize_artwork),
            ("Quitar", self._remove_artwork),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_BTN_CSS.replace("8px 13px", "4px 7px").replace("12.5px", "10.5px"))
            btn.clicked.connect(slot)
            art_btns.addWidget(btn)
        v.addLayout(art_btns)

        # Tabs
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(f"""
            QTabWidget::pane {{ background: transparent; border: none; }}
            QTabBar::tab {{
                background: transparent; color: {_TEXT3}; padding: 6px 12px;
                font-size: 11.5px; border: none; border-bottom: 2px solid transparent;
            }}
            QTabBar::tab:selected {{ color: {_TEXT}; border-bottom: 2px solid {_TEXT}; }}
            QTabBar::tab:hover {{ color: {_TEXT2}; }}
        """)

        self._basic_tab = self._build_field_tab([
            ("Título", "title"), ("Artista", "artist"),
            ("Álbum", "album"), ("Artista álbum", "albumartist"),
            ("Nº pista", "tracknumber"), ("Total pistas", "tracktotal"),
            ("Disco", "discnumber"), ("Total discos", "disctotal"),
            ("Año", "date"), ("Género", "genre"),
        ])
        self._advanced_tab = self._build_field_tab([
            ("Compositor", "composer"), ("Comentario", "comment"),
            ("Letra", "lyrics"), ("BPM", "bpm"), ("ISRC", "isrc"),
            ("MB Track ID", "musicbrainz_trackid"), ("MB Album ID", "musicbrainz_albumid"),
        ])

        self._file_tab = QWidget()
        fv = QVBoxLayout(self._file_tab)
        fv.setSpacing(4)
        self._file_info_label = QLabel()
        self._file_info_label.setWordWrap(True)
        self._file_info_label.setStyleSheet(f"color: {_TEXT3}; font-size: 11px; background: transparent; border: none;")
        fv.addWidget(self._file_info_label)
        fv.addStretch()

        self._changes_tab = QWidget()
        cv = QVBoxLayout(self._changes_tab)
        cv.setSpacing(4)
        self._changes_label = QLabel()
        self._changes_label.setWordWrap(True)
        self._changes_label.setStyleSheet(f"color: {_TEXT2}; font-size: 11px; background: transparent; border: none;")
        cv.addWidget(self._changes_label)
        cv.addStretch()

        self._tabs.addTab(self._basic_tab, "Básico")
        self._tabs.addTab(self._advanced_tab, "Avanzado")
        self._tabs.addTab(self._file_tab, "Archivo")
        self._tabs.addTab(self._changes_tab, "Cambios")

        v.addWidget(self._tabs)
        return panel

    def _build_field_tab(self, fields: list[tuple[str, str]]) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(6)

        for label, attr in fields:
            row = QHBoxLayout()
            row.setSpacing(6)
            lbl = QLabel(label)
            lbl.setFixedWidth(78)
            lbl.setStyleSheet(f"color: {_TEXT3}; font-size: 11px; background: transparent; border: none;")
            row.addWidget(lbl)

            if attr == "bpm":
                edit = QSpinBox()
                edit.setRange(0, 999)
                edit.setStyleSheet(_FIELD_CSS)
                edit.valueChanged.connect(lambda v, a=attr: self._on_field_changed(a, str(v)))
            else:
                edit = QLineEdit()
                edit.setStyleSheet(_FIELD_CSS)
                edit.textChanged.connect(lambda txt, a=attr: self._on_field_changed(a, txt))

            self._field_widgets[attr] = edit
            row.addWidget(edit)
            layout.addLayout(row)

        return w

    # ── Inspector updates ──

    def _update_inspector(self):
        if not self._selected_indices:
            self._clear_inspector()
            return

        idx = self._selected_indices[0]
        if idx >= len(self._tags):
            self._clear_inspector()
            return

        tag = self._tags[idx]
        multi = len(self._selected_indices) > 1

        # Artwork
        if tag.artwork_data:
            pix = QPixmap()
            pix.loadFromData(tag.artwork_data)
            sc = pix.scaled(176, 176, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._artwork_label.setPixmap(sc)
            self._artwork_label.setText("")
        else:
            self._artwork_label.clear()
            self._artwork_label.setText("Sin carátula")
            self._artwork_label.setStyleSheet(
                f"background: rgba(255,255,255,0.050); border: 1px solid {_BORDER};"
                f" border-radius: 12px; color: {_TEXT_DIM}; font-size: 12px;")

        # Fields
        for attr, w in self._field_widgets.items():
            if attr not in tag.TEXT_FIELDS:
                continue
            w.blockSignals(True)
            val = getattr(tag, attr, "")
            if isinstance(w, QSpinBox):
                w.setValue(int(val) if val and val.isdigit() else 0)
            else:
                if multi:
                    vals = set(
                        getattr(self._tags[i], attr, "")
                        for i in self._selected_indices if i < len(self._tags))
                    w.setText(val if len(vals) == 1 else "")
                    w.setPlaceholderText("— múltiples —" if len(vals) > 1 else "")
                else:
                    w.setText(val)
                    w.setPlaceholderText("")
            w.blockSignals(False)

        # File info
        info_lines = [
            f"Ruta: {tag.filepath}",
            f"Formato: {tag.kind}",
        ]
        if tag.bitrate:
            info_lines.append(f"Bitrate: {tag.bitrate} kbps")
        if tag.sample_rate:
            info_lines.append(f"Sample rate: {tag.sample_rate} Hz")
        if tag.channels:
            info_lines.append(f"Canales: {tag.channels}")
        info_lines.append(f"Duración: {int(tag.duration // 60)}:{int(tag.duration % 60):02d}")
        info_lines.append(f"Tamaño: {tag.filesize / (1024 * 1024):.1f} MB")
        self._file_info_label.setText("\n".join(info_lines))

        # Changes tab
        if tag.dirty and tag.original:
            lines = ["Campos modificados:"]
            for f in sorted(tag.dirty_fields):
                old = getattr(tag.original, f, "")
                new = getattr(tag, f, "")
                lines.append(f"  {f}: \"{old}\" → \"{new}\"")
            self._changes_label.setText("\n".join(lines))
        else:
            self._changes_label.setText("Sin cambios")

    def _clear_inspector(self):
        self._artwork_label.clear()
        self._artwork_label.setText("")
        self._artwork_label.setStyleSheet(
            f"background: rgba(255,255,255,0.050); border: 1px solid {_BORDER}; border-radius: 12px;")
        for w in self._field_widgets.values():
            w.blockSignals(True)
            if isinstance(w, QLineEdit):
                w.clear()
                w.setPlaceholderText("")
            elif isinstance(w, QSpinBox):
                w.setValue(0)
            w.blockSignals(False)
        self._file_info_label.setText("")
        self._changes_label.setText("Sin cambios")

    # ── Field editing ──

    def _on_field_changed(self, attr: str, value: str):
        if not self._selected_indices:
            return
        changed = False
        for idx in self._selected_indices:
            if idx < len(self._tags) and self._tags[idx].set_field(attr, value):
                changed = True
        if changed:
            self._dirty_count = sum(1 for t in self._tags if t.dirty)
            self._rebuild_navigator()
            self._populate_table()
            self.metadata_changed.emit()

    # ═══════════════════════════════════════════════════════
    # Batch actions
    # ═══════════════════════════════════════════════════════

    def _selected_tags(self) -> list[TrackTags]:
        return [self._tags[i] for i in self._selected_indices if i < len(self._tags)]

    def _batch_apply_all(self):
        items = self._selected_tags()
        if not items:
            return
        field, ok = QInputDialog.getItem(self, "Aplicar a todos", "Campo:",
                                         ["artist", "album", "albumartist", "genre", "date", "composer"], 0, False)
        if not ok:
            return
        value, ok = QInputDialog.getText(self, "Valor", f"Valor para '{field}':")
        if not ok:
            return
        ta.apply_field_to_all(items, field, value)
        self._refresh_after_batch()

    def _batch_number_tracks(self):
        ta.auto_number_tracks(self._selected_tags(), 1)
        self._refresh_after_batch()

    def _batch_normalize(self):
        ta.normalize_spaces(self._selected_tags())
        self._refresh_after_batch()

    def _batch_title_case(self):
        ta.title_case(self._selected_tags())
        self._refresh_after_batch()

    def _batch_clear_field(self):
        items = self._selected_tags()
        if not items:
            return
        field, ok = QInputDialog.getItem(self, "Limpiar campo", "Campo:",
                                         ["title", "artist", "album", "albumartist", "genre", "date",
                                          "composer", "comment", "lyrics", "tracknumber", "discnumber"], 0, False)
        if not ok:
            return
        reply = QMessageBox.question(self, "Confirmar", f"¿Limpiar '{field}' en {len(items)} archivos?")
        if reply != QMessageBox.Yes:
            return
        ta.clear_field(items, field)
        self._refresh_after_batch()

    def _batch_search_replace(self):
        items = self._selected_tags()
        if not items:
            return
        field, ok = QInputDialog.getItem(self, "Buscar/reemplazar", "Campo:",
                                         ["title", "artist", "album", "albumartist", "genre", "composer", "comment"],
                                         0, False)
        if not ok:
            return
        old, ok = QInputDialog.getText(self, "Buscar", "Texto a buscar:")
        if not ok:
            return
        new, ok = QInputDialog.getText(self, "Reemplazar", "Reemplazar por:")
        if not ok:
            return
        ta.search_replace(items, field, old, new)
        self._refresh_after_batch()

    def _refresh_after_batch(self):
        self._dirty_count = sum(1 for t in self._tags if t.dirty)
        self._rebuild_navigator()
        self._populate_table()
        self._update_inspector()
        self.metadata_changed.emit()

    # ═══════════════════════════════════════════════════════
    # File loading
    # ═══════════════════════════════════════════════════════

    def load_files(self, filepaths: list[str]):
        tags = []
        for fp in filepaths:
            ext = os.path.splitext(fp)[1].lower()
            if ext not in AUDIO_EXTS:
                continue
            tag = read_tags(fp)
            tags.append(tag)

        self._tags = tags
        self._dirty_count = 0
        self._selected_indices = []
        self._filter_key = "all"
        self._rebuild_navigator()
        self._populate_table()
        self._clear_inspector()

        if not self._tags:
            self._show_empty_dashboard()

    def _open_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Abrir archivos de audio", "",
            "Audio (*.mp3 *.flac *.ogg *.opus *.m4a *.mp4 *.wav *.aiff *.aif *.ape);;Todos (*.*)")
        if paths:
            self.load_files(paths)

    def _open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Abrir carpeta musical")
        if not folder:
            return
        files = []
        for root, _, fnames in os.walk(folder):
            for fn in fnames:
                if os.path.splitext(fn)[1].lower() in AUDIO_EXTS:
                    files.append(os.path.join(root, fn))

        if not files:
            QMessageBox.information(self, "Sin archivos", "No se encontraron archivos de audio en esta carpeta.")
            return

        reply = QMessageBox.question(self, "Cargar carpeta",
                                     f"Se encontraron {len(files)} archivos de audio.\n¿Cargarlos todos?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.load_files(files)

    # ═══════════════════════════════════════════════════════
    # Save
    # ═══════════════════════════════════════════════════════

    def _save_all(self):
        dirty = [t for t in self._tags if t.dirty]
        if not dirty:
            return

        changed_fields = set()
        for t in dirty:
            changed_fields.update(t.dirty_fields)
        fields_str = ", ".join(sorted(changed_fields)[:8])

        reply = QMessageBox.question(
            self, "Guardar cambios",
            f"Se guardarán cambios en {len(dirty)} archivos.\n"
            f"Campos: {fields_str}\n\n¿Confirmar?",
            QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        saved = []
        failed = 0
        for tag in dirty:
            if write_tags(tag):
                saved.append(tag.filepath)
            else:
                failed += 1

        self._dirty_count = sum(1 for t in self._tags if t.dirty)
        self._rebuild_navigator()
        self._populate_table()

        if saved:
            self.files_saved.emit(saved)
            self.request_library_refresh.emit()
        if failed:
            QMessageBox.warning(self, "Errores al guardar", f"{failed} archivos no se pudieron guardar.")

    def _revert_all(self):
        for tag in self._tags:
            tag.revert()
        self._dirty_count = 0
        self._rebuild_navigator()
        self._populate_table()
        self._clear_inspector()

    # ═══════════════════════════════════════════════════════
    # Identify stub
    # ═══════════════════════════════════════════════════════

    def _identify(self):
        QMessageBox.information(self, "Identificar",
                                "Identificación online pendiente de implementar.\n\n"
                                "MusicBrainz y AcoustID estarán disponibles en una actualización futura.")

    # ═══════════════════════════════════════════════════════
    # Artwork
    # ═══════════════════════════════════════════════════════

    def _change_artwork(self):
        if not self._selected_indices:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar carátula", "",
            "Imágenes (*.jpg *.jpeg *.png *.webp);;Todos (*.*)")
        if not path:
            return
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError:
            return

        mime = "image/jpeg" if path.lower().endswith((".jpg", ".jpeg")) else "image/png"

        # Show resize dialog if Pillow available
        if _pillow_available:
            from ui.artwork_picker import ArtworkResizeDialog
            dlg = ArtworkResizeDialog(data, mime, self)
            dlg.artwork_ready.connect(lambda d, m: self._apply_artwork(d, m))
            dlg.use_original.connect(lambda: self._apply_artwork(data, mime))
            dlg.exec()
        else:
            self._apply_artwork(data, mime)

    def _apply_artwork(self, data: bytes, mime: str):
        items = self._selected_tags() if self._selected_indices else []
        if not items:
            return
        multi = len(items) > 1
        if multi:
            reply = QMessageBox.question(
                self, "Aplicar carátula",
                f"¿Aplicar esta carátula a los {len(items)} archivos seleccionados?",
                QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                items = [items[0]]

        for tag in items:
            tag.has_artwork = True
            tag.artwork_mime = mime
            tag.artwork_data = data
            tag.mark_artwork_dirty()

        self._dirty_count = sum(1 for t in self._tags if t.dirty)
        self._rebuild_navigator()
        self._populate_table()
        self._update_inspector()
        self.metadata_changed.emit()

    def _resize_artwork(self):
        if not self._selected_indices:
            return
        idx = self._selected_indices[0]
        if idx >= len(self._tags):
            return
        tag = self._tags[idx]
        if not tag.artwork_data:
            return

        if not _pillow_available:
            QMessageBox.information(self, "Pillow requerido", "Instala Pillow para redimensionar: pip install pillow")
            return

        from ui.artwork_picker import ArtworkResizeDialog
        dlg = ArtworkResizeDialog(tag.artwork_data, tag.artwork_mime or "image/jpeg", self)
        dlg.artwork_ready.connect(lambda d, m: self._apply_artwork(d, m))
        dlg.exec()

    def _remove_artwork(self):
        if not self._selected_indices:
            return
        for idx in self._selected_indices:
            if idx < len(self._tags):
                self._tags[idx].has_artwork = False
                self._tags[idx].artwork_mime = ""
                self._tags[idx].artwork_data = None
                self._tags[idx].mark_artwork_dirty()
        self._dirty_count = sum(1 for t in self._tags if t.dirty)
        self._rebuild_navigator()
        self._populate_table()
        self._update_inspector()
        self.metadata_changed.emit()

    # ═══════════════════════════════════════════════════════
    # Rename dialog
    # ═══════════════════════════════════════════════════════

    def _show_rename_dialog(self):
        items = self._selected_tags()
        if not items:
            if self._tags:
                items = self._tags
            else:
                QMessageBox.information(self, "Renombrar", "Carga archivos primero para usar el renombrador.")
                return

        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLineEdit

        dlg = QDialog(self)
        dlg.setWindowTitle("Renombrar archivos desde tags")
        dlg.setMinimumSize(700, 450)
        dlg.setStyleSheet(f"QDialog {{ background: {_BG}; }}")

        dv = QVBoxLayout(dlg)
        dv.setContentsMargins(20, 20, 20, 16)
        dv.setSpacing(12)

        title_lbl = QLabel("Renombrar archivos")
        title_lbl.setStyleSheet(f"color: {_TEXT}; font-size: 18px; font-weight: 700; background: transparent;")
        dv.addWidget(title_lbl)

        # Pattern
        pat_row = QHBoxLayout()
        pat_row.addWidget(self._label("Patrón:"))
        self._rename_pattern = QLineEdit("%artist% - %title%")
        self._rename_pattern.setStyleSheet(_FIELD_CSS)
        pat_row.addWidget(self._rename_pattern)
        dv.addLayout(pat_row)

        # Templates
        tmpl_row = QHBoxLayout()
        tmpl_row.addWidget(self._label("Plantillas:"))
        self._tmpl_combo = QComboBox()
        self._tmpl_combo.addItems([
            "%artist% - %title%",
            "%artist%/%album%/%track% - %title%",
            "%albumartist%/%album%/%track% - %title%",
            "%genre%/%artist%/%album%/%track% - %title%",
            "%artist% - %album%/%track% - %title%",
            "%track% - %title%",
        ])
        self._tmpl_combo.setStyleSheet(f"""
            QComboBox {{ background: rgba(255,255,255,0.06); color: {_TEXT}; border: 1px solid {_BORDER};
              border-radius: 8px; padding: 6px 10px; }}
            QComboBox QAbstractItemView {{ background: rgba(22,24,31,0.97); color: {_TEXT};
              border: 1px solid {_BORDER}; selection-background-color: rgba(255,255,255,0.10); }}
        """)
        self._tmpl_combo.currentTextChanged.connect(self._rename_pattern.setText)
        tmpl_row.addWidget(self._tmpl_combo)
        dv.addLayout(tmpl_row)

        # Preview button
        prev_btn = QPushButton("Vista previa")
        prev_btn.setStyleSheet(_BTN_CSS)
        dv.addWidget(prev_btn)

        # Preview table
        self._rename_table = QTableWidget()
        self._rename_table.setColumnCount(2)
        self._rename_table.setHorizontalHeaderLabels(["Ruta actual", "Nueva ruta"])
        self._rename_table.setAlternatingRowColors(True)
        self._rename_table.setShowGrid(False)
        self._rename_table.setFrameShape(QFrame.NoFrame)
        self._rename_table.verticalHeader().setVisible(False)
        self._rename_table.horizontalHeader().setStretchLastSection(True)
        self._rename_table.setStyleSheet(f"""
            QTableWidget {{ background: transparent; color: {_TEXT}; border: none;
              alternate-background-color: rgba(255,255,255,0.018); }}
            QHeaderView::section {{
                background: rgba(255,255,255,0.045); color: rgba(255,255,255,0.86);
                border: none; border-bottom: 1px solid rgba(255,255,255,0.03);
                padding: 8px 10px; font-size: 11px; font-weight: 700;
            }}
        """)
        dv.addWidget(self._rename_table)

        # Run preview
        def _do_preview():
            pattern = self._rename_pattern.text().strip()
            if not pattern:
                return
            preview = preview_rename(items, pattern)
            self._rename_table.setRowCount(len(preview))
            for i, (old, new) in enumerate(preview):
                self._rename_table.setItem(i, 0, QTableWidgetItem(old))
                self._rename_table.setItem(i, 1, QTableWidgetItem(new))

        prev_btn.clicked.connect(_do_preview)
        _do_preview()

        # Apply button
        btn_box = QDialogButtonBox()
        cancel_btn = btn_box.addButton("Cancelar", QDialogButtonBox.RejectRole)
        apply_btn = btn_box.addButton("Renombrar", QDialogButtonBox.AcceptRole)
        apply_btn.setStyleSheet(_BTN_CSS)
        cancel_btn.setStyleSheet(_BTN_CSS)
        btn_box.accepted.connect(lambda: self._do_rename(items, dlg))
        btn_box.rejected.connect(dlg.reject)
        dv.addWidget(btn_box)

        dlg.exec()

    def _do_rename(self, items, dlg):
        pattern = self._rename_pattern.text().strip()
        preview = preview_rename(items, pattern)
        reply = QMessageBox.question(
            self, "Confirmar renombrado",
            f"Se renombrarán {len(preview)} archivos.\n\n¿Confirmar?",
            QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        ok, fail = apply_rename(preview)
        if ok:
            self._toast_info(f"{ok} archivos renombrados")
        if fail:
            QMessageBox.warning(self, "Errores", f"{fail} archivos no se pudieron renombrar.")
        dlg.accept()

    def _toast_info(self, msg: str):
        try:
            pass
        except Exception:
            import logging
        logging.getLogger("michi").debug("Metadata editor: non-critical op failed")
        # Try to emit the signal so the parent can toast
        self.metadata_changed.emit()

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {_TEXT2}; font-size: 11.5px; background: transparent;")
        return lbl

    # ═══════════════════════════════════════════════════════
    # Drag & Drop
    # ═══════════════════════════════════════════════════════

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        paths = []
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if os.path.isfile(p):
                if os.path.splitext(p)[1].lower() in AUDIO_EXTS:
                    paths.append(p)
            elif os.path.isdir(p):
                for root, _, fnames in os.walk(p):
                    for fn in fnames:
                         if os.path.splitext(fn)[1].lower() in AUDIO_EXTS:
                            paths.append(os.path.join(root, fn))
        if paths:
            self.load_files(paths)

    # ═══════════════════════════════════════════════════════
    # Smart Tagging + Library Doctor
    # ═══════════════════════════════════════════════════════

    def _toggle_smart_tagging(self):
        visible = not self._tools_tabs.isVisible()
        self._tools_tabs.setVisible(visible)
        if visible and self._tags:
            self._tools_tabs.setCurrentIndex(0)
            self._st_panel.set_loading(True)
            self._run_smart_tagging()

    def _run_smart_tagging(self):
        suggestions = []
        try:
            if self._tags:
                for i, tags in enumerate(self._tags):
                    artist = getattr(tags, 'artist', '') or ''
                    title = getattr(tags, 'title', '') or ''
                    album = getattr(tags, 'album', '') or ''
                    genre = getattr(tags, 'genre', '') or ''

                    if artist is None:
                        artist = ""
                    if title is None:
                        title = ""
                    if album is None:
                        album = ""

                    if title or artist:
                        base = "track"
                        if i == 0 and len(self._tags) > 1:
                            base = "selection"

                        if title:
                            track = type('Track', (), {
                                'title': title, 'artist': artist,
                                'album': album, 'genre': genre,
                                'track_number': getattr(tags, 'tracknumber', '') or '',
                                'duration': getattr(tags, 'duration', 0) or 0,
                            })()
                            for sug in self._st_service.suggest_for_track(track):
                                sug.target_index = i
                                sug.scope = base
                                suggestions.append(sug)

                        if album and i == 0:
                            for sug in self._st_service.suggest_for_album(artist, album):
                                sug.target_index = None
                                sug.scope = "album"
                                suggestions.append(sug)

                        if artist and i == 0:
                            norm = self._st_service.normalize_artist_name(artist)
                            if norm.confidence > 0:
                                norm.target_index = i
                                norm.scope = base
                                suggestions.append(norm)

                        if genre and i == 0 and self._tags:
                            genre_sug = self._st_service.suggest_genre(tags)
                            if genre_sug.confidence > 0:
                                genre_sug.target_index = i
                                genre_sug.scope = base
                                suggestions.append(genre_sug)
        except Exception:
            import logging
            logging.getLogger("michi").warning("Smart tagging failed", exc_info=True)

        self._st_panel.set_loading(False)
        self._st_panel.set_suggestions(suggestions)

    def _on_st_suggestions_accepted(self, suggestions):
        import contextlib
        if not self._tags:
            return
        for sug in suggestions:
            if not sug.apply or not sug.suggested:
                continue
            field = sug.field
            value = sug.suggested
            field_map = {"album": "album", "year": "date", "mb_album_id": "musicbrainz_albumid", "cover_url": ""}
            tag_field = field_map.get(field, field)
            if not tag_field:
                continue

            if sug.target_index is not None and sug.scope == "track":
                if sug.target_index < len(self._tags):
                    with contextlib.suppress(Exception):
                        self._tags[sug.target_index].set_field(tag_field, value)
            elif sug.scope == "album":
                for tags in self._tags:
                    with contextlib.suppress(Exception):
                        tags.set_field(tag_field, value)
            elif sug.scope == "selection":
                for i, tags in enumerate(self._tags):
                    if i == sug.target_index or sug.target_index is None:
                        with contextlib.suppress(Exception):
                            tags.set_field(tag_field, value)
            else:
                for tags in self._tags:
                    with contextlib.suppress(Exception):
                        tags.set_field(tag_field, value)

        if hasattr(self, '_rebuild_after_load'):
            self._rebuild_after_load()
        self._tools_tabs.setVisible(False)

    def _on_scan_library(self):
        self._doctor_panel.set_loading(True)
        try:
            from ui.audio_lab.services.library_doctor import LibraryDoctor
            from library.library_db import LibraryDB
            db = LibraryDB()
            doctor = LibraryDoctor(db)
            scan = doctor.scan_all()
            repair = doctor.generate_repair_plan()
        except Exception:
            import logging
            logging.getLogger("michi").warning("Library Doctor failed", exc_info=True)
            scan = {}
            repair = {"total_issues": 0, "fixable": 0, "suggestions": []}
        self._doctor_panel.set_loading(False)
        self._doctor_panel.show_results(scan, repair)
