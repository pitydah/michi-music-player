"""Tests for EqualizerService — bands, presets, preamp, bypass."""
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def eq():
    from core.equalizer_service import EqualizerService
    return EqualizerService()


@pytest.fixture
def eq_with_player():
    from core.equalizer_service import EqualizerService
    player = MagicMock()
    return EqualizerService(player_service=player)


class TestEqualizer:
    def test_initial_state(self, eq):
        assert not eq.available
        assert not eq.enabled
        assert eq.get_bands() == [0.0] * 31
        assert eq.get_preamp() == 0.0

    def test_set_bands(self, eq):
        bands = [-5.0, -3.0, 0.0, 2.0, 4.0, 3.0, 1.0, -1.0, -3.0, -5.0]
        eq.set_bands(bands)
        assert eq.get_bands() == bands

    def test_set_preamp(self, eq):
        eq.set_preamp(-3.5)
        assert eq.get_preamp() == -3.5

    def test_set_enabled(self, eq):
        assert not eq.enabled
        eq.set_enabled(True)
        assert eq.enabled
        eq.set_enabled(False)
        assert not eq.enabled

    def test_save_load_preset(self, eq):
        eq.set_bands([1.0] * 31)
        eq.set_preamp(2.0)
        eq.set_enabled(True)
        eq.save_preset("Test Preset")
        assert "Test Preset" in eq.list_presets()

        # Reset and load
        eq.reset()
        assert eq.get_bands() == [0.0] * 31
        eq.load_preset("Test Preset")
        assert eq.get_bands() == [1.0] * 31
        assert eq.get_preamp() == 2.0

    def test_delete_preset(self, eq):
        eq.save_preset("Temp Preset")
        eq.delete_preset("Temp Preset")
        assert "Temp Preset" not in eq.list_presets()

    def test_delete_nonexistent(self, eq):
        result = eq.delete_preset("Nonexistent")
        assert not result["ok"]

    def test_load_nonexistent(self, eq):
        result = eq.load_preset("Nonexistent")
        assert not result["ok"]

    def test_reset(self, eq):
        eq.set_bands([5.0] * 31)
        eq.set_preamp(3.0)
        eq.set_enabled(True)
        eq.reset()
        assert eq.get_bands() == [0.0] * 31
        assert eq.get_preamp() == 0.0
        assert not eq.enabled

    def test_health(self, eq):
        health = eq.health()
        assert not health["available"]
        assert health["presets"] == 0

    def test_with_player(self, eq_with_player):
        assert eq_with_player.available
        eq_with_player.set_enabled(True)
        eq_with_player._player.set_eq_bypass.assert_called_with(False)
        eq_with_player.set_bands([2.0] * 10)
        eq_with_player._player.set_eq_graphic.assert_called_with([2.0] * 10)
        eq_with_player.set_preamp(-2.0)
        eq_with_player._player.set_eq_preamp.assert_called_with(-2.0)
