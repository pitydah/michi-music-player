"""F11 basic-EQ bridge contract (draft != effective, no second DSP authority)."""

from __future__ import annotations

from typing import Any

from michi.domain.audio_processing import (
    BiquadType,
    ParametricEqNode,
    PreampNode,
)
from michi.domain.audio_signal import ChannelLayout, PcmSignalFormat
from michi.presentation.audio_processing_bridge import (
    MICHI_10_CENTERS_HZ,
    MICHI_10_Q,
    AudioProcessingBridge,
)


def _signal(rate_hz: int = 44_100) -> PcmSignalFormat:
    return PcmSignalFormat(
        rate_hz=rate_hz,
        transport_format="F32LE",
        significant_bits=32,
        layout=ChannelLayout(positions=("FL", "FR")),
    )


class _Processing:
    def __init__(self) -> None:
        self.applied: list[dict[str, Any]] = []
        self.bypassed = 0
        self.state = "bypassed"

    def processing_truth(self) -> dict[str, Any]:
        return {
            "capability_state": "queried",
            "requested_revision": 2,
            "effective_revision": 1,
            "effective_state": self.state,
            "strategies": ["BIQUAD_CASCADE", "GAIN"],
        }

    def apply_processing_async(self, graph, signal, **kwargs) -> None:
        self.applied.append({"graph": graph, "signal": signal})
        self.state = "effective"
        kwargs["on_done"](
            {"plan_id": "plan:f11", "revision": 2, "graph_revision": graph.revision}
        )

    def disable_processing_async(self, **kwargs) -> None:
        self.bypassed += 1
        self.state = "bypassed"
        kwargs["on_done"](True)


def _bridge(*, family: str = "pcm", signal: PcmSignalFormat | None = None):
    service = _Processing()
    bridge = AudioProcessingBridge(
        service,
        signal_provider=lambda: signal if signal is not None else _signal(),
        source_family_provider=lambda: family,
        async_submit=lambda work, completed: completed(work(), None),
    )
    return bridge, service


def test_draft_is_local_and_apply_builds_the_exact_ten_peak_graph() -> None:
    bridge, service = _bridge()
    bridge.set_draft_band(0, 6.3)
    bridge.set_draft_preamp(-2.0)
    assert bridge.committedRevision == 1
    assert service.applied == []
    assert bridge.bands[0]["gainDb"] == 6.5

    bridge.apply_draft_async()

    assert len(service.applied) == 1
    graph = service.applied[0]["graph"]
    preamp = next(node for node in graph.nodes if isinstance(node, PreampNode))
    eq = next(node for node in graph.nodes if isinstance(node, ParametricEqNode))
    assert preamp.gain_db == -2.0
    assert tuple(band.frequency_hz for band in eq.bands) == MICHI_10_CENTERS_HZ
    assert all(band.filter_type is BiquadType.PEAK for band in eq.bands)
    assert all(band.q == MICHI_10_Q for band in eq.bands)
    assert [band.gain_db for band in eq.bands][0] == 6.5
    assert bridge.bypassEffective is False
    assert bridge.effectiveState == "effective"
    assert bridge.enabledDraft is True
    assert bridge.errorCode == ""


def test_factory_presets_have_unique_ids() -> None:
    bridge, _ = _bridge()
    ids = [preset["id"] for preset in bridge.factoryPresets]
    assert ids.count("flat") == 1
    assert len(ids) == len(set(ids))


def test_reset_and_bypass_keep_parameters() -> None:
    bridge, _service = _bridge()
    bridge.set_draft_band(3, -7.0)
    bridge.reset_draft()
    assert all(band["gainDb"] == 0.0 for band in bridge.bands)
    assert bridge.presetId == "flat"
    assert bridge.enabledDraft is True

    bridge.set_bypass_requested(True)
    assert bridge.enabledDraft is False
    assert bridge.bands[3]["gainDb"] == 0.0


def test_draft_edits_are_ignored_while_a_commit_is_in_flight() -> None:
    class _Held(_Processing):
        def __init__(self) -> None:
            super().__init__()
            self.pending: dict[str, Any] | None = None

        def apply_processing_async(self, graph, signal, **kwargs) -> None:
            self.applied.append({"graph": graph, "signal": signal})
            self.state = "effective"
            self.pending = kwargs

    service = _Held()
    bridge = AudioProcessingBridge(
        service,
        signal_provider=_signal,
        async_submit=lambda work, completed: completed(work(), None),
    )
    bridge.set_draft_band(0, 6.0)
    bridge.apply_draft_async()
    assert bridge.busy is True
    assert service.pending is not None

    bridge.set_draft_band(1, 4.0)
    bridge.set_draft_preamp(3.0)
    bridge.select_preset("flat")
    bridge.reset_draft()
    bridge.set_bypass_requested(True)
    bridge.discard_draft()

    assert bridge.bands[0]["gainDb"] == 6.0
    assert bridge.bands[1]["gainDb"] == 0.0
    assert bridge.preampDb == 0.0
    assert bridge.enabledDraft is True

    service.pending["on_done"](
        {"plan_id": "plan:f11", "revision": 2, "graph_revision": 2}
    )

    assert bridge.busy is False
    assert bridge.bands[0]["gainDb"] == 6.0
    assert bridge.bands[1]["gainDb"] == 0.0
    assert bridge.errorCode == ""
    assert bridge.effectiveState == "effective"


def test_bypass_preserves_the_curve_and_reset_never_reenables_it() -> None:
    bridge, _service = _bridge()
    bridge.set_draft_band(2, 5.0)
    bridge.set_draft_preamp(-3.0)
    bridge.set_bypass_requested(True)

    assert bridge.bands[2]["gainDb"] == 5.0
    assert bridge.preampDb == -3.0
    assert bridge.enabledDraft is False

    bridge.reset_draft()

    assert all(band["gainDb"] == 0.0 for band in bridge.bands)
    assert bridge.preampDb == 0.0
    assert bridge.enabledDraft is False


def test_dsd_pcm_conversion_family_remains_processable_and_truthful() -> None:
    bridge, _service = _bridge(family="dsd_to_pcm")

    assert bridge.sourceFamily == "dsd_to_pcm"
    assert bridge.available is True
    assert bridge.canApply is True


def test_native_dsd_refuses_processing_without_converting() -> None:
    bridge, service = _bridge(family="native_dsd")
    assert bridge.available is False
    assert "DSD" in bridge.capabilityReason

    bridge.apply_draft_async()

    assert service.applied == []
    assert bridge.errorCode == "DSP_REQUIRES_DSD_PCM_CONVERSION"


def test_missing_decoded_signal_is_typed_and_never_applied() -> None:
    bridge = AudioProcessingBridge(
        _Processing(),
        signal_provider=lambda: None,
        async_submit=lambda work, completed: completed(work(), None),
    )

    bridge.apply_draft_async()

    assert bridge.errorCode == "DSP_SIGNAL_UNKNOWN"
    assert bridge.canApply is False


def test_manual_edit_marks_custom_and_flat_preset_restores_zeroes() -> None:
    bridge, _service = _bridge()
    bridge.set_draft_band(9, 12.0)
    assert bridge.presetId == "custom"

    bridge.select_preset("flat")

    assert bridge.presetId == "flat"
    assert all(band["gainDb"] == 0.0 for band in bridge.bands)


def test_bands_above_nyquist_are_marked_inactive_without_losing_the_draft() -> None:
    bridge, _service = _bridge(signal=_signal(rate_hz=16_000))
    bridge.set_draft_band(9, 6.0)

    bands = bridge.bands

    assert bands[9]["gainDb"] == 6.0
    assert bands[9]["enabled"] is False
    assert bands[9]["inactiveReason"] == "Unavailable at current sample rate"
    assert bands[0]["enabled"] is True
    assert bands[0]["inactiveReason"] == ""


def test_failed_apply_keeps_the_draft_and_never_fakes_the_effective_state() -> None:
    class _Failing(_Processing):
        def apply_processing_async(self, graph, signal, **kwargs) -> None:
            kwargs["on_failed"](RuntimeError("host rejected the graph"))

    bridge = AudioProcessingBridge(
        _Failing(),
        signal_provider=_signal,
        async_submit=lambda work, completed: completed(work(), None),
    )
    bridge.set_draft_band(0, 4.0)

    bridge.apply_draft_async()

    assert bridge.busy is False
    assert bridge.bands[0]["gainDb"] == 4.0
    assert bridge.effectiveState == "bypassed"
    assert bridge.errorCode == "DSP_APPLY_FAILED"
    assert "host rejected" in bridge.errorMessage
