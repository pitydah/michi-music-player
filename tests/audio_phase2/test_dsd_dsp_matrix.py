from __future__ import annotations

import pytest

from michi.application.dsd_policy_service import (
    DsdIntent,
    DsdPolicyRequest,
    DsdPolicyService,
    OutputFamily,
    SourceKind,
)
from michi.domain.dsd_signal import (
    DsdBitOrder,
    DsdOrganization,
    DsdPacking,
    DsdSignalFormat,
)

DSD = DsdSignalFormat(
    bit_rate_hz=2_822_400,
    channels=2,
    packing=DsdPacking.DSD_U8,
    bit_order=DsdBitOrder.LSBF,
    organization=DsdOrganization.PLANAR,
    layout=("FL", "FR"),
)


def _request(**kw):
    base = dict(
        source_kind=SourceKind.DSD,
        source_identity="track:1",
        source_format=DSD,
        intent=DsdIntent.NATIVE_DSD,
        dsp_requested=False,
        conversion_consent=False,
        decoder_available=True,
        target_qualified=True,
        dsp_available=True,
        native_available=True,
        dop_available=True,
        source_truth_verified=True,
        request_epoch=2,
        current_epoch=1,
        processing_graph_revision=4,
        current_processing_graph_revision=4,
        binding_generation=3,
        current_binding_generation=3,
    )
    base.update(kw)
    return DsdPolicyRequest(**base)


@pytest.mark.parametrize(
    ("intent", "dsp", "decision"),
    [
        (DsdIntent.PRESERVE_DSD, False, OutputFamily.NATIVE_DSD),
        (DsdIntent.NATIVE_DSD, False, OutputFamily.NATIVE_DSD),
        (DsdIntent.DOP, False, OutputFamily.DOP),
        (DsdIntent.CONVERT_TO_PCM, False, OutputFamily.DSD_TO_PCM),
        (DsdIntent.PROCESS_AS_PCM, True, OutputFamily.DSD_TO_PCM_DSP),
    ],
)
def test_dsd_matrix_requires_consent_for_conversion(intent, dsp, decision):
    result = DsdPolicyService().decide(
        _request(intent=intent, dsp_requested=dsp, conversion_consent=True)
    )
    assert result.decision is decision


@pytest.mark.parametrize(
    "intent", [DsdIntent.NATIVE_DSD, DsdIntent.DOP, DsdIntent.PRESERVE_DSD]
)
def test_dsp_on_dsd_transport_is_refused(intent):
    result = DsdPolicyService().decide(_request(intent=intent, dsp_requested=True))
    assert result.decision is OutputFamily.REFUSED


def test_conversion_without_consent_is_refused():
    result = DsdPolicyService().decide(_request(intent=DsdIntent.CONVERT_TO_PCM))
    assert result.decision is OutputFamily.REFUSED
    assert result.reason == "CONVERSION_CONSENT_REQUIRED"


def test_pcm_matrix():
    service = DsdPolicyService()
    direct = service.decide(
        _request(
            source_kind=SourceKind.PCM,
            source_format=None,
            intent=DsdIntent.PCM_DIRECT,
        )
    )
    assert direct.decision is OutputFamily.PCM_DIRECT
    processed = service.decide(
        _request(
            source_kind=SourceKind.PCM,
            source_format=None,
            intent=DsdIntent.PCM_PROCESSED,
            dsp_requested=True,
        )
    )
    assert processed.decision is OutputFamily.PCM_PROCESSED


@pytest.mark.parametrize(
    ("kw", "reason"),
    [
        ({"request_epoch": 1}, "REQUEST_EPOCH_DUPLICATE"),
        ({"request_epoch": 0}, "REQUEST_EPOCH_STALE"),
        ({"current_processing_graph_revision": 5}, "PROCESSING_GRAPH_STALE"),
        ({"current_binding_generation": 4}, "BINDING_GENERATION_STALE"),
        (
            {"decoder_available": False, "conversion_consent": True},
            "DSD_PCM_DECODER_UNAVAILABLE",
        ),
        (
            {"target_qualified": False, "conversion_consent": True},
            "DSD_PCM_TARGET_UNQUALIFIED",
        ),
        (
            {"dsp_available": False, "conversion_consent": True, "dsp_requested": True},
            "DSD_PCM_DSP_UNAVAILABLE",
        ),
    ],
)
def test_typed_unavailable_or_stale(kw, reason):
    kw.setdefault(
        "intent",
        DsdIntent.CONVERT_TO_PCM
        if "conversion_consent" in kw
        else DsdIntent.NATIVE_DSD,
    )
    result = DsdPolicyService().decide(_request(**kw))
    assert result.reason == reason
    assert result.decision in (OutputFamily.UNAVAILABLE, OutputFamily.REFUSED)


def test_auto_without_consent_preserves_dsd_and_without_decoder_is_unavailable():
    service = DsdPolicyService()
    preserved = service.decide(_request(intent=DsdIntent.AUTO))
    assert preserved.decision is OutputFamily.NATIVE_DSD
    unavailable = service.decide(
        _request(
            intent=DsdIntent.AUTO, conversion_consent=True, decoder_available=False
        )
    )
    assert unavailable.reason == "AUTO_CANNOT_DECIDE"


def test_pcm_incompatible_intent_is_refused_not_pcm_direct():
    result = DsdPolicyService().decide(
        _request(
            source_kind=SourceKind.PCM,
            source_format=None,
            intent=DsdIntent.NATIVE_DSD,
        )
    )
    assert result.decision is OutputFamily.REFUSED
    assert result.reason == "PCM_INTENT_INCOMPATIBLE"


def test_auto_with_consent_never_converts_implicitly():
    result = DsdPolicyService().decide(
        _request(intent=DsdIntent.AUTO, conversion_consent=True)
    )
    assert result.decision is OutputFamily.UNAVAILABLE
    assert result.reason == "AUTO_CANNOT_DECIDE"


def test_preserve_requires_available_native_route():
    result = DsdPolicyService().decide(
        _request(intent=DsdIntent.PRESERVE_DSD, native_available=False)
    )
    assert result.decision is OutputFamily.UNAVAILABLE
    assert result.reason == "NATIVE_DSD_UNAVAILABLE"


def test_conversion_requires_verified_source_truth():
    result = DsdPolicyService().decide(
        _request(
            intent=DsdIntent.CONVERT_TO_PCM,
            conversion_consent=True,
            source_truth_verified=False,
        )
    )
    assert result.decision is OutputFamily.UNAVAILABLE
    assert result.reason == "DSD_SOURCE_TRUTH_REQUIRED"
