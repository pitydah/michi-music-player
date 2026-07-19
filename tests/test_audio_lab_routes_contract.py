from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
from ui_qml_bridge.route_registry import ROUTES, resolve_route


REPO_ROOT = Path(__file__).resolve().parent.parent
QML_ROOT = REPO_ROOT / "ui_qml"

CANONICAL_AREA_ROUTES = {
    "diagnostics": "audio_lab.analysis",
    "identifier": "audio_lab.metadata",
    "backup": "audio_lab",
    "output_profiles": "audio_lab.output_profiles",
    "local_intelligence": "audio_lab.analysis",
}


@pytest.mark.parametrize("legacy, canonical", CANONICAL_AREA_ROUTES.items())
def test_audio_lab_area_routes_resolve_to_canonical_destinations(
    legacy: str, canonical: str,
) -> None:
    legacy_route = f"audio_lab.{legacy}"
    if legacy == "output_profiles":
        legacy_route = canonical

    assert resolve_route(legacy_route) == canonical
    assert canonical in ROUTES


def test_legacy_audio_lab_hubs_are_not_canonical_routes() -> None:
    assert "audio_lab.diagnostics" not in ROUTES
    assert "audio_lab.identifier" not in ROUTES
    assert "audio_lab.backup" not in ROUTES
    assert "audio_lab.local_intelligence" not in ROUTES


def test_audio_lab_bridge_area_navigation_uses_canonical_routes() -> None:
    navigation = MagicMock()
    navigation.navigate.side_effect = lambda route: {"ok": True, "route": route}
    bridge = AudioLabBridge(navigation_bridge=navigation)

    for area, route in CANONICAL_AREA_ROUTES.items():
        assert bridge.navigateToArea(area) == {"ok": True, "route": route}
        navigation.navigate.assert_called_with(route)


def test_audio_lab_bridge_exposes_area_navigation_slot() -> None:
    bridge = AudioLabBridge()
    method = bridge.metaObject().indexOfMethod("navigateToArea(QString)")

    assert method >= 0
    assert bridge.metaObject().method(method).parameterCount() == 1


@pytest.mark.parametrize(
    "relative_path, canonical_type",
    [
        ("pages/audio_lab/AudioLabOverviewPage.qml", "AudioLabHubPage"),
        ("pages/assistant/AudioLabPage.qml", "AudioLabPages.AudioLabHubPage"),
    ],
)
def test_legacy_audio_lab_roots_are_thin_wrappers(
    relative_path: str, canonical_type: str,
) -> None:
    source = (QML_ROOT / relative_path).read_text(encoding="utf-8")

    assert canonical_type in source
    assert "audioLabBridge" not in source
    assert "navigationBridge.navigate" not in source


def test_processing_hub_equalizer_uses_equalizer_route() -> None:
    source = (
        QML_ROOT / "pages/audio_lab/AudioProcessingHubPage.qml"
    ).read_text(encoding="utf-8")

    assert 'navigationBridge.navigate("audio_lab.equalizer")' in source
