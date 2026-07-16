from __future__ import annotations

from pathlib import Path

import pytest

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
PAGE_FILES = sorted(QML_DIR.rglob("*.qml"))


def _is_component(path: Path) -> bool:
    rel = path.relative_to(QML_DIR)
    return str(rel).startswith("components/")


def _is_theme(path: Path) -> bool:
    rel = path.relative_to(QML_DIR)
    return str(rel).startswith("theme/")


def _is_material(path: Path) -> bool:
    rel = path.relative_to(QML_DIR)
    return str(rel).startswith("materials/") or str(rel).startswith("effects/")


def _is_import_or_qmldir(path: Path) -> bool:
    return path.name in ("qmldir", "dirs.qml")


PAGE_FILES_FILTERED = [
    p for p in PAGE_FILES
    if not _is_component(p) and not _is_theme(p)
    and not _is_material(p) and not _is_import_or_qmldir(p)
]


@pytest.mark.parametrize("qml_file", PAGE_FILES_FILTERED, ids=lambda p: str(p.relative_to(QML_DIR)))
def test_page_has_accessible_role(qml_file):
    content = qml_file.read_text()
    assert "Accessible.role" in content, (
        f"{qml_file.relative_to(QML_DIR)} lacks Accessible.role on root"
    )


@pytest.mark.parametrize("qml_file", PAGE_FILES_FILTERED, ids=lambda p: str(p.relative_to(QML_DIR)))
def test_page_has_object_name(qml_file):
    content = qml_file.read_text()
    assert "objectName" in content, (
        f"{qml_file.relative_to(QML_DIR)} lacks objectName on root"
    )
