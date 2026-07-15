"""AI Assistant chat panel — premium, privacy-focused, with suggested actions panel."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLineEdit, QPushButton, QLabel, QFrame, QSizePolicy,
)

from ui.effects.michi_glass import apply_card_shadow
from ui.central.central_styles import (
    glass_hero_qss, glass_action_card_qss, glass_chip_button_qss,
    empty_state_qss, glass_button_qss, card_title_qss, card_desc_qss,
    glass_input_qss,
)

_PRIVACY_NOTICE = "IA local · Datos protegidos · Sin rutas sensibles"

_PLACEHOLDER = "Pregunta a Michi Assistant..."

_EXAMPLE_CHIPS = [
    "Recomiéndame algo para escuchar",
    "Busca álbumes sin carátula",
    "Crea una playlist tranquila",
    "Revisa metadatos pendientes",
    "Conectar Michi Micro Server",
    "Abrir Home Audio",
]

# Keyword → suggested actions (navigate via window._on_sidebar_navigate)
_SUGGESTION_RULES: list[tuple[list[str], list[dict]]] = [
    (["metadata", "tags", "carátula", "álbum", "artista", "metadato", "cover", "portada"], [
        {"title": "Abrir Metadata Editor", "desc": "Edita y normaliza etiquetas de tus archivos.",
         "target": "metadata_editor", "kind": "metadata"},
        {"title": "Revisar metadatos pendientes", "desc": "Busca archivos con información incompleta.",
         "target": "audio_lab", "kind": "diagnóstico"},
    ]),
    (["sync", "sincronizar", "android", "dispositivo", "michi sync", "manifiesto"], [
        {"title": "Abrir Michi Sync", "desc": "Prepara un manifiesto para sincronizar con Android.",
         "target": "devices_page", "kind": "sync"},
    ]),
    (["biblioteca", "problemas", "duplicados", "reparar", "library", "doctor"],
        [
        {"title": "Abrir Library Doctor", "desc": "Analiza tu colección en busca de errores.",
         "target": "audio_lab", "kind": "diagnóstico"},
    ]),
    (["servidor", "navidrome", "jellyfin", "subsonic", "conexiones", "remoto"],
        [
        {"title": "Abrir Conexiones", "desc": "Configura servidores de música remotos.",
         "target": "connections_hub", "kind": "conexión"},
    ]),
    (["playlist", "recomienda", "mix", "similar", "descubrir", "género"],
        [
        {"title": "Abrir Mix", "desc": "Explora recomendaciones y mezclas inteligentes.",
         "target": "mix_hub", "kind": "recomendación"},
        {"title": "Abrir Playlist", "desc": "Crea y administra listas de reproducción.",
         "target": "playlist_hub", "kind": "playlist"},
    ]),
    (["radio", "streaming", "emisora", "flow"], [
        {"title": "Abrir Radio", "desc": "Escucha emisoras y streaming en vivo.",
         "target": "radio", "kind": "recomendación"},
    ]),
    (["micro server", "michi server", "ecosistema", "michi micro"], [
        {"title": "Abrir Conexiones — Michi Micro Server",
         "desc": "Servidor musical doméstico del ecosistema Michi: centraliza biblioteca, playlists y streaming.",
         "target": "connections_hub", "kind": "servidor"},
    ]),
    (["home audio", "asistente hogar", "casa", "parlante", "multiroom", "snapcast"], [
        {"title": "Abrir Home Audio", "desc": "Controla Home Assistant, Snapcast y futuros receptores Michi.",
         "target": "home_audio", "kind": "conexión"},
    ]),
    (["local", "biblioteca local", "archivos"], [
        {"title": "Abrir Biblioteca", "desc": "Explora tu música local, álbumes, artistas y géneros.",
         "target": "library_hub", "kind": "navegación"},
    ]),
    (["artista", "discografía", "álbumes del artista", "canciones del artista", "música de"], [
        {"title": "Explorar Artistas", "desc": "Navega la sección Artistas de tu biblioteca.",
         "target": "artists", "kind": "navegación"},
        {"title": "Crear un mix del artista", "desc": "Genera una mezcla inteligente con las canciones principales.",
         "target": "artists", "kind": "mix"},
        {"title": "Analizar calidad de discografía", "desc": "Revisa formatos, bitrate y ReplayGain de sus álbumes.",
         "target": "artists", "kind": "análisis"},
    ]),
    (["duplicados", "alias", "artista duplicado", "fusionar artista", "nombres repetidos"], [
        {"title": "Resolver duplicados de artista", "desc": "Detecta y fusiona artistas con nombre similar.",
         "target": "artists", "kind": "metadata"},
    ]),
    (["enriquecer", "info externa", "biografía", "musicbrainz", "wikipedia", "theaudiodb"], [
        {"title": "Actualizar info externa de artistas", "desc": "Busca biografías, imágenes y metadatos en línea.",
         "target": "artists", "kind": "metadata"},
    ]),
]


class AiAssistantPanel(QWidget):
    send_requested = Signal(str)
    action_confirmed = Signal(str)
    action_cancelled = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("aiAssistantPanel")
        self._messages: list[dict[str, str]] = []
        self._build_ui()
        self._apply_qss()

    # ── UI build ──

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header ──
        header = QFrame()
        header.setObjectName("assistantHeader")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(24, 16, 24, 12)
        hl.setSpacing(4)

        hrow = QHBoxLayout()
        ht = QLabel("Michi Assistant")
        ht.setObjectName("assistantHeaderTitle")
        hrow.addWidget(ht)
        hrow.addStretch()
        self._status_badge = QLabel("Ollama no disponible")
        self._status_badge.setObjectName("assistantStatusBadge")
        hrow.addWidget(self._status_badge)
        hl.addLayout(hrow)

        hs = QLabel("IA local para explorar, organizar y mejorar tu biblioteca.")
        hs.setWordWrap(True)
        hs.setObjectName("assistantHeaderSubtitle")
        hl.addWidget(hs)
        layout.addWidget(header)

        # ── Body: chat (left) + suggestions panel (right) ──
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(12)

        # Chat area
        chat_wrapper = QFrame()
        chat_wrapper.setObjectName("assistantChatCard")
        cvl = QVBoxLayout(chat_wrapper)
        cvl.setContentsMargins(0, 0, 0, 0)
        cvl.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setObjectName("assistantChatScroll")

        self._chat_container = QWidget()
        self._chat_container.setObjectName("assistantChatContainer")
        self._chat_layout = QVBoxLayout(self._chat_container)
        self._chat_layout.setContentsMargins(16, 12, 16, 12)
        self._chat_layout.setSpacing(12)

        self._empty_state = self._build_empty_state()
        self._chat_layout.addWidget(self._empty_state)
        self._chat_layout.addStretch()

        self._scroll.setWidget(self._chat_container)
        cvl.addWidget(self._scroll, 1)

        # Input
        input_row = QHBoxLayout()
        input_row.setContentsMargins(12, 8, 12, 12)
        input_row.setSpacing(8)

        self._input = QLineEdit()
        self._input.setObjectName("assistantInput")
        self._input.setPlaceholderText(_PLACEHOLDER)
        self._input.setMinimumHeight(42)
        self._input.returnPressed.connect(self._on_send)
        input_row.addWidget(self._input, 1)

        self._send_btn = QPushButton("Enviar")
        self._send_btn.setObjectName("assistantSendBtn")
        self._send_btn.setCursor(Qt.PointingHandCursor)
        self._send_btn.clicked.connect(self._on_send)
        input_row.addWidget(self._send_btn)

        cvl.addLayout(input_row)
        body.addWidget(chat_wrapper, 3)

        # Right panel — suggested actions
        self._suggestions_panel = self._build_suggestions_panel()
        body.addWidget(self._suggestions_panel, 1)

        layout.addLayout(body, 1)

        # ── Privacy badge ──
        self._privacy_badge = QLabel(_PRIVACY_NOTICE)
        self._privacy_badge.setObjectName("assistantPrivacyBadge")
        self._privacy_badge.setWordWrap(True)
        self._privacy_badge.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._privacy_badge)

    # ── Empty state ──

    def _build_empty_state(self) -> QWidget:
        w = QWidget()
        w.setObjectName("assistantEmptyState")
        vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 40, 0, 40)
        vl.setAlignment(Qt.AlignCenter)
        vl.setSpacing(12)

        et = QLabel("Pregunta por tu música")
        et.setObjectName("assistantEmptyTitle")
        et.setAlignment(Qt.AlignCenter)
        vl.addWidget(et)

        ed = QLabel("Puedes pedir recomendaciones, revisar metadatos, crear playlists o explorar tu biblioteca local.")
        ed.setObjectName("assistantEmptyDesc")
        ed.setAlignment(Qt.AlignCenter)
        ed.setWordWrap(True)
        vl.addWidget(ed)

        chip_row = QHBoxLayout()
        chip_row.setAlignment(Qt.AlignCenter)
        chip_row.setSpacing(8)
        for chip_text in _EXAMPLE_CHIPS:
            chip = QPushButton(chip_text)
            chip.setCursor(Qt.PointingHandCursor)
            chip.setObjectName("assistantChip")
            chip.clicked.connect(lambda c=None, t=chip_text: self._fill_example(t))
            chip_row.addWidget(chip)
        vl.addLayout(chip_row)

        return w

    def _fill_example(self, text: str):
        self._input.setText(text)
        self._input.setFocus()

    def _hide_empty_state(self):
        if self._empty_state and not self._empty_state.isHidden():
            self._empty_state.hide()

    # ── Suggestions panel ──

    def _build_suggestions_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("assistantSuggestionsPanel")
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(16, 14, 16, 14)
        pl.setSpacing(8)

        st = QLabel("Acciones sugeridas")
        st.setObjectName("assistantSuggTitle")
        pl.addWidget(st)

        sd = QLabel("Atajos contextuales generados por Michi Assistant.")
        sd.setWordWrap(True)
        sd.setObjectName("assistantSuggDesc")
        pl.addWidget(sd)

        self._sugg_empty = QLabel(
            "Las acciones aparecerán cuando Michi detecte algo útil en la conversación.")
        self._sugg_empty.setWordWrap(True)
        self._sugg_empty.setObjectName("assistantSuggEmpty")
        pl.addWidget(self._sugg_empty)

        self._sugg_scroll = QScrollArea()
        self._sugg_scroll.setWidgetResizable(True)
        self._sugg_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._sugg_scroll.setObjectName("assistantSuggScroll")
        self._sugg_container = QWidget()
        self._sugg_container.setObjectName("assistantSuggContainer")
        self._sugg_layout = QVBoxLayout(self._sugg_container)
        self._sugg_layout.setContentsMargins(0, 0, 0, 0)
        self._sugg_layout.setSpacing(8)
        self._sugg_layout.addStretch()
        self._sugg_scroll.setWidget(self._sugg_container)
        pl.addWidget(self._sugg_scroll, 1)

        return panel

    def _update_suggestions(self, text: str):
        """Refresh the suggestions panel based on keyword matching in text."""
        # Clear existing suggestions
        while self._sugg_layout.count() > 1:
            item = self._sugg_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        text_lower = text.lower() if text else ""
        matched = []
        seen = set()
        for keywords, actions in _SUGGESTION_RULES:
            for kw in keywords:
                if kw in text_lower:
                    for a in actions:
                        k = a["title"]
                        if k not in seen:
                            seen.add(k)
                            matched.append(a)
                    break

        if matched:
            self._sugg_empty.hide()
            for a in matched:
                card = self._build_action_card(a)
                self._sugg_layout.insertWidget(self._sugg_layout.count() - 1, card)
        else:
            self._sugg_empty.show()

    def _build_action_card(self, action: dict) -> QFrame:
        name = f"suggAction_{action['title'].replace(' ','_')}"
        card = QFrame()
        card.setObjectName(name)
        card.setStyleSheet(glass_action_card_qss(name))
        vl = QVBoxLayout(card)
        vl.setContentsMargins(12, 10, 12, 10)
        vl.setSpacing(4)

        top = QHBoxLayout()
        t = QLabel(action["title"])
        t.setObjectName("suggActionTitle")
        t.setStyleSheet(card_title_qss())
        t.setWordWrap(True)
        top.addWidget(t, 1)
        kind = action.get("kind", "")
        if kind:
            badge = QLabel(kind.capitalize())
            badge.setObjectName("suggActionBadge")
            badge.setStyleSheet(
                "QLabel { color: rgba(143,183,255,0.60); font-size: 9px;"
                "  font-weight: 600; background: rgba(143,183,255,0.08);"
                "  border-radius: 6px; padding: 1px 6px; }")
            top.addWidget(badge)
        vl.addLayout(top)

        d = QLabel(action.get("desc", ""))
        d.setWordWrap(True)
        d.setObjectName("suggActionDesc")
        d.setStyleSheet(card_desc_qss())
        vl.addWidget(d)

        target = action.get("target", "")
        if target:
            btn = QPushButton("Abrir")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setObjectName("suggActionBtn")
            btn.setStyleSheet(glass_button_qss("accent"))
            btn.clicked.connect(lambda c=None, t=target: self._navigate_safe(t))
            vl.addWidget(btn)

        return card

    def _navigate_safe(self, target: str):
        """Navigate to a section if the window supports it."""
        w = self.window()
        if w and hasattr(w, '_on_sidebar_navigate'):
            w._on_sidebar_navigate(target)
        else:
            self._input.setText(f"Abrir {target}")
            self._input.setFocus()

    # ── Send / messages ──

    def _apply_qss(self):
        self.setStyleSheet(self._build_panel_qss())
        header = self.findChild(QFrame, "assistantHeader")
        if header:
            header.setStyleSheet(glass_hero_qss("assistantHeader"))
        chat_card = self.findChild(QFrame, "assistantChatCard")
        if chat_card:
            chat_card.setStyleSheet(glass_action_card_qss("assistantChatCard"))
            apply_card_shadow(chat_card)
        sugg_panel = self.findChild(QFrame, "assistantSuggestionsPanel")
        if sugg_panel:
            sugg_panel.setStyleSheet(glass_action_card_qss("assistantSuggestionsPanel"))
            apply_card_shadow(sugg_panel)
        input_field = self.findChild(QLineEdit, "assistantInput")
        if input_field:
            input_field.setStyleSheet(glass_input_qss())
        send_btn = self.findChild(QPushButton, "assistantSendBtn")
        if send_btn:
            send_btn.setStyleSheet(glass_button_qss("primary"))
        sugg_title = self.findChild(QLabel, "assistantSuggTitle")
        if sugg_title:
            sugg_title.setStyleSheet(card_title_qss())
        sugg_desc = self.findChild(QLabel, "assistantSuggDesc")
        if sugg_desc:
            sugg_desc.setStyleSheet(card_desc_qss())
        sugg_empty = self.findChild(QLabel, "assistantSuggEmpty")
        if sugg_empty:
            sugg_empty.setStyleSheet(card_desc_qss())
        empty_state = self.findChild(QWidget, "assistantEmptyState")
        if empty_state:
            empty_state.setStyleSheet(empty_state_qss())
        for chip in self.findChildren(QPushButton, "assistantChip"):
            chip.setStyleSheet(glass_chip_button_qss())

    def _on_send(self):
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self._hide_empty_state()
        self.add_message("user", text)
        self._update_suggestions(text)
        self.send_requested.emit(text)

    def add_message(self, role: str, content: str, pending: dict | None = None):
        bubble = _ChatBubble(role, content, self._chat_container)
        idx = self._chat_layout.count() - 1
        self._chat_layout.insertWidget(max(0, idx), bubble)
        if pending:
            card = _PendingActionCard(pending, self._chat_container)
            card.confirmed.connect(self.action_confirmed.emit)
            card.cancelled.connect(self.action_cancelled.emit)
            self._chat_layout.insertWidget(self._chat_layout.count() - 1, card)
        self._scroll_to_bottom()

    def add_message_r(self, content: str):
        self.add_message("assistant", content)

    def add_response(self, response: dict):
        reply = response.get("reply", "")
        if reply:
            self.add_message("assistant", reply)
        pending = response.get("pending")
        if pending:
            card = _PendingActionCard(pending, self._chat_container)
            card.confirmed.connect(
                lambda aid=pending.get("action_id", ""): self.action_confirmed.emit(aid))
            card.cancelled.connect(
                lambda aid=pending.get("action_id", ""): self.action_cancelled.emit(aid))
            self._chat_layout.insertWidget(self._chat_layout.count() - 1, card)
            self._scroll_to_bottom()

    def set_thinking(self, thinking: bool):
        if thinking:
            self._send_btn.setEnabled(False)
            self._input.setEnabled(False)
            self._send_btn.setText("Pensando...")
        else:
            self._send_btn.setEnabled(True)
            self._input.setEnabled(True)
            self._send_btn.setText("Enviar")
            self._input.setFocus()

    def set_ollama_status(self, available: bool, model: str = ""):
        if available:
            self._status_badge.setText(
                f"Ollama conectado · {model}" if model else "Ollama conectado")
            self._status_badge.setStyleSheet(
                "QLabel { color: rgba(100,220,140,0.65); font-size: 11px; font-weight: 500;"
                "  background: rgba(100,220,140,0.08); border: 1px solid rgba(100,220,140,0.10);"
                "  border-radius: 8px; padding: 3px 10px; }")
        else:
            self._status_badge.setText("Ollama no disponible")
            self._status_badge.setStyleSheet(
                "QLabel { color: rgba(255,255,255,0.54); font-size: 11px; font-weight: 500;"
                "  background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.04);"
                "  border-radius: 8px; padding: 3px 10px; }")
        self._privacy_badge.setText(_PRIVACY_NOTICE)

    def clear_messages(self):
        while self._chat_layout.count() > 1:
            item = self._chat_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self._messages.clear()
        if self._empty_state and self._empty_state.isHidden():
            self._empty_state.show()

    def _scroll_to_bottom(self):
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ── Panel QSS ──

    @staticmethod
    def _build_panel_qss() -> str:
        return (
            "QWidget#aiAssistantPanel { background: #090B11; }"
            "QLabel#assistantHeaderTitle { color: rgba(255,255,255,0.92); font-size: 18px;"
            "  font-weight: 700; background: transparent; }"
            "QLabel#assistantHeaderSubtitle { color: rgba(255,255,255,0.62); font-size: 12px;"
            "  background: transparent; }"
            "QScrollArea#assistantChatScroll { background: transparent; border: none; }"
            "QWidget#assistantChatContainer { background: transparent; }"
            "QLabel#assistantPrivacyBadge { color: rgba(255,255,255,0.48); font-size: 11px;"
            "  padding: 6px 16px; background: rgba(143,183,255,0.04);"
            "  border-top: 1px solid rgba(255,255,255,0.04); }"
            "QScrollArea#assistantSuggScroll { background: transparent; border: none; }"
            "QWidget#assistantSuggContainer { background: transparent; }"
        )


class _ChatBubble(QFrame):
    def __init__(self, role: str, content: str, parent: QWidget):
        super().__init__(parent)
        self.setObjectName(f"chatBubble_{role}")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(content)
        label.setWordWrap(True)
        label.setTextFormat(Qt.PlainText)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        if role == "user":
            label.setObjectName("bubbleUser")
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            layout.addWidget(label)
            layout.setAlignment(Qt.AlignRight)
        else:
            label.setObjectName("bubbleAssistant")
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            layout.addWidget(label)
            layout.setAlignment(Qt.AlignLeft)

        label.setStyleSheet(
            "QLabel#bubbleUser {"
            "  background: rgba(143,183,255,0.10);"
            "  border: 1px solid rgba(143,183,255,0.12);"
            "  border-radius: 14px;"
            "  padding: 10px 16px;"
            "  color: rgba(255,255,255,0.90);"
            "  font-size: 13px;"
            "  max-width: 520px;"
            "}"
            "QLabel#bubbleAssistant {"
            "  background: rgba(255,255,255,0.040);"
            "  border: 1px solid rgba(255,255,255,0.05);"
            "  border-radius: 14px;"
            "  padding: 10px 16px;"
            "  color: rgba(255,255,255,0.84);"
            "  font-size: 13px;"
            "  max-width: 620px;"
            "}"
        )


class _PendingActionCard(QFrame):
    confirmed = Signal(str)
    cancelled = Signal(str)

    def __init__(self, pending: dict, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("pendingActionCard")
        self._action_id = pending.get("action_id", "")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        title = QLabel(pending.get("title", "Acción pendiente"))
        title.setObjectName("pendingTitle")
        title.setStyleSheet(card_title_qss())
        layout.addWidget(title)

        desc = pending.get("description", "")
        if desc:
            desc_label = QLabel(desc)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(card_desc_qss())
            layout.addWidget(desc_label)

        badge = QLabel("Requiere confirmación")
        badge.setObjectName("pendingBadge")
        badge.setStyleSheet(
            "QLabel { color: rgba(180,150,255,0.60); font-size: 10px; font-weight: 500;"
            "  background: rgba(180,150,255,0.08); border-radius: 6px; padding: 2px 8px; }")
        layout.addWidget(badge)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        confirm_btn = QPushButton("Confirmar")
        confirm_btn.setObjectName("pendingConfirmBtn")
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.setStyleSheet(glass_button_qss("primary"))
        confirm_btn.clicked.connect(lambda: self.confirmed.emit(self._action_id))
        btn_row.addWidget(confirm_btn)

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("pendingCancelBtn")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(glass_button_qss("ghost"))
        cancel_btn.clicked.connect(lambda: self.cancelled.emit(self._action_id))
        btn_row.addWidget(cancel_btn)

        layout.addLayout(btn_row)

        self.setStyleSheet(glass_action_card_qss("pendingActionCard"))
