"""Inline dialog builders — cover preview, nowplaying details, audio diagnostics."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QMenu

from ui.central.central_styles import dialog_qss


def show_cover_preview(parent, pixmap):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Carátula")
    dlg.setFixedSize(460, 460)
    dlg.setStyleSheet(dialog_qss())
    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(20, 20, 20, 20)
    lbl = QLabel()
    lbl.setAlignment(Qt.AlignCenter)
    if pixmap and not pixmap.isNull():
        lbl.setPixmap(pixmap.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    lbl.setStyleSheet("background: transparent; border: none;")
    layout.addWidget(lbl)
    dlg.exec()


def show_nowplaying_details(parent, point, track_ref):
    from ui.premium_menus import premium_menu_qss
    menu = QMenu(parent)
    menu.setStyleSheet(premium_menu_qss())
    current = track_ref.uri if track_ref else ""
    name = os.path.basename(current) if current else "Sin reproducción"
    artist = track_ref.artist if track_ref else ""
    album = track_ref.album if track_ref else ""

    menu.addAction(f"Título: {name}").setEnabled(False)
    if artist:
        menu.addAction(f"Artista: {artist}").setEnabled(False)
    if album:
        menu.addAction(f"Álbum: {album}").setEnabled(False)
    menu.addSeparator()
    if current and not current.startswith("http"):
        menu.addAction("Abrir carpeta", lambda: parent._on_album_open_folder(os.path.dirname(current)))
        menu.addAction("Editar metadatos", lambda: parent._open_metadata_for_files([current]))

    menu.exec(point)


def show_audio_diagnostics(parent, playback):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Diagnostico de ruta de audio")
    dlg.setMinimumWidth(420)
    dlg.setStyleSheet(
        "QDialog { background: rgba(15,17,22,0.96);"
        " border: 1px solid rgba(255,255,255,0.07);"
        " border-radius: 16px; }"
        "QLabel { background: transparent; }")
    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setSpacing(6)

    try:
        diag = playback.get_audio_diagnostics()
        lines = diag.to_tooltip().split("\n") if diag else ["Sin diagnóstico"]
    except Exception:
        lines = ["Diagnostico no disponible"]

    title = QLabel("Ruta de audio activa")
    title.setStyleSheet(
        "font-size: 16px; font-weight: 740; color: rgba(255,255,255,0.92);")
    layout.addWidget(title)
    layout.addSpacing(8)

    for line in lines:
        lbl = QLabel(line)
        lbl.setStyleSheet(
            "font-size: 12px; color: rgba(255,255,255,0.62);"
            "font-family: monospace;")
        layout.addWidget(lbl)

    layout.addSpacing(12)
    close_btn = QLabel("Clic para cerrar")
    close_btn.setStyleSheet(
        "font-size: 11px; color: rgba(255,255,255,0.32);")
    close_btn.setAlignment(Qt.AlignCenter)
    layout.addWidget(close_btn)
    dlg.mousePressEvent = lambda e: dlg.accept()
    dlg.exec()
