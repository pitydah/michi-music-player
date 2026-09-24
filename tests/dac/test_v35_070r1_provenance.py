"""DAC-V35-070R1 production provenance corrective gates."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from michi.application.audio_device_registry import AudioDeviceRegistry
from michi.domain.audio_device import BindingKind
from michi.domain.audio_evidence import PcmTuple
from michi.domain.signal_truth import (
    AlsaRuntimeEvidence,
    DecodedRuntimeEvidence,
    EngineRuntimeEvidence,
    OutputPlanEvidence,
    SignalTruthIdentity,
    SignalTruthReason,
    SignalTruthRecorder,
    SignalTruthVerdict,
    SourceFileFactsEvidence,
)
from michi.infrastructure.audio_devices.alsa_runtime_observer import (
    AlsaHwParamsObserver,
)
from michi.infrastructure.audio_devices.sysfs_snapshot import (
    read_alsa_cards,
    read_usb_devices,
)
from tests.dac._fixtures import AlsaCard, UsbDevice, build_linux_sysfs, make_roots

_HW_PARAMS_96_24 = """access: RW_INTERLEAVED
format: S32_LE
subformat: STD
channels: 2
rate: 96000 (96000/1)
period_size: 1024
buffer_size: 4096
msbits: 24
"""


def _proc_pcm(
    tmp_path: Path,
    *,
    card: int = 2,
    device: int = 0,
    subdevices: dict[int, str],
    card_id: str = "DX5",
) -> Path:
    proc_root = tmp_path / "proc" / "asound"
    card_root = proc_root / f"card{card}"
    card_root.mkdir(parents=True, exist_ok=True)
    (card_root / "id").write_text(f"{card_id}\n", encoding="utf-8")
    for subdevice, hw_params in subdevices.items():
        sub_root = card_root / f"pcm{device}p" / f"sub{subdevice}"
        sub_root.mkdir(parents=True, exist_ok=True)
        (sub_root / "hw_params").write_text(hw_params, encoding="utf-8")
    return proc_root


def _discovered_binding(tmp_path: Path, *, proc_root: Path, card_index: int = 2):
    sysfs_root = make_roots(tmp_path)
    usb = UsbDevice("2-1", "2622", "0105", serial="DX5ABC123")
    card = AlsaCard(card_index=card_index, card_id="DX5", usb_devpath="2-1")
    build_linux_sysfs(sysfs_root, usb_devices=(usb,), cards=(card,))
    registry = AudioDeviceRegistry()
    registry.ingest(
        read_usb_devices(sysfs_root)
        + read_alsa_cards(sysfs_root, proc_asound_root=proc_root)
    )
    stable_id = "usb:2622:0105:DX5ABC123"
    binding = registry.binding_for(stable_id, BindingKind.ALSA_PCM)
    assert binding is not None
    return stable_id, binding


def _identity(binding, stable_id: str) -> SignalTruthIdentity:
    return SignalTruthIdentity(
        plan_id="plan-r1",
        execution_generation=7,
        port_generation=11,
        binding_generation=binding.generation,
        stable_device_id=stable_id,
        stable_endpoint_signature=binding.stable_endpoint_signature,
    )


def test_st70r1_01_production_discovery_resolves_exact_alsa_runtime_endpoint(
    tmp_path: Path,
) -> None:
    proc_root = _proc_pcm(tmp_path, subdevices={3: _HW_PARAMS_96_24})
    stable_id, binding = _discovered_binding(tmp_path, proc_root=proc_root)

    assert binding.pcm_subdevice == 3
    assert binding.stable_endpoint_signature.endswith(":sub:3")

    event = AlsaHwParamsObserver(proc_asound_root=proc_root).observe(
        _identity(binding, stable_id), binding
    )
    assert isinstance(event, AlsaRuntimeEvidence)
    assert event.pcm_subdevice == 3
    assert event.proc_path.endswith("card2/pcm0p/sub3/hw_params")


def test_st70r1_02_multiple_subdevices_never_select_first_arbitrarily(
    tmp_path: Path,
) -> None:
    proc_root = _proc_pcm(
        tmp_path,
        subdevices={0: "closed\n", 1: _HW_PARAMS_96_24},
    )
    stable_id, binding = _discovered_binding(tmp_path, proc_root=proc_root)

    assert binding.pcm_subdevice is None
    assert not binding.stable_endpoint_signature.endswith(":sub:0")

    event = AlsaHwParamsObserver(proc_asound_root=proc_root).observe(
        _identity(binding, stable_id), binding
    )
    assert isinstance(event, AlsaRuntimeEvidence)
    assert event.pcm_subdevice == 1
    assert event.proc_path.endswith("sub1/hw_params")


def test_st70r1_02_multiple_active_subdevices_remain_unresolved(
    tmp_path: Path,
) -> None:
    proc_root = _proc_pcm(
        tmp_path,
        subdevices={0: _HW_PARAMS_96_24, 1: _HW_PARAMS_96_24},
    )
    stable_id, binding = _discovered_binding(tmp_path, proc_root=proc_root)

    assert binding.pcm_subdevice is None
    assert (
        AlsaHwParamsObserver(proc_asound_root=proc_root).observe(
            _identity(binding, stable_id), binding
        )
        is None
    )


def test_st70r1_03_unresolved_subdevice_remains_unknown_never_fabricated(
    tmp_path: Path,
) -> None:
    proc_root = _proc_pcm(
        tmp_path,
        subdevices={0: "closed\n", 1: "closed\n"},
    )
    stable_id, binding = _discovered_binding(tmp_path, proc_root=proc_root)
    assert binding.pcm_subdevice is None
    assert (
        AlsaHwParamsObserver(proc_asound_root=proc_root).observe(
            _identity(binding, stable_id), binding
        )
        is None
    )


def _pcm(
    rate: int = 96_000,
    fmt: str = "S32_LE",
    channels: int = 2,
    sbits: int | None = 24,
) -> PcmTuple:
    return PcmTuple(rate, fmt, channels, sbits)


def _proven_chain():
    """The §12 required positive chain: an OBSERVED transforming converter whose
    preservation policy is proven (dithering and noise shaping disabled)."""
    from michi.domain.audio_evidence import RuntimeTransformEvidence

    return RuntimeTransformEvidence(
        converter_present=True,
        converter_transforming=True,
        resampler_present=False,
        resampler_transforming=False,
        remix_transforming=False,
        converter_dithering_disabled=True,
        converter_noise_shaping_disabled=True,
    )


def _truth(
    *,
    decoded: PcmTuple | None = None,
    effective: PcmTuple | None = None,
    alsa: PcmTuple | None = None,
    source: PcmTuple | None = None,
    resampling: bool = False,
    remix: bool = False,
    transforms=None,
) -> SignalTruthRecorder:
    from michi.domain.audio_evidence import RuntimeTransformEvidence

    identity = SignalTruthIdentity("p", 1, 2, 3, "dac", "endpoint")
    recorder = SignalTruthRecorder()
    recorder.begin_candidate(
        OutputPlanEvidence(identity, _pcm(), "alsasink", "hw:CARD=DX5,DEV=0", True)
    )
    if source is not None:
        recorder.observe(SourceFileFactsEvidence(identity, "flac", "flac", source))
    if decoded is not None:
        recorder.observe(DecodedRuntimeEvidence(identity, decoded))
    if effective is not None:
        recorder.observe(
            EngineRuntimeEvidence(
                identity=identity,
                effective_pcm=effective,
                sink_factory="alsasink",
                sink_device="hw:CARD=DX5,DEV=0",
                graph_factories=("flacdec", "capsfilter", "alsasink"),
                transform_evidence=(
                    transforms if transforms is not None else RuntimeTransformEvidence()
                ),
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
    if alsa is not None:
        recorder.observe(
            AlsaRuntimeEvidence(
                identity=identity,
                negotiated_pcm=alsa,
                access="RW_INTERLEAVED",
                subformat="STD",
                period_size=1024,
                buffer_size=4096,
                proc_path="/proc/asound/card2/pcm0p/sub1/hw_params",
                card_index=2,
                pcm_device=0,
                pcm_subdevice=1,
                locator="hw:CARD=DX5,DEV=0",
                stable_endpoint_signature="endpoint",
                binding_generation=3,
            )
        )
    return recorder


def test_st70r1_04_engine_container_bits_unknown_do_not_block_authorized_route():
    snapshot = _truth(
        decoded=_pcm(fmt="S24_3LE"),
        effective=_pcm(fmt="S32_LE", sbits=None),
        alsa=_pcm(fmt="S32_LE"),
        transforms=_proven_chain(),
    ).candidate_snapshot
    # R110R1 PRESERVATION SEMANTIC UPDATE
    # Old invariant: an unknown ENGINE container width blocks the authorized
    #   representation-preserving route.
    # Why superseded: the engine stage reports the CARRIER container. S32_LE
    #   precision is deliberately unknown, so demanding it made every
    #   authorized 24/source route permanently UNKNOWN. §17 proves preservation
    #   from the decoded width, the authorized pair, the declared policy and the
    #   runtime graph facts — not from the container's width.
    # Canonical authority: §297 (container_representation_changed) + §292.
    # New invariant: the authorized route is DIRECT_CONTAINER_ADAPTED; an
    #   unknown container width alone never blocks it.
    assert snapshot.verdict is SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED
    assert SignalTruthReason.ST_CONTAINER_ADAPTED in snapshot.reasons


def test_st70r1_05_decoded_sbits_unknown_blocks_container_adaptation():
    snapshot = _truth(
        decoded=_pcm(fmt="S24_3LE", sbits=None),
        effective=_pcm(fmt="S32_LE"),
        alsa=_pcm(fmt="S32_LE"),
    ).candidate_snapshot
    assert snapshot.verdict is SignalTruthVerdict.UNKNOWN


def test_st70r1_06_alsa_container_bits_unknown_do_not_block_authorized_route():
    snapshot = _truth(
        decoded=_pcm(fmt="S24_3LE"),
        effective=_pcm(fmt="S32_LE"),
        alsa=_pcm(fmt="S32_LE", sbits=None),
        transforms=_proven_chain(),
    ).candidate_snapshot
    # R110R1 PRESERVATION SEMANTIC UPDATE
    # Old invariant: an unknown ALSA container width blocks the authorized route.
    # Why superseded: the ALSA stage negotiates the CARRIER container; §17 does
    #   not require its intrinsic width for an authorized representation-only
    #   change. Requiring it made the physical S32 route permanently UNKNOWN.
    # Canonical authority: §297 (container_representation_changed) + §292.
    # New invariant: DIRECT_CONTAINER_ADAPTED for the proven authorized route.
    assert snapshot.verdict is SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED


def test_st70r1_07_all_three_prove_24_sbits_allows_container_adaptation():
    snapshot = _truth(
        decoded=_pcm(fmt="S24_3LE"),
        effective=_pcm(fmt="S32_LE"),
        alsa=_pcm(fmt="S32_LE"),
        transforms=_proven_chain(),
    ).candidate_snapshot
    assert snapshot.verdict is SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED
    assert snapshot.reasons == (SignalTruthReason.ST_CONTAINER_ADAPTED,)


def test_st70r1_08_s32_alone_never_proves_32_significant_bits():
    snapshot = _truth(
        decoded=_pcm(sbits=None),
        effective=_pcm(sbits=None),
        alsa=_pcm(sbits=None),
    ).candidate_snapshot
    assert snapshot.verdict is SignalTruthVerdict.UNKNOWN
    assert SignalTruthReason.ST_SIGNIFICANT_BITS_UNKNOWN in snapshot.reasons


def test_st70r1_09_engine_effective_sbits_mismatch_blocks_adaptation():
    snapshot = _truth(
        decoded=_pcm(fmt="S24_3LE", sbits=24),
        effective=_pcm(fmt="S32_LE", sbits=20),
        alsa=_pcm(fmt="S32_LE", sbits=24),
    ).candidate_snapshot
    # R110R1 PRESERVATION SEMANTIC UPDATE
    # Old invariant: a proven engine/ALSA width mismatch stays UNKNOWN.
    # Why superseded: a PROVEN width that contradicts the decoded signal is a
    #   real contradiction between the runtime and the promised signal, so it is
    #   REFUTED rather than merely unknown. Never adapted is preserved.
    # Canonical authority: §297 with the established contradiction vocabulary.
    # New invariant: CONTRADICTED with the significant-bit reason.
    assert snapshot.verdict is SignalTruthVerdict.CONTRADICTED
    assert SignalTruthReason.ST_SIGNIFICANT_BITS_MISMATCH in snapshot.reasons


def test_source_decoded_mismatch_is_preserved_without_overriding_runtime_truth():
    snapshot = _truth(
        source=_pcm(rate=96_000),
        decoded=_pcm(rate=48_000),
        effective=_pcm(rate=48_000),
        alsa=_pcm(rate=48_000),
    ).candidate_snapshot
    assert snapshot.verdict is SignalTruthVerdict.DIRECT
    assert SignalTruthReason.ST_SOURCE_DECODED_MISMATCH in snapshot.reasons


def test_alsa_rate_conflict_without_transform_is_contradicted():
    snapshot = _truth(
        decoded=_pcm(rate=96_000),
        effective=_pcm(rate=96_000),
        alsa=_pcm(rate=48_000),
    ).candidate_snapshot
    assert snapshot.verdict is SignalTruthVerdict.CONTRADICTED
    assert SignalTruthReason.ST_ALSA_NEGOTIATION_CONTRADICTION in snapshot.reasons


def test_alsa_channel_conflict_without_remix_is_contradicted():
    snapshot = _truth(
        decoded=_pcm(channels=2),
        effective=_pcm(channels=2),
        alsa=_pcm(channels=1),
    ).candidate_snapshot
    assert snapshot.verdict is SignalTruthVerdict.CONTRADICTED


def test_observed_rate_and_channel_transforms_retain_transform_verdicts():
    resampled = _truth(
        decoded=_pcm(rate=96_000),
        effective=_pcm(rate=48_000),
        alsa=_pcm(rate=48_000),
        resampling=True,
    ).candidate_snapshot
    assert resampled.verdict is SignalTruthVerdict.RESAMPLED
    assert SignalTruthReason.ST_RATE_MISMATCH in resampled.reasons

    remixed = _truth(
        decoded=_pcm(channels=2),
        effective=_pcm(channels=1),
        alsa=_pcm(channels=1),
        remix=True,
    ).candidate_snapshot
    assert remixed.verdict is SignalTruthVerdict.REMIXED
    assert SignalTruthReason.ST_CHANNEL_MISMATCH in remixed.reasons


def _superseded_candidates():
    recorder = SignalTruthRecorder()
    identity_b = SignalTruthIdentity("same-plan", 2, 20, 4, "dac", "endpoint")
    identity_c = SignalTruthIdentity("same-plan", 3, 21, 4, "dac", "endpoint")
    recorder.begin_candidate(
        OutputPlanEvidence(identity_b, _pcm(), "alsasink", "hw:CARD=DX5,DEV=0", True)
    )
    recorder.begin_candidate(
        OutputPlanEvidence(identity_c, _pcm(), "alsasink", "hw:CARD=DX5,DEV=0", True)
    )

    return recorder, identity_b, identity_c


def test_st70r1_13_stale_decoded_evidence_ignored_after_supersession():
    recorder, identity_b, identity_c = _superseded_candidates()

    assert recorder.observe(DecodedRuntimeEvidence(identity_b, _pcm())) is False
    assert recorder.candidate_snapshot.identity == identity_c
    assert recorder.candidate_snapshot.decoded_runtime is None


def test_st70r1_14_stale_alsa_evidence_ignored_after_supersession():
    recorder, identity_b, identity_c = _superseded_candidates()

    assert (
        recorder.observe(
            AlsaRuntimeEvidence(
                identity_b,
                _pcm(),
                "RW_INTERLEAVED",
                "STD",
                1024,
                4096,
                "/old",
            )
        )
        is False
    )
    assert recorder.candidate_snapshot.identity == identity_c
    assert recorder.candidate_snapshot.device_negotiated is None


def test_st70r1_15_late_candidate_cannot_become_active_after_c_commit():
    recorder, identity_b, identity_c = _superseded_candidates()

    assert recorder.commit_candidate(identity_c) is True
    assert recorder.commit_candidate(identity_b) is False
    assert recorder.active_snapshot is not None
    assert recorder.active_snapshot.identity == identity_c


def test_st70r1_16_closed_hw_params_never_reused_as_evidence(tmp_path: Path) -> None:
    proc_root = _proc_pcm(
        tmp_path,
        subdevices={0: "closed\n"},
    )
    stable_id, binding = _discovered_binding(tmp_path, proc_root=proc_root)
    assert (
        AlsaHwParamsObserver(proc_asound_root=proc_root).observe(
            _identity(binding, stable_id), binding
        )
        is None
    )


def test_st70r1_17_malformed_hw_params_fail_closed(tmp_path: Path) -> None:
    proc_root = _proc_pcm(tmp_path, subdevices={0: "format: S32_LE\n"})
    stable_id, binding = _discovered_binding(tmp_path, proc_root=proc_root)
    assert (
        AlsaHwParamsObserver(proc_asound_root=proc_root).observe(
            _identity(binding, stable_id), binding
        )
        is None
    )


def test_st70r1_18_subdevice_conflict_is_absent_without_positive_proof(
    tmp_path: Path,
) -> None:
    proc_root = _proc_pcm(tmp_path, subdevices={0: "closed\n", 1: "closed\n"})
    stable_id, binding = _discovered_binding(tmp_path, proc_root=proc_root)
    assert binding.pcm_subdevice is None
    assert (
        AlsaHwParamsObserver(proc_asound_root=proc_root).observe(
            _identity(binding, stable_id), binding
        )
        is None
    )


def test_positive_endpoint_signature_conflict_is_binding_contradiction(
    tmp_path: Path,
) -> None:
    proc_root = _proc_pcm(tmp_path, subdevices={0: _HW_PARAMS_96_24})
    stable_id, binding = _discovered_binding(tmp_path, proc_root=proc_root)
    conflicting = replace(binding, stable_endpoint_signature="other-endpoint")
    event = AlsaHwParamsObserver(proc_asound_root=proc_root).observe(
        _identity(binding, stable_id), conflicting
    )
    assert event is not None
    assert event.kind.value == "binding_mismatch"


def test_st70r1_19_old_card_hw_params_cannot_satisfy_new_binding_generation(
    tmp_path: Path,
) -> None:
    old_proc = _proc_pcm(
        tmp_path / "old",
        card=2,
        subdevices={0: _HW_PARAMS_96_24},
    )
    new_proc = _proc_pcm(
        tmp_path / "new",
        card=4,
        subdevices={0: "closed\n"},
    )
    old_sysfs = make_roots(tmp_path / "old")
    new_sysfs = make_roots(tmp_path / "new")
    usb = UsbDevice("2-1", "2622", "0105", serial="DX5ABC123")
    build_linux_sysfs(
        old_sysfs,
        usb_devices=(usb,),
        cards=(AlsaCard(2, "DX5", "2-1"),),
    )
    build_linux_sysfs(
        new_sysfs,
        usb_devices=(usb,),
        cards=(AlsaCard(4, "DX5", "2-1"),),
    )
    registry = AudioDeviceRegistry()
    registry.ingest(
        read_usb_devices(old_sysfs)
        + read_alsa_cards(old_sysfs, proc_asound_root=old_proc)
    )
    stable_id = "usb:2622:0105:DX5ABC123"
    old_binding = registry.binding_for(stable_id, BindingKind.ALSA_PCM)
    assert old_binding is not None
    registry.ingest(
        read_usb_devices(new_sysfs)
        + read_alsa_cards(new_sysfs, proc_asound_root=new_proc)
    )
    new_binding = registry.binding_for(stable_id, BindingKind.ALSA_PCM)
    assert new_binding is not None
    new_identity = SignalTruthIdentity(
        "new-plan",
        9,
        12,
        new_binding.generation,
        stable_id,
        new_binding.stable_endpoint_signature,
    )

    assert old_binding.card_index == 2
    assert new_binding.card_index == 4
    assert old_binding.generation < new_binding.generation
    reads: list[str] = []
    assert (
        AlsaHwParamsObserver(
            lambda path: reads.append(path) or _HW_PARAMS_96_24,
            proc_asound_root=old_proc,
        ).observe(new_identity, old_binding)
        is None
    )
    assert reads == []
