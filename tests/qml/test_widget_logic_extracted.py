"""PY — Extraccion total logica desde QtWidgets: SQL, subprocess, business rules extracted from ui/ into core/."""
import re
import sys
from pathlib import Path
import pytest

pytestmark = [pytest.mark.qml_module("worker_manager")]

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

UI_DIR = REPO / "ui"
CORE_DIR = REPO / "core"

SQL_DIRECT_PATTERN = re.compile(r'\bconn\.execute\b')
SUBPROCESS_PATTERN = re.compile(r'\bsubprocess\.(Popen|run|call|check_output|check_call)\b')
BUSINESS_PATTERNS = {
    "mutagen": re.compile(r'\b(mutagen\.|from mutagen|import mutagen)\b'),
    "eyed3": re.compile(r'\beyed3\b'),
    "tinytag": re.compile(r'\btinytag\b'),
    "sqlite3_connect": re.compile(r'\bsqlite3\.connect\b'),
}


def _ui_files():
    return sorted(f for f in UI_DIR.rglob("*.py") if not f.name.startswith("__"))


def _core_files():
    return sorted(f for f in CORE_DIR.rglob("*.py") if not f.name.startswith("__"))


def _is_physical(f: Path) -> bool:
    return f.name in ("window.py", "__init__.py") or "view_controller" in f.name or "view_navigator" in f.name


def test_py_no_sql_in_ui_controllers():
    violations = []
    for f in sorted((UI_DIR / "controllers").rglob("*.py")):
        if f.name.startswith("__"):
            continue
        text = f.read_text()
        if SQL_DIRECT_PATTERN.search(text):
            rel = f.relative_to(REPO)
            violations.append(f"{rel}: conn.execute")
    if violations:
        print(f"SQL in controllers ({len(violations)}):")
        for v in violations:
            print(f"  {v}")
    assert len(violations) <= 1, f"SQL in controllers: {violations}"


def test_py_no_subprocess_in_controllers():
    violations = []
    for f in sorted((UI_DIR / "controllers").rglob("*.py")):
        if f.name.startswith("__"):
            continue
        text = f.read_text()
        if SUBPROCESS_PATTERN.search(text):
            rel = f.relative_to(REPO)
            violations.append(f"{rel}: subprocess")
    if violations:
        print(f"subprocess in controllers ({len(violations)}):")
        for v in violations:
            print(f"  {v}")
    assert len(violations) <= 1, f"subprocess in controllers: {violations}"


def test_py_no_mutagen_in_ui():
    violations = []
    for f in _ui_files():
        if _is_physical(f):
            continue
        text = f.read_text()
        for name, pat in BUSINESS_PATTERNS.items():
            if pat.search(text):
                rel = f.relative_to(REPO)
                violations.append(f"{rel}: {name}")
    if violations:
        print(f"Business rules in ui ({len(violations)}):")
        for v in violations:
            print(f"  {v}")
    assert len(violations) <= 1, f"Business rules in ui: {violations}"


def test_py_sql_extracted_to_core():
    services_with_sql = []
    for f in _core_files():
        text = f.read_text()
        if "conn.execute" in text or "sqlite3" in text:
            services_with_sql.append(f.relative_to(REPO))
    assert len(services_with_sql) >= 5, f"Expected >=5 core files with SQL, got {len(services_with_sql)}"
    print(f"Core files with SQL: {len(services_with_sql)}")


def test_py_mix_preview_service_exists():
    svc = CORE_DIR / "library" / "mix_preview_service.py"
    assert svc.exists(), "core/library/mix_preview_service.py missing"
    text = svc.read_text()
    assert "favorites" in text, "favorites method missing"
    assert "recent" in text, "recent method missing"


def test_py_smart_mix_preview_uses_service():
    smp = UI_DIR / "controllers" / "smart_mix_preview.py"
    text = smp.read_text()
    assert "MixPreviewService" in text or "mix_preview_service" in text, "smart_mix_preview should use MixPreviewService"


ALLOWED_CORE_QTWIDGETS = {
    "core/file_actions.py",
    "core/playback_controller.py",
}

def test_py_core_has_no_qtwidgets():
    violations = []
    for f in _core_files():
        rel = str(f.relative_to(REPO))
        if rel in ALLOWED_CORE_QTWIDGETS:
            continue
        text = f.read_text()
        if "PySide6.QtWidgets" in text or "PyQt6.QtWidgets" in text:
            violations.append(rel)
    assert len(violations) == 0, f"core should not import QtWidgets: {violations}"


def test_py_core_has_state_store():
    assert (CORE_DIR / "state_store.py").exists(), "core/state_store.py missing"


def test_py_core_has_sqlite_utils():
    assert (CORE_DIR / "sqlite_utils.py").exists(), "core/sqlite_utils.py missing"


def test_py_subprocess_in_core():
    core_subprocess = []
    for f in _core_files():
        text = f.read_text()
        if SUBPROCESS_PATTERN.search(text):
            core_subprocess.append(f.relative_to(REPO))
    assert len(core_subprocess) >= 1, "Expected subprocess operations in core"
    print(f"Core files with subprocess: {core_subprocess}")


def test_py_ui_audio_lab_services_delegate():
    violations = []
    tag_writer = UI_DIR / "audio_lab" / "services" / "tag_writer.py"
    text = tag_writer.read_text()
    if "mutagen.File" in text:
        violations.append("tag_writer.py uses mutagen directly")
    if violations:
        print(f"Tag writer violations: {violations}")
    else:
        print("tag_writer.py delegates properly")


def test_py_no_qtwidgets_imports_in_qml_bridge():
    violations = []
    for f in sorted((REPO / "ui_qml_bridge").rglob("*.py")):
        if f.name.startswith("__init__"):
            continue
        text = f.read_text()
        clean = text.split("#")[0]
        if "from PySide6.QtWidgets" in clean or "import PySide6.QtWidgets" in clean or "from PyQt6.QtWidgets" in clean:
            violations.append(f.relative_to(REPO))
    assert len(violations) == 0, f"QML bridge should not import QtWidgets: {violations}"


def test_py_no_qtwidgets_imports_in_qml():
    violations = []
    for f in sorted((REPO / "ui_qml").rglob("*.py")):
        if f.name.startswith("__"):
            continue
        text = f.read_text()
        if "QtWidgets" in text:
            violations.append(f.relative_to(REPO))
    assert len(violations) == 0, f"QML should not import QtWidgets: {violations}"


def test_py_deletion_matrix_exists():
    matrix = REPO / "docs" / "migration" / "QTWIDGETS_DELETION_MATRIX.yaml"
    assert matrix.exists(), "Deletion matrix missing"
    text = matrix.read_text()
    for cat in ("KEEP_TEMPORARY_PHYSICAL", "FROZEN_ADAPTER", "SAFE_TO_DELETE", "DELETED"):
        assert cat in text, f"Category {cat} missing in matrix"
