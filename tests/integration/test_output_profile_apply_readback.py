"""OutputProfileService vertical: apply -> readback -> honest status.

Real OutputProfileService with a controllable fake player implementing the
PlayerService facade readback surface (get_active_profile_id,
get_active_backend_id, get_output_device_id, set_profile, get_eq_state,
get_transmit_device).
"""
from __future__ import annotations

import pytest

from core.output_profile_service import (
    STATUS_CAPABILITY_UNAVAILABLE,
    STATUS_COMPLETED,
    STATUS_CONFLICT,
    STATUS_FAILED,
    STATUS_PARTIAL_SUCCESS,
    OutputProfileService,
)


class FakePlayerForProfiles:
    """Controllable fake implementing the PlayerService readback surface."""

    def __init__(self, profile_id: str = "standard", backend: str = "gstreamer",
                 device: str = "auto", eq_mode: str = "bypass",
                 transmit: object | None = None):
        self._profile = profile_id
        self._backend = backend
        self._device = device
        self._eq_mode = eq_mode
        self._transmit = transmit
        self.set_profile_calls: list[str] = []
        self.set_profile_result: dict | None = None
        self.apply_error: Exception | None = None

    def get_active_profile_id(self) -> str:
        return self._profile

    def get_active_backend_id(self) -> str:
        return self._backend

    def get_output_device_id(self) -> str:
        return self._device

    def get_transmit_device(self):
        return self._transmit

    def get_eq_state(self) -> dict:
        return {"mode": self._eq_mode}

    def set_profile(self, profile_id: str) -> dict:
        self.set_profile_calls.append(profile_id)
        if self.apply_error is not None:
            raise self.apply_error
        if self.set_profile_result is not None:
            return dict(self.set_profile_result)
        self._profile = profile_id
        from audio.output_profiles import get_profile, is_mpd_profile

        profile = get_profile(profile_id)
        self._backend = "mpd" if is_mpd_profile(profile_id) else "gstreamer"
        self._device = getattr(profile, "preferred_device", "") or "auto"
        return {
            "ok": True,
            "active_profile": profile_id,
            "active_backend": self._backend,
            "fallback": False,
            "requires_restart": False,
            "verified": True,
        }


@pytest.fixture()
def player():
    return FakePlayerForProfiles()


@pytest.fixture()
def svc(player):
    return OutputProfileService(player_service=player)


class TestOutputProfileApplyReadback:
    def test_apply_success_readback_confirms(self, svc, player):
        result = svc.set_profile("hifi_pcm")
        assert result["ok"] is True
        assert result["status"] == STATUS_COMPLETED
        assert player.set_profile_calls == ["hifi_pcm"]
        # Readback reflects the intent.
        assert svc.get_active_profile_id() == "hifi_pcm"
        assert svc.get_active_backend_id() == player.get_active_backend_id()

    def test_apply_success_with_mpd_backend(self, svc, player):
        result = svc.set_profile("michi_hifi_mpd")
        assert result["ok"] is True
        assert result["status"] == STATUS_COMPLETED
        assert svc.get_active_backend_id() == "mpd"

    def test_apply_readback_mismatch_is_partial(self, player):
        class StuckPlayer(FakePlayerForProfiles):
            def set_profile(self, profile_id: str) -> dict:
                self.set_profile_calls.append(profile_id)
                return {"ok": True, "active_profile": profile_id}

        stuck = StuckPlayer()
        svc = OutputProfileService(player_service=stuck)
        result = svc.set_profile("hifi_pcm")
        assert result["ok"] is False
        assert result["status"] == STATUS_PARTIAL_SUCCESS
        assert result["code"] == "READBACK_MISMATCH"

    def test_unknown_profile_is_failed(self, svc):
        result = svc.set_profile("no_such_profile")
        assert result["ok"] is False
        assert result["status"] == STATUS_FAILED
        assert result["code"] == "UNKNOWN_PROFILE"

    def test_backend_error_is_failed_not_success(self, player):
        player.apply_error = RuntimeError("pipeline exploded")
        svc = OutputProfileService(player_service=player)
        result = svc.set_profile("hifi_pcm")
        assert result["ok"] is False
        assert result["status"] == STATUS_FAILED
        assert result["code"] == "APPLY_ERROR"

    def test_apply_result_failure_is_failed(self, player):
        player.set_profile_result = {"ok": False, "code": "VERIFY_FAILED",
                                     "message": "verificación falló"}
        svc = OutputProfileService(player_service=player)
        result = svc.set_profile("hifi_pcm")
        assert result["ok"] is False
        assert result["status"] == STATUS_FAILED

    def test_bitperfect_conflict_with_eq(self, player):
        player._eq_mode = "graphic"
        svc = OutputProfileService(player_service=player)
        conflicts = svc.check_compatibility("bitperfect_pcm")
        assert "eq" in conflicts
        result = svc.set_profile("bitperfect_pcm")
        assert result["ok"] is False
        assert result["status"] == STATUS_CONFLICT
        assert "eq" in result["data"].get("conflicts", [])
        assert player.set_profile_calls == [], "apply must be refused on conflict"

    def test_bitperfect_conflict_with_transmit(self, player):
        player._transmit = object()
        svc = OutputProfileService(player_service=player)
        conflicts = svc.check_compatibility("bitperfect_pcm")
        assert "transmit" in conflicts
        result = svc.set_profile("bitperfect_pcm")
        assert result["status"] == STATUS_CONFLICT

    def test_non_bitperfect_profile_has_no_conflicts(self, player):
        player._eq_mode = "graphic"
        player._transmit = object()
        svc = OutputProfileService(player_service=player)
        assert svc.check_compatibility("standard") == []

    def test_available_false_without_player(self):
        svc = OutputProfileService(player_service=None)
        assert svc.available is False
        health = svc.health()
        assert health["available"] is False
        assert "player_missing" in health["reasons"]

    def test_apply_without_player_is_capability_unavailable(self):
        svc = OutputProfileService(player_service=None)
        result = svc.set_profile("hifi_pcm")
        assert result["ok"] is False
        assert result["status"] == STATUS_CAPABILITY_UNAVAILABLE

    def test_available_true_with_full_readback(self, svc):
        assert svc.available is True
        health = svc.health()
        assert health["available"] is True
        assert health["reasons"] == []

    def test_event_published_on_apply(self, player):
        events = []

        class Bus:
            def publish(self, event, **data):
                events.append((event, data))

        svc = OutputProfileService(player_service=player, event_bus=Bus())
        svc.set_profile("hifi_pcm")
        assert any(event == "output_profile.applied" for event, _ in events)
