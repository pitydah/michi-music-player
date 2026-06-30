"""SongsBulkActionBar — actions bar for multi-selection in songs view."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel

from ui.central.central_styles import glass_button_qss


class SongsBulkActionBar(QWidget):
    """Appears when one or more songs are selected. Offers bulk actions."""

    action_play = Signal(list)
    action_queue = Signal(list)
    action_edit_metadata = Signal(list)
    action_add_to_playlist = Signal(list)
    action_toggle_fav = Signal(object)
    action_analyze = Signal(list)
    action_locate = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_count = 0
        self._setup_ui()
        self.setVisible(False)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self._count_label = QLabel("0 seleccionados")
        self._count_label.setStyleSheet("color: rgba(255,255,255,0.72); font-size: 12px;")
        layout.addWidget(self._count_label)
        layout.addStretch()

        self._play_btn = QPushButton("▶ Reproducir")
        self._play_btn.setStyleSheet(glass_button_qss("primary"))
        self._play_btn.clicked.connect(lambda: self.action_play.emit([]))
        layout.addWidget(self._play_btn)

        self._queue_btn = QPushButton("⊕ Cola")
        self._queue_btn.setStyleSheet(glass_button_qss("primary"))
        self._queue_btn.clicked.connect(lambda: self.action_queue.emit([]))
        layout.addWidget(self._queue_btn)

        self._edit_btn = QPushButton("✎ Editar")
        self._edit_btn.setStyleSheet(glass_button_qss("primary"))
        self._edit_btn.clicked.connect(lambda: self.action_edit_metadata.emit([]))
        layout.addWidget(self._edit_btn)

        self._fav_btn = QPushButton("♥ Favorito")
        self._fav_btn.setStyleSheet(glass_button_qss("primary"))
        self._fav_btn.clicked.connect(lambda: self.action_toggle_fav.emit(None))
        layout.addWidget(self._fav_btn)

        self._analyze_btn = QPushButton("🔬 Analizar")
        self._analyze_btn.setStyleSheet(glass_button_qss("primary"))
        self._analyze_btn.clicked.connect(lambda: self.action_analyze.emit([]))
        layout.addWidget(self._analyze_btn)

        self._locate_btn = QPushButton("📁 Localizar")
        self._locate_btn.setStyleSheet(glass_button_qss("primary"))
        self._locate_btn.clicked.connect(lambda: self.action_locate.emit(None))
        layout.addWidget(self._locate_btn)

    def show_for_selection(self, count: int):
        self._selected_count = count
        self._count_label.setText(f"{count} seleccionados")
        self.setVisible(count > 0)
