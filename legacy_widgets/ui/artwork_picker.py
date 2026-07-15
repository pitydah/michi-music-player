"""Artwork resize dialog — preview and resize album art before embedding."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QCheckBox, QFrame, QGridLayout,
)

from metadata.artwork_utils import (
    _pillow_available, image_info, resize_artwork_bytes,
    make_artwork_pixmap, PRESETS, DEFAULT_SIZE,
)

_BG = "#090B11"
_PANEL = "rgba(255,255,255,0.035)"
_TEXT = "#FFFFFF"
_TEXT2 = "rgba(255,255,255,0.76)"
_TEXT3 = "rgba(255,255,255,0.62)"
_BORDER = "rgba(255,255,255,0.08)"


def _btn_css() -> str:
    return f"""
        QPushButton {{
            background: rgba(255,255,255,0.060); color: {_TEXT};
            border: 1px solid {_BORDER}; border-radius: 10px;
            padding: 8px 14px; font-size: 12px; font-weight: 600;
        }}
        QPushButton:hover {{
            background: rgba(255,255,255,0.095);
            border: 1px solid rgba(255,255,255,0.14);
        }}
    """


class ArtworkResizeDialog(QDialog):
    artwork_ready = Signal(bytes, str)  # data, mime
    use_original = Signal()

    def __init__(self, image_data: bytes, mime: str = "image/jpeg", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Redimensionar carátula")
        self.setMinimumSize(720, 500)
        self.setStyleSheet(f"QDialog {{ background: {_BG}; }}")

        self._original_data = image_data
        self._original_mime = mime
        self._result_data: bytes | None = None
        self._result_mime = mime

        main = QVBoxLayout(self)
        main.setContentsMargins(20, 20, 20, 16)
        main.setSpacing(14)

        if not _pillow_available:
            lbl = QLabel("Instala Pillow para redimensionar carátulas:\npip install pillow")
            lbl.setStyleSheet(f"color: {_TEXT2}; font-size: 13px;")
            lbl.setAlignment(Qt.AlignCenter)
            main.addWidget(lbl)
            return

        info = image_info(image_data) or {}

        # ── Previews row ──
        preview_row = QHBoxLayout()
        preview_row.setSpacing(16)

        # Original
        orig_box = self._make_preview_box("Original", image_data, info)
        preview_row.addWidget(orig_box)

        # Arrow
        arrow = QLabel("→")
        arrow.setStyleSheet(f"color: {_TEXT3}; font-size: 28px; font-weight: 700; background: transparent;")
        preview_row.addWidget(arrow, alignment=Qt.AlignCenter)

        # Result preview
        self._result_preview = self._make_preview_box("Final", image_data, info)
        preview_row.addWidget(self._result_preview)

        main.addLayout(preview_row)

        # ── Controls ──
        ctrl_frame = QFrame()
        ctrl_frame.setStyleSheet(
            f"QFrame {{ background: {_PANEL}; border: 1px solid {_BORDER}; border-radius: 14px; }}")
        ctrl = QGridLayout(ctrl_frame)
        ctrl.setContentsMargins(14, 12, 14, 12)
        ctrl.setSpacing(10)

        # Preset
        ctrl.addWidget(self._label("Tamaño:"), 0, 0)
        self._preset = QComboBox()
        self._preset.addItems(["600 (recomendado)", "300 (liviano)", "1000 (alta calidad)", "1400 (hi-res)", "Original", "Personalizado"])
        self._preset.setCurrentIndex(0)
        self._preset.setStyleSheet(f"""
            QComboBox {{ background: rgba(255,255,255,0.06); color: {_TEXT}; border: 1px solid {_BORDER};
              border-radius: 8px; padding: 6px 10px; }}
            QComboBox:hover {{ border-color: rgba(255,255,255,0.14); }}
            QComboBox QAbstractItemView {{ background: rgba(22,24,31,0.97); color: {_TEXT};
              border: 1px solid {_BORDER}; selection-background-color: rgba(255,255,255,0.10); }}
        """)
        self._preset.currentIndexChanged.connect(self._preview_apply)
        ctrl.addWidget(self._preset, 0, 1)

        self._custom_size = QSpinBox()
        self._custom_size.setRange(100, 4000)
        self._custom_size.setValue(DEFAULT_SIZE)
        self._custom_size.setEnabled(False)
        self._custom_size.setStyleSheet(f"""
            QSpinBox {{ background: rgba(255,255,255,0.06); color: {_TEXT}; border: 1px solid {_BORDER};
              border-radius: 8px; padding: 6px; }}
        """)
        self._custom_size.valueChanged.connect(self._preview_apply)
        ctrl.addWidget(self._custom_size, 0, 2)

        # Format
        ctrl.addWidget(self._label("Formato:"), 1, 0)
        self._fmt = QComboBox()
        self._fmt.addItems(["JPEG", "PNG"])
        self._fmt.currentIndexChanged.connect(self._preview_apply)
        self._fmt.setStyleSheet(self._preset.styleSheet())
        ctrl.addWidget(self._fmt, 1, 1)

        # Quality
        ctrl.addWidget(self._label("Calidad JPEG:"), 1, 2)
        self._quality = QSpinBox()
        self._quality.setRange(30, 100)
        self._quality.setValue(85)
        self._quality.valueChanged.connect(self._preview_apply)
        self._quality.setStyleSheet(self._custom_size.styleSheet())
        ctrl.addWidget(self._quality, 1, 3)

        # Options
        self._crop_cb = QCheckBox("Recortar a cuadrado")
        self._crop_cb.setChecked(True)
        self._crop_cb.setStyleSheet(f"QCheckBox {{ color: {_TEXT2}; font-size: 11.5px; }}")
        self._crop_cb.stateChanged.connect(self._preview_apply)
        ctrl.addWidget(self._crop_cb, 2, 0, 1, 2)

        self._aspect_cb = QCheckBox("Mantener proporción")
        self._aspect_cb.setChecked(True)
        self._aspect_cb.setStyleSheet(f"QCheckBox {{ color: {_TEXT2}; font-size: 11.5px; }}")
        self._aspect_cb.stateChanged.connect(self._preview_apply)
        ctrl.addWidget(self._aspect_cb, 2, 2, 1, 2)

        main.addWidget(ctrl_frame)

        # ── Size warning ──
        ow = info.get("width", 0)
        oh = info.get("height", 0)
        omb = info.get("size_mb", 0)
        if ow > 3000 or oh > 3000 or omb > 5:
            warn = QLabel(f"La imagen es muy grande ({ow}×{oh}, {omb:.1f} MB). Se recomienda redimensionar a 600×600 o 1000×1000.")
            warn.setWordWrap(True)
            warn.setStyleSheet("color: rgba(200,180,100,0.60); font-size: 11px; background: transparent;")
            main.addWidget(warn)

        # ── Buttons ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setStyleSheet(_btn_css())
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        orig_btn = QPushButton("Usar original")
        orig_btn.setStyleSheet(_btn_css())
        orig_btn.clicked.connect(self._on_use_original)
        btn_row.addWidget(orig_btn)

        apply_btn = QPushButton("Aplicar")
        apply_btn.setStyleSheet(_btn_css().replace("0.060", "0.095"))
        apply_btn.clicked.connect(self._on_apply)
        btn_row.addWidget(apply_btn)

        main.addLayout(btn_row)

        self._preview_apply()

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {_TEXT2}; font-size: 11.5px; background: transparent;")
        return lbl

    def _make_preview_box(self, title: str, data: bytes, info: dict) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background: {_PANEL}; border: 1px solid {_BORDER}; border-radius: 14px; }}")
        v = QVBoxLayout(frame)
        v.setContentsMargins(10, 8, 10, 10)
        v.setSpacing(6)

        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {_TEXT}; font-size: 13px; font-weight: 600; background: transparent;")
        v.addWidget(lbl, alignment=Qt.AlignCenter)

        img_lbl = QLabel()
        img_lbl.setFixedSize(200, 200)
        img_lbl.setAlignment(Qt.AlignCenter)
        pix = make_artwork_pixmap(data, 196) if data else None
        if pix and not pix.isNull():
            img_lbl.setPixmap(pix)
        else:
            img_lbl.setText("—")
            img_lbl.setStyleSheet(f"color: {_TEXT3}; font-size: 16px; background: {_PANEL}; border-radius: 12px;")
        img_lbl.setObjectName(f"preview_{title}")
        v.addWidget(img_lbl, alignment=Qt.AlignCenter)

        # Info
        w, h = info.get("width", 0), info.get("height", 0)
        mb = info.get("size_mb", 0)
        info_lbl = QLabel(f"{w}×{h} · {info.get('format','—')} · {mb:.2f} MB")
        info_lbl.setStyleSheet(f"color: {_TEXT3}; font-size: 10.5px; background: transparent;")
        info_lbl.setObjectName(f"info_{title}")
        info_lbl.setAlignment(Qt.AlignCenter)
        v.addWidget(info_lbl)

        return frame

    def _get_size(self) -> int:
        idx = self._preset.currentIndex()
        if idx == 4:  # Original
            return 99999
        if idx == 5:  # Custom
            return self._custom_size.value()
        keys = list(PRESETS.keys())
        return PRESETS.get(keys[min(idx, len(keys) - 1)], DEFAULT_SIZE)

    def _preview_apply(self):
        max_sz = self._get_size()
        fmt = self._fmt.currentText()
        quality = self._quality.value()
        crop = self._crop_cb.isChecked()
        aspect = self._aspect_cb.isChecked()

        if max_sz >= 9999:
            self._result_data = self._original_data
            self._result_mime = self._original_mime
            info = image_info(self._original_data) or {}
        else:
            result = resize_artwork_bytes(
                self._original_data, max_sz, fmt, quality, crop, aspect)
            if result:
                self._result_data, self._result_mime, info_res = result
                info = {"width": info_res.get("nw", 0), "height": info_res.get("nh", 0),
                        "format": fmt, "size_mb": info_res.get("nf_mb", 0)}
            else:
                return

        # Update result preview
        result_img = self._result_preview.findChild(QLabel, "preview_Final")
        if result_img and self._result_data:
            pix = make_artwork_pixmap(self._result_data, 196)
            if pix:
                result_img.setPixmap(pix)
                result_img.setText("")

        result_info = self._result_preview.findChild(QLabel, "info_Final")
        if result_info:
            w = info.get("width", 0)
            h = info.get("height", 0)
            mb = info.get("size_mb", 0)
            result_info.setText(f"{w}×{h} · {info.get('format','—')} · {mb:.2f} MB")

    def _on_use_original(self):
        self.use_original.emit()
        self.artwork_ready.emit(self._original_data, self._original_mime)
        self.accept()

    def _on_apply(self):
        if self._result_data:
            self.artwork_ready.emit(self._result_data, self._result_mime)
        self.accept()
