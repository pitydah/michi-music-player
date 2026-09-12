"""DAC-V35-040 — OutputSessionService gates (§0H.2/§21/§22/§403 + DAC-C08).

El servicio implementa la firma EXACTA del PlaybackOutputTransactionPort:
`prepare_for_media(path) -> str`. PlaybackService nunca conoce ni
construye OutputPlan: el assembly vive detrás del subsistema de output.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from conftest import FakeAudioPort

from michi.application.audio_output_planner import OutputPlanner
from michi.application.output_session_service import (
    OutputSessionError,
    OutputSessionService,
)
from michi.application.ports import (
    PlaybackOutputTransactionPort,
    SharedOutputTransaction,
)
from michi.domain.audio_output import OutputPlan, OutputSessionState
from tests.dac.test_v34_output_planner import _facts


def _plan() -> OutputPlan:
    result = OutputPlanner().plan(_facts())
    assert isinstance(result, OutputPlan)
    return result


def _service(*, engine: str = "gstreamer") -> OutputSessionService:
    return OutputSessionService(
        OutputPlanner(),
        facts_provider=lambda path: _facts(active_engine_id=engine),
    )


def test_session_service_satisfies_canonical_port() -> None:
    """C08: conformidad estructural con el port canónico."""
    service = _service()
    assert isinstance(service, PlaybackOutputTransactionPort)
    signature = inspect.signature(OutputSessionService.prepare_for_media)
    parameters = list(signature.parameters)
    assert parameters == ["self", "path"], (
        "prepare_for_media NO debe recibir OutputPlan (C08)"
    )
    assert signature.return_annotation in (str, "str")


def test_prepare_without_plan_source_raises_typed_error() -> None:
    service = OutputSessionService(OutputPlanner())
    with pytest.raises(OutputSessionError) as exc_info:
        service.prepare_for_media(Path("a.flac"))
    assert exc_info.value.code == "no_plan_source"


def test_prepare_refusal_raises_typed_error() -> None:
    service = _service(engine="mpd")
    with pytest.raises(OutputSessionError) as exc_info:
        service.prepare_for_media(Path("a.flac"))
    assert exc_info.value.code == "ENGINE_NOT_GSTREAMER"


def test_prepare_commit_runs_session(tmp_path: Path) -> None:
    service = _service()
    token = service.prepare_for_media(tmp_path / "a.flac")
    assert service.state is OutputSessionState.READY
    service.commit_media(token, tmp_path / "a.flac")
    assert service.state is OutputSessionState.RUNNING
    selection = service.selection_state()
    assert selection.active_plan_id == _plan().plan_id
    assert selection.active_device_id is not None


def test_abort_returns_to_idle_with_reason(tmp_path: Path) -> None:
    service = _service()
    token = service.prepare_for_media(tmp_path / "a.flac")
    service.abort_media(token, "media_rejected")
    assert service.state is OutputSessionState.IDLE
    assert service.plan is None
    assert service.selection_state().error_code == "media_rejected"


def test_release_active_returns_to_idle(tmp_path: Path) -> None:
    service = _service()
    token = service.prepare_for_media(tmp_path / "a.flac")
    service.commit_media(token, tmp_path / "a.flac")
    service.release_active("stop")
    assert service.state is OutputSessionState.IDLE
    assert service.plan is None


def test_stale_generation_callbacks_are_discarded(tmp_path: Path) -> None:
    service = _service()
    stale = service.prepare_for_media(tmp_path / "a.flac")
    service.release_active("stop")
    fresh = service.prepare_for_media(tmp_path / "b.flac")
    assert fresh != stale
    # El commit del token viejo NO debe mutar la sesión nueva.
    service.commit_media(stale, tmp_path / "a.flac")
    assert service.state is OutputSessionState.READY, (
        "callbacks de generations viejas se descartan"
    )
    service.commit_media(fresh, tmp_path / "b.flac")
    assert service.state is OutputSessionState.RUNNING


def test_device_lost_preserves_selected_and_clears_active(tmp_path: Path) -> None:
    service = _service()
    service.select(device_id="usb:2622:0105:DX5ABC123", profile_id="p1")
    token = service.prepare_for_media(tmp_path / "a.flac")
    service.commit_media(token, tmp_path / "a.flac")
    service.device_lost()
    selection = service.selection_state()
    assert service.state is OutputSessionState.LOST
    assert selection.selected_device_id == "usb:2622:0105:DX5ABC123", (
        "el selected sobrevive a la desaparición (§22)"
    )
    assert selection.active_device_id is None
    assert selection.active_plan_id is None


def test_illegal_transition_raises() -> None:
    service = _service()
    with pytest.raises(OutputSessionError) as exc_info:
        service.commit_media("output-tx:None:0", Path("x.flac"))
    assert exc_info.value.code == "illegal_transition"


def test_reprepare_from_ready_reconfigures(tmp_path: Path) -> None:
    service = _service()
    first = service.prepare_for_media(tmp_path / "a.flac")
    second = service.prepare_for_media(tmp_path / "b.flac")
    assert second != first
    assert service.state is OutputSessionState.READY


def test_fail_records_error_code() -> None:
    service = _service()
    service.fail("device_removed")
    assert service.state is OutputSessionState.FAILED
    assert service.selection_state().error_code == "device_removed"


def test_shared_transaction_is_noop_with_truthful_mode(tmp_path: Path) -> None:
    shared = SharedOutputTransaction()
    assert shared.mode == "shared"
    assert isinstance(shared, PlaybackOutputTransactionPort)
    token = shared.prepare_for_media(tmp_path / "a.flac")
    shared.commit_media(token, tmp_path / "a.flac")
    shared.abort_media(token, "x")
    shared.release_active("y")
    assert token == "shared:noop"


# ── DAC-D: PlaybackService consume el port productivamente (P1..P9) ──


class _RecordingOutputTx:
    """Output transaction espiado: registra el orden exacto de eventos."""

    def __init__(self, events: list[str], *, fail_prepare: bool = False) -> None:
        self._events = events
        self._fail_prepare = fail_prepare

    def prepare_for_media(self, path: Path) -> str:
        self._events.append("prepare")
        if self._fail_prepare:
            raise RuntimeError("prepare failed")
        return "tx:1"

    def commit_media(self, token: str, path: Path) -> None:
        self._events.append("commit")

    def abort_media(self, token: str, reason: str) -> None:
        self._events.append(f"abort:{reason}")

    def release_active(self, reason: str) -> None:
        self._events.append(f"release:{reason}")


class _SpyAudioPort(FakeAudioPort):
    def __init__(
        self,
        events: list[str],
        *,
        fail_load: bool = False,
        fail_play: bool = False,
    ) -> None:
        super().__init__()
        self._events = events
        self.fail_load = fail_load
        self.fail_play = fail_play

    def load(self, p):
        self._events.append("load")
        super().load(p)

    def play(self):
        self._events.append("play")
        if self.fail_play:
            raise RuntimeError("play failed")
        super().play()

    def stop(self):
        self._events.append("stop")
        super().stop()


def _playback(
    events: list[str], *, fail_prepare=False, fail_load=False, fail_play=False
):
    from michi.application.playback_service import PlaybackService

    tx = _RecordingOutputTx(events, fail_prepare=fail_prepare)
    audio = _SpyAudioPort(events, fail_load=fail_load, fail_play=fail_play)
    return PlaybackService(audio, output_tx=tx), audio


def test_p1_success_order_prepare_load_play_accept_commit(tmp_path: Path) -> None:
    events: list[str] = []
    service, audio = _playback(events)
    media = tmp_path / "a.flac"

    service.load_and_play(media)
    assert events == ["prepare", "load", "play"], (
        "el commit NO puede ocurrir antes del media accepted"
    )

    audio.trigger_media_accepted(media)
    assert events == ["prepare", "load", "play", "commit"]
    assert service.state.file_path == media


def test_p2_prepare_failure_touches_nothing(tmp_path: Path) -> None:
    events: list[str] = []
    service, _audio = _playback(events, fail_prepare=True)
    with pytest.raises(RuntimeError):
        service.load_and_play(tmp_path / "a.flac")
    assert events == ["prepare"], "sin load/play cuando prepare falla"
    assert service.state.file_path is None


def test_p3_load_failure_aborts_never_commits(tmp_path: Path) -> None:
    from michi.application.ports import AudioLoadError

    events: list[str] = []
    service, _audio = _playback(events, fail_load=True)
    with pytest.raises(AudioLoadError):
        service.load_and_play(tmp_path / "a.flac")
    assert "commit" not in events
    assert "abort:load_failed" in events


def test_p4_play_failure_aborts_never_commits(tmp_path: Path) -> None:
    events: list[str] = []
    service, _audio = _playback(events, fail_play=True)
    with pytest.raises(RuntimeError):
        service.load_and_play(tmp_path / "a.flac")
    assert "commit" not in events
    assert "abort:play_failed" in events


def test_p5_backend_rejection_aborts_never_commits(tmp_path: Path) -> None:
    events: list[str] = []
    service, audio = _playback(events)
    media = tmp_path / "a.flac"
    service.load_and_play(media)

    audio.trigger_media_rejected(media, "decode error")

    assert "commit" not in events
    assert "abort:media_rejected" in events
    from michi.domain.playback import PlaybackStatus

    assert service.state.status is PlaybackStatus.STOPPED


def test_p6_commit_happens_before_playback_acceptance(tmp_path: Path) -> None:
    events: list[str] = []
    service, audio = _playback(events)
    media = tmp_path / "a.flac"
    observed: list[list[str]] = []
    service.load_and_play(media, on_accepted=lambda path: observed.append(list(events)))

    audio.trigger_media_accepted(media)

    assert observed and "commit" in observed[0], (
        "el commit del output precede al commit de acceptance (§0H.2 paso 5)"
    )


def test_p7_stale_acceptance_does_not_commit_new_request(tmp_path: Path) -> None:
    events: list[str] = []
    service, audio = _playback(events)
    first = tmp_path / "a.flac"
    second = tmp_path / "b.flac"
    service.load_and_play(first)
    service.load_and_play(second)  # supersede
    events.clear()

    audio.trigger_media_accepted(first)  # aceptación vieja
    assert "commit" not in events, "una aceptación vieja no commitea"

    audio.trigger_media_accepted(second)
    assert events.count("commit") == 1


def test_p8_stop_releases_after_audio_stop(tmp_path: Path) -> None:
    events: list[str] = []
    service, audio = _playback(events)
    media = tmp_path / "a.flac"
    service.load_and_play(media)
    audio.trigger_media_accepted(media)
    events.clear()

    service.stop()

    assert events == ["stop", "release:stop"], (
        "la semántica de safety del AudioPort va primero (§0H.2)"
    )


def test_p9_engine_loss_releases_exactly_once(tmp_path: Path) -> None:
    events: list[str] = []
    service, audio = _playback(events)
    media = tmp_path / "a.flac"
    service.load_and_play(media)
    audio.trigger_media_accepted(media)
    events.clear()

    service.converge_after_engine_loss("engine lost")

    assert events.count("release:engine_loss") == 1
