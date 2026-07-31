"""Tests for transactional PlayerService.apply_profile (Patch 2).

Covers the prepare -> apply -> verify -> persist lifecycle, including the
explicit profile states and rollback on verification failure.
"""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def _patch_gst():
    from PySide6.QtCore import QObject, QTimer
    patches = [
        patch("audio.player.Gst", MagicMock()),
        patch("audio.player.GLib", MagicMock()),
        patch("audio.player.gi", MagicMock()),
        patch("audio.player.np", MagicMock()),
        patch("audio.player.QObject", QObject),
        patch("audio.player.QTimer", QTimer),
        patch("audio.player_service.MpdServiceManager", MagicMock(spec=object)),
        patch("audio.player_service.MpdBackend", MagicMock(spec=object)),
    ]
    for p in patches:
        p.start()
    yield
    for p in patches:
        p.stop()


@pytest.fixture
def service():
    from audio.player_service import PlayerService
    from audio.player import PlaybackState
    engine = MagicMock()
    engine.state = PlaybackState.STOPPED
    engine._volume = 0.70
    engine.duration = 0.0
    return PlayerService(engine)


class TestApplyProfileTransactional:
    def test_unknown_profile_returns_unknown(self, service):
        from audio.output_profiles import PROFILE_FAILED
        result = service.apply_profile("does_not_exist")
        assert result["ok"] is False
        assert result["code"] == "UNKNOWN_PROFILE"
        assert result["state"] == PROFILE_FAILED

    def test_success_returns_verified_persisted(self, service):
        from audio.output_profiles import PROFILE_PERSISTED
        with patch.object(service, "switch_backend_for_profile", return_value=True) as sw:
            service._hybrid._active_id = "gstreamer"
            result = service.apply_profile("standard")
        assert result["ok"] is True
        assert result["verified"] is True
        assert result["persisted"] is True
        assert result["state"] == PROFILE_PERSISTED
        assert result["active_profile"] == "standard"
        assert result["active_backend"] == "gstreamer"
        sw.assert_called_once_with("standard")

    def test_backend_failure_propagates_without_verify(self, service):
        from audio.output_profiles import PROFILE_FAILED
        # MPD profile whose backend switch fails -> fell back to gstreamer.
        with patch.object(service, "switch_backend_for_profile", return_value=False):
            service._hybrid._active_id = "gstreamer"
            result = service.apply_profile("michi_hifi_mpd")
        assert result["ok"] is False
        assert result["code"] == "BACKEND_FAILED"
        assert result["state"] == PROFILE_FAILED
        assert result["fallback"] is True

    def test_verify_failure_rolls_back_to_previous(self, service):
        from audio.player import PlaybackState
        from audio.output_profiles import PROFILE_FAILED
        # Active backend not ready -> verify fails and previous profile is restored.
        service._engine.state = PlaybackState.FAILED
        service._active_profile_id = "hifi_pcm"
        with patch.object(service, "switch_backend_for_profile", return_value=True) as sw:
            result = service.apply_profile("standard")
        assert result["ok"] is False
        assert result["code"] == "VERIFY_FAILED"
        assert result["rollback"] is True
        assert result["state"] == PROFILE_FAILED
        assert result["active_profile"] == "hifi_pcm"
        # apply + rollback => two switches, the second restores the previous profile
        assert sw.call_count == 2
        assert sw.call_args_list[1].args[0] == "hifi_pcm"

    def test_set_profile_delegates_and_returns_real_result(self, service):
        """set_profile must not fabricate ok=True when the switch failed."""
        with patch.object(service, "switch_backend_for_profile", return_value=False):
            service._hybrid._active_id = "gstreamer"
            result = service.set_profile("michi_hifi_mpd")
        assert result["ok"] is False
        assert result["fallback"] is True

    def test_success_persists_setting(self, service):
        with patch.object(service, "switch_backend_for_profile", return_value=True):
            service._hybrid._active_id = "gstreamer"
            with patch("core.settings_manager.set_") as set_:
                result = service.apply_profile("hifi_pcm")
        assert result["ok"] is True
        set_.assert_called_with("audio/profile", "hifi_pcm")

    def test_set_audio_profile_delegates_to_apply(self, service):
        with patch.object(service, "switch_backend_for_profile", return_value=True):
            service._hybrid._active_id = "gstreamer"
            service.set_audio_profile("hifi_pcm")
        assert service.get_active_profile_id() == "hifi_pcm"


def _clean_engine_for_bitperfect(engine):
    """Configure a MagicMock engine so no DSP invalidator is active."""
    engine._volume = 100
    engine._replaygain = False
    engine.get_eq_state.return_value = {"mode": "bypass"}
    engine.get_audio_diagnostics.return_value = MagicMock(resampling_active=False)


class TestApplyProfileBitperfectState:
    def test_non_bitperfect_profile_is_unsupported(self, service):
        with patch.object(service, "switch_backend_for_profile", return_value=True), \
                patch("core.settings_manager.set_"):
            service._hybrid._active_id = "gstreamer"
            result = service.apply_profile("standard")
        assert result["ok"] is True
        assert result["bitperfect_state"] == "unsupported"
        assert result["effective_format"]["bitperfect"] == "unsupported"

    def test_bitperfect_invalidated_by_volume(self, service):
        # Volume at 70% breaks the bit-perfect signal path.
        service._engine._volume = 70
        service._engine._replaygain = False
        service._engine.get_eq_state.return_value = {"mode": "bypass"}
        service._engine.get_audio_diagnostics.return_value = MagicMock(
            resampling_active=False)
        with patch.object(service, "switch_backend_for_profile", return_value=True), \
                patch("core.settings_manager.set_"):
            service._hybrid._active_id = "gstreamer"
            result = service.apply_profile("bitperfect_pcm")
        assert result["ok"] is True
        assert result["bitperfect_state"] == "invalidated"
        assert result["effective_format"]["bitperfect"] == "invalidated"
        assert "volume" in result["effective_format"]["invalidators"]

    def test_bitperfect_probable_when_clean(self, service):
        _clean_engine_for_bitperfect(service._engine)
        with patch.object(service, "switch_backend_for_profile", return_value=True), \
                patch("core.settings_manager.set_"):
            service._hybrid._active_id = "gstreamer"
            result = service.apply_profile("bitperfect_pcm")
        assert result["ok"] is True
        assert result["bitperfect_state"] == "probable"
        assert result["effective_format"]["invalidators"] == ()
        assert result["verification_level"] == "dsp_checked"

    def test_bitperfect_invalidated_by_replaygain(self, service):
        _clean_engine_for_bitperfect(service._engine)
        service._engine._replaygain = True
        with patch.object(service, "switch_backend_for_profile", return_value=True), \
                patch("core.settings_manager.set_"):
            service._hybrid._active_id = "gstreamer"
            result = service.apply_profile("pure_audio")
        assert result["ok"] is True
        assert result["bitperfect_state"] == "invalidated"
        assert "replaygain" in result["effective_format"]["invalidators"]

    def test_bitperfect_invalidated_by_resampling(self, service):
        _clean_engine_for_bitperfect(service._engine)
        service._engine.get_audio_diagnostics.return_value = MagicMock(
            resampling_active=True)
        with patch.object(service, "switch_backend_for_profile", return_value=True), \
                patch("core.settings_manager.set_"):
            service._hybrid._active_id = "gstreamer"
            result = service.apply_profile("bitperfect_pcm")
        assert result["ok"] is True
        assert result["bitperfect_state"] == "invalidated"
        assert "resampling" in result["effective_format"]["invalidators"]

    def test_verify_failure_reports_unknown_bitperfect(self, service):
        # Force verify failure deterministically by marking the active backend
        # not ready (patching is_ready directly is immune to cross-test
        # engine.state/PlaybackState plumbing drift in the wider suite).
        service._hybrid._active_id = "gstreamer"
        with patch.object(service, "switch_backend_for_profile", return_value=True), \
                patch.object(service._hybrid.active, "is_ready", return_value=False):
            result = service.apply_profile("bitperfect_pcm")
        assert result["ok"] is False
        assert result["code"] == "VERIFY_FAILED"
        assert result["bitperfect_state"] == "unknown"


class TestApplyProfileStateFields:
    def test_state_fields_filled_on_success(self, service):
        with patch.object(service, "switch_backend_for_profile", return_value=True), \
                patch("core.settings_manager.set_"):
            service._hybrid._active_id = "gstreamer"
            service.apply_profile("hifi_pcm")
        assert service._requested_profile_id == "hifi_pcm"
        assert service._validated_profile_id == "hifi_pcm"
        assert service._applied_profile_id == "hifi_pcm"
        assert service._effective_profile_id == "hifi_pcm"
        assert service._persisted_profile_id == "hifi_pcm"

    def test_state_fields_partial_on_unknown_profile(self, service):
        service.apply_profile("does_not_exist")
        assert service._requested_profile_id == "does_not_exist"
        assert service._validated_profile_id == ""
        assert service._applied_profile_id == ""
        assert service._effective_profile_id == ""
        assert service._persisted_profile_id == ""

    def test_last_apply_result_stored_and_typed(self, service):
        from audio.output_profiles import ProfileApplyResult
        with patch.object(service, "switch_backend_for_profile", return_value=True), \
                patch("core.settings_manager.get", return_value="standard"), \
                patch("core.settings_manager.set_"):
            service._hybrid._active_id = "gstreamer"
            service.apply_profile("hifi_pcm")
        assert isinstance(service._last_apply_result, ProfileApplyResult)
        assert service._last_apply_result.ok is True
        assert service._last_apply_result.persisted_profile_id == "hifi_pcm"
        assert service._last_apply_result.previous_profile_id == "standard"

    def test_rollback_result_records_rollback_ok(self, service):
        from audio.output_profiles import ProfileApplyResult
        service._active_profile_id = "hifi_pcm"
        service._hybrid._active_id = "gstreamer"
        # Deterministic verify failure via is_ready (immune to engine.state
        # plumbing drift in the wider test suite).
        with patch.object(service, "switch_backend_for_profile", return_value=True), \
                patch.object(service._hybrid.active, "is_ready", return_value=False):
            service.apply_profile("standard")
        result = service._last_apply_result
        assert isinstance(result, ProfileApplyResult)
        assert result.ok is False
        assert result.rollback_attempted is True
        assert result.rollback_ok is True
        assert result.applied_profile_id == "standard"
        assert result.effective_profile_id is None


class TestTestOutputDevice:
    def test_unknown_device_returns_false(self, service):
        ok, msg = service.test_output_device("nonexistent_device")
        assert ok is False
        assert "no encontrado" in msg

    def test_logical_sink_returns_true(self, service):
        # "auto" is a built-in device with device_string="autoaudiosink"
        # (no ALSA hw node to open).
        ok, msg = service.test_output_device("auto")
        assert ok is True
        assert "sink=autoaudiosink" in msg

    def test_alsa_hw_open_close_verified(self, service):
        from audio.output_device_manager import AudioDeviceInfo
        fake = AudioDeviceInfo(
            id="alsa_hw_0", display_name="hw:0,0 (fake)",
            backend="alsa", device_string="alsasink device=hw:0,0", is_hw=True,
        )
        with patch("audio.output_device_manager.get_device", return_value=fake), \
                patch("os.path.exists", return_value=True), \
                patch("os.access", return_value=True), \
                patch("os.open", return_value=42) as opened, \
                patch("os.close") as closed:
            ok, msg = service.test_output_device("alsa_hw_0")
        assert ok is True
        assert "open/close=ok" in msg
        opened.assert_called_once()
        closed.assert_called_once_with(42)

    def test_alsa_hw_missing_permissions_returns_false(self, service):
        from audio.output_device_manager import AudioDeviceInfo
        fake = AudioDeviceInfo(
            id="alsa_hw_0", backend="alsa",
            device_string="alsasink device=hw:1,0", is_hw=True,
        )
        with patch("audio.output_device_manager.get_device", return_value=fake), \
                patch("os.path.exists", return_value=True), \
                patch("os.access", return_value=False):
            ok, msg = service.test_output_device("alsa_hw_0")
        assert ok is False
        assert "permisos" in msg

    def test_alsa_hw_missing_node_returns_false(self, service):
        from audio.output_device_manager import AudioDeviceInfo
        fake = AudioDeviceInfo(
            id="alsa_hw_0", backend="alsa",
            device_string="alsasink device=hw:2,0", is_hw=True,
        )
        with patch("audio.output_device_manager.get_device", return_value=fake), \
                patch("os.path.exists", return_value=False):
            ok, msg = service.test_output_device("alsa_hw_0")
        assert ok is False
        assert "inexistente" in msg
