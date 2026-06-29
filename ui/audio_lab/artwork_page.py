"""ArtworkPage — manage album artwork: view, search local, replace, embed."""

from __future__ import annotations

import logging
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QFileDialog, QScrollArea,
    QListWidget, QProgressBar, QMessageBox,
)

from ui.central.central_styles import (
    glass_card_qss, glass_button_qss, glass_progress_qss,
)

logger = logging.getLogger("michi.artwork.ui")


class ArtworkPage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("artworkPage")
        self._resolver = None
        self._current_album = ""
        self._current_artist = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(40, 32, 40, 32)
        cl.setSpacing(16)

        title = QLabel("Carátulas")
        title.setStyleSheet(
            "color: rgba(255,255,255,0.92); font-size: 22px; "
            "font-weight: 700; background: transparent;"
        )
        cl.addWidget(title)

        sub = QLabel(
            "Gestiona las carátulas de tu biblioteca: busca, "
            "reemplaza e incrusta imágenes en tus archivos de música."
        )
        sub.setStyleSheet(
            "color: rgba(255,255,255,0.56); font-size: 13px; "
            "background: transparent;"
        )
        sub.setWordWrap(True)
        cl.addWidget(sub)

        # Current artwork display
        art_card = QFrame()
        art_card.setStyleSheet(glass_card_qss("artDisplayCard"))
        avl = QVBoxLayout(art_card)
        avl.setContentsMargins(20, 16, 20, 16)
        avl.setSpacing(10)

        art_top = QHBoxLayout()
        self._art_preview = QLabel()
        self._art_preview.setFixedSize(200, 200)
        self._art_preview.setAlignment(Qt.AlignCenter)
        self._art_preview.setStyleSheet(
            "background: rgba(255,255,255,0.03); "
            "border: 1px solid rgba(255,255,255,0.06); "
            "border-radius: 12px;"
        )
        art_top.addWidget(self._art_preview)

        art_info = QVBoxLayout()
        self._art_status = QLabel("Selecciona un álbum para ver su carátula.")
        self._art_status.setStyleSheet(
            "color: rgba(255,255,255,0.62); font-size: 12px; "
            "background: transparent;"
        )
        self._art_status.setWordWrap(True)
        art_info.addWidget(self._art_status)

        art_info.addStretch()

        self._replace_btn = QPushButton("Reemplazar desde archivo...")
        self._replace_btn.setCursor(Qt.PointingHandCursor)
        self._replace_btn.setStyleSheet(glass_button_qss("secondary"))
        self._replace_btn.clicked.connect(self._replace_artwork)
        art_info.addWidget(self._replace_btn)

        self._embed_btn = QPushButton("Incrustar en archivos")
        self._embed_btn.setCursor(Qt.PointingHandCursor)
        self._embed_btn.setStyleSheet(glass_button_qss("primary"))
        self._embed_btn.clicked.connect(self._embed_artwork)
        art_info.addWidget(self._embed_btn)

        art_top.addLayout(art_info, 1)
        avl.addLayout(art_top)

        cl.addWidget(art_card)

        # Albums without artwork
        missing_card = QFrame()
        missing_card.setStyleSheet(glass_card_qss("artMissingCard"))
        mvl = QVBoxLayout(missing_card)
        mvl.setContentsMargins(20, 16, 20, 16)
        mvl.setSpacing(10)

        ml = QLabel("Álbumes sin carátula")
        ml.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 14px; "
            "font-weight: 600; background: transparent;"
        )
        mvl.addWidget(ml)

        self._scan_missing_btn = QPushButton("Detectar álbumes sin carátula")
        self._scan_missing_btn.setCursor(Qt.PointingHandCursor)
        self._scan_missing_btn.setStyleSheet(glass_button_qss("secondary"))
        self._scan_missing_btn.clicked.connect(self._scan_missing)
        mvl.addWidget(self._scan_missing_btn)

        self._missing_list = QListWidget()
        self._missing_list.setStyleSheet(
            "QListWidget { background: rgba(255,255,255,0.02); "
            "border: 1px solid rgba(255,255,255,0.04); "
            "border-radius: 8px; color: rgba(255,255,255,0.72); "
            "font-size: 11px; min-height: 100px; }"
        )
        mvl.addWidget(self._missing_list)

        self._missing_progress = QProgressBar()
        self._missing_progress.setRange(0, 100)
        self._missing_progress.setValue(0)
        self._missing_progress.setVisible(False)
        self._missing_progress.setStyleSheet(glass_progress_qss())
        mvl.addWidget(self._missing_progress)

        cl.addWidget(missing_card)
        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _get_resolver(self):
        if self._resolver is None:
            from ui.audio_lab.services.artwork_resolver import ArtworkResolver
            self._resolver = ArtworkResolver()
        return self._resolver

    def _replace_artwork(self):
        fp, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar imagen", "",
            "Imágenes (*.jpg *.jpeg *.png *.gif *.webp *.bmp)"
        )
        if not fp:
            return

        pix = QPixmap(fp)
        if pix.isNull():
            QMessageBox.warning(self, "Carátulas", "No se pudo cargar la imagen.")
            return

        scaled = pix.scaled(
            200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self._art_preview.setPixmap(scaled)
        self._art_status.setText(
            f"Imagen cargada: {os.path.basename(fp)}\n"
            f"{pix.width()}x{pix.height()} px"
        )
        self._new_artwork_path = fp

    def _embed_artwork(self):
        fp = getattr(self, '_new_artwork_path', None)
        if not fp or not os.path.exists(fp):
            QMessageBox.information(
                self, "Carátulas",
                "Selecciona una imagen primero con 'Reemplazar desde archivo'."
            )
            return

        try:
            from ui.audio_lab.services.tag_writer import TagWriter
            tw = TagWriter()
            tw.embed_cover("", fp)
            self._art_status.setText("Carátula incrustada correctamente.")
            logger.info("Artwork embedded from %s", fp)
        except Exception as e:
            logger.exception("Failed to embed artwork")
            QMessageBox.warning(self, "Error", f"No se pudo incrustar: {e}")

    def _scan_missing(self):
        self._missing_list.clear()
        self._missing_progress.setVisible(True)
        self._missing_progress.setValue(0)

        try:
            from library.library_db import LibraryDB, DB_PATH
            db = LibraryDB(DB_PATH)
            rows = db._conn.execute(
                "SELECT DISTINCT album, albumartist, directory "
                "FROM media_items WHERE deleted_at IS NULL "
                "AND album IS NOT NULL AND album != ''"
            ).fetchall()

            resolver = self._get_resolver()
            missing = []
            total = len(rows)

            for i, (album, artist, directory) in enumerate(rows):
                if (i + 1) % 10 == 0:
                    pct = int((i + 1) / total * 100)
                    self._missing_progress.setValue(pct)
                    from PySide6.QtCore import QCoreApplication
                    QCoreApplication.processEvents()

                if not directory or not os.path.isdir(directory):
                    continue

                covers = resolver.search_album_art({
                    "album": album, "artist": artist, "directory": directory,
                })
                if not covers:
                    missing.append(f"{artist} — {album}" if artist else album)

            self._missing_list.clear()
            if missing:
                for entry in missing[:100]:
                    self._missing_list.addItem(entry)
                if len(missing) > 100:
                    self._missing_list.addItem(
                        f"... y {len(missing) - 100} más"
                    )
            else:
                self._missing_list.addItem(
                    "Todos los álbumes tienen carátula."
                )

        except Exception as e:
            logger.exception("Missing artwork scan failed")
            self._missing_list.addItem(f"Error: {e}")

        self._missing_progress.setVisible(False)
