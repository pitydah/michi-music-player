"""Shared card/UI components for Broadcast hub."""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from ui.central.central_styles import glass_card_qss


def summary_card(title: str, value: str, accent: str = "rgba(143,183,255,0.90)") -> QFrame:
    card = QFrame()
    card.setStyleSheet(glass_card_qss("broadcastSummaryCard"))
    card.setMinimumWidth(140)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(4)

    val = QLabel(value)
    val.setObjectName("broadcastSummaryValue")
    val.setStyleSheet(
        f"color: {accent}; font-size: 26px; font-weight: 700; "
        f"background: transparent; border: none;"
    )
    layout.addWidget(val)
    card._value_label = val

    lbl = QLabel(title)
    lbl.setStyleSheet(
        "color: rgba(255,255,255,0.56); font-size: 11px; "
        "background: transparent; border: none;"
    )
    layout.addWidget(lbl)
    return card


def _set_card_value(card: QFrame, value: str):
    label = getattr(card, '_value_label', None)
    if label:
        label.setText(value)


def episode_row(
    title: str,
    subtitle: str,
    duration: str = "",
    status: str = "",
    is_new: bool = False,
) -> QFrame:
    row = QFrame()
    row.setStyleSheet(
        "QFrame { background: rgba(255,255,255,0.02); border: none; "
        "border-bottom: 1px solid rgba(255,255,255,0.03); }"
    )
    row.setFixedHeight(48)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(12, 0, 12, 0)

    info = QVBoxLayout()
    info.setSpacing(1)
    t = QLabel(title)
    t.setStyleSheet(
        "color: rgba(255,255,255,0.82); font-size: 12px; "
        "font-weight: 500; background: transparent; border: none;"
    )
    info.addWidget(t)

    s = QLabel(subtitle)
    s.setStyleSheet(
        "color: rgba(255,255,255,0.48); font-size: 10px; "
        "background: transparent; border: none;"
    )
    info.addWidget(s)
    layout.addLayout(info, 1)

    if duration:
        d = QLabel(duration)
        d.setStyleSheet(
            "color: rgba(255,255,255,0.40); font-size: 10px; "
            "background: transparent; border: none;"
        )
        layout.addWidget(d)

    if is_new:
        badge = QLabel("NUEVO")
        badge.setStyleSheet(
            "color: rgba(100,220,100,0.90); font-size: 9px; font-weight: 700; "
            "background: rgba(100,220,100,0.10); border: 1px solid rgba(100,220,100,0.15); "
            "border-radius: 4px; padding: 1px 6px;"
        )
        layout.addWidget(badge)

    return row
