#!/usr/bin/env python3
"""Minimal QtMultimedia isolation probe (CI environment evidence).

Runs the exact object lifecycle that segfaults on the CI runner, in a separate
process, and prints a machine-readable step trace. It is diagnostic only and is
NOT part of the test gate.

Usage: python scripts/qt_multimedia_probe.py [--wav PATH]
Exit codes: 0 = all steps completed; 2 = an exception (traceback printed);
            a segfault produces the interpreter's native fault output.
"""

from __future__ import annotations

import json
import os
import platform
import sys
import tempfile
import wave


def _tiny_wav() -> str:
    path = os.path.join(tempfile.mkdtemp(prefix="michi-qt-probe-"), "probe.wav")
    with wave.open(path, "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(44100)
        handle.writeframes(b"\x00\x00\x00\x00" * 4410)
    return path


def main() -> int:
    report: dict = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "env": {
            key: os.environ.get(key)
            for key in (
                "QT_QPA_PLATFORM",
                "QT_MEDIA_BACKEND",
                "QT_MULTIMEDIA_PREFERRED_PLUGINS",
                "PULSE_SERVER",
                "XDG_RUNTIME_DIR",
                "DISPLAY",
            )
        },
        "steps": [],
    }
    try:
        from PySide6 import __version__ as pyside_version
        from PySide6.QtCore import QCoreApplication, QUrl, qVersion
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

        report["pyside"] = pyside_version
        report["qt"] = qVersion()
        app = QCoreApplication.instance() or QCoreApplication([])
        report["steps"].append("qcoreapplication")

        player = QMediaPlayer()
        report["steps"].append("qmediaplayer")
        output = QAudioOutput()
        report["steps"].append("qaudiooutput")
        player.setAudioOutput(output)
        report["steps"].append("bind_output")

        player.setSource(QUrl.fromLocalFile(_tiny_wav()))
        report["steps"].append("set_source")
        player.play()
        report["steps"].append("play")
        for _ in range(20):
            app.processEvents()
        player.pause()
        report["steps"].append("pause")
        player.play()
        report["steps"].append("resume")
        player.stop()
        report["steps"].append("stop")
        player.setSource(QUrl())
        player.setAudioOutput(None)
        report["steps"].append("detach")
        del player, output
        report["steps"].append("destroy")
        print(json.dumps(report))
        return 0
    except Exception as exc:  # noqa: BLE001 - diagnostic boundary
        report["error"] = f"{type(exc).__name__}: {exc}"
        print(json.dumps(report))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
