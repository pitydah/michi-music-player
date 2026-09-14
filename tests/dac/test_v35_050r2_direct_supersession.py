"""DAC-V35-050R2 Direct A→B→C supersession gates (R2-01..R2-14)."""

from __future__ import annotations

from pathlib import Path

import pytest

from michi.application.audio_output_ports import OutputExecutorAbortDisposition
from michi.application.ports import AudioLoadError
from michi.domain.audio_output import AudioOutputSelection, OutputSessionState
from michi.domain.playback import PlaybackStatus
from michi.infrastructure.audio_output.direct_output_executor import (
    DirectExecutionState,
    DirectExecutorError,
)
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


def _accept_direct_a(graph, bindings, path: Path):
    graph.playback.load_and_play(path)
    _accept_current(graph, bindings)
    handle = graph.direct_output_executor.handle
    assert handle is not None
    assert graph.output_session.state is OutputSessionState.RUNNING
    return handle


def _start_post_destructive_b(graph, bindings, media_a: Path, media_b: Path):
    handle_a = _accept_direct_a(graph, bindings, media_a)
    graph.playback.load_and_play(media_b)
    port = graph.gstreamer_engine_provider.current_port
    assert port is not None
    handle_b = graph.direct_output_executor.handle
    assert handle_b is not None
    assert port._pending_path == media_b
    assert bindings.null_request_count == 1
    return port, handle_a, handle_b, bindings.pipelines[-1], port._generation


def test_r2_01_pre_destructive_b_failure_restores_a(tmp_path: Path) -> None:
    graph, bindings = _direct_graph(tmp_path)
    media_a = tmp_path / "a.flac"
    try:
        handle_a = _accept_direct_a(graph, bindings, media_a)
        pipeline_a = bindings.pipelines[-1]
        bindings.failed_states.add(bindings.STATE.NULL)

        with pytest.raises(RuntimeError, match="pipeline anterior"):
            graph.playback.load_and_play(tmp_path / "b.flac")

        assert graph.playback.state.file_path == media_a
        assert graph.playback._accepted is True
        assert graph.output_session.state is OutputSessionState.RUNNING
        assert graph.direct_output_executor.handle == handle_a
        assert graph.gstreamer_engine_provider.current_port._pipeline is pipeline_a
    finally:
        bindings.failed_states.clear()
        _close_graph(graph)


def test_r2_02_post_destructive_b_failure_never_restores_a(tmp_path: Path) -> None:
    graph, bindings = _direct_graph(tmp_path)
    media_a = tmp_path / "a.flac"
    try:
        _accept_direct_a(graph, bindings, media_a)
        bindings.arm_exception_stage = "set_uri"
        bindings.arm_exception = RuntimeError("B arm failed")

        with pytest.raises(AudioLoadError) as caught:
            graph.playback.load_and_play(tmp_path / "b.flac")

        assert caught.value.previous_source_preserved is False
        assert graph.playback.state.file_path == media_a
        assert graph.playback._accepted is False
        assert graph.playback.state.status is PlaybackStatus.STOPPED
        assert graph.output_session.state is OutputSessionState.IDLE
        assert graph.direct_output_executor.state is DirectExecutionState.IDLE
    finally:
        bindings.arm_exception_stage = None
        bindings.arm_exception = None
        _close_graph(graph)


def test_r2_03_post_destructive_b_can_be_superseded_by_shared_c(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    media_a = tmp_path / "a.flac"
    media_b = tmp_path / "b.flac"
    media_c = tmp_path / "c.flac"
    try:
        port, _handle_a, _handle_b, _pipeline_b, _generation_b = (
            _start_post_destructive_b(graph, bindings, media_a, media_b)
        )

        graph.audio_output_profiles.save_selection(AudioOutputSelection(None, None, 2))
        graph.playback.load_and_play(media_c)

        assert graph.playback.state.file_path == media_a
        assert graph.playback._pending_path == media_c
        assert graph.output_session.mode == "shared"
        assert graph.output_session.plan is None
        assert graph.direct_output_executor.state is DirectExecutionState.IDLE
        assert graph.direct_output_executor.handle is None
        assert port._pending_path == media_c
        assert bindings.pipelines[-1].audio_sink is None

        _accept_current(graph, bindings)
        assert graph.playback.state.file_path == media_c
        assert graph.output_session.mode == "shared"
        assert graph.direct_output_executor.state is DirectExecutionState.IDLE
    finally:
        _close_graph(graph)


def test_r2_04_post_destructive_b_can_be_superseded_by_direct_c(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    media_a = tmp_path / "a.flac"
    media_b = tmp_path / "b.flac"
    media_c = tmp_path / "c.flac"
    try:
        _port, handle_a, handle_b, _pipeline_b, _generation_b = (
            _start_post_destructive_b(graph, bindings, media_a, media_b)
        )

        graph.playback.load_and_play(media_c)
        handle_c = graph.direct_output_executor.handle

        assert handle_c is not None
        assert handle_a.generation < handle_b.generation < handle_c.generation
        assert graph.output_session.state is OutputSessionState.READY
        assert graph.output_session.plan is not None
        assert graph.output_session.plan.plan_id == handle_c.plan_id
        assert graph.gstreamer_engine_provider.current_port._pending_path == media_c

        _accept_current(graph, bindings)
        assert graph.playback.state.file_path == media_c
        assert graph.output_session.state is OutputSessionState.RUNNING
        assert graph.direct_output_executor.state is DirectExecutionState.COMMITTED
        assert graph.direct_output_executor.handle == handle_c
    finally:
        _close_graph(graph)


def test_r2_05_pre_destructive_b_to_shared_c_restores_then_retires_a(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    media_a = tmp_path / "a.flac"
    try:
        handle_a = _accept_direct_a(graph, bindings, media_a)
        graph.output_session.prepare_for_media(tmp_path / "b.flac")
        handle_b = graph.direct_output_executor.handle
        dispositions = []
        original_abort = graph.direct_output_executor.abort

        def recording_abort(receipt, reason):
            result = original_abort(receipt, reason)
            dispositions.append(result)
            return result

        graph.direct_output_executor.abort = recording_abort
        graph.audio_output_profiles.save_selection(AudioOutputSelection(None, None, 2))
        media_c = tmp_path / "c.flac"
        graph.playback.load_and_play(media_c)

        assert handle_b is not None and handle_a.generation < handle_b.generation
        assert OutputExecutorAbortDisposition.PREDECESSOR_RESTORED in dispositions
        assert graph.output_session.mode == "shared"
        assert graph.direct_output_executor.state is DirectExecutionState.IDLE
        assert graph.gstreamer_engine_provider.current_port._pending_path == media_c
        assert bindings.pipelines[-1].audio_sink is None
    finally:
        _close_graph(graph)


def test_r2_06_pre_destructive_b_to_direct_c_collapses_to_one_candidate(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        handle_a = _accept_direct_a(graph, bindings, tmp_path / "a.flac")
        graph.output_session.prepare_for_media(tmp_path / "b.flac")
        handle_b = graph.direct_output_executor.handle

        media_c = tmp_path / "c.flac"
        graph.playback.load_and_play(media_c)
        handle_c = graph.direct_output_executor.handle

        assert handle_b is not None and handle_c is not None
        assert handle_a.generation < handle_b.generation < handle_c.generation
        assert graph.output_session.state is OutputSessionState.READY
        assert graph.gstreamer_engine_provider.current_port._pending_path == media_c
        assert graph.direct_output_executor._committed is None
        _accept_current(graph, bindings)
        assert graph.playback.state.file_path == media_c
        assert graph.direct_output_executor.handle == handle_c
        assert graph.direct_output_executor.state is DirectExecutionState.COMMITTED
    finally:
        _close_graph(graph)


def test_r2_06b_direct_c_teardown_failure_cannot_reauthorize_a_or_b(
    tmp_path: Path,
) -> None:
    from PySide6.QtCore import QCoreApplication
    from test_gstreamer_audio_port import FakeMessage, _FakeMsgType

    graph, bindings = _direct_graph(tmp_path)
    media_a = tmp_path / "a.flac"
    media_b = tmp_path / "b.flac"
    try:
        port, _a, _b, pipeline_b, generation_b = _start_post_destructive_b(
            graph, bindings, media_a, media_b
        )
        bindings.failed_states.add(bindings.STATE.NULL)

        with pytest.raises(AudioLoadError) as caught:
            graph.playback.load_and_play(tmp_path / "c.flac")

        assert caught.value.previous_source_preserved is False
        assert graph.playback.state.file_path == media_a
        assert graph.playback._accepted is False
        assert graph.playback.state.status is PlaybackStatus.STOPPED
        assert graph.output_session.state is OutputSessionState.IDLE
        assert graph.direct_output_executor.state is DirectExecutionState.IDLE
        assert port._pending_path is None and port._current_path is None
        assert port._pipeline is pipeline_b  # retryable physical cleanup anchor only

        with pytest.raises(AudioLoadError) as repeated:
            graph.playback.load_and_play(tmp_path / "d.flac")
        assert repeated.value.previous_source_preserved is False
        assert graph.playback._accepted is False
        assert graph.output_session.state is OutputSessionState.IDLE
        assert graph.direct_output_executor.state is DirectExecutionState.IDLE

        port._process_message(
            FakeMessage(_FakeMsgType.ASYNC_DONE, pipeline_b),
            generation_b,
            pipeline_b,
        )
        QCoreApplication.processEvents()
        assert graph.playback.state.file_path == media_a
        assert graph.playback._accepted is False
    finally:
        bindings.failed_states.clear()
        _close_graph(graph)


def test_r2_07_late_b_async_done_cannot_reclaim_after_shared_c(
    tmp_path: Path,
) -> None:
    from PySide6.QtCore import QCoreApplication
    from test_gstreamer_audio_port import FakeMessage, _FakeMsgType

    graph, bindings = _direct_graph(tmp_path)
    media_a = tmp_path / "a.flac"
    media_b = tmp_path / "b.flac"
    media_c = tmp_path / "c.flac"
    try:
        port, _a, _b, pipeline_b, generation_b = _start_post_destructive_b(
            graph, bindings, media_a, media_b
        )
        graph.audio_output_profiles.save_selection(AudioOutputSelection(None, None, 2))
        graph.playback.load_and_play(media_c)
        _accept_current(graph, bindings)
        pipeline_c = port._pipeline

        port._process_message(
            FakeMessage(_FakeMsgType.ASYNC_DONE, pipeline_b),
            generation_b,
            pipeline_b,
        )
        QCoreApplication.processEvents()

        assert graph.playback.state.file_path == media_c
        assert graph.output_session.mode == "shared"
        assert graph.direct_output_executor.state is DirectExecutionState.IDLE
        assert port._current_path == media_c
        assert port._pipeline is pipeline_c
    finally:
        _close_graph(graph)


def test_r2_08_stale_b_abort_cannot_mutate_direct_c(tmp_path: Path) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        _port, _a, _b, _pipeline_b, _generation_b = _start_post_destructive_b(
            graph, bindings, tmp_path / "a.flac", tmp_path / "b.flac"
        )
        receipt_b = graph.output_session._executor_receipt
        token_b = graph.output_session._token_value
        graph.playback.load_and_play(tmp_path / "c.flac")
        handle_c = graph.direct_output_executor.handle
        token_c = graph.output_session._token_value

        disposition = graph.direct_output_executor.abort(receipt_b, "late_b_abort")
        graph.output_session.abort_media(token_b, "late_b_abort")

        assert disposition is OutputExecutorAbortDisposition.STALE
        assert graph.direct_output_executor.handle == handle_c
        assert graph.output_session._token_value == token_c
        assert graph.output_session.state is OutputSessionState.READY
    finally:
        _close_graph(graph)


def test_r2_09_stale_b_commit_raises_without_mutating_direct_c(tmp_path: Path) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        _port, _a, _b, _pipeline_b, _generation_b = _start_post_destructive_b(
            graph, bindings, tmp_path / "a.flac", tmp_path / "b.flac"
        )
        receipt_b = graph.output_session._executor_receipt
        graph.playback.load_and_play(tmp_path / "c.flac")
        handle_c = graph.direct_output_executor.handle

        with pytest.raises(DirectExecutorError) as caught:
            graph.direct_output_executor.commit(receipt_b)

        assert caught.value.code == "DIRECT_STALE_EXECUTION"
        assert graph.direct_output_executor.handle == handle_c
        assert graph.output_session.state is OutputSessionState.READY
    finally:
        _close_graph(graph)


def test_r2_10_same_plan_id_a_b_c_remains_generation_isolated(tmp_path: Path) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        _port, handle_a, handle_b, _pipeline_b, _generation_b = (
            _start_post_destructive_b(
                graph, bindings, tmp_path / "a.flac", tmp_path / "b.flac"
            )
        )
        receipt_b = graph.output_session._executor_receipt
        graph.playback.load_and_play(tmp_path / "c.flac")
        handle_c = graph.direct_output_executor.handle

        assert handle_c is not None
        assert handle_a.plan_id == handle_b.plan_id == handle_c.plan_id
        assert handle_a.generation < handle_b.generation < handle_c.generation
        assert (
            graph.direct_output_executor.abort(receipt_b, "same_plan_stale")
            is OutputExecutorAbortDisposition.STALE
        )
        assert graph.direct_output_executor.handle == handle_c
    finally:
        _close_graph(graph)


def test_r2_11_failed_shared_c_after_post_destructive_b_restores_nothing(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    media_a = tmp_path / "a.flac"
    try:
        _start_post_destructive_b(graph, bindings, media_a, tmp_path / "b.flac")
        graph.audio_output_profiles.save_selection(AudioOutputSelection(None, None, 2))
        bindings.arm_exception_stage = "set_uri"
        bindings.arm_exception = RuntimeError("Shared C arm failed")

        with pytest.raises(AudioLoadError) as caught:
            graph.playback.load_and_play(tmp_path / "c.flac")

        assert caught.value.previous_source_preserved is False
        assert graph.playback.state.file_path == media_a
        assert graph.playback._accepted is False
        assert graph.output_session.state is OutputSessionState.IDLE
        assert graph.direct_output_executor.state is DirectExecutionState.IDLE
        assert graph.gstreamer_engine_provider.current_port._current_path is None
    finally:
        bindings.arm_exception_stage = None
        bindings.arm_exception = None
        _close_graph(graph)


def test_r2_12_failed_direct_c_after_post_destructive_b_restores_nothing(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    media_a = tmp_path / "a.flac"
    try:
        _start_post_destructive_b(graph, bindings, media_a, tmp_path / "b.flac")
        bindings.arm_exception_stage = "set_uri"
        bindings.arm_exception = RuntimeError("Direct C arm failed")

        with pytest.raises(AudioLoadError) as caught:
            graph.playback.load_and_play(tmp_path / "c.flac")

        assert caught.value.previous_source_preserved is False
        assert graph.playback.state.file_path == media_a
        assert graph.playback._accepted is False
        assert graph.output_session.state is OutputSessionState.IDLE
        assert graph.direct_output_executor.state is DirectExecutionState.IDLE
        assert graph.gstreamer_engine_provider.current_port._current_path is None
    finally:
        bindings.arm_exception_stage = None
        bindings.arm_exception = None
        _close_graph(graph)


def test_r2_13_stop_fallback_is_not_bypassed_during_a_b_c_failure(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        _start_post_destructive_b(
            graph, bindings, tmp_path / "a.flac", tmp_path / "b.flac"
        )
        bindings.arm_exception_stage = "set_uri"
        bindings.arm_exception = RuntimeError("C failed")

        with pytest.raises(AudioLoadError):
            graph.playback.load_and_play(tmp_path / "c.flac")

        assert graph.audio_router.bound_engine_id.value == "gstreamer"
        assert graph.output_session.state is OutputSessionState.IDLE
        assert graph.direct_output_executor.state is DirectExecutionState.IDLE
        assert all(pipeline.audio_sink is not None for pipeline in bindings.pipelines)
    finally:
        bindings.arm_exception_stage = None
        bindings.arm_exception = None
        _close_graph(graph)


def test_r2_14_shared_c_never_inherits_b_strict_recipe(tmp_path: Path) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        _start_post_destructive_b(
            graph, bindings, tmp_path / "a.flac", tmp_path / "b.flac"
        )
        direct_recipe_count = len(bindings.built_recipes)
        graph.audio_output_profiles.save_selection(AudioOutputSelection(None, None, 2))

        graph.playback.load_and_play(tmp_path / "c.flac")

        assert len(bindings.built_recipes) == direct_recipe_count
        assert bindings.pipelines[-1].audio_sink is None
        assert graph.output_session.mode == "shared"
        assert graph.direct_output_executor.state is DirectExecutionState.IDLE
    finally:
        _close_graph(graph)
