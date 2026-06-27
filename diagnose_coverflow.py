#!/usr/bin/env python3
"""CoverFlow diagnostic tool — standalone measurement and geometry dump.

Usage:
    python diagnose_coverflow.py          # Standard test
    MICHI_COVERFLOW_DEBUG=1 python diagnose_coverflow.py  # Verbose

Creates a window with a mock CoverFlow (30 colored squares), runs a 3-second
scrolling test, and prints a diagnostic report.
"""
import os
import sys
import json

os.environ["MICHI_COVERFLOW_DEBUG"] = "1"

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import QApplication


def _make_mock_pixmap(color: QColor, size: int = 200, index: int = 0) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(color)
    painter.setPen(QPen(color.darker(120), 2))
    painter.drawRoundedRect(2, 2, size - 4, size - 4, 14, 14)
    painter.setPen(QColor(255, 255, 255, 200))
    painter.setFont(QFont("sans-serif", 24, QFont.Bold))
    painter.drawText(pix.rect(), Qt.AlignCenter, str(index + 1))
    painter.end()
    return pix


def run_diagnostic():
    app = QApplication.instance() or QApplication(sys.argv)

    from library.coverflow import CoverFlowWidget
    from library.album_art import CoverFlowItem

    colors = [QColor(h, 180, 120) for h in range(0, 360, 12)]
    items = []
    for i, color in enumerate(colors[:30]):
        pix = _make_mock_pixmap(color, 200, i)
        item = CoverFlowItem(
            pixmap=pix,
            title=f"Album {i + 1}",
            subtitle=f"Artist {i + 1} · 2024 · 12 \u266a",
            data={"album": f"Album {i + 1}", "artist": f"Artist {i + 1}", "tracks": []},
        )
        items.append(item)

    cf = CoverFlowWidget()
    cf.resize(1024, 600)
    cf.show()
    cf.set_items(items)

    diag = cf.dump_diagnostic()
    print(f"OpenGL: {'si' if diag['opengl'] else 'no'}")
    print(f"Viewport: {diag['viewport_type']}")
    print(f"Mode: {diag['render_mode']}")
    print(f"Items: {diag['items_total']}")
    print(f"Cover size: {diag['cover_size']}")

    step = 0.15
    scroll_steps = 20
    delay_ms = 80

    def do_step(n: int = 0):
        if n >= scroll_steps:
            QTimer.singleShot(500, finish)
            return
        cf.scroll_to(int(step * n), animated=False)
        cf.viewport().update()
        QTimer.singleShot(delay_ms, lambda: do_step(n + 1))

    def finish():
        diag = cf.dump_diagnostic()
        print("\n=== CoverFlow Diagnostic Report ===")
        print(f"Total items:     {diag['items_total']}")
        print(f"Visible items:   {diag['items_visible']}")
        print(f"Current index:   {diag['current_index']}")
        print(f"Current pos:     {diag['current_pos']}")
        print(f"Velocity:        {diag['velocity']}")
        print(f"OpenGL:          {diag['opengl']}")
        print(f"Viewport type:   {diag['viewport_type']}")
        print(f"Render mode:     {diag['render_mode']}")
        print(f"Cover size:      {diag['cover_size']}")
        print(f"Layout time:     {diag['layout_time_ms']} ms")
        print(f"Pending covers:  {diag['pending_covers']}")
        print(f"Snapping:        {diag['snapping']}")

        path = "/tmp/coverflow_diagnostic.txt"
        with open(path, "w") as f:
            json.dump(diag, f, indent=2)
        print(f"\nFull report: {path}")
        app.quit()

    QTimer.singleShot(200, lambda: do_step(0))
    app.exec()


if __name__ == "__main__":
    run_diagnostic()
