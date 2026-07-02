from PySide6.QtCore import QObject, Signal, Property


class NowPlayingBridge(QObject):
    coverChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cover_key = ""

    @Property(str, notify=coverChanged)
    def coverKey(self):
        return self._cover_key

    def set_cover_from_path(self, filepath: str):
        import hashlib
        if filepath:
            self._cover_key = f"track_{hashlib.md5(filepath.encode()).hexdigest()[:12]}"
        else:
            self._cover_key = ""
        self.coverChanged.emit()
