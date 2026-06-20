"""File actions — open, scan, drop, and folder import operations."""
import os

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QFileDialog

from library.library_db import ScannerWorker
from ui.loading_overlay import LoadingOverlay
from ui.toast_notification import ToastNotification


class FileActions:
    def __init__(self, window):
        self._win = window
        self._db = window._db

    def open_file(self, all_exts: frozenset):
        exts = " ".join(f"*{e}" for e in sorted(all_exts))
        fp, _ = QFileDialog.getOpenFileName(
            self._win, "Abrir archivo", os.path.expanduser("~"),
            f"Multimedia ({exts});;Todos (*)")
        if fp:
            self._db.add_file(fp)
            self._win._load_library()
            self._win._play_file(fp)

    def add_folder(self):
        path = QFileDialog.getExistingDirectory(
            self._win, "Añadir carpeta", os.path.expanduser("~"))
        if not path:
            return
        self.scan_path(path)

    def folder_create_playlist(self, name: str, filepaths: list):
        pid = self._db.create_playlist(name)
        if pid:
            for fp in filepaths:
                self._db.add_to_playlist(pid, fp)
            self._win._rebuild_sidebar()
            ToastNotification.success(
                f"Playlist \"{name}\" creada con {len(filepaths)} canciones", self._win)

    def scan_path(self, path: str):
        worker = ScannerWorker(self._db, path)
        thread = QThread()

        overlay = LoadingOverlay(self._win._content)
        overlay.set_text("Escaneando...")
        overlay.show(delay_ms=100)

        worker.progress.connect(
            lambda c, t, f: overlay.set_text(
                f"Escaneando [{c}/{t}]\n{os.path.basename(f)[:60]}"))

        def _on_done(added):
            overlay.hide()
            overlay.deleteLater()
            self._win._load_library()
            ToastNotification.success(
                f"Escaneo completado: {added} archivos añadidos", self._win)

        worker.moveToThread(thread)
        worker.finished.connect(lambda a: _on_done(a))
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.start()
