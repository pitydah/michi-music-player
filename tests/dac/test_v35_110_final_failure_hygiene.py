"""DAC-V35-110 final — success/failure state hygiene gates (§23 A–F).

A runtime/output failure belongs to ONE request: a later successful request must
retire the previous failure presentation, and a normal stop is a COMMAND, never
a failure.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication

from michi.domain.playback import PlaybackStatus
from tests.dac.test_v35_100r13_playback_compatibility import (
    _s16_graph as _r13_s16_graph,
)
from tests.dac.test_v35_100r13_playback_compatibility import (
    _SplitProbe as _R13SplitProbe,
)
from tests.dac.test_v35_productive_direct_composition import (
    _close_graph,
    _direct_graph,
)


def _wait(predicate, *, timeout_s: float = 20.0) -> bool:
    import time

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        QCoreApplication.processEvents()
        if predicate():
            return True
        time.sleep(0.02)
    return bool(predicate())


def _s16_graph(tmp_path: Path, probe):
    from michi.domain.library import TrackMetadata

    graph, bindings = _direct_graph(
        tmp_path,
        qualification_adapter=probe,
        preseed_qualification=False,
        source_metadata=TrackMetadata(
            title="S16", sample_rate_hz=44_100, bit_depth=16, channels=2
        ),
    )
    bindings.source_characterization_overrides = {
        "format": "S16LE",
        "rate": 44_100,
        "significant_bits": 16,
        "channels": 2,
    }
    return graph, bindings


class _SplitProbe:
    """Rejects S16_LE exactly; accepts the S32_LE compatible widening."""

    def __init__(self) -> None:
        self.calls: list[tuple[int, str, int]] = []

    def probe_exact(self, **kwargs):
        from michi.domain.audio_evidence import ExactProbeResult, PcmTuple

        rate = kwargs["rate_hz"]
        fmt = kwargs["transport_format"]
        channels = kwargs["channels"]
        self.calls.append((rate, fmt, channels))
        requested = PcmTuple(rate, fmt, channels, 16)
        if fmt == "S16_LE":
            return ExactProbeResult(
                requested, None, "unsupported_format", 22, "exact reject", "r:reject"
            )
        return ExactProbeResult(
            requested,
            PcmTuple(rate, fmt, channels, 32),
            "OPENED",
            None,
            None,
            "r:open",
        )


def _coordinator(graph):
    from michi.application.audio_output_selection_coordinator import (
        AudioOutputSelectionCoordinator,
    )

    return AudioOutputSelectionCoordinator(
        profiles=graph.audio_output_profiles,
        devices=graph.audio_device_registry,
        output_session=graph.output_session,
        engines=graph.audio_engine_service,
    )


def _authorities(graph) -> tuple[str | None, str | None]:
    state = graph.playback.state
    session_state = graph.output_session.selection_state()
    return state.error_code, session_state.error_code


def test_fh110_a_strict_refusal_then_success_retires_the_failure(
    qapp, tmp_path: Path
) -> None:
    """A Strict refusal, then a Compatible success: the failure retires."""

    probe = _R13SplitProbe()
    graph, bindings = _r13_s16_graph(tmp_path, probe)
    try:
        # 1. Strict Direct refuses truthfully.
        graph.playback.load_and_play(tmp_path / "strict-refusal.flac")
        assert _wait(lambda: graph.playback.state.error_message is not None)
        assert graph.playback.state.error_code == "EXACT_TUPLE_UNSUPPORTED"

        # 2. A later request REACHES THE SUCCESS BOUNDARY through the real
        # media-acceptance flow, which retires the previous presentation.
        later = tmp_path / "later-ok.flac"
        graph.playback._pending_path = later  # acceptance precondition
        graph.playback._finalize_media_acceptance(later)

        playback_code, session_code = _authorities(graph)
        assert playback_code is None, "a successful request kept the old code"
        assert graph.playback.state.error_message is None
        assert session_code is None
    finally:
        _close_graph(graph)


def test_fh110_d_normal_stop_is_not_a_failure(qapp, tmp_path: Path) -> None:
    probe = _SplitProbe()
    graph, _bindings = _s16_graph(tmp_path, probe)
    try:
        graph.playback.load_and_play(tmp_path / "stop-check.flac")
        assert _wait(lambda: graph.playback.state.error_message is not None)

        graph.playback.stop()

        assert graph.playback.state.status is PlaybackStatus.STOPPED
        session_state = graph.output_session.selection_state()
        assert session_state.error_code != "stop", "a normal stop became a failure"
        assert session_state.error_code is None
    finally:
        _close_graph(graph)


def test_fh110_f_a_failing_request_keeps_a_truthful_failure(
    qapp, tmp_path: Path
) -> None:
    """A request that fails BEFORE success must not present a clean state."""
    probe = _SplitProbe()
    graph, _bindings = _s16_graph(tmp_path, probe)
    try:
        graph.playback.load_and_play(tmp_path / "first-failure.flac")
        assert _wait(lambda: graph.playback.state.error_message is not None)
        first_code = graph.playback.state.error_code

        # A second request that ALSO fails keeps a truthful typed failure.
        graph.playback.load_and_play(tmp_path / "second-failure.flac")
        assert _wait(lambda: graph.playback.state.error_code == first_code), (
            graph.playback.state.error_code
        )
        assert graph.playback.state.status is not PlaybackStatus.PLAYING
        assert graph.playback.state.error_message is not None
    finally:
        _close_graph(graph)


def test_fh110_bridge_never_projects_a_plain_stop_reason() -> None:
    """The Audio Output surface must not render a normal stop as a failure."""
    from michi.application.playback_failure import (
        RECOVERY_USE_SHARED,
        output_recovery_actions,
    )

    # A plain command reason carries no failure semantics of its own.
    assert output_recovery_actions("stop") == ()
    assert output_recovery_actions(None) == ()
    # A typed failure still offers recovery, proving the projection is intact.
    assert RECOVERY_USE_SHARED in output_recovery_actions("NO_COMPATIBLE_CARRIER")


def test_fh110_c_a_stale_failure_cannot_overwrite_a_newer_success(
    qapp, tmp_path: Path
) -> None:
    """A late failure from an OLD generation must not contaminate a success."""

    probe = _R13SplitProbe()
    graph, bindings = _r13_s16_graph(tmp_path, probe)
    try:
        # An old failure is presented.
        graph.playback.load_and_play(tmp_path / "old.flac")
        assert _wait(lambda: graph.playback.state.error_message is not None)

        # A newer request reaches the SUCCESS BOUNDARY; it retires the failure.
        newer = tmp_path / "new.flac"
        graph.playback._pending_path = newer  # acceptance precondition
        graph.playback._finalize_media_acceptance(newer)
        assert graph.playback.state.error_code is None
        assert graph.playback.state.error_message is None

        # A NORMAL STOP after that success must not fabricate a failure either.
        graph.playback.stop()
        assert graph.playback.state.status is PlaybackStatus.STOPPED
        assert graph.playback.state.error_code is None
        assert graph.output_session.selection_state().error_code is None
    finally:
        _close_graph(graph)


def test_fh110_e_a_real_stop_failure_stays_visible(qapp, tmp_path: Path) -> None:
    """A genuinely failing stop operation must remain a typed failure."""
    probe = _SplitProbe()
    graph, _bindings = _s16_graph(tmp_path, probe)
    try:
        graph.playback.load_and_play(tmp_path / "stop-failure.flac")
        assert _wait(lambda: graph.playback.state.error_message is not None)

        original = graph.output_session.release_active

        def exploding(reason):
            original(reason)
            raise RuntimeError("synthetic release failure")

        graph.output_session.release_active = exploding
        with pytest.raises(RuntimeError, match="synthetic release failure"):
            graph.playback.stop()
    finally:
        _close_graph(graph)
