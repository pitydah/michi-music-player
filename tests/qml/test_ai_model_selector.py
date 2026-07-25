from __future__ import annotations

from pathlib import Path


QML_DIR = Path(__file__).resolve().parents[2] / "ui_qml"
SELECTOR_PATH = QML_DIR / "pages" / "assistant" / "AIModelSelector.qml"
ASSISTANT_PATH = QML_DIR / "pages" / "assistant" / "AssistantPage.qml"


def test_selector_exposes_future_integration_contract() -> None:
    content = SELECTOR_PATH.read_text(encoding="utf-8")

    assert 'property string selectedModelId: "calico"' in content
    assert "signal modelSelectionRequested(string modelId)" in content
    assert "integrationReady" in content
    assert "michiAiBridge" not in content
    assert "setBackend" not in content
    assert "installModel" not in content


def test_selector_contains_all_five_model_identities() -> None:
    content = SELECTOR_PATH.read_text(encoding="utf-8")

    for model_id in ("calico", "munchkin", "carey", "maine_coon", "sphynx"):
        assert f'modelId: "{model_id}"' in content

    for asset_name in (
        "michi-calico.png",
        "michi-munchkin.png",
        "michi-carey.png",
        "michi-maine-coon.png",
        "michi-sphynx.png",
    ):
        assert (QML_DIR / "assets" / "ai_models" / asset_name).is_file()


def test_selector_is_integrated_without_backend_side_effects() -> None:
    content = ASSISTANT_PATH.read_text(encoding="utf-8")

    assert "AIModelSelector {" in content
    assert "signal aiModelSelectionRequested(string modelId)" in content
    assert "root.aiModelSelectionRequested(modelId)" in content
