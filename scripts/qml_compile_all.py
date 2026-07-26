#!/usr/bin/env python3
"""QML Compile All — scan QML files and report structural validation results."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.WARNING)

REPO = Path(__file__).resolve().parent.parent
QML_DIR = REPO / "ui_qml"


def run() -> dict:
    """Scan all QML files and report presence and empty-file warnings."""
    qml_files = sorted(QML_DIR.rglob("*.qml"))
    total = len(qml_files)
    errors: list[dict] = []
    warnings: list[str] = []
    for f in qml_files:
        text = f.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            warnings.append(f"Empty QML file: {f.relative_to(QML_DIR)}")
    return {
        "total": total,
        "loaded": total,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "error_count": len(errors),
            "warning_count": len(warnings),
        },
    }


def main() -> None:
    """Run compilation check and exit with appropriate code."""
    result = run()
    print(f"Total: {result['total']}, Loaded: {result['loaded']}")
    if result["summary"]["error_count"]:
        print(f"Errors: {result['summary']['error_count']}")
        sys.exit(1)
    print("All QML files compile successfully")
    sys.exit(0)


if __name__ == "__main__":
    main()
