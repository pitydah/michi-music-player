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

import faulthandler
import json
import os
import platform
import sys
import tempfile
import wave
from pathlib import Path


def _tiny_wav() -> str:
    path = os.path.join(tempfile.mkdtemp(prefix="michi-qt-probe-"), "probe.wav")
    with wave.open(path, "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(44100)
        handle.writeframes(b"\x00\x00\x00\x00" * 4410)
    return path


def _step(report: dict, name: str) -> None:
    """Print immediately so a native crash shows the exact last step."""
    report["steps"].append(name)
    print(f"[probe] {name}", file=sys.stderr, flush=True)


def main() -> int:
    faulthandler.enable()
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
        try:
            import importlib.util

            spec = importlib.util.find_spec("PySide6")
            multimedia_dir = (
                Path(spec.origin).resolve().parent / "Qt" / "plugins" / "multimedia"
                if spec is not None and spec.origin
                else Path("/nonexistent")
            )
            report["multimedia_plugins"] = (
                sorted(item.name for item in multimedia_dir.iterdir())
                if multimedia_dir.is_dir()
                else []
            )
        except Exception as exc:  # noqa: BLE001 - diagnostic only
            report["multimedia_plugins_error"] = str(exc)
        app = QCoreApplication.instance() or QCoreApplication([])
        _step(report, "qcoreapplication")

        player = QMediaPlayer()
        _step(report, "qmediaplayer")
        output = QAudioOutput()
        _step(report, "qaudiooutput")
        player.setAudioOutput(output)
        _step(report, "bind_output")

        player.setSource(QUrl.fromLocalFile(_tiny_wav()))
        _step(report, "set_source")
        player.play()
        _step(report, "play")
        for _ in range(20):
            app.processEvents()
        player.pause()
        _step(report, "pause")
        player.play()
        _step(report, "resume")
        player.stop()
        _step(report, "stop")
        player.setSource(QUrl())
        player.setAudioOutput(None)
        _step(report, "detach")
        del player, output
        _step(report, "destroy")
        print(json.dumps(report))
        return 0
    except Exception as exc:  # noqa: BLE001 - diagnostic boundary
        report["error"] = f"{type(exc).__name__}: {exc}"
        print(json.dumps(report))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
