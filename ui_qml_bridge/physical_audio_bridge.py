"""PhysicalAudioBridge — reads artifacts/qml-physical-results.json for physical audio closure.

Does NOT calculate its own score based on heuristic methods.
Reads the artifact produced by scripts/qml_physical_runner.py.
States: PENDING, RUNNING, VERIFIED, FAILED, BLOCKED_HARDWARE.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Property, Slot

logger = logging.getLogger(__name__)


ARTIFACT_PATH = Path(__file__).resolve().parent.parent / "artifacts" / "qml-physical-results.json"


def _read_artifact() -> dict:
    try:
        if ARTIFACT_PATH.exists():
            return json.loads(ARTIFACT_PATH.read_text())
    except Exception:
        pass
    return {"status": "PENDING", "checks": [], "passed": 0, "total": 0}


class PhysicalAudioBridge(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def _artifact(self) -> dict:
        return _read_artifact()

    @Property(str, notify=dataChanged)
    def status(self) -> str:
        return self._artifact().get("status", "PENDING")

    @Property(int, notify=dataChanged)
    def passed(self) -> int:
        return self._artifact().get("passed", 0)

    @Property(int, notify=dataChanged)
    def total(self) -> int:
        return self._artifact().get("total", 0)

    @Property(str, notify=dataChanged)
    def sha(self) -> str:
        return self._artifact().get("sha", "")

    @Property(str, notify=dataChanged)
    def date(self) -> str:
        return self._artifact().get("date", "")

    @Property(str, notify=dataChanged)
    def platform(self) -> str:
        return self._artifact().get("platform", "")

    @Property(str, notify=dataChanged)
    def backend(self) -> str:
        return self._artifact().get("backend", "")

    @Property(str, notify=dataChanged)
    def device(self) -> str:
        return self._artifact().get("device", "")

    @Property(str, notify=dataChanged)
    def version(self) -> str:
        return self._artifact().get("version", "")

    @Property("QVariantList", notify=dataChanged)
    def checks(self):
        return self._artifact().get("checks", [])

    @Slot(result=dict)
    def physicalAudioScore(self) -> dict:
        art = self._artifact()
        status = art.get("status", "PENDING")
        passed = art.get("passed", 0)
        total = art.get("total", 0) or 1
        score = int((passed / total) * 100) if total > 0 else 0
        return {
            "score": score,
            "status": status,
            "passed": passed,
            "total": total,
            "verified": status == "VERIFIED",
            "sha": art.get("sha", ""),
            "date": art.get("date", ""),
            "platform": art.get("platform", ""),
            "backend": art.get("backend", ""),
            "device": art.get("device", ""),
        }

    @Slot()
    def refresh(self):
        self.dataChanged.emit()
