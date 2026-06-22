"""Premium equalizer panel — dark glass, segmented modes, preset chips."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QCheckBox, QMessageBox, QWidget,
)

from audio.eq_basic import GraphicEqWidget
from audio.eq_advanced import AdvancedEqWidget
from audio.eq_curve import EqCurveWidget
from audio.spectrum import SpectrumWidget
from audio.eq_presets import (
    load_graphic_preset, load_parametric_preset,
)
from audio.eq_convert import graphic_to_parametric, parametric_to_graphic

PRESET_LIST = ["Plano", "Rock", "Pop", "Jazz", "Clásica", "Vocal",
               "Bass Boost", "Treble Boost", "Night"]


class EqDialog(QDialog):
    eq_bypass_changed = Signal(bool)
    eq_bands_graphic_changed = Signal(list)
    eq_bands_parametric_changed = Signal(list)
    preamp_changed = Signal(float)
    spectrum_mode_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ecualizador")
        self.resize(950, 640)
        self.setMinimumSize(750, 480)
        self.setStyleSheet("""
            QDialog { background: rgba(15,17,22,0.96); border-radius: 16px;
              border: 1px solid rgba(255,255,255,0.07); }
        """)
        from ui.theme import apply_dialog_shadow
        apply_dialog_shadow(self)
        self._mode = "basic"
        self._ab_state = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # ── Header ──
        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        title_lbl = QLabel("Ecualizador")
        title_lbl.setStyleSheet(
            "font-size: 17px; font-weight: 700; color: rgba(255,255,255,0.94);"
            "background: transparent;")
        subtitle = QLabel("Ajuste fino de frecuencias")
        subtitle.setStyleSheet(
            "font-size: 11.5px; color: rgba(255,255,255,0.48);"
            "background: transparent;")
        title_col.addWidget(title_lbl)
        title_col.addWidget(subtitle)
        header.addLayout(title_col)
        header.addStretch()

        self._status_badge = QLabel("Activo")
        self._status_badge.setStyleSheet(
            "background: rgba(255,122,0,0.12); color: #FF7A00;"
            "border: 1px solid rgba(255,122,0,0.22); border-radius: 8px;"
            "padding: 3px 10px; font-size: 11px; font-weight: 600;")
        header.addWidget(self._status_badge)

        close_btn = QPushButton("×")
        close_btn.setFixedSize(28, 28)
        close_btn.setFlat(True)
        close_btn.setStyleSheet(
            "QPushButton { color: rgba(255,255,255,0.35); font-size: 16px; }"
            "QPushButton:hover { color: #FF3C48; }")
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # ── Mode selector (segmented capsule) ──
        mode_frame = QWidget()
        mode_frame.setStyleSheet("""
            QWidget {
                background: rgba(255,255,255,0.035);
                border: 1px solid rgba(255,255,255,0.075);
                border-radius: 14px; padding: 3px;
            }
        """)
        mode_layout = QHBoxLayout(mode_frame)
        mode_layout.setContentsMargins(3, 3, 3, 3)
        mode_layout.setSpacing(0)

        btn_qss = """
            QPushButton {
                background: transparent; border: 1px solid transparent;
                border-radius: 10px; padding: 6px 16px;
                color: rgba(255,255,255,0.66); font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background: rgba(255,255,255,0.07); color: #fff; }
            QPushButton[active="true"] {
                background: rgba(255,255,255,0.125); color: #fff;
                border: 1px solid rgba(255,255,255,0.12);
            }
        """

        self._bypass_btn = QPushButton("Bypass")
        self._bypass_btn.setCheckable(True)
        self._bypass_btn.setStyleSheet(btn_qss)
        self._bypass_btn.clicked.connect(lambda: self._set_mode("bypass_val"))
        mode_layout.addWidget(self._bypass_btn)

        self._graphic_btn = QPushButton("Gráfico (31 bandas)")
        self._graphic_btn.setCheckable(True)
        self._graphic_btn.setChecked(True)
        self._graphic_btn.setProperty("active", True)
        self._graphic_btn.setStyleSheet(btn_qss)
        self._graphic_btn.style().polish(self._graphic_btn)
        self._graphic_btn.clicked.connect(lambda: self._set_mode("graphic"))
        mode_layout.addWidget(self._graphic_btn)

        self._param_btn = QPushButton("Paramétrico")
        self._param_btn.setCheckable(True)
        self._param_btn.setStyleSheet(btn_qss)
        self._param_btn.clicked.connect(lambda: self._set_mode("parametric"))
        mode_layout.addWidget(self._param_btn)

        mode_layout.addStretch()
        layout.addWidget(mode_frame)

        # ── Spectrum + Curve ──
        self._spectrum = SpectrumWidget()
        layout.addWidget(self._spectrum, 1)

        self._curve = EqCurveWidget()
        layout.addWidget(self._curve, 1)

        # ── EQ bands (basic or advanced) ──
        self._basic = GraphicEqWidget()
        self._advanced = AdvancedEqWidget()
        self._advanced.bands_changed.connect(self._on_advanced_change)
        self._advanced.preamp_changed.connect(self._on_preamp_adv)
        layout.addWidget(self._basic, 3)
        layout.addWidget(self._advanced, 3)
        self._advanced.hide()

        # ── Presets (chips) ──
        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        preset_lbl = QLabel("Presets:")
        preset_lbl.setStyleSheet(
            "color: rgba(255,255,255,0.48); font-size: 11px;"
            "background: transparent;")
        preset_row.addWidget(preset_lbl)

        chip_qss = """
            QPushButton {
                background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.07);
                border-radius: 8px; padding: 5px 12px; color: rgba(255,255,255,0.6);
                font-size: 11px; font-weight: 550;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.08); color: #fff;
                border: 1px solid rgba(255,255,255,0.12);
            }
        """
        for preset_name in PRESET_LIST:
            btn = QPushButton(preset_name)
            btn.setStyleSheet(chip_qss)
            btn.clicked.connect(lambda checked=False, n=preset_name: self._on_preset(n))
            preset_row.addWidget(btn)
        preset_row.addStretch()
        layout.addLayout(preset_row)

        # ── Bottom bar ──
        bottom = QHBoxLayout()
        bottom.setSpacing(8)

        self._bypass_cb = QCheckBox("Activo")
        self._bypass_cb.setChecked(True)
        self._bypass_cb.setStyleSheet(
            "QCheckBox { color: rgba(255,255,255,0.68); font-size: 12px; }")
        self._bypass_cb.toggled.connect(lambda v: self.eq_bypass_changed.emit(not v))
        self._bypass_cb.toggled.connect(
            lambda v: self._status_badge.setText("Activo" if v else "Bypass"))
        self._bypass_cb.toggled.connect(
            lambda v: self._status_badge.setStyleSheet(
                "background: rgba(255,122,0,0.12); color: #FF7A00;"
                "border: 1px solid rgba(255,122,0,0.22); border-radius: 8px;"
                "padding: 3px 10px; font-size: 11px; font-weight: 600;"
                if v else
                "background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.4);"
                "border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;"
                "padding: 3px 10px; font-size: 11px; font-weight: 600;"))
        bottom.addWidget(self._bypass_cb)

        self._spectrum_cb = QCheckBox("Spectrum")
        self._spectrum_cb.setChecked(True)
        self._spectrum_cb.setStyleSheet(
            "QCheckBox { color: rgba(255,255,255,0.55); font-size: 11px; }")
        self._spectrum_cb.toggled.connect(lambda v: self._spectrum.setVisible(v))
        bottom.addWidget(self._spectrum_cb)

        bottom.addStretch()

        self._preamp_lbl = QLabel("Preamp: +0.0dB")
        self._preamp_lbl.setStyleSheet(
            "color: rgba(255,255,255,0.48); font-size: 12px;")
        bottom.addWidget(self._preamp_lbl)

        action_btn_qss = """
            QPushButton {
                background: rgba(255,255,255,0.055); border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px; padding: 7px 14px;
                color: rgba(255,255,255,0.72); font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background: rgba(255,255,255,0.09); color: #fff; }
        """
        save_btn = QPushButton("Guardar")
        save_btn.setStyleSheet(action_btn_qss)
        save_btn.clicked.connect(self._save_preset)
        bottom.addWidget(save_btn)

        reset_btn = QPushButton("Reset")
        reset_btn.setStyleSheet(action_btn_qss)
        reset_btn.clicked.connect(self._reset)
        bottom.addWidget(reset_btn)

        ab_btn = QPushButton("A/B")
        ab_btn.setToolTip("Comparar configuraciones")
        ab_btn.setStyleSheet(action_btn_qss)
        ab_btn.clicked.connect(self._ab_compare)
        bottom.addWidget(ab_btn)

        layout.addLayout(bottom)

        # ── Wire basic sliders ──
        self._basic.bands_changed.connect(self._on_basic_change)

    def _set_mode(self, mode: str):
        if mode == "bypass_val":
            self._bypass_cb.setChecked(not self._bypass_cb.isChecked())
            return

        btn_map = {
            "graphic": (self._graphic_btn, "basic"),
            "parametric": (self._param_btn, "advanced"),
        }
        for m, (btn, _view_mode) in btn_map.items():
            active = (m == mode)
            btn.setChecked(active)
            btn.setProperty("active", active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if mode == "graphic" and self._mode == "advanced":
            configs, preamp = self._advanced.get_config()
            gbands = parametric_to_graphic(configs, preamp)
            self._basic.set_bands(gbands)
        elif mode == "parametric" and self._mode == "basic":
            bands, preamp = graphic_to_parametric(self._basic.get_bands())
            self._advanced.load_preset(bands, preamp)

        self._mode = "basic" if mode == "graphic" else "advanced"
        self._basic.setVisible(self._mode == "basic")
        self._advanced.setVisible(self._mode == "advanced")

    # ── Presets ──

    def _on_preset(self, name: str):
        if self._mode == "basic":
            bands = load_graphic_preset(name)
            self._basic.set_bands(bands)
            self.eq_bands_graphic_changed.emit(bands)
            pbands, _ = graphic_to_parametric(bands)
            self._curve.set_bands(pbands, 0.0)
        else:
            bands = load_parametric_preset(name)
            self._advanced.load_preset(bands, 0.0)
            self.eq_bands_parametric_changed.emit(bands)
            self._curve.set_bands(bands, 0.0)

    def _save_preset(self):
        from audio.eq_presets import save_custom_presets, load_custom_presets
        presets = load_custom_presets()
        if self._mode == "basic":
            presets[f"Custom_{len(presets)}"] = {
                "mode": "graphic",
                "bands": self._basic.get_bands(),
                "preamp": 0.0,
            }
        save_custom_presets(presets)

    def _ab_compare(self):
        if self._ab_state is None:
            if self._mode == "basic":
                self._ab_state = ("basic", self._basic.get_bands(), 0.0)
            else:
                self._ab_state = ("advanced", self._advanced.get_config())
            QMessageBox.information(self, "A/B",
                "Estado A guardado. Modifica el EQ y presiona A/B para comparar.")
        else:
            QMessageBox.information(self, "A/B", "Volviendo al estado A.")
            if self._ab_state[0] == "basic":
                self._basic.set_bands(self._ab_state[1])
            else:
                bands, preamp = self._ab_state[1]
                self._advanced.load_preset(bands, preamp)
            self._ab_state = None

    def _reset(self):
        if self._mode == "basic":
            self._basic.reset()
            self.eq_bands_graphic_changed.emit([0.0] * 31)
        else:
            self._advanced.reset()
            self.eq_bands_parametric_changed.emit([])

    def _on_basic_change(self, idx: int, value: float):
        bands = self._basic.get_bands()
        self.eq_bands_graphic_changed.emit(bands)
        pbands, _ = graphic_to_parametric(bands)
        self._curve.set_bands(pbands, 0.0)

    def _on_advanced_change(self, bands: list):
        self.eq_bands_parametric_changed.emit(bands)
        preamp = self._advanced.get_config()[1]
        self._curve.set_bands(bands, preamp)

    def _on_preamp_adv(self, db: float):
        self._preamp_lbl.setText(f"Preamp: {db:+.1f}dB")
        self.preamp_changed.emit(db)
