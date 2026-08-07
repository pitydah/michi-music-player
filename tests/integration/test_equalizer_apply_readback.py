"""EqualizerService vertical: validate -> apply -> readback -> update state.

Real EqualizerService with a controllable fake player that mirrors applied EQ
state in its readback, so readback-confirmed updates and failure paths are
exercised honestly.
"""
from __future__ import annotations

import pytest

from core.equalizer_service import (
    GRAPHIC_BAND_COUNT,
    STATUS_ACCEPTED,
    STATUS_CAPABILITY_UNAVAILABLE,
    STATUS_COMPLETED,
    STATUS_FAILED,
    EqualizerPresetRepository,
    EqualizerService,
)


class FakeEqPlayer:
    """Controllable fake mirroring EQ state through its readback."""

    def __init__(self, backend: str = "gstreamer", profile: str = "standard",
                 readback_lag: bool = False):
        self._backend = backend
        self._profile = profile
        self._bands = [0.0] * GRAPHIC_BAND_COUNT
        self._preamp = 0.0
        self._bypass = True
        self._mode = "bypass"
        self.apply_error: Exception | None = None
        self._mirror = not readback_lag

    def get_active_backend_id(self) -> str:
        return self._backend

    def get_active_profile_id(self) -> str:
        return self._profile

    def get_eq_state(self) -> dict:
        return {
            "mode": self._mode,
            "bands_31": list(self._bands),
            "bands_parametric": [],
            "preamp_db": self._preamp,
        }

    def set_eq_graphic(self, bands: list[float]) -> None:
        if self.apply_error is not None:
            raise self.apply_error
        if self._mirror:
            self._bands = [float(b) for b in bands]
        self._mode = "graphic" if self._mirror else self._mode

    def set_eq_preamp(self, db: float) -> None:
        if self.apply_error is not None:
            raise self.apply_error
        if self._mirror:
            self._preamp = float(db)

    def set_eq_bypass(self, bypass: bool) -> None:
        if self.apply_error is not None:
            raise self.apply_error
        if self._mirror:
            self._bypass = bool(bypass)
            self._mode = "bypass" if bypass else "graphic"


@pytest.fixture()
def player():
    return FakeEqPlayer()


@pytest.fixture()
def svc(player):
    return EqualizerService(
        player_service=player,
        preset_repository=EqualizerPresetRepository(persist=False),
    )


class TestEqualizerApplyReadback:
    def test_apply_preset_readback_confirms_state(self, svc):
        bands = [1.0] * GRAPHIC_BAND_COUNT
        result = svc.set_bands(bands)
        assert result["ok"] is True
        assert result["status"] == STATUS_COMPLETED
        assert svc.get_bands() == bands

    def test_readback_lag_does_not_update_state(self):
        player = FakeEqPlayer(readback_lag=True)
        svc = EqualizerService(
            player_service=player,
            preset_repository=EqualizerPresetRepository(persist=False),
        )
        result = svc.set_bands([2.0] * GRAPHIC_BAND_COUNT)
        assert result["ok"] is False
        assert result["status"] == STATUS_FAILED
        assert result["code"] == "READBACK_MISMATCH"
        assert svc.get_bands() == [0.0] * GRAPHIC_BAND_COUNT, (
            "state must not update without backend confirmation")

    def test_backend_error_is_failed_state_unchanged(self, player, svc):
        player.apply_error = RuntimeError("gst pipeline failed")
        result = svc.set_bands([3.0] * GRAPHIC_BAND_COUNT)
        assert result["ok"] is False
        assert result["status"] == STATUS_FAILED
        assert result["code"] == "BACKEND_APPLY_FAILED"
        assert svc.get_bands() == [0.0] * GRAPHIC_BAND_COUNT

    def test_invalid_band_count_is_failed(self, player, svc):
        result = svc.set_bands([1.0, 2.0, 3.0])
        assert result["ok"] is False
        assert result["status"] == STATUS_FAILED
        assert result["code"] == "INVALID_BAND_COUNT"

    def test_gain_out_of_range_is_failed(self, player, svc):
        result = svc.set_bands([99.0] * GRAPHIC_BAND_COUNT)
        assert result["ok"] is False
        assert result["status"] == STATUS_FAILED
        assert result["code"] == "GAIN_OUT_OF_RANGE"

    def test_mpd_backend_capability_unavailable(self):
        player = FakeEqPlayer(backend="mpd")
        svc = EqualizerService(
            player_service=player,
            preset_repository=EqualizerPresetRepository(persist=False),
        )
        assert svc.available is False
        result = svc.set_bands([1.0] * GRAPHIC_BAND_COUNT)
        assert result["ok"] is False
        assert result["status"] == STATUS_CAPABILITY_UNAVAILABLE

    def test_bitperfect_profile_capability_unavailable(self):
        player = FakeEqPlayer(profile="bitperfect_pcm")
        svc = EqualizerService(
            player_service=player,
            preset_repository=EqualizerPresetRepository(persist=False),
        )
        caps = svc.capabilities()
        assert caps.bitperfect_blocked is True
        assert svc.available is False
        result = svc.set_enabled(True)
        assert result["ok"] is False
        assert result["status"] == STATUS_CAPABILITY_UNAVAILABLE

    def test_profile_forbidding_eq_capability_unavailable(self):
        player = FakeEqPlayer(profile="michi_hifi_mpd")
        svc = EqualizerService(
            player_service=player,
            preset_repository=EqualizerPresetRepository(persist=False),
        )
        assert svc.available is False
        assert any("eq" in r for r in svc.capabilities().reasons)

    def test_enabled_readback_confirmed(self, player, svc):
        result = svc.set_enabled(True)
        assert result["ok"] is True
        assert result["status"] == STATUS_COMPLETED
        assert svc.enabled is True
        result = svc.set_enabled(False)
        assert result["ok"] is True
        assert not svc.enabled

    def test_preamp_readback_confirmed(self, player, svc):
        result = svc.set_preamp(-3.5)
        assert result["ok"] is True
        assert result["status"] == STATUS_COMPLETED
        assert svc.get_preamp() == -3.5

    def test_local_only_without_player_is_accepted(self):
        svc = EqualizerService(
            preset_repository=EqualizerPresetRepository(persist=False))
        assert svc.available is False
        result = svc.set_bands([4.0] * GRAPHIC_BAND_COUNT)
        assert result["ok"] is True
        assert result["status"] == STATUS_ACCEPTED
        assert result["code"] == "LOCAL_ONLY"
        assert svc.get_bands() == [4.0] * GRAPHIC_BAND_COUNT

    def test_preset_persists_and_loads(self, svc):
        bands = [2.0] * GRAPHIC_BAND_COUNT
        svc.set_bands(bands)
        svc.set_preamp(1.5)
        result = svc.save_preset("Mi Preset")
        assert result["ok"] is True
        assert "Mi Preset" in svc.list_presets()
        svc.reset()
        assert svc.get_bands() == [0.0] * GRAPHIC_BAND_COUNT
        loaded = svc.load_preset("Mi Preset")
        assert loaded["ok"] is True
        assert svc.get_bands() == bands

    def test_persistent_repository_round_trip(self, tmp_path):
        from audio import eq_presets

        original_path = eq_presets.PRESETS_PATH
        original_dir = eq_presets.SETTINGS_DIR
        try:
            eq_presets.PRESETS_PATH = str(tmp_path / "eq_presets.json")
            eq_presets.SETTINGS_DIR = str(tmp_path)
            repo = EqualizerPresetRepository(persist=True)
            assert repo.save("Persistido", [5.0] * GRAPHIC_BAND_COUNT, 0.0, True)
            repo2 = EqualizerPresetRepository(persist=True)
            assert "Persistido" in repo2.list_presets()
            assert repo2.get("Persistido")["bands"] == [5.0] * GRAPHIC_BAND_COUNT
            assert repo2.delete("Persistido")
            assert "Persistido" not in repo2.list_presets()
        finally:
            eq_presets.PRESETS_PATH = original_path
            eq_presets.SETTINGS_DIR = original_dir
