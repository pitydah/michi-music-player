"""DSPPage — control panel for audio output profiles, upsampling, and room correction.

Connects to existing audio profiles (output_profiles.py), DspState, and EQ system.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QComboBox, QCheckBox,
    QScrollArea, QFileDialog,
)

from ui.central.central_styles import (
    glass_card_qss, glass_button_qss, glass_combo_qss,
)
from core.settings_manager import get_str, get_bool, set_

logger = logging.getLogger("michi.dsp.ui")


class DSPPage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("dspPage")
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

        title = QLabel("Perfiles de Salida")
        title.setStyleSheet(
            "color: rgba(255,255,255,0.92); font-size: 22px; "
            "font-weight: 700; background: transparent;"
        )
        cl.addWidget(title)

        sub = QLabel(
            "EXPERIMENTAL — Controla la ruta de audio: perfil de salida, "
            "upsampling, corrección de sala y estado del DAC.\n"
            "Upsampling y Room Correction son solo UI preliminar — "
            "no están conectados al pipeline de audio."
        )
        sub.setStyleSheet(
            "color: rgba(255,255,255,0.56); font-size: 13px; "
            "background: transparent;"
        )
        sub.setWordWrap(True)
        cl.addWidget(sub)

        # ── Current status ──
        self._status_card = self._build_card("Estado actual", self._build_status_panel())
        cl.addWidget(self._status_card)

        # ── Output profile ──
        self._profile_card = self._build_card("Perfil de salida", self._build_profile_panel())
        cl.addWidget(self._profile_card)

        # ── Upsampling ──
        self._upsample_card = self._build_card("Upsampling", self._build_upsample_panel())
        cl.addWidget(self._upsample_card)

        # ── Room correction ──
        self._room_card = self._build_card("Corrección de sala", self._build_room_panel())
        cl.addWidget(self._room_card)

        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        self._refresh_status()

    def _build_card(self, card_title: str, panel: QWidget) -> QFrame:
        card = QFrame()
        card.setObjectName(f"dspCard_{card_title[:20]}")
        card.setStyleSheet(glass_card_qss(card.objectName(), "base"))
        vl = QVBoxLayout(card)
        vl.setContentsMargins(20, 16, 20, 16)
        vl.setSpacing(10)

        t = QLabel(card_title)
        t.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 15px; "
            "font-weight: 600; background: transparent; border: none;"
        )
        vl.addWidget(t)
        vl.addWidget(panel)
        return card

    def _build_status_panel(self) -> QWidget:
        w = QWidget()
        wl = QVBoxLayout(w)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(4)

        self._status_lines = {}
        for label, key in [
            ("Perfil activo", "profile"),
            ("Bit-perfect", "bitperfect"),
            ("Resample", "resample"),
            ("EQ", "eq"),
            ("ReplayGain", "replaygain"),
            ("Upsampling", "upsampling"),
            ("Room Correction", "room"),
            ("Dispositivo", "device"),
        ]:
            row = QHBoxLayout()
            lbl = QLabel(f"{label}:")
            lbl.setStyleSheet(
                "color: rgba(255,255,255,0.56); font-size: 11px; "
                "background: transparent;"
            )
            val = QLabel("--")
            val.setStyleSheet(
                "color: rgba(255,255,255,0.78); font-size: 11px; "
                "font-weight: 600; background: transparent;"
            )
            row.addWidget(lbl)
            row.addWidget(val, 1)
            wl.addLayout(row)
            self._status_lines[key] = val

        self._refresh_btn = QPushButton("Actualizar estado")
        self._refresh_btn.setCursor(Qt.PointingHandCursor)
        self._refresh_btn.setStyleSheet(glass_button_qss("ghost"))
        self._refresh_btn.clicked.connect(self._refresh_status)
        wl.addWidget(self._refresh_btn)
        return w

    def _build_profile_panel(self) -> QWidget:
        w = QWidget()
        wl = QHBoxLayout(w)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(10)

        from audio.output_profiles import PROFILES
        self._profile_combo = QComboBox()
        self._profile_combo.setStyleSheet(glass_combo_qss())
        for key, prof in PROFILES.items():
            label = f"{prof.name} {'🔒' if prof.bitperfect else ''}"
            self._profile_combo.addItem(label, key)
        current = get_str("audio/profile", "standard")
        for i in range(self._profile_combo.count()):
            if self._profile_combo.itemData(i) == current:
                self._profile_combo.setCurrentIndex(i)
                break

        wl.addWidget(self._profile_combo)

        self._apply_profile_btn = QPushButton("Aplicar")
        self._apply_profile_btn.setCursor(Qt.PointingHandCursor)
        self._apply_profile_btn.setStyleSheet(glass_button_qss("primary"))
        self._apply_profile_btn.clicked.connect(self._apply_profile)
        wl.addWidget(self._apply_profile_btn)

        self._bitperfect_btn = QPushButton("Modo Bit-perfect")
        self._bitperfect_btn.setCursor(Qt.PointingHandCursor)
        self._bitperfect_btn.setStyleSheet(glass_button_qss("secondary"))
        self._bitperfect_btn.clicked.connect(self._set_bitperfect)
        wl.addWidget(self._bitperfect_btn)

        wl.addStretch()
        return w

    def _build_upsample_panel(self) -> QWidget:
        w = QWidget()
        wl = QVBoxLayout(w)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(8)

        row = QHBoxLayout()
        self._upsample_enable = QCheckBox("Activar upsampling")
        self._upsample_enable.setEnabled(False)
        self._upsample_enable.setStyleSheet(
            "color: rgba(255,255,255,0.42); font-size: 12px; "
            "background: transparent;"
        )
        row.addWidget(self._upsample_enable)

        self._upsample_rate = QComboBox()
        self._upsample_rate.setEnabled(False)
        self._upsample_rate.setStyleSheet(glass_combo_qss())
        for label, sr in [("2x (88.2/96 kHz)", 2), ("4x (176.4/192 kHz)", 4)]:
            self._upsample_rate.addItem(label, sr)
        row.addWidget(self._upsample_rate)
        row.addStretch()
        wl.addLayout(row)

        hint = QLabel(
            "⚠ UI preliminar — el upsampling no está conectado "
            "al pipeline de GStreamer. Esta sección es solo "
            "interfaz de configuración futura."
        )
        hint.setStyleSheet(
            "color: rgba(255,255,255,0.42); font-size: 11px; "
            "background: transparent;"
        )
        hint.setWordWrap(True)
        wl.addWidget(hint)
        return w

    def _build_room_panel(self) -> QWidget:
        w = QWidget()
        wl = QVBoxLayout(w)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(8)

        row = QHBoxLayout()
        self._room_enable = QCheckBox("Activar corrección de sala")
        self._room_enable.setEnabled(False)
        self._room_enable.setStyleSheet(
            "color: rgba(255,255,255,0.42); font-size: 12px; "
            "background: transparent;"
        )
        row.addWidget(self._room_enable)

        self._room_file_btn = QPushButton("Cargar impulso WAV...")
        self._room_file_btn.setEnabled(False)
        self._room_file_btn.setCursor(Qt.PointingHandCursor)
        self._room_file_btn.setStyleSheet(glass_button_qss("secondary"))
        self._room_file_btn.clicked.connect(self._load_impulse)
        row.addWidget(self._room_file_btn)

        self._room_file_label = QLabel("(ninguno)")
        self._room_file_label.setStyleSheet(
            "color: rgba(255,255,255,0.50); font-size: 11px; "
            "background: transparent;"
        )
        row.addWidget(self._room_file_label, 1)
        row.addStretch()
        wl.addLayout(row)

        hint = QLabel(
            "⚠ UI preliminar — la convolución FIR no está implementada. "
            "Seleccionar un WAV no activa la corrección de sala. "
            "Pendiente de motor FIR."
        )
        hint.setStyleSheet(
            "color: rgba(255,255,255,0.42); font-size: 11px; "
            "background: transparent;"
        )
        hint.setWordWrap(True)
        wl.addWidget(hint)
        return w

    # ── Actions ──

    def _refresh_status(self):
        try:
            profile_key = get_str("audio/profile", "standard")
            from audio.output_profiles import PROFILES
            prof = PROFILES.get(profile_key)
            self._status_lines["profile"].setText(
                prof.name if prof else profile_key
            )
            self._status_lines["bitperfect"].setText(
                "Sí" if prof and prof.bitperfect else "No"
            )
            self._status_lines["resample"].setText(
                "Permitido" if get_bool("audio/allow_resample", False)
                else "No permitido"
            )
            self._status_lines["eq"].setText(
                "Activo" if get_bool("audio/eq/enabled", False) else "Inactivo"
            )
            self._status_lines["replaygain"].setText(
                get_str("audio/replaygain/mode", "off")
            )
            self._status_lines["device"].setText(
                get_str("audio/output_device", "auto")
            )
        except Exception as e:
            logger.warning("Status refresh error: %s", e)

    def _apply_profile(self):
        key = self._profile_combo.currentData()
        if key:
            set_("audio/profile", key)
            self._refresh_status()
            logger.info("Audio profile set to: %s", key)

    def _set_bitperfect(self):
        set_("audio/profile", "bitperfect_pcm")
        set_("audio/allow_resample", False)
        for i in range(self._profile_combo.count()):
            if self._profile_combo.itemData(i) == "bitperfect_pcm":
                self._profile_combo.setCurrentIndex(i)
                break
        self._refresh_status()
        logger.info("Bit-perfect mode activated")

    def _load_impulse(self):
        fp, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar respuesta al impulso", "",
            "WAV (*.wav)"
        )
        if fp:
            self._room_file_label.setText(fp.split("/")[-1])
            logger.info("Impulse response loaded: %s", fp)
