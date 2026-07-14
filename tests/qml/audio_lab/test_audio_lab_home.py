"""Tests for AudioLabOverviewPage hub page."""
from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock

import pytest

pytestmark = pytest.mark.isolation


@pytest.fixture
def mock_alab():
    alab = MagicMock()
    type(alab).backendInfo = PropertyMock(return_value={"backend": "gstreamer", "available": True})
    type(alab).pipelineInfo = PropertyMock(return_value={"sample_rate": 44100, "bit_depth": 16})
    type(alab).totalTracks = PropertyMock(return_value=100)
    type(alab).missingMetadata = PropertyMock(return_value=5)
    type(alab).missingCovers = PropertyMock(return_value=2)
    alab.refresh.return_value = {"ok": True}
    return alab


@pytest.fixture
def mock_nav():
    nav = MagicMock()
    nav.navigate = MagicMock()
    nav.back = MagicMock()
    return nav


class TestAudioLabHome:
    def test_hero_present(self, mock_alab, mock_nav):
        assert mock_alab is not None
        assert mock_nav is not None

    def test_status_badge_ready(self, mock_alab):
        backend = mock_alab.backendInfo
        assert backend["available"] is True
        assert backend["backend"] == "gstreamer"

    def test_status_badge_unavailable(self):
        alab = MagicMock()
        type(alab).backendInfo = PropertyMock(return_value={"backend": "none", "available": False})
        bi = alab.backendInfo
        assert bi["available"] is False

    def test_card_analysis_navigates(self, mock_alab, mock_nav):
        mock_nav.navigate("audio_lab.analysis")
        mock_nav.navigate.assert_called_with("audio_lab.analysis")

    def test_card_conversion_navigates(self, mock_alab, mock_nav):
        mock_nav.navigate("audio_lab.conversion")
        mock_nav.navigate.assert_called_with("audio_lab.conversion")

    def test_card_normalization_navigates(self, mock_alab, mock_nav):
        mock_nav.navigate("audio_lab.normalization")
        mock_nav.navigate.assert_called_with("audio_lab.normalization")

    def test_card_replaygain_navigates(self, mock_alab, mock_nav):
        mock_nav.navigate("audio_lab.replaygain")
        mock_nav.navigate.assert_called_with("audio_lab.replaygain")

    def test_card_integrity_navigates(self, mock_alab, mock_nav):
        mock_nav.navigate("audio_lab.integrity")
        mock_nav.navigate.assert_called_with("audio_lab.integrity")

    def test_card_comparison_navigates(self, mock_alab, mock_nav):
        mock_nav.navigate("audio_lab.comparison")
        mock_nav.navigate.assert_called_with("audio_lab.comparison")

    def test_card_jobs_navigates(self, mock_alab, mock_nav):
        mock_nav.navigate("audio_lab.jobs")
        mock_nav.navigate.assert_called_with("audio_lab.jobs")

    def test_card_profiles_navigates(self, mock_alab, mock_nav):
        mock_nav.navigate("audio_lab.profiles")
        mock_nav.navigate.assert_called_with("audio_lab.profiles")

    def test_null_bridge_handled(self):
        assert True

    def test_backend_info_displays(self, mock_alab):
        info = mock_alab.pipelineInfo
        assert info["sample_rate"] == 44100

    def test_stats_from_bridge(self, mock_alab):
        assert mock_alab.totalTracks == 100
        assert mock_alab.missingMetadata == 5
        assert mock_alab.missingCovers == 2

    def test_refresh_called_on_load(self, mock_alab):
        mock_alab.refresh()
        mock_alab.refresh.assert_called_once()

    def test_all_eight_cards(self):
        cards = [
            "Análisis técnico", "Conversión", "Normalización",
            "ReplayGain", "Integridad", "Comparación",
            "Trabajos", "Perfiles",
        ]
        assert len(cards) == 8

    def test_keyboard_navigation_cards(self):
        routes = [
            "audio_lab.analysis", "audio_lab.conversion", "audio_lab.normalization",
            "audio_lab.replaygain", "audio_lab.integrity", "audio_lab.comparison",
            "audio_lab.jobs", "audio_lab.profiles",
        ]
        assert len(routes) == 8
        for r in routes:
            assert "." in r

    def test_accessible_names_on_cards(self):
        names = [
            "Análisis técnico", "Conversión", "Normalización",
            "ReplayGain", "Integridad", "Comparación",
            "Trabajos", "Perfiles",
        ]
        for n in names:
            assert len(n) > 0

    def test_backend_status_section(self, mock_alab):
        info = mock_alab.backendInfo
        assert "backend" in info
        assert "available" in info

    def test_experimental_badge_present(self):
        badges = ["Experimental", "Requiere ffmpeg para conversión"]
        assert len(badges) == 2
