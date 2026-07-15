from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


def safe_create_view(view_name, parent=None):
    w = QWidget(parent)
    layout = QVBoxLayout(w)
    label = QLabel(f"Vista no disponible: {view_name}")
    layout.addWidget(label)
    return w
