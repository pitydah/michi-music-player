"""M9-R3 P0 gates: scan convergence, precision-mode removal and visual canon."""

import hashlib
from pathlib import Path

QML = Path("src/michi/presentation/qml")


def _text(relative: str) -> str:
    return (QML / relative).read_text()


def test_library_toolbar_has_real_id_for_empty_state_scan_intent() -> None:
    source = _text("views/LibraryView.qml")
    assert "LibraryToolbar {\n            id: libraryToolbar" in source
    assert "onScanRequested: libraryToolbar.performScan()" in source


def test_scan_and_folder_actions_share_native_folder_picker_contract() -> None:
    toolbar = _text("views/LibraryToolbar.qml")
    assert "performScan" in toolbar
    assert "scanAllSources" not in toolbar
    assert "root.scanning" in toolbar


def test_precision_mode_is_completely_removed_from_production_qml() -> None:
    popup = _text("views/LibraryViewOptionsPopup.qml")
    assert "precisionMode" not in popup


def test_m9_r3_frozen_visual_canon_hashes() -> None:
    """POST-MERGE SEMANTIC RECOVERY: el canon visual ACTUAL (main
    premium post-merge) se congela por hash REAL — no solo por
    existencia. Un cambio de theme sin re-sellar el canon rompe el gate."""
    expected = {
        "theme/MichiPalette.qml": (
            "78ce2d7f9252805ad5930c6b5923f1192a23c9d54ba4348611a6be475813c2a1"
        ),
        "theme/MichiSemanticColors.qml": (
            "4293def77539e4f50530a7bc3fa5522d2daa672747fd95c9455127edeac599a3"
        ),
        "primitives/MichiMaterialTexture.qml": (
            "24e26fd8b3081b52624debf45eb0e3a12bc85e7dd19644a675db2f37ceb22702"
        ),
        "primitives/MichiGlassSurface.qml": (
            "1102d687399f07160bddb1730182495dea06058f9a223f8e44a5f5a5a759dc4e"
        ),
    }
    for relative, digest in expected.items():
        assert hashlib.sha256((QML / relative).read_bytes()).hexdigest() == digest, (
            f"visual canon changed: {relative} (re-seal intentionally)"
        )
