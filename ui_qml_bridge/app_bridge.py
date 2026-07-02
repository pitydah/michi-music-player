from importlib.metadata import version, PackageNotFoundError

from PySide6.QtCore import QObject, Signal, Property, Slot


def get_app_version() -> str:
    try:
        return version("michi-music-player")
    except PackageNotFoundError:
        return "0.2.0-alpha.1"


class AppBridge(QObject):
    statusChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._app_name = "Michi Music Player"
        self._version = get_app_version()
        self._experimental_qml = True

    @Property(str, constant=True)
    def appName(self):
        return self._app_name

    @Property(str, constant=True)
    def version(self):
        return self._version

    @Property(bool, constant=True)
    def experimentalQml(self):
        return self._experimental_qml

    @Slot()
    def quit(self):
        from PySide6.QtCore import QCoreApplication
        QCoreApplication.quit()
