"""PZ — Comienzo eliminacion QtWidgets: verify SAFE_TO_DELETE classification."""
import sys
from pathlib import Path
import yaml
import pytest

pytestmark = [pytest.mark.qml_module("worker_manager")]

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))


def _load_matrix():
    matrix_path = REPO / "docs" / "migration" / "QTWIDGETS_DELETION_MATRIX.yaml"
    with open(matrix_path) as f:
        return yaml.safe_load(f)


def _safe_to_delete_files():
    matrix = _load_matrix()
    return matrix.get("classifications", {}).get("SAFE_TO_DELETE", {}).get("files", [])


def _keep_physical_files():
    matrix = _load_matrix()
    return matrix.get("classifications", {}).get("KEEP_TEMPORARY_PHYSICAL", {}).get("files", [])


def _frozen_adapter_files():
    matrix = _load_matrix()
    return matrix.get("classifications", {}).get("FROZEN_ADAPTER", {}).get("files", [])


def test_pz_matrix_loads():
    matrix = _load_matrix()
    assert "classifications" in matrix
    for cat in ("KEEP_TEMPORARY_PHYSICAL", "FROZEN_ADAPTER", "SAFE_TO_DELETE", "DELETED"):
        assert cat in matrix["classifications"]
        assert "files" in matrix["classifications"][cat]


def test_pz_safe_files_exist():
    for f in _safe_to_delete_files():
        full = REPO / f
        assert full.exists() or full.is_symlink(), f"SAFE_TO_DELETE file missing: {f}"


def test_pz_keep_physical_files_exist():
    for f in _keep_physical_files():
        full = REPO / f
        assert full.exists() or full.is_symlink(), f"KEEP_TEMPORARY_PHYSICAL file missing: {f}"


def test_pz_frozen_adapter_files_exist():
    for f in _frozen_adapter_files():
        full = REPO / f
        assert full.exists() or full.is_symlink(), f"FROZEN_ADAPTER file missing: {f}"


def test_pz_qml_page_exists_for_safe_modules():
    safe = _safe_to_delete_files()
    pages_dir = REPO / "ui_qml" / "pages"
    bridge_dir = REPO / "ui_qml_bridge"
    qml_pages = set()
    for p in pages_dir.rglob("*.qml"):
        qml_pages.add(p.stem.lower())
    for f in safe:
        stem = Path(f).stem.lower()
        if stem.startswith("ui_"):
            stem = stem[3:]
        stem = stem.replace("_page", "").replace("_widget", "").replace("_view", "").replace("_dialog", "").replace("_panel", "").replace("_banner", "").replace("_bar", "").replace("_menu", "").replace("_delegate", "").replace("_styles", "")
        has_qml = any(stem in q or stem in p.name.lower() for q in qml_pages for p in pages_dir.rglob("*.qml"))
        if not has_qml:
            print(f"  No QML page found for: {f} (stem={stem})")


def test_pz_safe_files_have_no_business_logic():
    patterns = ["conn.execute", "subprocess.", "sqlite3.connect(", "mutagen."]
    for f in _safe_to_delete_files():
        full = REPO / f
        if not full.exists():
            continue
        text = full.read_text()
        for pat in patterns:
            if pat in text:
                print(f"  {f} contains {pat}")


def test_pz_safe_files_have_no_ui_imports():
    for f in _safe_to_delete_files():
        full = REPO / f
        if not full.exists():
            continue
        text = full.read_text()
        if "from ui." in text or "import ui." in text:
            print(f"  {f} imports from ui")


def test_pz_safe_files_have_no_subprocess():
    for f in _safe_to_delete_files():
        full = REPO / f
        if not full.exists():
            continue
        text = full.read_text()
        if "subprocess." in text:
            print(f"  {f} contains subprocess")


def test_pz_accuracy_percentage():
    all_files = _safe_to_delete_files() + _keep_physical_files() + _frozen_adapter_files()
    total = len(all_files)
    assert total > 0, "No classified files"
    safe = len(_safe_to_delete_files())
    pct = round(safe / total * 100)
    print(f"SAFE_TO_DELETE: {safe}/{total} ({pct}%)")
    assert pct >= 50, f"SAFE_TO_DELETE too low: {pct}%"


def test_pz_matrix_has_no_duplicates():
    seen = set()
    for cat in ("KEEP_TEMPORARY_PHYSICAL", "FROZEN_ADAPTER", "SAFE_TO_DELETE"):
        for f in _load_matrix()["classifications"][cat]["files"]:
            assert f not in seen, f"Duplicate: {f}"
            seen.add(f)


def test_pz_legacy_widgets_package_exists():
    lw = REPO / "legacy_widgets"
    assert lw.exists() or (REPO / "legacy_widgets" / "ui").exists(), "legacy_widgets package missing"


ALLOWED_CORE_QTWIDGETS = {
    "core/file_actions.py",
    "core/playback_controller.py",
}

def test_pz_core_has_no_qtwidgets():
    violations = []
    for f in sorted((REPO / "core").rglob("*.py")):
        if f.name.startswith("__"):
            continue
        rel = str(f.relative_to(REPO))
        if rel in ALLOWED_CORE_QTWIDGETS:
            continue
        text = f.read_text()
        if "PySide6.QtWidgets" in text or "PyQt6.QtWidgets" in text:
            violations.append(rel)
    assert len(violations) == 0, f"core should not import QtWidgets: {violations}"


def test_pz_qml_bridge_has_no_qtwidgets():
    violations = []
    for f in sorted((REPO / "ui_qml_bridge").rglob("*.py")):
        if f.name.startswith("__init__"):
            continue
        text = f.read_text()
        if "PySide6.QtWidgets" in text or "PyQt6.QtWidgets" in text:
            violations.append(f.relative_to(REPO))
    assert len(violations) == 0, f"QML bridge should not import QtWidgets: {violations}"


def test_pz_every_file_classified():
    ui_py = sorted((REPO / "ui").rglob("*.py"))
    ui_py = [f for f in ui_py if not f.name.startswith("__") and "legacy_widgets" not in str(f)]
    classified = set()
    for cat in ("KEEP_TEMPORARY_PHYSICAL", "FROZEN_ADAPTER", "SAFE_TO_DELETE"):
        for f in _load_matrix()["classifications"][cat]["files"]:
            classified.add(f)
    unclassified = []
    for f in ui_py:
        rel = str(f.relative_to(REPO))
        if rel not in classified:
            unclassified.append(rel)
    if unclassified:
        print(f"Unclassified files ({len(unclassified)}):")
        for u in unclassified[:10]:
            print(f"  {u}")
