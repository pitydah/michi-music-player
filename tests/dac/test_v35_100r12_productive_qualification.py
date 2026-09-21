"""DAC-V35-100R1.2 productive exact-qualification gates."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest
from conftest import FakeAudioPort

from michi.application.dac_qualification_service import DacQualificationService
from michi.application.playback_service import PlaybackService
from michi.domain.audio_evidence import (
    CapabilityEvidence,
    EvidenceStrength,
    ExactProbeResult,
    PcmTuple,
)
from michi.domain.library import TrackMetadata


class _Cache:
    def __init__(self, evidence=()) -> None:
        self.evidence = tuple(evidence)

    def load_qualification_cache(self, _stable_device_id):
        return self.evidence

    def replace_qualification_cache(self, _stable_device_id, evidence):
        self.evidence = tuple(evidence)


class _Probe:
    def __init__(self, result: ExactProbeResult) -> None:
        self.result = result

    def probe_exact(self, **_kwargs):
        return self.result


class _ChangingEnvironmentProbe(_Probe):
    def __init__(self, result: ExactProbeResult, change_environment) -> None:
        super().__init__(result)
        self._change_environment = change_environment

    def probe_exact(self, **kwargs):
        self._change_environment()
        return super().probe_exact(**kwargs)


def _evidence(rate_hz: int) -> CapabilityEvidence:
    return CapabilityEvidence(
        stable_device_id="usb:dac",
        tuple=PcmTuple(rate_hz, "S16_LE", 2, 16),
        supported=True,
        strength=EvidenceStrength.OPENED,
        source="michi-alsa-probe",
        observed_at_ns=1,
        environment_fingerprint="current",
        evidence_refs=(f"probe:{rate_hz}",),
    )


def test_q100r12_03_qualifying_tuple_b_preserves_current_tuple_a() -> None:
    requested = PcmTuple(48_000, "S16_LE", 2, 16)
    cache = _Cache((_evidence(44_100),))
    service = DacQualificationService(
        _Probe(ExactProbeResult(requested, requested, "OPENED", None, None, "B")),
        cache=cache,
        environment_fingerprint=lambda: "current",
    )

    service.qualify_and_cache(
        stable_device_id="usb:dac",
        locator="hw:1,0",
        rate_hz=48_000,
        transport_format="S16_LE",
        channels=2,
    )

    assert [item.tuple.rate_hz for item in cache.evidence] == [44_100, 48_000]


def test_q100r12_06_environment_change_during_probe_never_caches_claim() -> None:
    requested = PcmTuple(48_000, "S16_LE", 2, 16)
    environment = ["before"]
    cache = _Cache((_evidence(44_100),))
    service = DacQualificationService(
        _ChangingEnvironmentProbe(
            ExactProbeResult(requested, requested, "OPENED", None, None, "moving"),
            lambda: environment.__setitem__(0, "after"),
        ),
        cache=cache,
        environment_fingerprint=lambda: environment[0],
    )

    result = service.qualify_and_cache(
        stable_device_id="usb:dac",
        locator="hw:1,0",
        rate_hz=48_000,
        transport_format="S16_LE",
        channels=2,
    )

    assert result.supported is None
    assert result.evidence_refs[-1] == "environment_changed"
    assert cache.evidence == (_evidence(44_100),)


class _AsyncOutputTransaction:
    mode = "shared"
    volume_policy = None
    release_invalidates_media = False

    def __init__(self) -> None:
        self.requests = []
        self.aborted = []

    def prepare_for_media_async(self, path, on_prepared, on_failed):
        self.requests.append((path, on_prepared, on_failed))

    def prepare_for_media(self, _path):  # pragma: no cover - forbidden path
        raise AssertionError("synchronous preparation must not run")

    def abort_media(self, token, reason):
        self.aborted.append((token, reason))

    def commit_media(self, _token, _path):
        return None

    def release_active(self, _reason):
        return None


def test_q100r12_01_async_output_prepare_resumes_exactly_once() -> None:
    audio = FakeAudioPort()
    output = _AsyncOutputTransaction()
    playback = PlaybackService(audio, output_tx=output)
    source = Path("/music/fresh.mp3")

    playback.load_and_play(source)

    assert audio.loaded is None
    assert len(output.requests) == 1
    _path, on_prepared, _on_failed = output.requests[0]
    on_prepared("output:1")

    assert audio.loaded == source
    assert audio.state == "playing"


def test_q100r12_07_superseded_async_completion_never_loads_old_media() -> None:
    audio = FakeAudioPort()
    output = _AsyncOutputTransaction()
    playback = PlaybackService(audio, output_tx=output)
    first = Path("/music/a.mp3")
    second = Path("/music/b.flac")

    playback.load_and_play(first)
    playback.load_and_play(second)
    output.requests[0][1]("output:a")
    output.requests[1][1]("output:b")

    assert output.aborted == [("output:a", "superseded")]
    assert audio.loaded == second


def test_unexpected_async_prepare_error_clears_pending_before_reraising() -> None:
    audio = FakeAudioPort()
    output = _AsyncOutputTransaction()
    playback = PlaybackService(audio, output_tx=output)

    playback.load_and_play(Path("/music/broken.flac"))
    with pytest.raises(RuntimeError, match="programming defect"):
        output.requests[0][2](RuntimeError("programming defect"))

    assert playback._pending_path is None
    assert playback._intent is False


class _OpeningProbe:
    def __init__(self) -> None:
        self.calls = []

    def probe_exact(self, **kwargs):
        self.calls.append((threading.get_ident(), kwargs))
        requested = PcmTuple(
            kwargs["rate_hz"], kwargs["transport_format"], kwargs["channels"], 16
        )
        return ExactProbeResult(
            requested, requested, "OPENED", None, None, "probe:fresh-play"
        )


class _DispositionProbe(_OpeningProbe):
    def __init__(self, disposition: str) -> None:
        super().__init__()
        self.disposition = disposition

    def probe_exact(self, **kwargs):
        opened = super().probe_exact(**kwargs)
        if self.disposition == "OPENED":
            return opened
        return ExactProbeResult(
            opened.requested,
            None,
            self.disposition,
            16 if self.disposition == "device_busy" else 22,
            self.disposition,
            f"probe:{self.disposition}",
        )


def _process_until(predicate, timeout_s: float = 2.0) -> None:
    from PySide6.QtCore import QCoreApplication

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline and not predicate():
        QCoreApplication.processEvents()
        time.sleep(0.01)
    assert predicate()


def test_q100r12_02_fresh_productive_play_qualifies_off_owner_and_reuses_cache(
    qapp,
    tmp_path: Path,
) -> None:
    from PySide6.QtCore import QCoreApplication

    from tests.dac.test_v35_productive_direct_composition import (
        _accept_current,
        _close_graph,
        _direct_graph,
    )

    probe = _OpeningProbe()
    metadata = TrackMetadata(
        title="Fresh MP3",
        container="mp3",
        codec="MP3",
        sample_rate_hz=44_100,
        bit_depth=0,
        channels=2,
    )
    graph, bindings = _direct_graph(
        tmp_path,
        source_metadata=metadata,
        preseed_qualification=False,
        qualification_adapter=probe,
    )
    bindings.source_characterization_overrides = {
        "format": "S16LE",
        "rate": 44_100,
        "channels": 2,
    }
    owner_thread = threading.get_ident()

    try:
        graph.playback.load_and_play(tmp_path / "fresh.mp3")
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and not bindings.pipelines:
            QCoreApplication.processEvents()
            time.sleep(0.01)

        assert len(probe.calls) == 1
        assert probe.calls[0][0] != owner_thread
        assert bindings.pipelines, graph.playback.state.error_message
        _accept_current(graph, bindings)

        graph.playback.load_and_play(tmp_path / "cached.mp3")
        assert len(probe.calls) == 1
    finally:
        _close_graph(graph)


@pytest.mark.parametrize(
    ("disposition", "expected_message"),
    [
        ("unsupported_format", "Format unsupported:"),
        ("device_busy", "Device busy:"),
    ],
)
def test_q100r12_04_05_probe_refusals_are_contained_before_backend(
    qapp,
    tmp_path: Path,
    disposition: str,
    expected_message: str,
) -> None:
    from tests.dac.test_v35_productive_direct_composition import (
        _close_graph,
        _direct_graph,
    )

    probe = _DispositionProbe(disposition)
    graph, bindings = _direct_graph(
        tmp_path,
        preseed_qualification=False,
        qualification_adapter=probe,
    )
    try:
        graph.playback.load_and_play(tmp_path / "refused.flac")
        _process_until(lambda: graph.playback.state.error_message is not None)

        assert graph.playback.state.error_message.startswith(expected_message)
        assert len(probe.calls) == 1
        assert bindings.pipelines == []
        assert graph.direct_output_executor.handle is None
        cached = graph.dac_qualification.cached_evidence("usb:2622:0105:DX5ABC123")
        if disposition == "device_busy":
            assert cached == ()
        else:
            assert len(cached) == 1 and cached[0].supported is False
    finally:
        _close_graph(graph)


class _BlockingProbe(_OpeningProbe):
    def __init__(self) -> None:
        super().__init__()
        self.started = threading.Event()
        self.release = threading.Event()

    def probe_exact(self, **kwargs):
        self.started.set()
        assert self.release.wait(2.0)
        return super().probe_exact(**kwargs)


class _FirstRateBlockingProbe(_OpeningProbe):
    def __init__(self, blocked_rate: int) -> None:
        super().__init__()
        self.blocked_rate = blocked_rate
        self.started = threading.Event()
        self.release = threading.Event()

    def probe_exact(self, **kwargs):
        if kwargs["rate_hz"] == self.blocked_rate:
            self.started.set()
            assert self.release.wait(2.0)
        return super().probe_exact(**kwargs)


def test_q100r12_08_stop_invalidates_inflight_probe_continuation(
    qapp,
    tmp_path: Path,
) -> None:
    from tests.dac.test_v35_productive_direct_composition import (
        _close_graph,
        _direct_graph,
    )

    probe = _BlockingProbe()
    graph, bindings = _direct_graph(
        tmp_path,
        preseed_qualification=False,
        qualification_adapter=probe,
    )
    try:
        graph.playback.load_and_play(tmp_path / "stopped.flac")
        assert probe.started.wait(1.0)
        graph.playback.stop()
        probe.release.set()
        _process_until(lambda: len(probe.calls) == 1)
        for _ in range(5):
            from PySide6.QtCore import QCoreApplication

            QCoreApplication.processEvents()

        assert bindings.pipelines == []
        assert graph.direct_output_executor.handle is None
        assert graph.dac_qualification.cached_evidence("usb:2622:0105:DX5ABC123") == ()
    finally:
        probe.release.set()
        _close_graph(graph)


def test_q100r12_07_new_play_supersedes_old_probe_without_stale_cache(
    qapp,
    tmp_path: Path,
) -> None:
    from tests.dac.test_v35_productive_direct_composition import (
        _close_graph,
        _direct_graph,
        _wait_for_pipeline_count,
    )

    probe = _FirstRateBlockingProbe(44_100)
    graph, bindings = _direct_graph(
        tmp_path,
        preseed_qualification=False,
        qualification_adapter=probe,
    )
    try:
        bindings.source_characterization_overrides = {
            "format": "S16LE",
            "rate": 44_100,
            "channels": 2,
        }
        graph.playback.load_and_play(tmp_path / "old.mp3")
        assert probe.started.wait(1.0)

        bindings.source_characterization_overrides = {
            "format": "S16LE",
            "rate": 48_000,
            "channels": 2,
        }
        graph.playback.load_and_play(tmp_path / "new.flac")
        _wait_for_pipeline_count(bindings, 1)
        probe.release.set()
        _process_until(lambda: len(probe.calls) == 2)
        for _ in range(5):
            qapp.processEvents()

        assert len(bindings.pipelines) == 1
        assert graph.output_session.plan.requested_pcm.rate_hz == 48_000
        cached_rates = {
            item.tuple.rate_hz
            for item in graph.dac_qualification.cached_evidence(
                "usb:2622:0105:DX5ABC123"
            )
        }
        assert cached_rates == {48_000}
    finally:
        probe.release.set()
        _close_graph(graph)


def test_q100r12_09_device_loss_invalidates_inflight_probe(
    qapp,
    tmp_path: Path,
) -> None:
    from tests.dac.test_v35_productive_direct_composition import (
        _close_graph,
        _direct_graph,
    )

    probe = _BlockingProbe()
    graph, bindings = _direct_graph(
        tmp_path,
        preseed_qualification=False,
        qualification_adapter=probe,
    )
    try:
        graph.playback.load_and_play(tmp_path / "lost.flac")
        assert probe.started.wait(1.0)
        graph.audio_device_registry.handle_removed("2-1")
        probe.release.set()
        _process_until(lambda: len(probe.calls) == 1)
        for _ in range(5):
            qapp.processEvents()

        assert bindings.pipelines == []
        assert graph.direct_output_executor.handle is None
        assert graph.dac_qualification.cached_evidence("usb:2622:0105:DX5ABC123") == ()
    finally:
        probe.release.set()
        _close_graph(graph)
