"""M11.4 PCM closure — normal DAC playback gates.

The normal (NowPlaying) surface must let a user pick a physical DAC and play
common 16-bit PCM without knowing anything about ALSA, while Strict Direct stays
exact and honest and no policy is ever switched silently.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QCoreApplication

from michi.application.playback_failure import (
    RECOVERY_CANCEL,
    RECOVERY_TRY_COMPATIBLE_DIRECT,
    RECOVERY_USE_SHARED,
    output_recovery_actions,
)
from michi.domain.audio_output import OutputPathPreference
from tests.dac.test_v35_100r13_playback_compatibility import (
    _close_graph,
    _coordinator,
    _SplitProbe,
    _wait_for_pipeline,
    _wait_until,
)
from tests.dac.test_v35_productive_direct_composition import (
    _accept_current,
    _direct_graph,
)

DEVICE_ID = "usb:2622:0105:DX5ABC123"


def _s16_graph_at(tmp_path: Path, probe, rate_hz: int):
    """Sixteen-bit source at the requested rate, with S16_LE refused by ALSA."""
    from michi.domain.library import TrackMetadata

    graph, bindings = _direct_graph(
        tmp_path,
        qualification_adapter=probe,
        preseed_qualification=False,
        source_metadata=TrackMetadata(
            title=f"S16 source at {rate_hz}",
            sample_rate_hz=rate_hz,
            bit_depth=16,
            channels=2,
        ),
    )
    bindings.source_characterization_overrides = {
        "format": "S16LE",
        "rate": rate_hz,
        "significant_bits": 16,
        "channels": 2,
    }
    return graph, bindings


def _selected_profile(graph):
    selection = graph.audio_output_profiles.load_selection()
    return next(
        profile
        for profile in graph.audio_output_profiles.load_profiles()
        if profile.profile_id == selection.selected_profile_id
    )


def test_ndp_01_normal_intent_binds_the_recommended_direct_policy(
    qapp, tmp_path
) -> None:
    """Choosing a DAC from the normal surface means "play through this DAC"."""
    probe = _SplitProbe()
    graph, _bindings = _s16_graph_at(tmp_path, probe, 44_100)
    try:
        coordinator = _coordinator(graph)
        coordinator.select_shared_output()
        assert graph.output_session.mode == "shared"

        coordinator.select_device_for_playback(DEVICE_ID)

        profile = _selected_profile(graph)
        assert profile.stable_device_id == DEVICE_ID
        assert profile.path is OutputPathPreference.HARDWARE_DIRECT_COMPATIBLE
        assert graph.audio_device_registry.selected_device_id == DEVICE_ID
        # The session records the selection; its execution mode only changes
        # when a Direct plan is actually prepared for playback.
        selection = graph.output_session.selection_state()
        assert selection.selected_device_id == DEVICE_ID
        assert selection.selected_profile_id == profile.profile_id
    finally:
        _close_graph(graph)


def test_ndp_02_identity_only_selection_never_implies_a_policy(qapp, tmp_path) -> None:
    """The advanced identity-only intent keeps routing exactly where it was."""
    probe = _SplitProbe()
    graph, _bindings = _s16_graph_at(tmp_path, probe, 44_100)
    try:
        coordinator = _coordinator(graph)
        coordinator.select_shared_output()

        coordinator.select_device(DEVICE_ID)

        assert graph.audio_device_registry.selected_device_id == DEVICE_ID
        assert graph.output_session.mode == "shared"
        stored = graph.audio_output_profiles.load_selection()
        assert stored.selected_profile_id is None
        session_selection = graph.output_session.selection_state()
        assert session_selection.selected_device_id == DEVICE_ID
        assert session_selection.selected_profile_id is None
    finally:
        _close_graph(graph)


def test_ndp_03_strict_refusal_is_honest_and_offers_explicit_recovery(
    qapp, tmp_path
) -> None:
    """Strict Direct keeps failing honestly and never switches policy on its own."""
    probe = _SplitProbe()
    graph, bindings = _s16_graph_at(tmp_path, probe, 44_100)
    try:
        coordinator = _coordinator(graph)
        coordinator.select_path_mode("strict")
        graph.playback.load_and_play(tmp_path / "strict-common-16.flac")

        assert _wait_until(lambda: bool(graph.playback.state.error_message)), (
            "the strict refusal was never contained"
        )
        assert graph.playback.state.error_code == "EXACT_TUPLE_UNSUPPORTED"
        assert bindings.pipelines == []
        assert probe.calls == [(44_100, "S16_LE", 2)]

        # The refusal is tuple-scoped and the policy did not move.
        assert _selected_profile(graph).path is OutputPathPreference.HARDWARE_DIRECT
        assert graph.output_session.mode == "shared"

        # The refusal carries the three explicit recovery intents.
        assert output_recovery_actions("EXACT_TUPLE_UNSUPPORTED") == (
            RECOVERY_TRY_COMPATIBLE_DIRECT,
            RECOVERY_USE_SHARED,
            RECOVERY_CANCEL,
        )
    finally:
        _close_graph(graph)


def test_ndp_04_explicit_recovery_plays_common_16bit_at_44100(qapp, tmp_path) -> None:
    """After an explicit policy switch, 44.1k/16 PCM plays through S32_LE."""
    probe = _SplitProbe()
    graph, bindings = _s16_graph_at(tmp_path, probe, 44_100)
    try:
        coordinator = _coordinator(graph)
        coordinator.select_path_mode("strict")
        media = tmp_path / "recover-44100-16.flac"
        graph.playback.load_and_play(media)
        assert _wait_until(
            lambda: graph.playback.state.error_code == "EXACT_TUPLE_UNSUPPORTED"
        )
        assert bindings.pipelines == []

        # Explicit user recovery: switch the policy, then retry.
        coordinator.select_path_mode("compatible")
        graph.playback.load_and_play(media)
        _wait_for_pipeline(bindings, graph)
        # Deliver the real backend ASYNC_DONE so playback acceptance completes.
        _accept_current(graph, bindings)

        # Only the two authorized candidates were probed: same rate, same
        # channels, no other format, no resample and no remix decision.
        assert probe.calls == [(44_100, "S16_LE", 2), (44_100, "S32_LE", 2)]

        plan = graph.output_session.plan
        assert plan is not None
        assert plan.requested_pcm.rate_hz == 44_100
        assert plan.requested_pcm.channels == 2
        assert plan.requested_pcm.transport_format == "S32_LE"
        assert plan.requested_pcm.significant_bits == 16
        assert plan.carrier_adaptation == "container_width"

        recipe = bindings.built_recipes[-1]
        assert recipe.container_conversion is True
        assert recipe.gst_format == "S32LE"
        assert recipe.rate_hz == 44_100
        assert recipe.channels == 2
        assert recipe.device == "hw:CARD=DX5,DEV=0"

        # Acceptance is the success boundary: the previous typed refusal is
        # retired (message AND code), never left stale after good playback.
        assert _wait_until(lambda: graph.playback.state.error_code is None), (
            "the previous typed refusal was not retired after successful playback"
        )
        assert graph.playback.state.error_message is None
        assert graph.playback.state.file_path == media
    finally:
        _close_graph(graph)


def test_ndp_05_explicit_recovery_plays_common_16bit_at_48000(qapp, tmp_path) -> None:
    """The same contract holds at 48 kHz."""
    probe = _SplitProbe()
    graph, bindings = _s16_graph_at(tmp_path, probe, 48_000)
    try:
        coordinator = _coordinator(graph)
        coordinator.select_path_mode("strict")
        media = tmp_path / "recover-48000-16.flac"
        graph.playback.load_and_play(media)
        assert _wait_until(
            lambda: graph.playback.state.error_code == "EXACT_TUPLE_UNSUPPORTED"
        )
        assert bindings.pipelines == []

        coordinator.select_path_mode("compatible")
        graph.playback.load_and_play(media)
        _wait_for_pipeline(bindings, graph)
        _accept_current(graph, bindings)

        assert probe.calls == [(48_000, "S16_LE", 2), (48_000, "S32_LE", 2)]
        plan = graph.output_session.plan
        assert plan is not None
        assert plan.requested_pcm.rate_hz == 48_000
        assert plan.requested_pcm.channels == 2
        assert plan.requested_pcm.transport_format == "S32_LE"
        assert plan.requested_pcm.significant_bits == 16
        assert plan.carrier_adaptation == "container_width"
        assert bindings.built_recipes[-1].gst_format == "S32LE"
        assert _wait_until(lambda: graph.playback.state.error_code is None), (
            "the previous typed refusal was not retired after successful playback"
        )
        assert graph.playback.state.error_message is None
    finally:
        _close_graph(graph)


def test_ndp_06_persisted_strict_startup_resume_stays_honest_and_recoverable(
    qapp, tmp_path
) -> None:
    """A persisted Strict policy must not autoplay, switch or hide the refusal."""
    from michi.domain.playback import PlaybackStatus
    from tests.dac.test_v35_100r1_startup_resume import (
        _persisted_resume,
        _restore_direct_resume,
    )

    probe = _SplitProbe()
    graph, bindings = _s16_graph_at(tmp_path, probe, 44_100)
    persistence = None
    try:
        coordinator = _coordinator(graph)
        coordinator.select_path_mode("strict")
        target = tmp_path / "startup-16.flac"

        persistence, _repo = _restore_direct_resume(graph, _persisted_resume(target))

        assert _wait_until(
            lambda: bool(
                graph.playback.state.error_code
                or graph.output_session.selection_state().error_code
            )
        ), "the startup refusal was never published by any authority"
        # Honest typed refusal, no autoplay, no fabricated route. At startup
        # without prior evidence the refusal is EXACT_TUPLE_UNKNOWN; with a
        # refused probe it is EXACT_TUPLE_UNSUPPORTED. Both are tuple-scoped.
        refusal = (
            graph.playback.state.error_code
            or graph.output_session.selection_state().error_code
        )
        assert refusal in {
            "EXACT_TUPLE_UNKNOWN",
            "EXACT_TUPLE_UNSUPPORTED",
        }, refusal
        assert graph.playback.state.status is PlaybackStatus.STOPPED
        assert bindings.pipelines == []
        # The persisted intent survives and the policy did not move silently.
        assert _selected_profile(graph).path is OutputPathPreference.HARDWARE_DIRECT
        # Recovery is available exactly where the refusal appears.
        assert output_recovery_actions(refusal) == (
            RECOVERY_TRY_COMPATIBLE_DIRECT,
            RECOVERY_USE_SHARED,
            RECOVERY_CANCEL,
        )
    finally:
        if persistence is not None:
            persistence.shutdown()
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_ndp_07_recovery_reissues_the_refused_request(qapp, tmp_path) -> None:
    """Try Compatible Direct must really retry, not only switch the policy."""
    probe = _SplitProbe()
    graph, bindings = _s16_graph_at(tmp_path, probe, 44_100)
    try:
        coordinator = _coordinator(graph)
        coordinator.select_path_mode("strict")
        media = tmp_path / "retry-44100-16.flac"
        graph.playback.load_and_play(media)
        assert _wait_until(
            lambda: graph.playback.state.error_code == "EXACT_TUPLE_UNSUPPORTED"
        )
        assert bindings.pipelines == []

        # Explicit recovery: switch policy, then re-issue the refused request.
        coordinator.select_path_mode("compatible")
        assert graph.playback.retry_last_refused() is True
        _wait_for_pipeline(bindings, graph)
        _accept_current(graph, bindings)

        assert probe.calls == [(44_100, "S16_LE", 2), (44_100, "S32_LE", 2)]
        plan = graph.output_session.plan
        assert plan is not None
        assert plan.requested_pcm.transport_format == "S32_LE"
        assert graph.playback.state.file_path == media
        assert _wait_until(lambda: graph.playback.state.error_code is None), (
            "the refused failure must retire after the successful retry"
        )
    finally:
        _close_graph(graph)


def test_ndp_08_retry_is_retired_and_generation_safe(qapp, tmp_path) -> None:
    """A refused request is retried once; success and newer requests retire it."""
    probe = _SplitProbe()
    graph, bindings = _s16_graph_at(tmp_path, probe, 44_100)
    try:
        # Nothing refused yet: no retry.
        assert graph.playback.retry_last_refused() is False

        coordinator = _coordinator(graph)
        coordinator.select_path_mode("strict")
        media = tmp_path / "retire-44100-16.flac"
        graph.playback.load_and_play(media)
        assert _wait_until(
            lambda: graph.playback.state.error_code == "EXACT_TUPLE_UNSUPPORTED"
        )

        # Acceptance retires the refusal: a later retry is a no-op.
        coordinator.select_path_mode("compatible")
        graph.playback.load_and_play(media)
        _wait_for_pipeline(bindings, graph)
        _accept_current(graph, bindings)
        assert _wait_until(lambda: graph.playback.state.error_code is None)
        assert graph.playback.retry_last_refused() is False
    finally:
        _close_graph(graph)


def test_ndp_09_handover_reprepares_the_accepted_track(qapp, tmp_path) -> None:
    """Selecting an output moves the accepted track instead of ignoring it."""
    probe = _SplitProbe()
    graph, bindings = _s16_graph_at(tmp_path, probe, 44_100)
    calls: list[tuple[str, int | None]] = []
    original = graph.playback.prepare_for_handover

    def counted(path, position_ms):
        calls.append((str(path), position_ms))
        return original(path, position_ms)

    graph.playback.prepare_for_handover = counted
    try:
        assert graph.playback.reroute_accepted_media() is False, (
            "nothing accepted means nothing to move"
        )

        coordinator = _coordinator(graph)
        coordinator.select_path_mode("compatible")
        media = tmp_path / "handover-44100-16.flac"
        graph.playback.load_and_play(media)
        _wait_for_pipeline(bindings, graph)
        _accept_current(graph, bindings)
        assert _wait_until(lambda: graph.playback.state.file_path == media)

        # The user switches output while the track is live.
        assert graph.playback.reroute_accepted_media() is True
        assert calls == [(str(media), 0)]
        assert _wait_until(lambda: len(bindings.pipelines) >= 2), (
            "the handover must re-prepare through the new route"
        )
    finally:
        _close_graph(graph)


def _handover_graph(qapp, tmp_path):
    probe = _SplitProbe()
    graph, bindings = _s16_graph_at(tmp_path, probe, 44_100)
    coordinator = _coordinator(graph)
    coordinator.select_path_mode("compatible")
    media = tmp_path / "handover-state.flac"
    graph.playback.load_and_play(media)
    _wait_for_pipeline(bindings, graph)
    _accept_current(graph, bindings)
    assert _wait_until(lambda: graph.playback.state.file_path == media)
    return graph, bindings, media


def test_ndp_10_handover_preserves_a_live_playing_position(qapp, tmp_path) -> None:
    """PLAYING at a non-zero position stays PLAYING at that position."""
    from michi.domain.playback import PlaybackStatus

    graph, bindings, media = _handover_graph(qapp, tmp_path)
    seen: list[tuple[str, int]] = []
    original = graph.playback.prepare_for_handover

    def counted(path, position_ms):
        seen.append((str(path), position_ms))
        return original(path, position_ms)

    graph.playback.prepare_for_handover = counted
    played: list[int] = []
    original_play = graph.playback.play

    def counted_play():
        played.append(1)
        return original_play()

    graph.playback.play = counted_play
    try:
        graph.playback.state.status = PlaybackStatus.PLAYING
        graph.playback.state.position_ms = 42_000

        assert graph.playback.reroute_accepted_media() is True
        assert seen == [(str(media), 42_000)]

        _wait_until(lambda: len(bindings.pipelines) >= 2)
        _accept_current(graph, bindings)
        assert _wait_until(lambda: bool(played)), (
            "a live handover must request playback resume"
        )
    finally:
        _close_graph(graph)


def test_ndp_11_handover_keeps_paused_and_stopped_states(qapp, tmp_path) -> None:
    """A paused or stopped track is moved, not started."""
    from michi.domain.playback import PlaybackStatus

    graph, bindings, _media = _handover_graph(qapp, tmp_path)
    try:
        graph.playback.state.status = PlaybackStatus.PAUSED
        graph.playback.state.position_ms = 7_500
        played: list[int] = []
        original_play = graph.playback.play
        graph.playback.play = lambda: played.append(1) or original_play()
        assert graph.playback.reroute_accepted_media() is True
        _wait_until(lambda: len(bindings.pipelines) >= 2)
        _accept_current(graph, bindings)
        QCoreApplication.processEvents()
        assert played == [], "a paused handover must not request playback"
        assert graph.playback.state.status is not PlaybackStatus.PLAYING
    finally:
        _close_graph(graph)


def test_ndp_12_newer_request_supersedes_a_pending_handover(qapp, tmp_path) -> None:
    """A newer request retires the pending handover playback intent."""
    from michi.domain.playback import PlaybackStatus

    graph, bindings, _media = _handover_graph(qapp, tmp_path)
    try:
        graph.playback.state.status = PlaybackStatus.PLAYING
        assert graph.playback.reroute_accepted_media() is True
        assert graph.playback._reroute_resume_playing is True

        newer = tmp_path / "newer.flac"
        graph.playback.load_and_play(newer)
        assert graph.playback._reroute_resume_playing is False, (
            "a newer request supersedes the handover intent"
        )
        _wait_for_pipeline(bindings, graph)
        _accept_current(graph, bindings)
        # The newer request is the one that lands, not the superseded handover.
        assert _wait_until(lambda: graph.playback.state.file_path == newer)
    finally:
        _close_graph(graph)
