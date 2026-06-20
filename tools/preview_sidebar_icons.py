"""Preview sidebar icons at 24px and 32px on a sidebar-colored background."""

import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QColor, QLinearGradient, QFont
from PySide6.QtWidgets import QApplication

from ui.icons import get_icon
from ui.icon_renderer import render_svg_icon

ICONS = [
    "sidebar_library", "sidebar_songs", "sidebar_albums", "sidebar_folders",
    "sidebar_playlists", "sidebar_playlist_item", "sidebar_mix",
    "sidebar_unplayed", "sidebar_popular", "sidebar_identifier",
    "sidebar_radio", "sidebar_servers", "sidebar_navidrome",
    "sidebar_jellyfin", "sidebar_devices", "sidebar_add",
]

SIDEBAR_TOP = QColor(68, 72, 84, 250)
SIDEBAR_BOT = QColor(48, 52, 64, 250)
COLS = 8
MARGIN = 20
CELL_W = 64
CELL_H = 60
LABEL_H = 14


def main():
    app = QApplication(sys.argv)

    rows = (len(ICONS) + COLS - 1) // COLS
    w = MARGIN * 2 + COLS * CELL_W
    h = MARGIN * 2 + 24 + 8 * 2 + rows * CELL_H + 8  # title + size labels + rows

    pix = QPixmap(w, h)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing, True)

    # Sidebar-matching background
    grad = QLinearGradient(0, 0, w, h)
    grad.setColorAt(0.0, SIDEBAR_TOP)
    grad.setColorAt(1.0, SIDEBAR_BOT)
    painter.fillRect(pix.rect(), grad)

    # Title
    painter.setPen(QColor(255, 122, 0))
    font = QFont("sans-serif", 14, QFont.Bold)
    painter.setFont(font)
    painter.drawText(MARGIN, MARGIN + 18, "Sidebar SVG Preview (24px + 32px)")

    sizes = [24, 32]
    y_offset = MARGIN + 24
    for sz_idx, sz in enumerate(sizes):
        sy = y_offset + 4
        painter.setPen(QColor(255, 255, 255, 100))
        font2 = QFont("sans-serif", 9)
        painter.setFont(font2)
        painter.drawText(MARGIN, sy + 10, f"{sz}x{sz}")

        for i, name in enumerate(ICONS):
            col = i % COLS
            row = i // COLS
            cx = MARGIN + col * CELL_W
            cy = sy + 12 + row * CELL_H

            # Icon
            path = get_icon(name)
            icon_pix = render_svg_icon(path, sz, 1) if path else QPixmap(sz, sz)
            ix = cx + (CELL_W - sz) // 2
            iy = cy + (38 - sz) // 2
            painter.drawPixmap(ix, iy, icon_pix)

            # Label
            short = name.replace("sidebar_", "")
            painter.setPen(QColor(255, 255, 255, 70))
            font3 = QFont("sans-serif", 7)
            painter.setFont(font3)
            painter.drawText(cx, cy + 42, CELL_W, LABEL_H,
                           Qt.AlignCenter, short)

    painter.end()
    out = "/home/cristian/music_player/sidebar_icon_preview.png"
    pix.save(out, "PNG")
    print(f"Preview saved: {out}")
    app.quit()


if __name__ == "__main__":
    main()
