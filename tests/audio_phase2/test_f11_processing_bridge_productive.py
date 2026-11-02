"""F11 productive proof: the quick EQ bridge commits through the real DSP owner.

The QML EQ surface owns only a draft. Applying it must delegate to the canonical
``AudioProcessingService`` over the real hosted GStreamer port, and the bridge
must publish EFFECTIVE only from the service readback. This test uses the lab
sink, so it proves the bridge transaction and readback, not a physical DAC.
"""

from __future__ import annotations

import importlib.util
import time
from pathlib import Path

import pytest

_HAS_GI = importlib.util.find_spec("gi") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_GI, reason="PyGObject/GStreamer not available on this host"
)

FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "evidence/dac-v35-110/2026-09-25-smsl-152a85dd-operator-run"
    / "fixtures/pcm16_44100.wav"
)


class _InlineExecutor:
    def submit(self, work, completed) -> None:
        try:
            value = work()
        except Exception as exc:  # noqa: BLE001 - typed completion boundary
            completed(None, exc)
        else:
            completed(value, None)


def _wait_until(predicate, *, timeout: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def _build_graph(tmp_path):
    from michi.bootstrap import _build_services
    from tests.conftest import FakeAudioPort

    return _build_services(
        tmp_path / "michi.db",
        backend=FakeAudioPort(),
        output_preparation_executor=_InlineExecutor(),
    )


def test_quick_eq_applies_and_bypasses_through_the_productive_chain(
    tmp_path, monkeypatch
) -> None:
    if not FIXTURE.is_file():
        pytest.skip("PCM fixture unavailable")
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")

    from michi.domain.audio_signal import ChannelLayout, PcmSignalFormat
    from michi.presentation.audio_processing_bridge import AudioProcessingBridge

    graph = _build_graph(tmp_path)
    port = graph.gstreamer_engine_provider.open()
    try:
        port.set_volume(0)
        port.load(FIXTURE)
        deadline = time.monotonic() + 30.0
        while not port.backend_state() and time.monotonic() < deadline:
            port.dispatch_pending()
            time.sleep(0.02)

        signal = PcmSignalFormat(
            rate_hz=44_100,
            transport_format="S16LE",
            significant_bits=16,
            layout=ChannelLayout(positions=("FL", "FR")),
        )
        bridge = AudioProcessingBridge(
            graph.audio_processing,
            signal_provider=lambda: signal,
            async_submit=_InlineExecutor().submit,
        )
        bridge.set_draft_band(0, 6.0)
        bridge.set_draft_preamp(-2.0)
        bridge.apply_draft_async()

        assert _wait_until(
            lambda: (
                not bridge.busy
                and graph.audio_processing.effective_state.value == "effective"
            )
        ), "the quick EQ never became effective"
        assert bridge.errorCode == ""
        assert bridge.effectiveState == "effective"
        assert bridge.bypassEffective is False
        truth = bridge.truth
        assert truth["effective_state"] == "effective"
        assert truth["bit_perfect"] is False
        assert graph.audio_processing.effective_revision >= 1

        bridge.set_bypass_requested(True)
        bridge.apply_draft_async()
        assert _wait_until(
            lambda: (
                not bridge.busy
                and graph.audio_processing.effective_state.value == "bypassed"
            )
        ), "the quick EQ bypass never became confirmed"
        assert bridge.errorCode == ""
        assert bridge.effectiveState == "bypassed"
        assert bridge.bypassEffective is True
        assert bridge.truth["bit_perfect"] is None
    finally:
        port.close()
