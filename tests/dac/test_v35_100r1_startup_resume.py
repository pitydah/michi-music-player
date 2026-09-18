"""DAC-V35-100R1 startup resume convergence gates (SR100R1-01..13)."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import pytest
from conftest import FakeSettingsRepo

from michi.application.persistence_coordinator import PersistenceCoordinator
from michi.application.settings_service import SettingsService
from michi.domain.audio_engine import AudioEngineId
from michi.domain.audio_output import AudioOutputSelection, OutputSessionState
from michi.domain.library import TrackMetadata
from michi.domain.playback import PlaybackStatus
from michi.domain.session import (
    FORMAT_VERSION,
    PersistedQueueEntry,
    PersistedSessionContext,
    PlaybackSessionSnapshot,
    RepeatMode,
)
from michi.infrastructure.session_repository import SqliteSessionRepository
from tests.dac.test_v35_productive_direct_composition import (
    _accept_current,
    _close_graph,
    _direct_graph,
)

_QT_APP = None


@pytest.fixture(autouse=True)
def _qt_runtime():
    global _QT_APP
    from PySide6.QtWidgets import QApplication

    _QT_APP = QApplication.instance() or QApplication([])
    yield _QT_APP


def _persisted_resume(path: Path) -> PlaybackSessionSnapshot:
    entries = tuple(
        PersistedQueueEntry(str(item), item.stem)
        for item in (path.with_name("a.mp3"), path, path.with_name("c.mp3"))
    )
    return PlaybackSessionSnapshot(
        format_version=FORMAT_VERSION,
        queue_entries=entries,
        context=PersistedSessionContext(
            context_type="queue",
            source_id=None,
            entries=entries,
            current_index=1,
        ),
        playback_path=str(path),
        position_ms=222_000,
        repeat_mode=RepeatMode.NONE,
        shuffle_enabled=False,
        shuffle_seed=0,
    )


def _lossy_graph(tmp_path: Path):
    metadata = TrackMetadata(
        title="B",
        container="mp3",
        codec="MP3",
        sample_rate_hz=44_100,
        bit_depth=0,
        channels=2,
    )
    graph, bindings = _direct_graph(tmp_path, source_metadata=metadata)
    from michi.application.audio_output_ports import SourceCharacterizationError

    bindings.source_characterization_error = SourceCharacterizationError(
        "SOURCE_CHARACTERIZATION_TIMEOUT", "startup characterization timed out"
    )
    return graph, bindings


def _restore_direct_resume(
    graph, snapshot: PlaybackSessionSnapshot, *, engine_available: bool = True
):
    repo = SqliteSessionRepository(graph.db_path)
    assert repo.save(snapshot) is True
    persistence = PersistenceCoordinator(
        repo,
        graph.queue,
        graph.playback_session,
        graph.playback,
        SettingsService(FakeSettingsRepo()),
        track_resolver=graph.track_resolver,
    )
    graph.playback_session.start()
    persistence.start()
    persistence.restore(engine_available=engine_available)
    return persistence, repo


@pytest.fixture
def failed_direct_resume(tmp_path: Path):
    target = tmp_path / "b.mp3"
    graph, bindings = _lossy_graph(tmp_path)
    snapshot = _persisted_resume(target)
    persistence, repo = _restore_direct_resume(graph, snapshot)
    try:
        yield graph, bindings, persistence, repo, snapshot, target
    finally:
        persistence.shutdown()
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_sr100r1_01_direct_unknown_source_facts_do_not_abort_startup(
    tmp_path: Path, caplog
) -> None:
    target = tmp_path / "b.mp3"
    graph, bindings = _lossy_graph(tmp_path)
    snapshot = _persisted_resume(target)
    selection = graph.audio_output_profiles.load_selection()
    caplog.set_level(logging.WARNING)
    try:
        persistence, repo = _restore_direct_resume(graph, snapshot)

        assert graph.playback.state.status is PlaybackStatus.STOPPED
        assert [track.file_path for track in graph.queue.state.tracks] == [
            tmp_path / "a.mp3",
            target,
            tmp_path / "c.mp3",
        ]
        assert graph.playback_session.state.current_index == 1
        assert graph.audio_output_profiles.load_selection() == selection
        assert graph.output_session.active_plan is None
        assert graph.output_session.active_device_id is None
        assert graph.direct_output_executor.handle is None
        assert graph.signal_truth.active_snapshot is None
        assert len(bindings.pipelines) == 0  # no Direct or Shared recovery pipeline
        assert "SOURCE_CHARACTERIZATION_TIMEOUT" in caplog.text

        persistence.shutdown()
        assert repo.load() == snapshot
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_sr100r1_02_queue_and_current_identity_survive(
    failed_direct_resume,
) -> None:
    graph, _bindings, _persistence, _repo, _snapshot, target = failed_direct_resume
    assert [track.file_path for track in graph.queue.state.tracks] == [
        target.with_name("a.mp3"),
        target,
        target.with_name("c.mp3"),
    ]
    assert graph.playback_session.state.current_entry.file_path == target


def test_sr100r1_03_selected_direct_device_and_profile_survive(
    failed_direct_resume,
) -> None:
    graph, _bindings, _persistence, _repo, _snapshot, _target = failed_direct_resume
    selection = graph.audio_output_profiles.load_selection()
    assert selection.selected_device_id == "usb:2622:0105:DX5ABC123"
    assert selection.selected_profile_id == "p1"


def test_sr100r1_04_failed_resume_does_not_fallback_or_switch_engine(
    failed_direct_resume,
) -> None:
    graph, bindings, _persistence, _repo, _snapshot, _target = failed_direct_resume
    assert graph.audio_engine_service.state.active_engine_id is AudioEngineId.GSTREAMER
    assert graph.audio_router.bound_engine_id is AudioEngineId.GSTREAMER
    assert len(bindings.pipelines) == 0
    # The service is inactive/default-Shared, but the authoritative persisted
    # selection remains Direct; no Shared transaction or pipeline was created.
    assert graph.audio_output_profiles.load_selection().selected_profile_id == "p1"


def test_sr100r1_05_failed_resume_leaves_no_stale_output_authority(
    failed_direct_resume,
) -> None:
    graph, _bindings, _persistence, _repo, _snapshot, _target = failed_direct_resume
    assert graph.output_session.state is OutputSessionState.IDLE
    assert graph.output_session.active_plan is None
    assert graph.output_session.active_device_id is None
    assert graph.direct_output_executor.handle is None
    assert graph.signal_truth.active_snapshot is None


def test_sr100r1_06_shutdown_preserves_last_durable_resume_snapshot(
    failed_direct_resume,
) -> None:
    _graph, _bindings, persistence, repo, snapshot, _target = failed_direct_resume
    assert persistence._resume_phase.name == "NONE"
    assert persistence._restored_snapshot is None
    assert persistence._protected_resume_snapshot == snapshot
    persistence.shutdown()
    assert repo.load() == snapshot


def test_sr100r1_07_shared_startup_resume_still_prepares_without_autoplay(
    tmp_path: Path,
) -> None:
    target = tmp_path / "b.mp3"
    graph, bindings = _lossy_graph(tmp_path)
    graph.audio_output_profiles.save_selection(AudioOutputSelection(None, None, 2))
    persistence = None
    try:
        persistence, _repo = _restore_direct_resume(graph, _persisted_resume(target))
        assert graph.output_session.mode == "shared"
        assert graph.playback.state.status is PlaybackStatus.STOPPED
        assert len(bindings.pipelines) == 1
    finally:
        if persistence is not None:
            persistence.shutdown()
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_sr100r1_08_complete_direct_resume_still_prepares_accepts_and_seeks(
    tmp_path: Path,
) -> None:
    target = tmp_path / "b.flac"
    graph, bindings = _direct_graph(tmp_path)
    persistence = None
    try:
        persistence, _repo = _restore_direct_resume(graph, _persisted_resume(target))
        assert graph.output_session.state is OutputSessionState.READY
        assert graph.playback.state.status is PlaybackStatus.STOPPED
        _accept_current(graph, bindings)
        assert graph.playback.state.file_path == target
        assert graph.playback.state.status is PlaybackStatus.STOPPED
        assert bindings.pipelines[-1].seek_calls == [222_000 * 1_000_000]
    finally:
        if persistence is not None:
            persistence.shutdown()
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_sr100r1_09_engine_unavailable_restores_logical_state_without_prepare(
    tmp_path: Path,
) -> None:
    target = tmp_path / "b.mp3"
    graph, bindings = _lossy_graph(tmp_path)
    persistence = None
    try:
        persistence, repo = _restore_direct_resume(
            graph, _persisted_resume(target), engine_available=False
        )
        assert graph.playback_session.state.current_entry.file_path == target
        assert graph.playback.state.file_path is None
        assert len(bindings.pipelines) == 0
        assert repo.load().playback_path == str(target)
    finally:
        if persistence is not None:
            persistence.shutdown()
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_sr100r1_10_true_persistence_failure_remains_fatal(tmp_path: Path) -> None:
    graph, _bindings = _lossy_graph(tmp_path)

    class _LockedRepository:
        def load(self):
            raise sqlite3.OperationalError("database is locked")

        def save(self, _snapshot):
            raise AssertionError("save must not be attempted")

    persistence = PersistenceCoordinator(
        _LockedRepository(),
        graph.queue,
        graph.playback_session,
        graph.playback,
        SettingsService(FakeSettingsRepo()),
    )
    try:
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            persistence.restore()
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_sr100r1_11_explicit_play_recharacterizes_and_plans_decoded_mp3(
    failed_direct_resume,
) -> None:
    from michi.domain.audio_evidence import (
        CapabilityEvidence,
        EvidenceStrength,
        PcmTuple,
    )

    graph, bindings, _persistence, _repo, _snapshot, _target = failed_direct_resume
    device_id = "usb:2622:0105:DX5ABC123"
    bindings.source_characterization_error = None
    bindings.source_characterization_overrides = {
        "format": "S16LE",
        "rate": 44_100,
        "channels": 2,
    }
    graph.dac_qualification.cache_evidence(
        device_id,
        (
            CapabilityEvidence(
                stable_device_id=device_id,
                tuple=PcmTuple(44_100, "S16_LE", 2, 16),
                supported=True,
                strength=EvidenceStrength.OPENED,
                source="michi-alsa-probe",
                observed_at_ns=1,
                environment_fingerprint=(
                    graph.dac_qualification.current_environment_fingerprint(device_id)
                ),
                evidence_refs=("probe:mp3-decoded",),
            ),
        ),
    )

    graph.playback_session.play_queue_index(1)

    assert graph.output_session.plan is not None
    assert graph.output_session.plan.requested_pcm == PcmTuple(44_100, "S16_LE", 2, 16)
    assert graph.direct_output_executor.handle is not None


def test_sr100r1_12_lossy_unknown_bits_remain_file_facts_not_decoded_truth(
    failed_direct_resume,
) -> None:
    graph, bindings, _persistence, _repo, _snapshot, target = failed_direct_resume
    bindings.source_characterization_error = None
    bindings.source_characterization_overrides = {
        "format": "S16LE",
        "rate": 44_100,
        "channels": 2,
    }
    request = graph.output_session._request_for(target)
    facts = request.facts
    assert facts is not None
    assert facts.decoded_source.significant_bits == 16
    assert facts.source_file_facts.container == "mp3"
    assert facts.source_file_facts.codec == "MP3"
    assert facts.source_file_facts.nominal_pcm.rate_hz == 44_100
    assert facts.source_file_facts.nominal_pcm.channels == 2
    assert facts.source_file_facts.nominal_pcm.significant_bits is None


def test_sr100r1_13_application_container_reaches_bridges_after_refusal(
    tmp_path: Path, monkeypatch
) -> None:
    from michi import bootstrap
    from michi.application.settings_service import SettingsService
    from michi.bootstrap import ApplicationContainer
    from michi.infrastructure.sqlite_settings import SQLiteSettingsRepository

    data_dir = tmp_path / "app-data"
    cache_dir = tmp_path / "cache"
    data_dir.mkdir()
    cache_dir.mkdir()
    graph, _bindings = _lossy_graph(data_dir)
    snapshot = _persisted_resume(data_dir / "b.mp3")
    assert SqliteSessionRepository(graph.db_path).save(snapshot) is True
    settings = SettingsService(SQLiteSettingsRepository.open_for_startup(graph.db_path))
    settings.set_audio_engine(AudioEngineId.GSTREAMER)
    settings.save()

    monkeypatch.setattr(bootstrap, "_data_dir", lambda: data_dir)
    monkeypatch.setattr(bootstrap, "_cache_dir", lambda: cache_dir)

    def use_prebuilt_graph(db_path, **_kwargs):
        assert Path(db_path) == graph.db_path
        return graph

    monkeypatch.setattr(bootstrap, "_build_services", use_prebuilt_graph)
    container = ApplicationContainer()
    container.initialize()
    try:
        assert container._playback.state.status is PlaybackStatus.STOPPED
        assert container._pb is not None
        assert container._aob is not None
        assert container._engine is not None
        assert container._persistence._resume_phase.name == "NONE"
    finally:
        container.shutdown()


def test_sr100r11_stop_01_accepted_explicit_stop_cancels_protected_resume(
    failed_direct_resume,
) -> None:
    graph, _bindings, persistence, repo, _snapshot, _target = failed_direct_resume

    graph.playback.stop()

    assert persistence._protected_resume_snapshot is None
    durable = repo.load()
    assert durable.playback_path is None
    assert durable.position_ms == 0


def test_sr100r11_stop_02_failed_explicit_stop_preserves_protected_resume(
    failed_direct_resume, monkeypatch
) -> None:
    graph, _bindings, persistence, repo, snapshot, _target = failed_direct_resume

    def reject_stop():
        raise RuntimeError("backend stop rejected")

    monkeypatch.setattr(graph.playback._audio, "stop", reject_stop)

    with pytest.raises(RuntimeError, match="backend stop rejected"):
        graph.playback.stop()

    assert persistence._protected_resume_snapshot == snapshot
    assert repo.load() == snapshot
