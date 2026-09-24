"""DAC-V35-100R1.3.1 — closure integrity corrective gates.

Phase prefixes:

- ``ci131_01_*`` device identity vs output path separation
- ``ci131_02_*`` qualification single-flight under follower timeout
- ``ci131_03_*`` GLib context-command commit authority
- ``ci131_04_*`` GStreamer close first-error-wins + best-effort
- ``ci131_05_*`` tuple-scoped capability presentation
- ``ci131_06_*`` one user intent -> one playback request
- ``ci131_07_*`` authorized container-adaptation relation
"""

from __future__ import annotations

from pathlib import Path

import pytest

from michi.application.audio_output_selection_coordinator import (
    AudioOutputSelectionCoordinator,
)
from tests.dac.test_v35_productive_direct_composition import (
    _close_graph,
    _direct_graph,
)

DEVICE_ID = "usb:2622:0105:DX5ABC123"


def _coordinator(graph) -> AudioOutputSelectionCoordinator:
    return AudioOutputSelectionCoordinator(
        profiles=graph.audio_output_profiles,
        devices=graph.audio_device_registry,
        output_session=graph.output_session,
        engines=graph.audio_engine_service,
    )


def _graph(tmp_path: Path, probe_calls: list[dict] | None = None):
    calls = probe_calls if probe_calls is not None else []

    class _ForbiddenProbe:
        def probe_exact(self, **kwargs):
            calls.append(kwargs)
            raise AssertionError("Shared output must never run an exact ALSA probe")

    return _direct_graph(
        tmp_path,
        qualification_adapter=_ForbiddenProbe(),
        preseed_qualification=False,
    )


# ── Phase 1 — device identity vs output path ───────────────────────────────


def test_ci131_01_a_shared_policy_preserves_selected_dac_identity(
    qapp, tmp_path: Path
) -> None:
    graph, _bindings = _graph(tmp_path)
    coordinator = _coordinator(graph)
    try:
        coordinator.select_shared_output()
        coordinator.select_device(DEVICE_ID)
        coordinator.select_path_mode("strict")
        coordinator.select_path_mode("shared")

        selection = graph.audio_output_profiles.load_selection()
        assert selection.selected_device_id == DEVICE_ID
        assert selection.selected_profile_id is None
        assert graph.output_session.mode == "shared"
        assert graph.output_session.selection_state().selected_device_id == DEVICE_ID
    finally:
        _close_graph(graph)


def test_ci131_01_b_shared_then_strict_keeps_the_same_dac(qapp, tmp_path: Path) -> None:
    graph, _bindings = _graph(tmp_path)
    coordinator = _coordinator(graph)
    try:
        coordinator.select_device(DEVICE_ID)
        coordinator.select_path_mode("compatible")
        coordinator.select_path_mode("shared")
        coordinator.select_path_mode("strict")

        selection = graph.audio_output_profiles.load_selection()
        assert selection.selected_device_id == DEVICE_ID
        profile = next(
            item
            for item in graph.audio_output_profiles.load_profiles()
            if item.profile_id == selection.selected_profile_id
        )
        assert profile.stable_device_id == DEVICE_ID
    finally:
        _close_graph(graph)


def test_ci131_01_c_restart_restores_remembered_dac_and_shared_policy(
    qapp, tmp_path: Path
) -> None:
    graph, _bindings = _graph(tmp_path)
    coordinator = _coordinator(graph)
    try:
        coordinator.select_device(DEVICE_ID)
        coordinator.select_path_mode("strict")
        coordinator.select_path_mode("shared")

        # Fresh coordinator over the same persisted authorities == restart.
        restarted = _coordinator(graph)
        selection = graph.audio_output_profiles.load_selection()
        assert selection.selected_device_id == DEVICE_ID
        assert selection.selected_profile_id is None

        restarted.select_path_mode("strict")
        after = graph.audio_output_profiles.load_selection()
        assert after.selected_device_id == DEVICE_ID
        assert after.selected_profile_id is not None
    finally:
        _close_graph(graph)


def test_ci131_01_d_clearing_the_device_is_an_explicit_intent(
    qapp, tmp_path: Path
) -> None:
    graph, _bindings = _graph(tmp_path)
    coordinator = _coordinator(graph)
    try:
        coordinator.select_device(DEVICE_ID)
        coordinator.select_path_mode("strict")

        coordinator.clear_device_selection()

        selection = graph.audio_output_profiles.load_selection()
        assert selection.selected_device_id is None
        assert selection.selected_profile_id is None
        assert graph.output_session.selection_state().selected_device_id is None
    finally:
        _close_graph(graph)


def test_ci131_01_e_shared_playback_still_bypasses_direct_and_probe(
    qapp, tmp_path: Path
) -> None:
    probe_calls: list[dict] = []
    graph, bindings = _graph(tmp_path, probe_calls)
    coordinator = _coordinator(graph)
    try:
        coordinator.select_device(DEVICE_ID)
        coordinator.select_path_mode("strict")
        coordinator.select_path_mode("shared")

        graph.playback.load_and_play(tmp_path / "shared-after-strict.flac")

        assert graph.output_session.mode == "shared"
        assert graph.output_session.plan is None
        assert graph.direct_output_executor.handle is None
        assert bindings.pipelines[-1].audio_sink is None
        assert probe_calls == []
    finally:
        _close_graph(graph)


# ── Phase 2 — qualification single-flight ──────────────────────────────────


def _await(predicate, *, timeout_s: float = 5.0) -> bool:
    import time

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return bool(predicate())


class _GatedProbe:
    """Exact-open double whose physical body is released by the test."""

    def __init__(self) -> None:
        import threading

        self.calls: list[dict] = []
        self.entered = threading.Event()
        self.release = threading.Event()

    def probe_exact(self, **kwargs):
        from michi.domain.audio_evidence import ExactProbeResult, PcmTuple

        self.calls.append(kwargs)
        self.entered.set()
        self.release.wait(timeout=15)
        requested = PcmTuple(
            kwargs["rate_hz"], kwargs["transport_format"], kwargs["channels"], 16
        )
        return ExactProbeResult(
            requested, requested, "OPENED", None, None, "probe:single-flight"
        )


def _qualification_service(probe, *, follower_timeout_s: float = 10.0, env=None):
    from michi.application.dac_qualification_service import DacQualificationService

    environment = env or (lambda: "env:a")
    return DacQualificationService(
        probe,
        environment_fingerprint=environment,
        single_flight_timeout_s=follower_timeout_s,
    )


def _probe_once(service, *, generation: int | None = None):
    return service.probe_for_play(
        stable_device_id="usb:2622:0105:DX5ABC123",
        locator="hw:CARD=DX5,DEV=0",
        rate_hz=44_100,
        transport_format="S16_LE",
        channels=2,
        binding_generation=generation,
    )


def test_ci131_02_a_one_physical_leader_for_concurrent_equivalent_requests() -> None:
    import threading

    probe = _GatedProbe()
    service = _qualification_service(probe)
    results: list[object] = []

    def worker() -> None:
        results.append(_probe_once(service))

    leader = threading.Thread(target=worker)
    leader.start()
    assert _await(probe.entered.is_set), "the leader never started its physical probe"

    followers = [threading.Thread(target=worker) for _ in range(100)]
    for follower in followers:
        follower.start()
    assert _await(
        lambda: (
            bool(service._flights)
            and next(iter(service._flights.values())).waiters == 100
        )
    ), "followers did not coalesce onto the in-flight qualification"

    probe.release.set()
    leader.join(timeout=15)
    for follower in followers:
        follower.join(timeout=15)

    assert len(probe.calls) == 1
    assert len(results) == 101


def test_ci131_02_b_follower_timeout_never_launches_a_second_probe() -> None:
    import threading

    from michi.application.dac_qualification_service import (
        QualificationSingleFlightTimeoutError,
    )

    probe = _GatedProbe()
    service = _qualification_service(probe, follower_timeout_s=0.2)
    leader_results: list[object] = []
    follower_errors: list[BaseException] = []

    def leader() -> None:
        leader_results.append(_probe_once(service))

    def follower() -> None:
        try:
            _probe_once(service)
        except BaseException as exc:  # noqa: BLE001 — typed assertion below
            follower_errors.append(exc)

    leader_thread = threading.Thread(target=leader)
    leader_thread.start()
    assert _await(probe.entered.is_set)

    followers = [threading.Thread(target=follower) for _ in range(5)]
    for thread in followers:
        thread.start()
    for thread in followers:
        thread.join(timeout=10)

    # The leader is STILL blocked while every follower already timed out.
    assert probe.release.is_set() is False
    assert len(probe.calls) == 1
    assert len(follower_errors) == 5
    assert all(
        isinstance(item, QualificationSingleFlightTimeoutError)
        for item in follower_errors
    )
    assert all(item.code == "EXACT_QUALIFICATION_TIMEOUT" for item in follower_errors)

    probe.release.set()
    leader_thread.join(timeout=15)
    assert len(leader_results) == 1
    assert len(probe.calls) == 1


def test_ci131_02_c_flight_retires_and_a_future_request_can_lead() -> None:
    probe = _GatedProbe()
    probe.release.set()
    service = _qualification_service(probe)

    first = _probe_once(service)
    assert first.evidence.supported is True
    assert service._flights == {}

    second = _probe_once(service)
    assert second.evidence.supported is True
    assert len(probe.calls) == 2


def test_ci131_02_d_binding_generation_change_is_a_different_flight() -> None:
    probe = _GatedProbe()
    probe.release.set()
    service = _qualification_service(probe)

    _probe_once(service, generation=1)
    _probe_once(service, generation=2)

    assert len(probe.calls) == 2


def test_ci131_02_e_environment_change_is_a_different_flight() -> None:
    probe = _GatedProbe()
    probe.release.set()
    environment = {"value": "env:a"}
    service = _qualification_service(probe, env=lambda: environment["value"])

    first = _probe_once(service)
    environment["value"] = "env:b"
    second = _probe_once(service)

    assert len(probe.calls) == 2
    assert (
        first.evidence.environment_fingerprint
        != second.evidence.environment_fingerprint
    )


# ── Phase 3 — GLib context-command commit authority ────────────────────────


class _ManualContext:
    """GLib-like context whose queued callbacks dispatch only on demand."""

    def __init__(self, *, immediate: bool = False) -> None:
        self.immediate = immediate
        self.queued: list = []

    def invoke_full(self, _priority, callback, _user_data) -> None:
        if self.immediate:
            callback(None)
            return
        self.queued.append(callback)

    def dispatch_async(self):
        import threading

        callback = self.queued.pop(0)
        thread = threading.Thread(target=lambda: callback(None), daemon=True)
        thread.start()
        return thread


def _bindings():
    from michi.infrastructure.audio_engines.gstreamer import GStreamerBindings

    return GStreamerBindings()


def _fenced_mutation(command, state, *, generation: int | None):
    """Authoritative mutation that only happens while the command owns it."""

    def body():
        if not command.commit_allowed(current_generation=generation):
            return "blocked"
        state["value"] = "committed"
        return "committed"

    return body


def test_ci131_03_a_pending_timeout_abandons_with_zero_mutation() -> None:
    from michi.infrastructure.audio_engines.gstreamer import (
        ContextCommand,
        ContextCommandState,
        ContextCommandTimeoutError,
    )

    bindings = _bindings()
    context = _ManualContext()
    command = ContextCommand("c-pending", 1)
    mutations: list[str] = []

    with pytest.raises(ContextCommandTimeoutError):
        bindings.invoke_context_sync(
            context,
            lambda: mutations.append("stale"),
            timeout_s=0.05,
            command=command,
        )

    assert command.state is ContextCommandState.ABANDONED
    context.queued[0](None)  # the wedged pump finally dispatches
    assert mutations == []


def test_ci131_03_b_late_running_completion_cannot_commit() -> None:
    import threading

    from michi.infrastructure.audio_engines.gstreamer import (
        ContextCommand,
        ContextCommandState,
        ContextCommandTimeoutError,
    )

    bindings = _bindings()
    context = _ManualContext()
    command = ContextCommand("c-running-late", 1)
    state: dict[str, str] = {}
    started = threading.Event()
    finish = threading.Event()
    generation = {"value": 1}
    errors: list[BaseException] = []

    def body():
        started.set()
        finish.wait(timeout=10)
        return _fenced_mutation(command, state, generation=generation["value"])()

    def caller() -> None:
        try:
            bindings.invoke_context_sync(context, body, timeout_s=0.2, command=command)
        except BaseException as exc:  # noqa: BLE001 — asserted below
            errors.append(exc)

    caller_thread = threading.Thread(target=caller)
    caller_thread.start()
    assert _await(lambda: bool(context.queued))
    dispatcher = context.dispatch_async()
    assert _await(started.is_set)
    caller_thread.join(timeout=10)

    assert len(errors) == 1 and isinstance(errors[0], ContextCommandTimeoutError)
    assert command.state is ContextCommandState.RUNNING
    assert command.commit_authorized is False

    # A newer generation starts and the old body finally finishes.
    generation["value"] = 2
    finish.set()
    dispatcher.join(timeout=10)

    assert state == {}


def test_ci131_03_c_retry_stays_authoritative_after_late_completion() -> None:
    import threading

    from michi.infrastructure.audio_engines.gstreamer import (
        ContextCommand,
        ContextCommandTimeoutError,
    )

    bindings = _bindings()
    context = _ManualContext()
    state: dict[str, str] = {}
    started = threading.Event()
    finish = threading.Event()
    errors: list[BaseException] = []

    stale_command = ContextCommand("c-stale", 1)

    def stale_body():
        started.set()
        finish.wait(timeout=10)
        return _fenced_mutation(stale_command, state, generation=1)()

    def caller() -> None:
        try:
            bindings.invoke_context_sync(
                context, stale_body, timeout_s=0.2, command=stale_command
            )
        except BaseException as exc:  # noqa: BLE001 — asserted below
            errors.append(exc)

    caller_thread = threading.Thread(target=caller)
    caller_thread.start()
    assert _await(lambda: bool(context.queued))
    dispatcher = context.dispatch_async()
    assert _await(started.is_set)
    caller_thread.join(timeout=10)
    assert len(errors) == 1 and isinstance(errors[0], ContextCommandTimeoutError)

    # Retry: a fresh command succeeds and becomes authoritative.
    retry_context = _ManualContext(immediate=True)
    retry_command = ContextCommand("c-retry", 2)
    value = bindings.invoke_context_sync(
        retry_context,
        _fenced_mutation(retry_command, state, generation=2),
        timeout_s=2.0,
        command=retry_command,
    )
    assert value == "committed"
    assert state["value"] == "committed"

    # The stale body finally finishes and must not overwrite the retry.
    finish.set()
    dispatcher.join(timeout=10)
    assert state["value"] == "committed"


def test_ci131_03_d_running_command_that_finishes_in_time_commits() -> None:
    from michi.infrastructure.audio_engines.gstreamer import ContextCommand

    bindings = _bindings()
    context = _ManualContext(immediate=True)
    command = ContextCommand("c-ok", 7)
    state: dict[str, str] = {}

    value = bindings.invoke_context_sync(
        context,
        _fenced_mutation(command, state, generation=7),
        timeout_s=2.0,
        command=command,
    )

    assert value == "committed"
    assert state == {"value": "committed"}


def test_ci131_03_e_generation_change_fences_a_claimed_command() -> None:
    from michi.infrastructure.audio_engines.gstreamer import (
        ContextCommand,
        ContextCommandState,
    )

    command = ContextCommand("c-gen", 4)
    assert command.claim() is True
    assert command.state is ContextCommandState.RUNNING
    assert command.commit_allowed(current_generation=4) is True
    # A newer port generation makes the same claimed command non-authoritative.
    assert command.commit_allowed(current_generation=5) is False
    command.revoke_commit()
    assert command.commit_allowed(current_generation=4) is False


# ── Phase 4 — close: first-error-wins + complete safe best-effort ──────────


class _Executor:
    """Direct-executor double with injectable release failure."""

    def __init__(self, *, fail: bool = False, keep_handle: bool = False) -> None:
        self.handle = "handle" if keep_handle else None
        self.releases: list[str] = []
        self.fail = fail
        self.keep_handle = keep_handle

    def release(self, reason: str) -> None:
        self.releases.append(reason)
        if self.fail:
            raise RuntimeError("synthetic release failure")
        if not self.keep_handle:
            self.handle = None

    def mark_previous_source_released(self) -> None:
        return None

    def abort(self, *_args, **_kwargs):
        return None

    def record_runtime_anomaly(self, *_args, **_kwargs) -> None:
        return None

    def discard_staged_load(self, *_args, **_kwargs) -> None:
        return None


def _port(*, executor=None, timer: bool = False):
    from michi.infrastructure.audio_engines.gstreamer import GStreamerAudioPort
    from tests.test_gstreamer_audio_port import FakeBindings

    bindings = FakeBindings()
    port = GStreamerAudioPort(bindings=bindings, direct_executor=executor)
    if timer:
        port._timer_source = object()
    return bindings, port


def _force_pipeline_error(port, message: str = "pipeline teardown failed") -> None:
    port._teardown_pipeline_terminal = lambda: RuntimeError(message)


def test_ci131_04_a_pipeline_error_wins_and_timer_cleanup_is_attempted() -> None:
    bindings, port = _port(timer=True)
    port._run_on_pump = lambda callback: callback()
    _force_pipeline_error(port)
    bindings.fail_destroy_source = True
    try:
        with pytest.raises(RuntimeError, match="pipeline teardown failed"):
            port.close()

        assert bindings.destroy_source_calls >= 1  # best-effort attempted
        assert port._timer_source is not None  # not cleared without proof
        assert port._closed is False
    finally:
        bindings.fail_destroy_source = False


def test_ci131_04_b_release_is_attempted_after_a_pipeline_error() -> None:
    executor = _Executor(fail=True)
    _bindings_unused, port = _port(executor=executor)
    _force_pipeline_error(port)

    with pytest.raises(RuntimeError, match="pipeline teardown failed"):
        port.close()

    assert executor.releases == ["gstreamer_close"]
    assert port._closed is False


def test_ci131_04_c_timer_error_wins_and_release_is_attempted() -> None:
    executor = _Executor(fail=True)
    bindings, port = _port(executor=executor, timer=True)
    port._run_on_pump = lambda callback: callback()
    bindings.fail_destroy_source = True
    try:
        with pytest.raises(RuntimeError, match="synthetic destroy_source failure"):
            port.close()

        assert executor.releases == ["gstreamer_close"]
        assert port._closed is False
    finally:
        bindings.fail_destroy_source = False


def test_ci131_04_d_pump_timeout_is_first_and_release_still_attempted() -> None:
    executor = _Executor(fail=True)
    bindings, port = _port(executor=executor)
    port._ensure_pump()
    bindings.ignore_quit = True
    try:
        with pytest.raises(RuntimeError, match="pump thread did not terminate"):
            port.close()

        assert executor.releases == ["gstreamer_close"]
        assert port._closed is False
        assert port._pump is not None  # residual ownership retained
    finally:
        bindings.ignore_quit = False
        if not port._closed:
            import contextlib

            with contextlib.suppress(Exception):
                port.close()


def test_ci131_04_e_release_only_failure_is_retryable() -> None:
    executor = _Executor(fail=True)
    _bindings_unused, port = _port(executor=executor)

    with pytest.raises(RuntimeError, match="synthetic release failure"):
        port.close()
    assert port._closed is False
    assert executor.releases == ["gstreamer_close"]

    executor.fail = False
    port.close()
    assert port._closed is True
    assert executor.releases == ["gstreamer_close", "gstreamer_close"]


def test_ci131_04_f_happy_path_closes_fully() -> None:
    executor = _Executor()
    _bindings_unused, port = _port(executor=executor)

    port.close()

    assert port._closed is True
    assert port._closing is False
    assert executor.releases == ["gstreamer_close"]


def test_ci131_04_g_release_that_keeps_a_handle_is_not_a_faked_closure() -> None:
    executor = _Executor(keep_handle=True)
    _bindings_unused, port = _port(executor=executor)

    with pytest.raises(RuntimeError, match="still owns a handle"):
        port.close()

    assert port._closed is False


# ── Phase 5 — tuple-scoped capability presentation ─────────────────────────


def _evidence(supported: bool, *, fmt: str = "S16_LE", bits: int = 16):
    from michi.domain.audio_evidence import (
        CapabilityEvidence,
        EvidenceStrength,
        PcmTuple,
    )

    return CapabilityEvidence(
        stable_device_id="usb:2622:0105:DX5ABC123",
        tuple=PcmTuple(44_100, fmt, 2, bits),
        supported=supported,
        strength=EvidenceStrength.PROBED,
        source="michi-alsa-probe",
        observed_at_ns=1,
        environment_fingerprint="qenv:test",
        evidence_refs=("probe:test",),
    )


def _qualified_graph(evidence, *, failing: bool = False):
    from michi.presentation.audio_output_bridge import AudioOutputBridge
    from tests.test_v35_090_audio_output_bridge import _graph

    graph = _graph()

    class _Qualification:
        def cached_evidence_current(self, _stable_device_id):
            if failing:
                raise RuntimeError("synthetic qualification failure")
            return tuple(evidence)

        def current_environment_fingerprint(self, _stable_device_id):
            return "qenv:test"

    graph.bridge.dispose()
    graph.bridge = AudioOutputBridge(
        graph.volume,
        graph.playback,
        graph.truth,
        devices=graph.devices,
        profiles=graph.profiles,
        output_session=graph.session,
        engines=graph.engines,
        selection_coordinator=graph.coordinator,
        qualification=_Qualification(),
    )
    return graph


def _device_row(graph):
    return next(
        row for row in graph.bridge.devices if row["stableDeviceId"] == graph.stable_id
    )


def test_ci131_05_a_negative_tuple_never_marks_the_dac_unavailable() -> None:
    graph = _qualified_graph([_evidence(False)])

    row = _device_row(graph)

    assert row["connectionLabel"] == "Available"
    assert row["capabilityEvidenceLabel"] != "Unavailable"
    assert row["capabilityEvidenceLabel"] == "Current format unsupported"


def test_ci131_05_b_mixed_evidence_is_partially_qualified() -> None:
    graph = _qualified_graph([_evidence(False), _evidence(True, fmt="S32_LE", bits=32)])

    row = _device_row(graph)

    assert row["connectionLabel"] == "Available"
    assert row["capabilityEvidenceLabel"] == "Partially qualified"


def test_ci131_05_c_positive_evidence_is_qualified() -> None:
    graph = _qualified_graph([_evidence(True, fmt="S32_LE", bits=32)])

    assert _device_row(graph)["capabilityEvidenceLabel"] == "Qualified"


def test_ci131_05_d_disconnected_device_reports_disconnected() -> None:
    graph = _qualified_graph([_evidence(False)])

    graph.devices.ingest(())

    row = _device_row(graph)
    assert row["connectionLabel"] == "Disconnected"
    assert row["available"] is False


def test_ci131_05_e_qualification_failure_degrades_honestly() -> None:
    graph = _qualified_graph([], failing=True)

    row = _device_row(graph)

    assert row["capabilityEvidenceLabel"] == "Evidence unavailable"
    assert row["connectionLabel"] == "Available"


def test_ci131_05_f_direct_compatibility_is_a_third_concept() -> None:
    graph = _qualified_graph([_evidence(False)])
    select_direct = __import__(
        "tests.test_v35_090_audio_output_bridge", fromlist=["_select_direct"]
    )._select_direct
    select_direct(graph)

    graph.playback.state.error_message = "raw copy"
    graph.playback.state.error_code = "EXACT_TUPLE_UNSUPPORTED"
    graph.playback.publish()

    row = _device_row(graph)
    assert row["capabilityEvidenceLabel"] == "Current format unsupported"
    assert row["directCompatibilityLabel"] == "Strict carrier unsupported"
    assert graph.bridge.directCompatibilityLabel == "Strict carrier unsupported"


# ── Phase 6 — one user intent -> one playback request ──────────────────────


class _CountingProbe:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str, int]] = []

    def probe_exact(self, **kwargs):
        from michi.domain.audio_evidence import ExactProbeResult, PcmTuple

        rate_hz = kwargs["rate_hz"]
        transport_format = kwargs["transport_format"]
        channels = kwargs["channels"]
        self.calls.append((rate_hz, transport_format, channels))
        requested = PcmTuple(rate_hz, transport_format, channels, 16)
        if transport_format == "S16_LE":
            return ExactProbeResult(
                requested,
                None,
                "unsupported_format",
                22,
                "exact reject",
                "probe:reject",
            )
        return ExactProbeResult(
            requested,
            PcmTuple(rate_hz, transport_format, channels, 32),
            "OPENED",
            None,
            None,
            "probe:open",
        )


def _cardinality_graph(tmp_path: Path):
    from michi.domain.library import TrackMetadata

    probe = _CountingProbe()
    graph, bindings = _direct_graph(
        tmp_path,
        qualification_adapter=probe,
        preseed_qualification=False,
        source_metadata=TrackMetadata(
            title="S16 source",
            sample_rate_hz=44_100,
            bit_depth=16,
            channels=2,
        ),
    )
    bindings.source_characterization_overrides = {
        "format": "S16LE",
        "rate": 44_100,
        "significant_bits": 16,
        "channels": 2,
    }
    counts = {"session": 0, "load": 0, "prepare": 0}

    # Every session context (SINGLE/ALBUM/PLAYLIST/queue slot) funnels through
    # one canonical transition creator.
    original_request = graph.playback_session._request

    def counted_request(*args, **kwargs):
        counts["session"] += 1
        return original_request(*args, **kwargs)

    graph.playback_session._request = counted_request

    original_load = graph.playback.load_and_play

    def counted_load(*args, **kwargs):
        counts["load"] += 1
        return original_load(*args, **kwargs)

    graph.playback.load_and_play = counted_load

    original_prepare = graph.output_session.prepare_for_media_async

    def counted_prepare(*args, **kwargs):
        counts["prepare"] += 1
        return original_prepare(*args, **kwargs)

    graph.output_session.prepare_for_media_async = counted_prepare
    return graph, bindings, probe, counts


def _seed_library(graph, media: Path) -> str:
    """Seed one visible library track and return its track id."""
    from michi.domain.library import MediaAvailability, TrackRef

    track_id = "track-1"
    # TD-013 validates the filesystem before any library-origin playback.
    media.parent.mkdir(parents=True, exist_ok=True)
    media.write_bytes(b"michi-r131-seed")
    graph.library._state.tracks = [
        TrackRef(
            media,
            title="Seeded",
            artist="Artist",
            album="Album",
            track_id=track_id,
            media_file_id="media-1",
            library_source_id="source-1",
            availability=MediaAvailability.AVAILABLE,
        )
    ]
    graph.library._rebuild_derived_library_state()
    return track_id


def _assert_single_intent(
    graph,
    probe,
    counts,
    *,
    expected_probes: int = 1,
    expected_session: int = 1,
) -> None:
    assert _await(lambda: len(probe.calls) >= expected_probes), (
        "the physical qualification never completed"
    )
    # A replay is not a new semantic context, so it legitimately opens no new
    # session transition; what must never happen is fan-out.
    assert counts["session"] == expected_session, (
        "one user intent must produce one session request"
    )
    assert counts["load"] == 1, "one user intent must produce one playback load"
    assert counts["prepare"] == 1, "one user intent must produce one preparation"
    # At most ONE physical qualification per carrier key — never a sweep.
    assert len(probe.calls) == expected_probes
    assert graph.output_session.mode == "shared"


def test_ci131_06_a_song_row_intent_is_one_request(qapp, tmp_path: Path) -> None:
    media = tmp_path / "song-row.flac"
    graph, _bindings, probe, counts = _cardinality_graph(tmp_path)
    track_id = _seed_library(graph, media)
    try:
        graph.library_playback.play_track_by_id(track_id, "Song row")
        assert _await(lambda: counts["load"] == 1)
        _assert_single_intent(graph, probe, counts)
    finally:
        _close_graph(graph)


def test_ci131_06_b_album_track_intent_is_one_request(qapp, tmp_path: Path) -> None:
    from michi.domain.library import build_music_model

    media = tmp_path / "album-track.flac"
    graph, _bindings, probe, counts = _cardinality_graph(tmp_path)
    _seed_library(graph, media)
    album_key = build_music_model(graph.library.state.tracks).albums[0].key
    try:
        graph.library_playback.play_album_track(album_key, 0)
        assert _await(lambda: counts["load"] == 1)
        _assert_single_intent(graph, probe, counts)
    finally:
        _close_graph(graph)


def test_ci131_06_c_playlist_track_intent_is_one_request(qapp, tmp_path: Path) -> None:
    from michi.domain.playback_session import PlaybackSequenceEntry

    media = tmp_path / "playlist-track.flac"
    graph, _bindings, probe, counts = _cardinality_graph(tmp_path)
    try:
        graph.playlist_playback.play_playlist_entries(
            "playlist-1",
            [PlaybackSequenceEntry(media, "Playlist track")],
            0,
        )
        assert _await(lambda: counts["load"] == 1)
        _assert_single_intent(graph, probe, counts)
    finally:
        _close_graph(graph)


def test_ci131_06_d_search_result_intent_is_one_request(qapp, tmp_path: Path) -> None:
    media = tmp_path / "search-result.flac"
    graph, _bindings, probe, counts = _cardinality_graph(tmp_path)
    track_id = _seed_library(graph, media)
    try:
        graph.library.search("Seeded")
        visible = graph.library.visible_tracks()
        assert visible, "the seeded track must be visible after search"
        graph.library_playback.play_track_by_id(track_id, "Search result")
        assert _await(lambda: counts["load"] == 1)
        _assert_single_intent(graph, probe, counts)
    finally:
        _close_graph(graph)


def test_ci131_06_e_queue_entry_intent_is_one_request(qapp, tmp_path: Path) -> None:
    from michi.presentation.playback_session_bridge import PlaybackSessionBridge

    media = tmp_path / "queue-entry.flac"
    graph, _bindings, probe, counts = _cardinality_graph(tmp_path)
    bridge = PlaybackSessionBridge(graph.playback_session)
    try:
        graph.queue.add(media, "Queue entry")
        bridge.play_queue_index(0)
        assert _await(lambda: counts["load"] == 1)
        _assert_single_intent(graph, probe, counts)
    finally:
        bridge.dispose()
        _close_graph(graph)


def test_ci131_06_f_now_playing_play_intent_is_one_request(
    qapp, tmp_path: Path
) -> None:
    from michi.presentation.playback_bridge import PlaybackBridge

    media = tmp_path / "now-playing.flac"
    graph, _bindings, probe, counts = _cardinality_graph(tmp_path)
    bridge = PlaybackBridge(graph.playback)
    try:
        # The public replay case: a stopped logical source re-enters the
        # canonical load path through the bridge.
        graph.playback._state.file_path = media
        graph.playback._accepted = False
        bridge.play()
        assert _await(lambda: counts["load"] == 1)
        _assert_single_intent(graph, probe, counts, expected_session=0)
    finally:
        bridge.dispose()
        _close_graph(graph)


# ── Phase 7 — authorized container-adaptation relation ─────────────────────


def _truth(
    *,
    decoded,
    requested,
    engine=None,
    alsa=None,
    plan_id: str = "plan:r131",
    resampling: bool = False,
    remix: bool = False,
):
    from michi.domain.signal_truth import (
        AlsaRuntimeEvidence,
        DecodedRuntimeEvidence,
        EngineRuntimeEvidence,
        OutputPlanEvidence,
        SignalTruthIdentity,
        SignalTruthRecorder,
    )

    identity = SignalTruthIdentity(plan_id, 1, 1, 1, "usb:dac", "ep:0")
    recorder = SignalTruthRecorder()
    recorder.begin_candidate(
        OutputPlanEvidence(identity, requested, "alsasink", "hw:CARD=X,DEV=0", True)
    )
    recorder.observe(DecodedRuntimeEvidence(identity, decoded))
    recorder.observe(
        EngineRuntimeEvidence(
            identity=identity,
            effective_pcm=engine if engine is not None else requested,
            sink_factory="alsasink",
            sink_device="hw:CARD=X,DEV=0",
            graph_factories=("flacdec", "audioconvert", "capsfilter", "alsasink"),
            graph_inspection_complete=True,
            software_gain=1.0,
            muted=False,
            sink_provides_clock=True,
            sink_clock_is_pipeline_clock=True,
            slave_method="none",
            resampling_observed=resampling,
            remix_observed=remix,
        )
    )
    recorder.observe(
        AlsaRuntimeEvidence(
            identity=identity,
            negotiated_pcm=alsa if alsa is not None else requested,
            access="RW_INTERLEAVED",
            subformat="STD",
            period_size=1024,
            buffer_size=4096,
            proc_path="/proc/asound/card1/pcm0p/sub0/hw_params",
            locator="hw:CARD=X,DEV=0",
        )
    )
    return recorder.candidate_snapshot


def test_ci131_07_a_authorized_sixteen_bit_widening_is_adapted() -> None:
    from michi.domain.audio_evidence import PcmTuple
    from michi.domain.signal_truth import SignalTruthReason, SignalTruthVerdict

    snapshot = _truth(
        decoded=PcmTuple(44_100, "S16_LE", 2, 16),
        requested=PcmTuple(44_100, "S32_LE", 2, 16),
        engine=PcmTuple(44_100, "S32_LE", 2, 16),
        alsa=PcmTuple(44_100, "S32_LE", 2, 16),
    )

    assert snapshot.verdict is SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED
    assert snapshot.reasons == (SignalTruthReason.ST_CONTAINER_ADAPTED,)


def test_ci131_07_b_narrowing_is_never_an_authorized_adaptation() -> None:
    from michi.domain.audio_evidence import PcmTuple
    from michi.domain.signal_truth import SignalTruthVerdict

    snapshot = _truth(
        decoded=PcmTuple(44_100, "S32_LE", 2, 16),
        requested=PcmTuple(44_100, "S16_LE", 2, 16),
        engine=PcmTuple(44_100, "S16_LE", 2, 16),
        alsa=PcmTuple(44_100, "S16_LE", 2, 16),
    )

    assert snapshot.verdict is not SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED
    assert snapshot.verdict is SignalTruthVerdict.DSP


def test_ci131_07_c_significant_bits_mismatch_is_never_adapted() -> None:
    from michi.domain.audio_evidence import PcmTuple
    from michi.domain.signal_truth import SignalTruthVerdict

    snapshot = _truth(
        decoded=PcmTuple(44_100, "S16_LE", 2, 16),
        requested=PcmTuple(44_100, "S32_LE", 2, 24),
        engine=PcmTuple(44_100, "S32_LE", 2, 24),
        alsa=PcmTuple(44_100, "S32_LE", 2, 24),
    )

    # R110R1 PRESERVATION SEMANTIC UPDATE
    # Old invariant: a requested-carrier/decoded width mismatch stays UNKNOWN.
    # Why superseded: the plan requested a width the decoded signal does not
    #   prove — a contradiction between declared intent and proven signal, so it
    #   is REFUTED rather than merely unknown. Never adapted is preserved.
    # Canonical authority: §297 (declared intent vs proven width) with the
    #   established contradiction vocabulary (§296).
    # New invariant: CONTRADICTED, never DIRECT_CONTAINER_ADAPTED.
    assert snapshot.verdict is not SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED
    assert snapshot.verdict is SignalTruthVerdict.CONTRADICTED


def test_ci131_07_d_observed_resampling_is_resampled() -> None:
    from michi.domain.audio_evidence import PcmTuple
    from michi.domain.signal_truth import SignalTruthVerdict

    pcm = PcmTuple(44_100, "S16_LE", 2, 16)
    snapshot = _truth(
        decoded=pcm,
        requested=pcm,
        engine=pcm,
        alsa=pcm,
        resampling=True,
    )

    assert snapshot.verdict is SignalTruthVerdict.RESAMPLED


def test_ci131_07_e_observed_channel_transform_is_remixed() -> None:
    from michi.domain.audio_evidence import PcmTuple
    from michi.domain.signal_truth import SignalTruthVerdict

    pcm = PcmTuple(44_100, "S16_LE", 2, 16)
    snapshot = _truth(
        decoded=pcm,
        requested=pcm,
        engine=pcm,
        alsa=pcm,
        remix=True,
    )

    assert snapshot.verdict is SignalTruthVerdict.REMIXED


def test_ci131_07_g_rate_contradiction_is_never_adapted() -> None:
    from michi.domain.audio_evidence import PcmTuple
    from michi.domain.signal_truth import SignalTruthVerdict

    snapshot = _truth(
        decoded=PcmTuple(44_100, "S16_LE", 2, 16),
        requested=PcmTuple(48_000, "S16_LE", 2, 16),
        engine=PcmTuple(48_000, "S16_LE", 2, 16),
        alsa=PcmTuple(48_000, "S16_LE", 2, 16),
    )

    assert snapshot.verdict is SignalTruthVerdict.CONTRADICTED


def test_ci131_07_f_unlisted_format_pair_is_not_adapted() -> None:
    from michi.domain.audio_evidence import PcmTuple
    from michi.domain.signal_truth import SignalTruthVerdict

    # S24_3LE -> S16LE is neither an authorized widening pair nor a lossless
    # container relation for 16 proven bits.
    snapshot = _truth(
        decoded=PcmTuple(44_100, "S24_3LE", 2, 16),
        requested=PcmTuple(44_100, "S16_LE", 2, 16),
        engine=PcmTuple(44_100, "S16_LE", 2, 16),
        alsa=PcmTuple(44_100, "S16_LE", 2, 16),
    )

    assert snapshot.verdict is not SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED
