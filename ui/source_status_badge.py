"""Source status badge — rotating dynamic badge under the volume slider."""
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import QPushButton


_CATEGORY_STYLES = {
    "unknown": {
        "bg": "rgba(255,255,255,0.060)",
        "border": "rgba(255,255,255,0.100)",
        "dot": "rgba(180,180,180,0.90)",
    },
    "lossy": {
        "bg": "rgba(255,170,60,0.105)",
        "border": "rgba(255,170,60,0.220)",
        "dot": "#FFB454",
    },
    "lossless": {
        "bg": "rgba(80,150,255,0.110)",
        "border": "rgba(80,150,255,0.240)",
        "dot": "#5CA8FF",
    },
    "hires": {
        "bg": "rgba(70,220,130,0.120)",
        "border": "rgba(70,220,130,0.280)",
        "dot": "#55E28A",
    },
    "dsd": {
        "bg": "rgba(180,120,255,0.120)",
        "border": "rgba(180,120,255,0.280)",
        "dot": "#B985FF",
    },
    "error": {
        "bg": "rgba(255,80,80,0.110)",
        "border": "rgba(255,80,80,0.260)",
        "dot": "#FF6868",
    },
}


class SourceStatusBadge(QPushButton):
    clicked_details = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sourceStatusBadge")
        self.setCursor(Qt.PointingHandCursor)
        self.setFlat(True)
        self._quality_cat = "unknown"
        self._apply_style()

        self._pages: list[str] = []
        self._page_index = 0
        self._source = ""
        self._timer = QTimer(self)
        self._timer.setInterval(5000)
        self._timer.timeout.connect(self._show_next_page)
        self._hovering = False

    def _apply_style(self):
        s = _CATEGORY_STYLES.get(self._quality_cat, _CATEGORY_STYLES["unknown"])
        self.setStyleSheet(f"""
            QPushButton#sourceStatusBadge {{
                background: {s['bg']};
                color: rgba(255,255,255,0.90);
                border: 1px solid {s['border']};
                border-radius: 12px;
                padding: 4px 14px 4px 10px;
                font-size: 10.5px;
                font-weight: 700;
                letter-spacing: 0.35px;
                min-height: 24px;
                min-width: 124px;
                max-width: 176px;
            }}
            QPushButton#sourceStatusBadge:hover {{
                background: rgba(255,255,255,0.090);
                border: 1px solid rgba(255,255,255,0.165);
                color: #FFFFFF;
            }}
            QPushButton#sourceStatusBadge[source="streaming"] {{
                background: rgba(255,255,255,0.075);
                border: 1px solid rgba(255,255,255,0.16);
            }}
            QPushButton#sourceStatusBadge[source="transmitting"] {{
                background: rgba(52,199,89,0.13);
                border: 1px solid rgba(52,199,89,0.28);
                color: #BFFFD0;
            }}
            QPushButton#sourceStatusBadge[source="error"] {{
                background: rgba(255,69,58,0.13);
                border: 1px solid rgba(255,69,58,0.28);
                color: #FFB4AE;
            }}
        """)

    def set_quality_category(self, category: str):
        """Set the quality category for color styling."""
        if category in _CATEGORY_STYLES:
            self._quality_cat = category
            self._apply_style()
            self.style().unpolish(self)
            self.style().polish(self)

    def set_text(self, text: str):
        """Set badge text with a colored dot prefix."""
        prefix = "\u25cf "  # ● unicode bullet — visible for ALL categories
        display = prefix + text.strip()
        self.setText(display)

    def set_context(self, **kwargs):
        """Set all context at once."""
        self._context = kwargs
        self._build_pages()

    def set_route_tooltip(self, diag):
        """Set tooltip from audio route diagnostics."""
        lines = [str(self.text()).strip()]
        if diag:
            if hasattr(diag, 'to_tooltip'):
                lines.append(diag.to_tooltip())
            elif isinstance(diag, dict):
                bp = diag.get("bitperfect_status", "unknown")
                lines.append(f"Bit-Perfect: {bp.upper()}")
                if diag.get("profile"):
                    lines.append(f"Perfil: {diag['profile']}")
        self.setToolTip("\n".join(lines))

    def _build_pages(self):
        ctx = getattr(self, '_context', {})
        pages = []
        source_type = ctx.get("source_type", "local_file")
        quality = ctx.get("quality", "")
        service = ctx.get("service", "")
        codec = ctx.get("codec", "")
        bitrate = ctx.get("bitrate", "")
        sample_rate = ctx.get("sample_rate", "")
        bit_depth = ctx.get("bit_depth", "")
        filepath = ctx.get("filepath", "")
        audio_output = ctx.get("audio_output", "")
        transmitting = ctx.get("transmitting", False)
        transmit_device = ctx.get("transmit_device", "")
        identifier_state = ctx.get("identifier_state", "")
        replaygain = ctx.get("replaygain", "")

        if not source_type:
            pages = ["SIN REPRODUCCIÓN"]
        elif source_type == "local_file":
            if quality:
                pages.append(f"LOCAL · {quality}")
            else:
                pages.append("LOCAL")
            if codec and sample_rate:
                detail = f"{codec}"
                if bit_depth:
                    detail += f" · {bit_depth}-bit"
                detail += f" · {sample_rate}"
                pages.append(detail)
            elif bitrate:
                pages.append(f"{codec} · {bitrate}" if codec else f"{bitrate}")
            if filepath:
                import os
                pages.append(f"ARCHIVO · {os.path.basename(filepath)[:20]}")
        elif source_type == "radio":
            pages.append("STREAMING · RADIO")
            if service:
                pages.append(service[:22])
            if quality:
                pages.append(quality[:22])
            if identifier_state:
                pages.append(f"IDENTIFICADOR · {identifier_state}")
        elif source_type in ("navidrome", "jellyfin"):
            label = source_type.upper()
            pages.append(f"STREAMING · {label}")
            if service:
                pages.append(f"SERVIDOR · {service[:22]}")
            if quality:
                pages.append(quality[:22])
        elif source_type == "remote_stream":
            pages.append("STREAMING")
            if quality:
                pages.append(quality[:22])

        if transmitting and transmit_device:
            pages.append(f"TRANSMITIENDO · {transmit_device[:18]}")

        if audio_output:
            pages.append(f"SALIDA · {audio_output[:22]}")

        if replaygain:
            pages.append(f"REPLAYGAIN · {replaygain}")

        if not pages:
            pages = [""]

        self.setProperty("source", "streaming" if source_type in ("radio", "navidrome", "jellyfin", "remote_stream") else
                         "transmitting" if transmitting else "")
        self.style().unpolish(self)
        self.style().polish(self)

        self._pages = pages
        self._page_index = 0

        if pages:
            self.set_text(pages[0])

        if len(pages) > 1:
            self._timer.start()
        else:
            self._timer.stop()

        # Tooltip
        parts = []
        if source_type == "local_file":
            parts.append("Fuente: Archivo local")
        elif source_type == "radio":
            parts.append("Fuente: Radio")
        elif source_type in ("navidrome", "jellyfin"):
            parts.append(f"Fuente: {source_type}")
        if service:
            parts.append(f"Servicio: {service}")
        if quality:
            parts.append(f"Calidad: {quality}")
        if audio_output:
            parts.append(f"Salida: {audio_output}")
        if transmitting:
            parts.append(f"Transmisión: {transmit_device}")
        if filepath:
            parts.append(f"Ruta: {filepath[:60]}")
        self.setToolTip("\n".join(parts))

    def _show_next_page(self):
        if self._hovering or not self._pages:
            return
        self._page_index = (self._page_index + 1) % len(self._pages)
        self.set_text(self._pages[self._page_index])

    def enterEvent(self, event):
        self._hovering = True
        self._timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovering = False
        if len(self._pages) > 1:
            self._timer.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self.clicked_details.emit()
        super().mousePressEvent(event)
