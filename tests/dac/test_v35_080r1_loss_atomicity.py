"""DAC-V35-080R1 loss cleanup atomicity and reconnect evidence gates."""

from __future__ import annotations

from pathlib import Path

import pytest

from michi.application.audio_output_planner import OutputPlanner
from michi.application.audio_output_ports import (
    OutputExecutorAbortDisposition,
    UnknownVolumeAuthorityError,
)
from michi.application.output_session_service import OutputRequest, OutputSessionService
from michi.domain.audio_output import (
    AudioOutputSelection,
    OutputSessionState,
    stable_direct_preset,
)
from michi.domain.playback import PlaybackStatus
from tests.dac.test_v34_output_planner import DEVICE, _evidence, _facts
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


class _ReleaseFailingExecutor:
    engine_id = "gstreamer"

    def __init__(self) -> None:
        self.receipt = ""
        self.release_calls: list[str] = []

    def prepare(self, plan) -> str:
        self.receipt = f"receipt:{plan.plan_id}"
        return self.receipt

    def commit(self, receipt: str) -> None:
        assert receipt == self.receipt

    def abort(self, receipt: str, reason: str) -> OutputExecutorAbortDisposition:
        del reason
        return (
            OutputExecutorAbortDisposition.CANDIDATE_DISCARDED
            if receipt == self.receipt
            else OutputExecutorAbortDisposition.STALE
        )

    def owns_committed_receipt(self, receipt: str) -> bool:
        return receipt == self.receipt

    def release(self, reason: str) -> None:
        self.release_calls.append(reason)
        raise RuntimeError("physical discard failed")


class _PredecessorAwareExecutor:
    engine_id = "gstreamer"

    def __init__(self) -> None:
        self.current_receipt: str | None = None
        self.committed_receipt: str | None = None
        self.predecessor_receipt: str | None = None
        self.releases: list[str] = []

    def prepare(self, plan) -> str:
        if self.committed_receipt is not None:
            self.predecessor_receipt = self.committed_receipt
        self.current_receipt = f"receipt:{plan.stable_device_id}:{plan.plan_id}"
        return self.current_receipt

    def commit(self, receipt: str) -> None:
        assert receipt == self.current_receipt
        self.committed_receipt = receipt
        self.predecessor_receipt = None

    def abort(self, receipt: str, reason: str) -> OutputExecutorAbortDisposition:
        del reason
        if receipt != self.current_receipt:
            return OutputExecutorAbortDisposition.STALE
        return OutputExecutorAbortDisposition.CANDIDATE_DISCARDED

    def owns_committed_receipt(self, receipt: str) -> bool:
        return receipt in (self.committed_receipt, self.predecessor_receipt)

    def cross_destructive_boundary(self) -> None:
        self.committed_receipt = None
        self.predecessor_receipt = None

    def release(self, reason: str) -> None:
        self.releases.append(reason)
        self.current_receipt = None
        self.committed_receipt = None
        self.predecessor_receipt = None


def _committed_service() -> tuple[OutputSessionService, _ReleaseFailingExecutor]:
    executor = _ReleaseFailingExecutor()
    service = OutputSessionService(
        OutputPlanner(),
        facts_provider=lambda _path: _facts(),
        executors={"gstreamer": executor},
    )
    media = Path("active.flac")
    token = service.prepare_for_media(media)
    service.commit_media(token, media)
    return service, executor


def test_r80r1_01_release_failure_still_commits_lost_logical_state() -> None:
    service, executor = _committed_service()
    stable_id = service.active_device_id

    service.topology_lost(stable_id, 2)

    assert executor.release_calls == ["device_lost"]
    assert service.state is OutputSessionState.LOST
    assert service.active_device_id is None
    assert service.active_plan is None
    assert service.plan is None


def test_r80r1_02_release_failure_is_retained_as_typed_diagnostic() -> None:
    service, _executor = _committed_service()

    service.topology_lost(service.active_device_id, 2)

    diagnostic = service.last_cleanup_diagnostic
    assert diagnostic is not None
    assert diagnostic.reason == "device_lost"
    assert diagnostic.code == "DIRECT_EXECUTOR_RELEASE_FAILED"
    assert diagnostic.detail == "physical discard failed"


def test_r80r1_03_loss_clears_every_output_transaction_reference() -> None:
    service, _executor = _committed_service()

    service.topology_lost(service.active_device_id, 2)

    assert service._executor is None
    assert service._executor_receipt is None
    assert service._shared_receipt is None
    assert service._previous_direct is None
    assert service._token_value is None
    assert service._path is None
    assert service._session_id is None
    assert service.mode == "lost"


def test_r80r1_04_loss_preserves_selection_but_not_active_authority() -> None:
    service, _executor = _committed_service()
    service.select(device_id="selected-dac", profile_id="selected-profile")

    service.device_lost()

    selection = service.selection_state()
    assert selection.selected_device_id == "selected-dac"
    assert selection.selected_profile_id == "selected-profile"
    assert selection.active_device_id is None
    assert selection.active_plan_id is None
    assert selection.session_state is OutputSessionState.LOST


def test_r80r1_05_duplicate_loss_does_not_retry_failed_physical_cleanup() -> None:
    service, executor = _committed_service()
    stable_id = service.active_device_id

    service.topology_lost(stable_id, 2)
    first_diagnostic = service.last_cleanup_diagnostic
    service.topology_lost(stable_id, 2)

    assert executor.release_calls == ["device_lost"]
    assert service.last_cleanup_diagnostic is first_diagnostic


def test_r80r1_06_pre_loss_token_cannot_commit_after_invalidation() -> None:
    executor = _ReleaseFailingExecutor()
    service = OutputSessionService(
        OutputPlanner(),
        facts_provider=lambda _path: _facts(),
        executors={"gstreamer": executor},
    )
    media = Path("candidate.flac")
    token = service.prepare_for_media(media)

    service.topology_lost(service.active_device_id, 2)
    service.commit_media(token, media)

    assert service.state is OutputSessionState.LOST
    assert service.plan is None


def test_r80r1_07_rebind_never_restores_pre_loss_execution() -> None:
    service, _executor = _committed_service()
    stable_id = service.active_device_id
    service.topology_lost(stable_id, 2)

    assert service.rebind_after_topology_change(stable_id, 1) is False
    assert service.rebind_after_topology_change(stable_id, 2) is False
    assert service.rebind_after_topology_change(stable_id, 3) is True
    assert service.state is OutputSessionState.IDLE
    assert service.plan is None
    assert service.active_device_id is None
    assert service._executor is None
    assert service._executor_receipt is None


def test_r80r1_08_unrelated_loss_does_not_mutate_committed_execution() -> None:
    service, executor = _committed_service()
    plan = service.plan

    service.topology_lost("usb:unrelated", 2)

    assert service.state is OutputSessionState.RUNNING
    assert service.plan is plan
    assert executor.release_calls == []


def test_r80r1_09_executor_release_failure_invalidates_runtime_and_signal_truth(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    port = graph.gstreamer_engine_provider.current_port
    original_discard = port.discard_direct_load
    try:
        graph.playback.load_and_play(tmp_path / "active.flac")
        _accept_current(graph, bindings)
        assert graph.signal_truth.active_snapshot is not None

        def fail_discard(*_args, **_kwargs):
            raise RuntimeError("physical pipeline refused NULL")

        port.discard_direct_load = fail_discard
        with pytest.raises(RuntimeError, match="refused NULL"):
            graph.direct_output_executor.release("device_lost")

        assert graph.direct_output_executor.handle is None
        assert graph.direct_output_executor.state.value == "idle"
        assert graph.signal_truth.active_snapshot is None
    finally:
        port.discard_direct_load = original_discard
        _close_graph(graph)


@pytest.mark.parametrize(
    ("stop_fails", "release_fails"),
    [
        pytest.param(False, False, id="R80R1-10-cleanup-ok"),
        pytest.param(True, False, id="R80R1-11-stop-fails"),
        pytest.param(False, True, id="R80R1-12-release-fails"),
        pytest.param(True, True, id="R80R1-13-stop-and-release-fail"),
    ],
)
def test_r80r1_10_13_productive_loss_always_converges(
    tmp_path: Path,
    stop_fails: bool,
    release_fails: bool,
) -> None:
    from tests.dac.test_v35_080_productive_lifecycle import _disconnect

    graph, bindings = _direct_graph(tmp_path)
    port = graph.gstreamer_engine_provider.current_port
    original_stop = graph.playback._audio.stop
    original_discard = port.discard_direct_load
    try:
        graph.playback.load_and_play(tmp_path / "active.flac")
        _accept_current(graph, bindings)
        stable_id = graph.output_session.active_device_id

        if stop_fails:
            graph.playback._audio.stop = lambda: (_ for _ in ()).throw(
                RuntimeError("transport stop failed")
            )
        if release_fails:
            port.discard_direct_load = lambda *_args, **_kwargs: (_ for _ in ()).throw(
                RuntimeError("executor release failed")
            )

        _disconnect(graph, tmp_path)

        assert stable_id not in graph.audio_device_registry.available_ids()
        assert graph.playback.state.status is PlaybackStatus.STOPPED
        assert graph.playback.state.error_message == "OUTPUT_DEVICE_LOST"
        assert graph.output_session.state is OutputSessionState.LOST
        assert graph.output_session.active_device_id is None
        assert graph.output_session.plan is None
        assert graph.direct_output_executor.handle is None
        assert graph.signal_truth.active_snapshot is None
        assert (graph.output_session.last_cleanup_diagnostic is not None) is (
            release_fails
        )
    finally:
        graph.playback._audio.stop = original_stop
        port.discard_direct_load = original_discard
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_r80r1_14_loss_retires_committed_a_while_b_is_provisional(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        graph.playback.load_and_play(tmp_path / "a.flac")
        _accept_current(graph, bindings)
        active_a = graph.signal_truth.active_snapshot
        assert active_a is not None

        graph.output_session.prepare_for_media(tmp_path / "b.flac")
        assert graph.direct_output_executor._committed is not None

        graph.output_session.topology_lost(graph.output_session.active_device_id, 2)

        assert graph.output_session.state is OutputSessionState.LOST
        assert graph.direct_output_executor.handle is None
        assert graph.direct_output_executor._committed is None
        assert graph.signal_truth.active_snapshot is None
        assert graph.signal_truth.last_snapshot.identity == active_a.identity
    finally:
        _close_graph(graph)


def test_r80r1_15_executor_reports_predecessor_receipt_until_boundary(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        graph.playback.load_and_play(tmp_path / "a.flac")
        _accept_current(graph, bindings)
        receipt_a = graph.output_session._executor_receipt

        graph.output_session.prepare_for_media(tmp_path / "b.flac")

        assert graph.direct_output_executor.owns_committed_receipt(receipt_a) is True
        graph.direct_output_executor.mark_previous_source_released()
        assert graph.direct_output_executor.owns_committed_receipt(receipt_a) is False
    finally:
        _close_graph(graph)


def _replacement_service() -> tuple[OutputSessionService, _PredecessorAwareExecutor]:
    device_b = "usb:vendor:product:device-b"

    def facts(path: Path):
        if path.stem == "b":
            return _facts(
                profile=stable_direct_preset("p-b", device_b),
                selected_device_id=device_b,
                evidence=(_evidence(device=device_b),),
            )
        return _facts()

    executor = _PredecessorAwareExecutor()
    service = OutputSessionService(
        OutputPlanner(),
        facts_provider=facts,
        executors={"gstreamer": executor},
    )
    media_a = Path("a.flac")
    token_a = service.prepare_for_media(media_a)
    service.commit_media(token_a, media_a)
    service.prepare_for_media(Path("b.flac"))
    return service, executor


def test_r80r1_16_predecessor_device_is_loss_relevant_before_boundary() -> None:
    service, _executor = _replacement_service()

    assert service.plan.stable_device_id != DEVICE
    assert service.topology_loss_applies(DEVICE) is True


def test_r80r1_17_predecessor_device_is_stale_after_destructive_boundary() -> None:
    service, executor = _replacement_service()

    executor.cross_destructive_boundary()

    assert service.topology_loss_applies(DEVICE) is False


def test_r80r1_18_pre_boundary_predecessor_loss_retires_candidate_too() -> None:
    service, executor = _replacement_service()

    service.topology_lost(DEVICE, 2)

    # Selected B did not disappear, so cleanup converges inactive/IDLE rather
    # than waiting forever for an unrelated A rebind.
    assert service.state is OutputSessionState.IDLE
    assert service.plan is None
    assert service._lost_device_id is None
    assert service._lost_binding_generation == 0
    assert executor.releases == ["device_lost"]


def test_r80r1_19_post_boundary_predecessor_loss_cannot_kill_candidate() -> None:
    service, executor = _replacement_service()
    plan_b = service.plan
    executor.cross_destructive_boundary()

    service.topology_lost(DEVICE, 2)

    assert service.state is OutputSessionState.READY
    assert service.plan is plan_b
    assert executor.releases == []


def test_r80r1_20_current_candidate_device_loss_is_always_relevant() -> None:
    service, executor = _replacement_service()
    device_b = service.plan.stable_device_id

    assert service.topology_loss_applies(device_b) is True
    service.topology_lost(device_b, 2)

    assert service.state is OutputSessionState.LOST
    assert service._lost_device_id == device_b
    assert service._lost_binding_generation == 2
    assert executor.releases == ["device_lost"]


def test_shared_candidate_loss_still_retires_owned_direct_predecessor() -> None:
    executor = _PredecessorAwareExecutor()

    def request(path: Path) -> OutputRequest:
        return (
            OutputRequest.shared()
            if path.stem == "shared"
            else OutputRequest.direct(_facts())
        )

    service = OutputSessionService(
        OutputPlanner(),
        request_provider=request,
        executors={"gstreamer": executor},
    )
    media_a = Path("a.flac")
    token_a = service.prepare_for_media(media_a)
    service.commit_media(token_a, media_a)
    service.prepare_for_media(Path("shared.flac"))
    assert service.mode == "shared"
    assert service._previous_direct is not None

    assert service.topology_loss_applies(DEVICE) is True
    service.topology_lost(DEVICE, 2)

    assert service.state is OutputSessionState.IDLE
    assert service._previous_direct is None
    assert service.plan is None
    assert executor.releases == ["device_lost"]


def test_r80r1_21_failed_cleanup_preserves_shared_volume_preference(
    tmp_path: Path,
) -> None:
    from tests.dac.test_v35_080_productive_lifecycle import _disconnect

    graph, bindings = _direct_graph(tmp_path)
    port = graph.gstreamer_engine_provider.current_port
    original_discard = port.discard_direct_load
    try:
        graph.audio_output_profiles.save_selection(AudioOutputSelection(None, None, 2))
        graph.playback.set_volume(37)
        graph.audio_output_profiles.save_selection(
            AudioOutputSelection("p1", "usb:2622:0105:DX5ABC123", 3)
        )
        graph.playback.load_and_play(tmp_path / "direct.flac")
        _accept_current(graph, bindings)
        port.discard_direct_load = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("release failed")
        )

        _disconnect(graph, tmp_path)

        assert graph.playback.snapshot_volume() == (37, False)
        assert graph.playback.state.volume == 100
        assert graph.output_session.last_cleanup_diagnostic is not None
    finally:
        port.discard_direct_load = original_discard
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_r80r1_22_lost_generation_has_no_reusable_volume_authority(
    tmp_path: Path,
) -> None:
    from michi.application.audio_output_ports import VolumeAuthority
    from tests.dac.test_v35_080_productive_lifecycle import _disconnect

    graph, bindings = _direct_graph(tmp_path)
    try:
        graph.playback.load_and_play(tmp_path / "direct.flac")
        _accept_current(graph, bindings)
        _disconnect(graph, tmp_path)

        assert graph.volume_policy.authority is VolumeAuthority.UNKNOWN
        with pytest.raises(UnknownVolumeAuthorityError):
            graph.playback.set_volume(37)
        assert graph.playback.state.volume == 100
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_r80r1_23_rebind_does_not_restore_old_volume_or_plan() -> None:
    service, _executor = _committed_service()
    old_plan = service.plan
    stable_id = service.active_device_id

    service.topology_lost(stable_id, 2)
    assert service.rebind_after_topology_change(stable_id, 3) is True

    assert service.mode == "shared"
    assert service.plan is None
    assert service.active_plan is None
    assert service.volume_policy is None
    assert old_plan is not service.plan


def test_r80r1_24_productive_loss_retires_active_signal_truth(
    tmp_path: Path,
) -> None:
    from tests.dac.test_v35_080_productive_lifecycle import _disconnect

    graph, bindings = _direct_graph(tmp_path)
    try:
        graph.playback.load_and_play(tmp_path / "direct.flac")
        _accept_current(graph, bindings)
        identity = graph.signal_truth.active_snapshot.identity

        _disconnect(graph, tmp_path)

        assert graph.signal_truth.active_snapshot is None
        assert graph.signal_truth.last_snapshot.identity == identity
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_r80r1_25_a_to_b_loss_retires_candidate_and_predecessor_on_failure(
    tmp_path: Path,
) -> None:
    from tests.dac.test_v35_080_productive_lifecycle import _disconnect

    graph, bindings = _direct_graph(tmp_path)
    port = graph.gstreamer_engine_provider.current_port
    original_discard = port.discard_direct_load
    try:
        graph.playback.load_and_play(tmp_path / "a.flac")
        _accept_current(graph, bindings)
        graph.playback.load_and_play(tmp_path / "b.flac")
        candidate_identity = graph.signal_truth.candidate_snapshot.identity
        port.discard_direct_load = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("B cleanup failed")
        )

        _disconnect(graph, tmp_path)

        assert graph.output_session.state is OutputSessionState.LOST
        assert graph.direct_output_executor.handle is None
        assert graph.signal_truth.active_snapshot is None
        with pytest.raises(RuntimeError, match="no Signal Truth candidate"):
            _candidate = graph.signal_truth.candidate_snapshot
        assert graph.signal_truth.last_snapshot.identity == candidate_identity
    finally:
        port.discard_direct_load = original_discard
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_r80r1_26_playback_stops_even_if_topology_transaction_raises(
    tmp_path: Path,
) -> None:
    from tests.dac.test_v35_080_productive_lifecycle import _disconnect

    graph, bindings = _direct_graph(tmp_path)
    original_topology_lost = graph.output_session.topology_lost
    try:
        graph.playback.load_and_play(tmp_path / "direct.flac")
        _accept_current(graph, bindings)
        graph.output_session.topology_lost = lambda *_args: (_ for _ in ()).throw(
            RuntimeError("transaction cleanup failed")
        )

        _disconnect(graph, tmp_path)

        assert graph.playback.state.status is PlaybackStatus.STOPPED
        assert graph.playback.state.error_message == "OUTPUT_DEVICE_LOST"
    finally:
        graph.output_session.topology_lost = original_topology_lost
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_r80r1_27_registry_delivers_truth_after_release_failure(
    tmp_path: Path,
) -> None:
    from tests.dac.test_v35_080_productive_lifecycle import _disconnect

    graph, bindings = _direct_graph(tmp_path)
    port = graph.gstreamer_engine_provider.current_port
    original_discard = port.discard_direct_load
    observed = []
    try:
        graph.playback.load_and_play(tmp_path / "direct.flac")
        _accept_current(graph, bindings)
        stable_id = graph.output_session.active_device_id
        graph.audio_device_registry.subscribe_topology_changed(observed.append)
        port.discard_direct_load = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("release failed")
        )

        _disconnect(graph, tmp_path)

        assert stable_id not in graph.audio_device_registry.available_ids()
        assert len(observed) == 1
        assert observed[0].stable_device_id == stable_id
        assert observed[0].current_available is False
    finally:
        port.discard_direct_load = original_discard
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_r80r1_28_pending_request_rejects_once_when_release_fails(
    tmp_path: Path,
) -> None:
    from tests.dac.test_v35_080_productive_lifecycle import _disconnect

    graph, _bindings = _direct_graph(tmp_path)
    port = graph.gstreamer_engine_provider.current_port
    original_discard = port.discard_direct_load
    rejected = []
    try:
        graph.playback.load_and_play(
            tmp_path / "pending.flac",
            on_rejected=lambda path, reason: rejected.append((path, reason)),
        )
        port.discard_direct_load = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("release failed")
        )

        _disconnect(graph, tmp_path)
        _disconnect(graph, tmp_path)

        assert len(rejected) == 1
        assert rejected[0][1] == "OUTPUT_DEVICE_LOST"
        assert graph.output_session.state is OutputSessionState.LOST
    finally:
        port.discard_direct_load = original_discard
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_r80r1_29_release_failure_never_emits_eom_or_allows_fallback(
    tmp_path: Path,
) -> None:
    from tests.dac.test_v35_080_productive_lifecycle import _disconnect

    graph, bindings = _direct_graph(tmp_path)
    port = graph.gstreamer_engine_provider.current_port
    original_discard = port.discard_direct_load
    eom = []
    try:
        graph.playback.load_and_play(tmp_path / "direct.flac")
        _accept_current(graph, bindings)
        graph.playback.subscribe_end_of_media(lambda: eom.append(True))
        port.discard_direct_load = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("release failed")
        )

        _disconnect(graph, tmp_path)

        assert eom == []
        assert graph.output_session.allows_automatic_engine_fallback() is False
        assert graph.audio_router.bound_engine_id.value == "gstreamer"
    finally:
        port.discard_direct_load = original_discard
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_r80r1_30_old_execution_handle_cannot_publish_after_loss(
    tmp_path: Path,
) -> None:
    from michi.infrastructure.audio_output.direct_output_executor import (
        DirectExecutorError,
    )
    from tests.dac.test_v35_080_productive_lifecycle import _disconnect

    graph, bindings = _direct_graph(tmp_path)
    try:
        graph.playback.load_and_play(tmp_path / "direct.flac")
        _accept_current(graph, bindings)
        old_handle = graph.direct_output_executor.handle

        _disconnect(graph, tmp_path)

        with pytest.raises(DirectExecutorError, match="DIRECT_STALE_EXECUTION"):
            graph.direct_output_executor.record_runtime_anomaly(old_handle, "late XRUN")
        assert graph.signal_truth.active_snapshot is None
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)
