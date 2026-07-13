"""RuntimeQualityBridge — monitors runtime health: imports, signals, threading."""
from __future__ import annotations

import sys
import importlib

from PySide6.QtCore import QObject, Signal, Property, Slot


class RuntimeQualityBridge(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        self._modules_ok = self._check_imports()
        self._pyside_version = self._get_pyside_version()
        self._qt_version = self._get_qt_version()

    def _check_imports(self) -> dict[str, bool]:
        critical = ["PySide6", "mutagen", "numpy"]
        return {m: importlib.util.find_spec(m) is not None for m in critical}

    def _get_pyside_version(self) -> str:
        try:
            from PySide6 import __version__
            return __version__
        except Exception:
            return "?"

    def _get_qt_version(self) -> str:
        try:
            from PySide6.QtCore import qVersion
            return qVersion()
        except Exception:
            return "?"

    @Property(str, notify=dataChanged)
    def pythonVersion(self):
        return self._py_version

    @Property(str, notify=dataChanged)
    def pysideVersion(self):
        return self._pyside_version

    @Property(str, notify=dataChanged)
    def qtVersion(self):
        return self._qt_version

    @Property("QVariantMap", notify=dataChanged)
    def moduleStatus(self):
        return dict(self._modules_ok)

    @Slot(result=dict)
    def runtimeQualityScore(self) -> dict:
        score = 0
        if self._modules_ok.get("PySide6"):
            score += 25
        if self._modules_ok.get("mutagen"):
            score += 20
        if self._modules_ok.get("numpy"):
            score += 15
        if self._pyside_version and self._pyside_version != "?":
            score += 15
        if self._qt_version and self._qt_version != "?":
            score += 15
        try:
            from PySide6.QtCore import qVersion
            if qVersion() >= "6.0":
                score += 10
        except Exception:
            pass
        return {
            "score": min(100, score),
            "python": self._py_version,
            "pyside": self._pyside_version,
            "qt": self._qt_version,
            "pyside_ok": self._modules_ok.get("PySide6", False),
            "mutagen_ok": self._modules_ok.get("mutagen", False),
            "numpy_ok": self._modules_ok.get("numpy", False),
        }

    @Slot()
    def refresh(self):
        self._modules_ok = self._check_imports()
        self.dataChanged.emit()
