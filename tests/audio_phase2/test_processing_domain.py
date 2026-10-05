"""AP2-F04 — processing domain: CORE vocabulary, immutability, semantics.

Contract anchors: R11-F04 (CORE node kinds exactly eight; GraphicEqNode stores
layout+gains; ConvolutionNode stores immutable asset id/hash), R11-G04
(ProcessingSampleContract), R11-G07 (realtime safety).
"""

from __future__ import annotations

import ast
import dataclasses
import math
import sys
from pathlib import Path

import pytest

from michi.domain.audio_processing import (
    GRAPHIC_EQ_BAND_COUNTS,
    GRAPHIC_EQ_CENTER_HZ,
    BiquadType,
    ChannelDelayNode,
    ChannelMapNode,
    CompiledProcessingNode,
    CompiledProcessingPlan,
    ConvolutionNode,
    DitherMode,
    DitherNode,
    GraphicEqLayout,
    GraphicEqNode,
    ParametricEqNode,
    PeqBand,
    PreampNode,
    ProcessingAdaptationReason,
    ProcessingGraph,
    ProcessingNodeKind,
    ProcessingProfile,
    ProcessingSampleContract,
    ProcessingStrategy,
    ResampleNode,
    ResampleQuality,
)

DOMAIN_MODULE = Path(sys.modules["michi.domain.audio_processing"].__file__)


class TestCoreVocabulary:
    def test_node_kinds_are_exactly_the_canonical_core(self) -> None:
        assert [member.name for member in ProcessingNodeKind] == [
            "PREAMP",
            "GRAPHIC_EQ",
            "PARAMETRIC_EQ",
            "CONVOLUTION",
            "CHANNEL_DELAY",
            "CHANNEL_MAP",
            "RESAMPLE",
            "DITHER",
        ]

    def test_non_core_concepts_are_absent(self) -> None:
        names = {member.name for member in ProcessingNodeKind}
        assert names.isdisjoint(
            {"BALANCE", "POLARITY", "CROSSFEED", "LOUDNESS", "FIR", "MIXER", "LIMITER"}
        )

    def test_biquad_filter_vocabulary(self) -> None:
        assert [member.value for member in BiquadType] == [
            "peak",
            "low_shelf",
            "high_shelf",
            "low_pass",
            "high_pass",
            "notch",
            "band_pass",
            "all_pass",
        ]

    def test_semantic_strategy_vocabulary(self) -> None:
        assert [member.value for member in ProcessingStrategy] == [
            "gain",
            "graphic_eq_nbands",
            "biquad_cascade",
            "convolution_fir",
            "resample",
            "channel_delay",
            "channel_map",
            "dither_terminal",
        ]

    def test_graphic_layout_band_counts(self) -> None:
        assert GRAPHIC_EQ_BAND_COUNTS[GraphicEqLayout.MICHI_10_V1] == 10
        assert GRAPHIC_EQ_BAND_COUNTS[GraphicEqLayout.ISO_31_V1] == 31

    def test_adaptation_reason_vocabulary(self) -> None:
        assert [member.value for member in ProcessingAdaptationReason] == [
            "graph_bypassed",
            "node_disabled",
            "inactive_above_nyquist",
            "unsupported_current_signal",
            "asset_unavailable",
            "asset_hash_mismatch",
            "channel_layout_unavailable",
        ]


class TestGraphicEq:
    def test_accepts_exact_band_count_and_preserves_order(self) -> None:
        gains = tuple(float(index) for index in range(10))
        node = GraphicEqNode(
            node_id="eq", layout_id=GraphicEqLayout.MICHI_10_V1, gains_db=gains
        )
        assert node.gains_db == gains
        assert node.kind is ProcessingNodeKind.GRAPHIC_EQ

    def test_rejects_wrong_band_count(self) -> None:
        with pytest.raises(ValueError):
            GraphicEqNode(
                node_id="eq",
                layout_id=GraphicEqLayout.MICHI_10_V1,
                gains_db=(0.0,) * 31,
            )

    def test_rejects_non_finite_gain(self) -> None:
        gains = [0.0] * 10
        gains[3] = math.inf
        with pytest.raises(ValueError):
            GraphicEqNode(
                node_id="eq",
                layout_id=GraphicEqLayout.MICHI_10_V1,
                gains_db=tuple(gains),
            )

    def test_flat_curve_semantics(self) -> None:
        flat = GraphicEqNode(
            node_id="eq",
            layout_id=GraphicEqLayout.MICHI_10_V1,
            gains_db=(0.0,) * 10,
        )
        shaped = dataclasses.replace(flat, gains_db=((1.5,) + (0.0,) * 9))
        assert flat.is_flat is True
        assert shaped.is_flat is False

    def test_immutability_and_serialization(self) -> None:
        node = GraphicEqNode(
            node_id="eq",
            layout_id=GraphicEqLayout.ISO_31_V1,
            gains_db=(0.5,) * 31,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            node.node_id = "other"  # type: ignore[misc]
        assert node == dataclasses.replace(node)


class TestParametricEq:
    def test_band_validation(self) -> None:
        band = PeqBand(
            band_id="b1",
            filter_type=BiquadType.PEAK,
            frequency_hz=1000.0,
            q=0.707,
            gain_db=-3.0,
        )
        assert band.enabled is True
        with pytest.raises(ValueError):
            dataclasses.replace(band, frequency_hz=0.0)
        with pytest.raises(ValueError):
            dataclasses.replace(band, frequency_hz=math.nan)
        with pytest.raises(ValueError):
            dataclasses.replace(band, q=0.0)

    def test_gain_is_rejected_on_gainless_filter_types(self) -> None:
        for filter_type in (
            BiquadType.LOW_PASS,
            BiquadType.HIGH_PASS,
            BiquadType.NOTCH,
            BiquadType.BAND_PASS,
            BiquadType.ALL_PASS,
        ):
            with pytest.raises(ValueError):
                PeqBand(
                    band_id="b",
                    filter_type=filter_type,
                    frequency_hz=1000.0,
                    q=0.707,
                    gain_db=6.0,
                )

    def test_unique_band_ids_and_band_limit(self) -> None:
        band = PeqBand(
            band_id="same",
            filter_type=BiquadType.PEAK,
            frequency_hz=1000.0,
            q=0.707,
            gain_db=0.0,
        )
        with pytest.raises(ValueError):
            ParametricEqNode(node_id="peq", bands=(band, band))
        many = tuple(
            dataclasses.replace(band, band_id=f"b{index}") for index in range(65)
        )
        with pytest.raises(ValueError):
            ParametricEqNode(node_id="peq", bands=many)


class TestConvolution:
    def test_requires_immutable_asset_identity(self) -> None:
        node = ConvolutionNode(
            node_id="ir",
            asset_id="ir:sha256:" + "ab" * 32,
            asset_sha256="ab" * 32,
            gain_db=-1.0,
        )
        assert node.kind is ProcessingNodeKind.CONVOLUTION
        assert node.enabled is True

    def test_rejects_path_like_asset_references(self) -> None:
        with pytest.raises(ValueError):
            ConvolutionNode(
                node_id="ir",
                asset_id="/home/user/room.wav",
                asset_sha256="ab" * 32,
            )

    def test_rejects_invalid_hash_and_gain(self) -> None:
        with pytest.raises(ValueError):
            ConvolutionNode(
                node_id="ir", asset_id="ir:sha256:" + "ab" * 32, asset_sha256="nope"
            )
        with pytest.raises(ValueError):
            ConvolutionNode(
                node_id="ir",
                asset_id="ir:sha256:" + "ab" * 32,
                asset_sha256="ab" * 32,
                gain_db=math.inf,
            )


class TestChannelAndRateNodes:
    def test_channel_delay_rejects_negative(self) -> None:
        node = ChannelDelayNode(node_id="d", delays_us=(0, 250))
        assert node.delays_us == (0, 250)
        with pytest.raises(ValueError):
            ChannelDelayNode(node_id="d", delays_us=(0, -1))

    def test_channel_map_requires_explicit_mapping(self) -> None:
        node = ChannelMapNode(node_id="m", output_to_input=(0, None, 1))
        assert node.output_to_input == (0, None, 1)
        with pytest.raises(ValueError):
            ChannelMapNode(node_id="m", output_to_input=())
        with pytest.raises(ValueError):
            ChannelMapNode(node_id="m", output_to_input=(-1,))

    def test_resample_requires_positive_target(self) -> None:
        node = ResampleNode(
            node_id="r", target_rate_hz=96000, quality=ResampleQuality.HIGH
        )
        assert node.quality is ResampleQuality.HIGH
        with pytest.raises(ValueError):
            ResampleNode(node_id="r", target_rate_hz=0, quality=ResampleQuality.FAST)

    def test_dither_target_precision_set(self) -> None:
        node = DitherNode(node_id="d", mode=DitherMode.TPDF, target_bits=16)
        assert node.mode is DitherMode.TPDF
        with pytest.raises(ValueError):
            DitherNode(node_id="d", mode=DitherMode.TPDF, target_bits=17)
        assert [member.value for member in DitherMode] == ["none", "tpdf"]


class TestGraphAndProfile:
    def test_graph_requires_unique_node_ids_and_valid_revision(self) -> None:
        node = PreampNode(node_id="pre", gain_db=-3.0)
        graph = ProcessingGraph(graph_id="g", revision=1, nodes=(node,))
        assert graph.nodes == (node,)
        with pytest.raises(ValueError):
            ProcessingGraph(graph_id="g", revision=1, nodes=(node, node))
        with pytest.raises(ValueError):
            ProcessingGraph(graph_id="g", revision=-1, nodes=(node,))

    def test_edit_creates_a_new_revision_and_never_mutates(self) -> None:
        graph = ProcessingGraph(
            graph_id="g", revision=1, nodes=(PreampNode(node_id="pre", gain_db=-3.0),)
        )
        edited = dataclasses.replace(graph, revision=2)
        assert graph.revision == 1
        assert edited.revision == 2
        with pytest.raises(dataclasses.FrozenInstanceError):
            graph.revision = 3  # type: ignore[misc]

    def test_bypass_keeps_saved_intent(self) -> None:
        node = PreampNode(node_id="pre", gain_db=-3.0)
        graph = ProcessingGraph(graph_id="g", revision=1, nodes=(node,), bypassed=True)
        assert graph.nodes == (node,)
        assert graph.bypassed is True

    def test_profile_identity_is_distinct_from_graph_revision(self) -> None:
        profile = ProcessingProfile(
            profile_id="p1",
            display_name="Room",
            graph=ProcessingGraph(
                graph_id="g",
                revision=4,
                nodes=(PreampNode(node_id="pre", gain_db=0.0),),
            ),
        )
        assert profile.profile_id == "p1"
        assert profile.graph.revision == 4


class TestCompiledTypes:
    def test_sample_contract_fields(self) -> None:
        contract = ProcessingSampleContract(
            input_format="S32LE",
            working_format="F64LE",
            output_format="S32LE",
            input_rate_hz=96000,
            output_rate_hz=96000,
            channels_in=2,
            channels_out=2,
            input_conversion=True,
            output_quantization=True,
            dither_mode="none",
            noise_shaping_mode="none",
        )
        assert contract.working_format == "F64LE"
        with pytest.raises(dataclasses.FrozenInstanceError):
            contract.working_format = "F32LE"  # type: ignore[misc]

    def test_compiled_plan_and_node_are_immutable(self) -> None:
        node = CompiledProcessingNode(
            node_id="pre",
            kind=ProcessingNodeKind.PREAMP,
            strategy=ProcessingStrategy.GAIN,
            properties=(("gain_db", -3.0),),
            expected_latency_samples=0,
        )
        plan = CompiledProcessingPlan(
            plan_id="dsp:test",
            graph_id="g",
            graph_revision=1,
            backend_id="test",
            sample_contract=ProcessingSampleContract(
                input_format="F32LE",
                working_format="F64LE",
                output_format="F32LE",
                input_rate_hz=48000,
                output_rate_hz=48000,
                channels_in=2,
                channels_out=2,
                input_conversion=False,
                output_quantization=False,
                dither_mode="none",
                noise_shaping_mode="none",
            ),
            nodes=(node,),
            total_latency_samples=0,
            asset_hashes=(),
            changes_sample_values=True,
            changes_representation=False,
            changes_rate=False,
            changes_channels=False,
            changes_timing=False,
            changes_channel_assignment=False,
            quantization_boundary=False,
            adaptation_reasons=(),
            evidence_refs=("graph:g:1",),
        )
        assert plan.nodes == (node,)
        with pytest.raises(dataclasses.FrozenInstanceError):
            plan.plan_id = "other"  # type: ignore[misc]


def test_domain_module_imports_stay_pure_and_factory_free() -> None:
    source = DOMAIN_MODULE.read_text(encoding="utf-8")
    for forbidden in (
        "PySide6",
        "Gst",
        "gi.repository",
        "numpy",
        "sqlite3",
        "equalizer-nbands",
        "audioiirfilter",
        "audiofirfilter",
        "audioconvert",
        "audioresample",
    ):
        assert forbidden not in source, forbidden


class TestCanonicalGraphicCenters:
    def test_michi_10_v1_centers_are_exact(self) -> None:
        assert GRAPHIC_EQ_CENTER_HZ[GraphicEqLayout.MICHI_10_V1] == (
            31.25,
            62.5,
            125.0,
            250.0,
            500.0,
            1000.0,
            2000.0,
            4000.0,
            8000.0,
            16000.0,
        )

    def test_iso_31_v1_centers_are_exact(self) -> None:
        assert GRAPHIC_EQ_CENTER_HZ[GraphicEqLayout.ISO_31_V1] == (
            20.0,
            25.0,
            31.0,
            40.0,
            50.0,
            63.0,
            80.0,
            100.0,
            125.0,
            160.0,
            200.0,
            250.0,
            315.0,
            400.0,
            500.0,
            630.0,
            800.0,
            1000.0,
            1250.0,
            1600.0,
            2000.0,
            2500.0,
            3150.0,
            4000.0,
            5000.0,
            6300.0,
            8000.0,
            10000.0,
            12500.0,
            16000.0,
            20000.0,
        )

    def test_presentation_labels_are_not_processing_centers(self) -> None:
        # The UI labels (31, 62, ...) must never become the DSP identity.
        michi = GRAPHIC_EQ_CENTER_HZ[GraphicEqLayout.MICHI_10_V1]
        assert michi[0] == 31.25
        assert michi[1] == 62.5

    def test_center_tables_are_defined_only_in_the_domain_module(self) -> None:
        root = Path(__file__).parents[2] / "src" / "michi"
        names = {
            "GRAPHIC_EQ_CENTER_HZ",
            "ADVANCED_GRAPHIC_31_HZ",
            "BASIC_EQ_CENTERS_HZ",
        }
        offenders: list[tuple[str, str]] = []
        for path in sorted(root.rglob("*.py")):
            if path.name == "audio_processing.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    targets = node.targets
                elif isinstance(node, ast.AnnAssign):
                    targets = [node.target]
                else:
                    continue
                for target in targets:
                    if isinstance(target, ast.Name) and target.id in names:
                        offenders.append((str(path), target.id))
        assert offenders == []


class TestGraphicEqGainEnvelope:
    def test_boundaries_are_accepted_for_both_layouts(self) -> None:
        for layout in GraphicEqLayout:
            count = GRAPHIC_EQ_BAND_COUNTS[layout]
            for gain in (-12.0, 12.0):
                node = GraphicEqNode(
                    node_id="eq", layout_id=layout, gains_db=(gain,) * count
                )
                assert node.gains_db[0] == gain

    def test_gains_outside_the_envelope_are_rejected(self) -> None:
        for layout in GraphicEqLayout:
            count = GRAPHIC_EQ_BAND_COUNTS[layout]
            for gain in (-12.0001, 12.0001, math.nan, math.inf, -math.inf):
                with pytest.raises(ValueError):
                    GraphicEqNode(
                        node_id="eq", layout_id=layout, gains_db=(gain,) * count
                    )

    def test_every_band_is_checked(self) -> None:
        for layout, index in (
            (GraphicEqLayout.MICHI_10_V1, 7),
            (GraphicEqLayout.ISO_31_V1, 29),
        ):
            count = GRAPHIC_EQ_BAND_COUNTS[layout]
            gains = [0.0] * count
            gains[index] = 12.5
            with pytest.raises(ValueError):
                GraphicEqNode(node_id="eq", layout_id=layout, gains_db=tuple(gains))


class TestPeqGainEnvelope:
    def test_boundaries_are_accepted_per_filter_type(self) -> None:
        for filter_type in (
            BiquadType.PEAK,
            BiquadType.LOW_SHELF,
            BiquadType.HIGH_SHELF,
        ):
            for gain in (-36.0, 36.0):
                band = PeqBand(
                    band_id="b",
                    filter_type=filter_type,
                    frequency_hz=1000.0,
                    q=0.707,
                    gain_db=gain,
                )
                assert band.gain_db == gain

    def test_gains_outside_the_envelope_are_rejected(self) -> None:
        for gain in (-36.0001, 36.0001, math.nan, math.inf, -math.inf):
            with pytest.raises(ValueError):
                PeqBand(
                    band_id="b",
                    filter_type=BiquadType.PEAK,
                    frequency_hz=1000.0,
                    q=0.707,
                    gain_db=gain,
                )


class TestSampleContractValidation:
    @staticmethod
    def _contract(**overrides):
        base: dict = {
            "input_format": "S32LE",
            "working_format": "F64LE",
            "output_format": "S32LE",
            "input_rate_hz": 96000,
            "output_rate_hz": 96000,
            "channels_in": 2,
            "channels_out": 2,
            "input_conversion": True,
            "output_quantization": True,
            "dither_mode": "none",
            "noise_shaping_mode": "none",
        }
        base.update(overrides)
        return ProcessingSampleContract(**base)

    def test_valid_contract_constructs(self) -> None:
        assert self._contract().working_format == "F64LE"

    def test_integer_carriers_are_legitimate_input_output(self) -> None:
        contract = self._contract(input_format="S24_3LE", output_format="S32LE")
        assert contract.input_format == "S24_3LE"
        assert contract.output_format == "S32LE"

    def test_output_format_may_be_none(self) -> None:
        assert self._contract(output_format=None).output_format is None

    def test_invalid_values_are_rejected(self) -> None:
        for overrides in (
            {"input_format": ""},
            {"input_format": "   "},
            {"working_format": "S32LE"},
            {"working_format": ""},
            {"output_format": ""},
            {"input_rate_hz": 0},
            {"input_rate_hz": -1},
            {"output_rate_hz": 0},
            {"channels_in": 0},
            {"channels_out": -2},
            {"dither_mode": ""},
            {"noise_shaping_mode": "  "},
        ):
            with pytest.raises(ValueError):
                self._contract(**overrides)


class TestCompiledInvariantValidation:
    @staticmethod
    def _node(**overrides):
        base: dict = {
            "node_id": "pre",
            "kind": ProcessingNodeKind.PREAMP,
            "strategy": ProcessingStrategy.GAIN,
            "properties": (("gain_db", -3.0),),
            "expected_latency_samples": 0,
        }
        base.update(overrides)
        return CompiledProcessingNode(**base)

    @classmethod
    def _plan(cls, **overrides):
        base: dict = {
            "plan_id": "dsp:test",
            "graph_id": "g",
            "graph_revision": 1,
            "backend_id": "test",
            "sample_contract": TestSampleContractValidation._contract(),
            "nodes": (cls._node(),),
            "total_latency_samples": 0,
            "asset_hashes": (),
            "changes_sample_values": True,
            "changes_representation": False,
            "changes_rate": False,
            "changes_channels": False,
            "changes_timing": False,
            "changes_channel_assignment": False,
            "quantization_boundary": False,
            "adaptation_reasons": (),
            "evidence_refs": ("graph:g:1",),
        }
        base.update(overrides)
        return CompiledProcessingPlan(**base)

    def test_valid_plan_constructs(self) -> None:
        assert self._plan().plan_id == "dsp:test"

    def test_invalid_identity_and_revision_are_rejected(self) -> None:
        with pytest.raises(ValueError):
            self._plan(plan_id="")
        with pytest.raises(ValueError):
            self._plan(graph_id=" ")
        with pytest.raises(ValueError):
            self._plan(backend_id="")
        with pytest.raises(ValueError):
            self._plan(graph_revision=-1)
        with pytest.raises(ValueError):
            self._plan(total_latency_samples=-1)

    def test_duplicate_node_ids_are_rejected(self) -> None:
        with pytest.raises(ValueError):
            self._plan(nodes=(self._node(), self._node()))

    def test_invalid_asset_hashes_are_rejected(self) -> None:
        with pytest.raises(ValueError):
            self._plan(asset_hashes=("not-a-sha",))
        with pytest.raises(ValueError):
            self._node(asset_sha256="not-a-sha")

    def test_typed_contract_is_required(self) -> None:
        with pytest.raises(TypeError):
            self._plan(sample_contract="none")

    def test_evidence_refs_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError):
            self._plan(evidence_refs=("",))
