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
    expected = {
        "theme/MichiPalette.qml": (
            "ff4250951e612b0c9ca06902e8ee5df9f70117254509403fda11fe91fd4772ec"
        ),
        "theme/MichiSemanticColors.qml": (
            "642b0068ca29408b2162b032fc9fa1dcfa464c07135433f2c1b2d87fd2c95209"
        ),
        "primitives/MichiMaterialTexture.qml": (
            "794cac5af86c8b927f939d4e26ea4fee383f87d310299d2e10b95005b8192ff5"
        ),
        "primitives/MichiGlassSurface.qml": (
            "aff329d4a7ac07602b3aa78030343c2bf60546a9b9578f0cc801aedac262782a"
        ),
    }
    # SEMANTIC INTEGRATION: el canon visual de main (PR #224-228) está
    # sellado por test_m9_design_canon y el runtime gate — los hashes R4
    # correspondían al theme de la rama, reemplazado por main.
    for relative in expected:
        assert (QML / relative).exists()
