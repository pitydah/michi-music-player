"""AP2-F08 — Native DSD session transaction and truth events."""

from __future__ import annotations

from pathlib import Path

from michi.application.audio_output_planner import OutputPlanner
from michi.application.dsd_output_planner import (
    AlsaDsdTuple,
    NativeDsdPlanner,
    NativeDsdQualification,
)
from michi.application.output_session_service import (
    NativeDsdSessionPrepared,
    OutputRequest,
    OutputSessionService,
)
from michi.domain.audio_output import OutputSessionState
from michi.domain.dsd_signal import (
    AlsaDsdGrouping,
    DsdBitOrder,
    DsdOrganization,
    DsdPacking,
    DsdSignalFormat,
)
from michi.domain.signal_truth import OutputFamilyState, SignalTruthRecorder

DEVICE = "usb:152a:85dd"
LOCATOR = "hw:3,0"


def _plan():
    source = DsdSignalFormat(
        bit_rate_hz=2_822_400,
        channels=2,
        packing=DsdPacking.DSD_U8,
        bit_order=DsdBitOrder.MSBF,
        organization=DsdOrganization.PLANAR,
        layout=("FL", "FR"),
    )
    requested = AlsaDsdTuple(
        format_name=AlsaDsdGrouping.DSD_U32_BE.alsa_format_name,
        frame_rate_hz=88_200,
        channels=2,
        sample_width_bits=32,
        source_bits_per_second_per_channel=2_822_400,
    )
    return NativeDsdPlanner().plan(
        stable_device_id=DEVICE,
        binding_locator=LOCATOR,
        binding_generation=1,
        source=source,
        qualifications=(
            NativeDsdQualification(
                stable_device_id=DEVICE,
                binding_generation=1,
                requested=requested,
                supported=True,
                evidence_ref="alsa-dsd:test",
            ),
        ),
        execution_id="exec:session",
        source_proven=True,
        active_engine_id="gstreamer",
    )


class _Provider:
    def __init__(self, plan) -> None:
        self.plan = plan

    def __call__(self, path: Path) -> OutputRequest:
        return OutputRequest.native_dsd(self.plan, DEVICE, "profile:direct")


class _Callbacks:
    def __init__(self) -> None:
        self.prepared: list[NativeDsdSessionPrepared] = []
        self.committed: list[NativeDsdSessionPrepared] = []
        self.aborted: list[tuple[NativeDsdSessionPrepared, str]] = []
        self.stopped: list[tuple[NativeDsdSessionPrepared, str]] = []

    def prepare(self, plan, path, instance_id):
        prepared = NativeDsdSessionPrepared(
            plan=plan,
            execution_id=plan.execution_id,
            stable_device_id=plan.stable_device_id,
            runtime_identity={"host_generation": 1, "sink": "alsasink"},
            evidence_refs=plan.evidence_refs,
            handle=object(),
        )
        self.prepared.append(prepared)
        return prepared

    def commit(self, prepared):
        self.committed.append(prepared)

    def abort(self, prepared, reason):
        self.aborted.append((prepared, reason))

    def stop(self, prepared, reason):
        self.stopped.append((prepared, reason))


def _service(plan=None, *, recorder=None, callbacks=None):
    plan = plan or _plan()
    callbacks = callbacks or _Callbacks()
    service = OutputSessionService(
        OutputPlanner(),
        request_provider=_Provider(plan),
        async_submit=None,
        native_dsd_prepare=callbacks.prepare,
        native_dsd_commit=callbacks.commit,
        native_dsd_abort=callbacks.abort,
        native_dsd_stop=callbacks.stop,
        native_dsd_plan_still_current=lambda _plan: True,
        truth_recorder=recorder,
    )
    return service, callbacks


def test_native_prepare_commit_release_and_truth() -> None:
    recorder = SignalTruthRecorder()
    service, callbacks = _service(recorder=recorder)
    path = Path("/tmp/source.dsf")
    token = service.prepare_for_media(path)
    assert service.mode == "native_dsd"
    assert service.state is OutputSessionState.READY
    assert service.native_dsd_active is True
    assert service.active_device_id == DEVICE
    assert service.active_execution_id == "exec:session"
    assert len(callbacks.prepared) == 1
    assert [e.state for e in recorder.output_family_events] == [OutputFamilyState.READY]

    service.commit_media(token, path)
    assert service.state is OutputSessionState.RUNNING
    assert [e.state for e in recorder.output_family_events] == [
        OutputFamilyState.READY,
        OutputFamilyState.RUNNING,
    ]

    service.release_active("stop")
    assert service.state is OutputSessionState.IDLE
    assert service.native_dsd_active is False
    assert callbacks.stopped and callbacks.stopped[0][1] == "stop"
    assert recorder.output_family_events[-1].state is OutputFamilyState.RELEASED


def test_native_abort_retires_the_candidate() -> None:
    recorder = SignalTruthRecorder()
    service, callbacks = _service(recorder=recorder)
    path = Path("/tmp/source.dsf")
    token = service.prepare_for_media(path)
    service.abort_media(token, "cancelled")
    assert service.state is OutputSessionState.IDLE
    assert service.native_dsd_active is False
    assert callbacks.aborted[0][1] == "cancelled"
    assert recorder.output_family_events[-1].state is OutputFamilyState.UNAVAILABLE


def test_native_supersession_aborts_the_previous_candidate() -> None:
    service, callbacks = _service()
    path = Path("/tmp/source.dsf")
    first = service.prepare_for_media(path)
    second = service.prepare_for_media(path)
    assert first != second
    assert len(callbacks.aborted) == 1
    assert callbacks.prepared[-1].execution_id == "exec:session"
    assert service.active_execution_id == "exec:session"


def test_native_host_loss_records_unavailable_without_forging_stop() -> None:
    recorder = SignalTruthRecorder()
    service, _callbacks = _service(recorder=recorder)
    path = Path("/tmp/source.dsf")
    service.prepare_for_media(path)
    service.notify_host_lost("host gone")
    assert recorder.output_family_events[-1].state is OutputFamilyState.UNAVAILABLE
    assert service.state is OutputSessionState.READY


def test_native_device_loss_retires_the_session() -> None:
    service, callbacks = _service()
    path = Path("/tmp/source.dsf")
    service.prepare_for_media(path)
    service.device_lost(DEVICE, 1)
    assert callbacks.aborted and callbacks.aborted[0][1] == "device_lost"
    assert service.state is OutputSessionState.IDLE
    assert service.native_dsd_active is False


def test_native_prepare_is_async_and_keeps_the_same_mode() -> None:
    service, callbacks = _service()
    path = Path("/tmp/source.dsf")
    prepared: list[str] = []
    failures: list[Exception] = []
    service.prepare_for_media_async(path, prepared.append, failures.append)
    assert failures == []
    assert prepared
    assert service.mode == "native_dsd"
    assert service.state is OutputSessionState.READY
    assert callbacks.prepared
