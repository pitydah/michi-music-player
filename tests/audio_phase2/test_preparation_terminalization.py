"""AP2-F05 WU0.1 — async terminalization + intent freshness seal (Part A).

Finding A: an early async ENGINE_SWITCH_REHYDRATION refusal must terminalize
through the ONE engine-switch path and release the exact lease.
Finding B: the persistence coordinator unsubscribes symmetrically and a late
refusal after stop() is inert.
"""

from __future__ import annotations

from pathlib import Path

from michi.application.output_session_service import OutputSessionError
from michi.application.persistence_coordinator import PersistenceCoordinator
from michi.application.playback_service import (
    MediaRequestPurpose,
    MediaRequestTerminalStatus,
    PlaybackService,
)
from michi.application.playback_session_service import PlaybackSessionService
from michi.application.queue_service import QueueService
from michi.application.settings_service import SettingsService
from michi.domain.playback import PlaybackStatus
from michi.infrastructure.session_repository import SqliteSessionRepository
from tests.conftest import FakeAudioPort, FakeSettingsRepo


class _AsyncOnlyTx:
    """Async-only transaction double: captures every dispatched preparation."""

    mode = "shared"
    volume_policy = None

    def __init__(self) -> None:
        self.pending: list[tuple[Path, object, object]] = []
        self.aborts: list[tuple[str, str]] = []

    def prepare_for_media_async(self, path, on_prepared, on_failed) -> None:
        self.pending.append((Path(path), on_prepared, on_failed))

    def abort_media(self, token, reason) -> None:
        self.aborts.append((token, reason))

    def release_active(self, reason) -> None:
        pass

    def commit_media(self, token, path) -> None:
        pass


def _service_with_snapshot(fake_audio, path: Path):
    tx = _AsyncOnlyTx()
    service = PlaybackService(fake_audio, output_tx=tx)
    service._state.file_path = path
    service._state.position_ms = 4_321
    service._state.status = PlaybackStatus.STOPPED
    return service, tx


def test_engine_switch_early_refusal_terminalizes_and_releases_exact_lease(
    fake_audio,
) -> None:
    path = Path("/tmp/rehydrate.flac")
    service, tx = _service_with_snapshot(fake_audio, path)
    lease = service.begin_engine_switch()
    assert lease.prepare_on_target() is True
    assert service._engine_switch_lease_active is True
    assert tx.pending and tx.pending[-1][0] == path

    # Early async refusal BEFORE the rehydration timeout was armed.
    _path, _prepared, failed = tx.pending[-1]
    failed(OutputSessionError("SOURCE_CHARACTERIZATION_TIMEOUT", "timed out"))

    # Exactly one terminal result, exact lease released, honest state.
    assert service._engine_switch_lease_active is False
    assert service._engine_switch_lease is None
    result = service.last_engine_switch_rehydration
    assert result is not None
    assert result.status is MediaRequestTerminalStatus.REJECTED
    assert result.file_path == str(path)
    assert service.state.status is PlaybackStatus.STOPPED
    assert "could not be prepared" in (service.state.error_message or "")
    # Media failure, never an engine startup failure; no autoplay, no load.
    assert fake_audio.loaded is None
    assert fake_audio.state == "stopped"
    # A later explicit switch is still allowed.
    assert service.engine_switch_readiness().allowed is True


def test_stale_engine_switch_refusal_cannot_release_a_newer_lease(fake_audio) -> None:
    path = Path("/tmp/rehydrate.flac")
    service, tx = _service_with_snapshot(fake_audio, path)
    lease_first = service.begin_engine_switch()
    assert lease_first.prepare_on_target() is True
    _path, _prepared, first_failed = tx.pending[-1]

    # A newer switch supersedes the pending rehydration.
    lease_second = service.begin_engine_switch()
    assert lease_second is not lease_first
    assert lease_second.prepare_on_target() is True
    assert tx.pending[-1][0] == path
    assert service._engine_switch_lease is lease_second

    # The delayed failure belongs to the OLD request: it must be inert.
    first_failed(OutputSessionError("SOURCE_CHARACTERIZATION_TIMEOUT", "late"))
    assert service._engine_switch_lease is lease_second
    assert service._engine_switch_lease_active is True

    # The current request still terminalizes exactly once.
    _path2, _prepared2, second_failed = tx.pending[-1]
    second_failed(OutputSessionError("SOURCE_FILE_UNAVAILABLE", "gone"))
    assert service._engine_switch_lease_active is False
    result = service.last_engine_switch_rehydration
    assert result is not None and result.status is MediaRequestTerminalStatus.REJECTED


def test_engine_switch_refusal_does_not_claim_engine_startup_failure(
    fake_audio,
) -> None:
    path = Path("/tmp/rehydrate.flac")
    service, tx = _service_with_snapshot(fake_audio, path)
    lease = service.begin_engine_switch()
    lease.prepare_on_target()
    tx.pending[-1][2](OutputSessionError("NO_ALSA_HW_BINDING", "no binding"))
    # The playback authority reports the media refusal via its own message;
    # no engine-startup failure code is fabricated.
    assert service.state.error_code is None
    assert "could not be prepared" in (service.state.error_message or "")


# ── Finding B: persistence subscription symmetry ──────────────────────
def _coordinator(tmp_path):
    repo = SqliteSessionRepository(tmp_path / "session.db")
    settings = SettingsService(FakeSettingsRepo())
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService()
    session = PlaybackSessionService(playback, queue)
    coordinator = PersistenceCoordinator(repo, queue, session, playback, settings)
    return coordinator, playback


def test_coordinator_stop_unsubscribes_preparation_refused(tmp_path) -> None:
    coordinator, playback = _coordinator(tmp_path)
    assert playback._preparation_refused_subscribers == []
    coordinator.start()
    assert coordinator._on_preparation_refused in (
        playback._preparation_refused_subscribers
    )
    coordinator.stop()
    assert playback._preparation_refused_subscribers == []


def test_late_refusal_after_stop_is_inert(tmp_path) -> None:
    coordinator, playback = _coordinator(tmp_path)
    coordinator.start()
    coordinator.stop()
    # Simulate a late async event delivered after teardown.
    phase_before = coordinator._resume_phase
    restored_before = coordinator._restored_snapshot
    protected_before = coordinator._protected_resume_snapshot
    playback._notify_preparation_refused(
        MediaRequestPurpose.STARTUP_RESTORE, "SOURCE_CHARACTERIZATION_TIMEOUT"
    )
    assert coordinator._resume_phase is phase_before
    assert coordinator._restored_snapshot is restored_before
    assert coordinator._protected_resume_snapshot is protected_before


def test_restart_and_repeated_lifecycle_subscribe_exactly_once(tmp_path) -> None:
    coordinator, playback = _coordinator(tmp_path)
    coordinator.start()
    coordinator.start()
    assert (
        playback._preparation_refused_subscribers.count(
            coordinator._on_preparation_refused
        )
        == 1
    )
    coordinator.stop()
    coordinator.stop()
    assert playback._preparation_refused_subscribers == []
    coordinator.start()
    assert (
        playback._preparation_refused_subscribers.count(
            coordinator._on_preparation_refused
        )
        == 1
    )
    coordinator.stop()
