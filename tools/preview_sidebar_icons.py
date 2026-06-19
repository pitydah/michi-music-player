"""Preview all sidebar icons at 24x24 and 32x32 using SidebarIcon widget."""

import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QGridLayout, QLabel, QVBoxLayout,
)
from PySide6.QtCore import Qt

from ui.sidebar_widget import SidebarIcon

ICONS = [
    "sidebar_library",
    "sidebar_songs",
    "sidebar_albums",
    "sidebar_folders",
    "sidebar_playlists",
    "sidebar_playlist_item",
    "sidebar_mix",
    "sidebar_unplayed",
    "sidebar_popular",
    "sidebar_identifier",
    "sidebar_radio",
    "sidebar_servers",
    "sidebar_navidrome",
    "sidebar_jellyfin",
    "sidebar_devices",
    "sidebar_add",
]


def main():
    app = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("Astra — Sidebar Icon Preview (QPainter Widget)")
    window.setStyleSheet("QWidget { background: #121215; }")

    layout = QVBoxLayout(window)
    layout.setContentsMargins(20, 20, 20, 20)

    title = QLabel("Sidebar Icons — SidebarIcon Widget")
    title.setStyleSheet(
        "color: #FF7A00; font-size: 16px; font-weight: 700; padding: 0 0 12px 0;")
    layout.addWidget(title)

    grid = QGridLayout()
    grid.setSpacing(12)

    for i, name in enumerate(ICONS):
        icon = SidebarIcon(name)
        icon.setFixedSize(36, 36)

        name_label = QLabel(name.replace("sidebar_", ""))
        name_label.setStyleSheet("color: rgba(245,245,247,0.45); font-size: 9px;")
        name_label.setAlignment(Qt.AlignCenter)

        col = i % 8
        row = (i // 8) * 2

        grid.addWidget(icon, row, col, Qt.AlignCenter)
        grid.addWidget(name_label, row + 1, col, Qt.AlignCenter)

    layout.addLayout(grid)
    layout.addStretch()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
