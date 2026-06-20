"""Tag Editor — edit audio file metadata using mutagen."""

from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QSpinBox,
    QDialogButtonBox, QMessageBox,
)


class TagEditorDialog(QDialog):
    def __init__(self, filepath: str, parent=None):
        super().__init__(parent)
        self._filepath = filepath
        self.setWindowTitle("Editar metadatos")
        self.setMinimumWidth(420)
        self.setModal(True)

        import mutagen
        self._mf = mutagen.File(filepath)
        self._tags = {}
        if self._mf and self._mf.tags:
            self._tags = dict(self._mf.tags)

        layout = QFormLayout(self)
        layout.setSpacing(10)

        def _get(field, index=0):
            vals = self._tags.get(field, [])
            return str(vals[index]) if len(vals) > index else ""

        self._title = QLineEdit(_get("title", 0) or _get("TIT2", 0))
        self._artist = QLineEdit(_get("artist", 0) or _get("TPE1", 0))
        self._album = QLineEdit(_get("album", 0) or _get("TALB", 0))
        self._year = QSpinBox()
        self._year.setRange(0, 2099)
        y = _get("date", 0) or _get("TDRC", 0)
        self._year.setValue(int(y[:4]) if y and y[:4].isdigit() else 0)
        self._track = QSpinBox()
        self._track.setRange(0, 999)
        t = _get("tracknumber", 0) or _get("TRCK", 0)
        self._track.setValue(int(t.split("/")[0]) if t else 0)
        self._genre = QLineEdit(_get("genre", 0) or _get("TCON", 0))

        layout.addRow("Título:", self._title)
        layout.addRow("Artista:", self._artist)
        layout.addRow("Álbum:", self._album)
        layout.addRow("Año:", self._year)
        layout.addRow("Pista:", self._track)
        layout.addRow("Género:", self._genre)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

        from ui.theme import apply_dialog_shadow
        apply_dialog_shadow(self)

    def _save(self):
        if not self._mf:
            QMessageBox.warning(self, "Error", "Formato no soportado.")
            return
        try:
            tags = self._mf.tags or mutagen._tags.EasyID3()
            tags["title"] = self._title.text()
            tags["artist"] = self._artist.text()
            tags["album"] = self._album.text()
            tags["date"] = str(self._year.value()) if self._year.value() else ""
            tags["tracknumber"] = str(self._track.value()) if self._track.value() else ""
            tags["genre"] = self._genre.text()
            self._mf.tags = tags
            self._mf.save()
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo guardar: {e}")
