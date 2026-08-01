from __future__ import annotations

"""Audio Lab hub — exactly five area cards in a 3+2 layout.

The hub (ui_qml/pages/audio_lab/AudioLabHubPage.qml) is the canonical
"audio_lab" route destination. It must expose exactly five cards navigating
to the five canonical audio_lab.* tool routes, without adding them to the
sidebar.
"""

from pathlib import Path

import pytest

from ui_qml_bridge.route_registry import ROUTES

pytestmark = pytest.mark.isolation

HUB = Path("ui_qml/pages/audio_lab/AudioLabHubPage.qml")

EXPECTED_CARDS = {
    "Diagnóstico": "audio_lab.diagnostics",
    "Identificador de Audios": "audio_lab.identifier",
    "Respaldar": "audio_lab.backup",
    "Perfiles de Salida": "audio_lab.output_profiles",
    "Inteligencia local": "audio_lab.local_intelligence",
}


@pytest.fixture(scope="module")
def hub_source() -> str:
    return HUB.read_text(encoding="utf-8")


class TestAudioLabHubFiveCards:
    def test_all_five_card_titles_present(self, hub_source):
        for title in EXPECTED_CARDS:
            assert title in hub_source, f"missing card title: {title}"

    def test_all_five_routes_present(self, hub_source):
        for route in EXPECTED_CARDS.values():
            assert f'"{route}"' in hub_source, f"missing card route: {route}"

    def test_no_legacy_area_routes(self, hub_source):
        for legacy in (
            "audio_lab.analysis",
            "audio_lab.processing",
            "audio_lab.metadata\"",
            "audio_lab.capture",
            "audio_lab.library_health",
        ):
            assert legacy not in hub_source, f"legacy card still present: {legacy}"

    def test_three_plus_two_layout(self, hub_source):
        assert "slice(0, 3)" in hub_source
        assert "slice(3, 5)" in hub_source
        assert "anchors.horizontalCenter: parent.horizontalCenter" in hub_source

    def test_card_fields_present(self, hub_source):
        for field in ("iconKey", "statusText", "capability", "metadataText", "onClicked"):
            assert field in hub_source, f"card field missing: {field}"

    def test_routes_exist_in_registry(self):
        for route in EXPECTED_CARDS.values():
            assert route in ROUTES, f"route not registered: {route}"

    def test_routes_not_in_sidebar(self):
        for route in EXPECTED_CARDS.values():
            assert ROUTES[route]["sidebar_visible"] is False, (
                f"{route} must stay out of the sidebar"
            )

    def test_hub_remains_canonical_audio_lab_page(self):
        assert ROUTES["audio_lab"]["source"].endswith("AudioLabHubPage.qml")
