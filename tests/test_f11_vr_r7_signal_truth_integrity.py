"""VR-R7: path proof must not claim verification from IDs alone."""

from pathlib import Path

from michi.presentation.signal_path_bridge import _path_proof_state

_FULL = ["Source", "host", "transport", "device"]


def test_unknown_verdict_is_not_fully_verified_despite_four_receipts():
    assert (
        _path_proof_state(
            temporal_status="ACTIVE",
            verdict_state="unknown",
            tone="neutral",
            proof_parts=_FULL,
        )
        == "partially_verified"
    )


def test_direct_verdict_with_full_path_can_be_verified():
    assert (
        _path_proof_state(
            temporal_status="ACTIVE",
            verdict_state="direct",
            tone="neutral",
            proof_parts=_FULL,
        )
        == "verified"
    )


def test_full_verdict_without_negotiated_transport_remains_partial():
    assert (
        _path_proof_state(
            temporal_status="ACTIVE",
            verdict_state="direct",
            tone="neutral",
            proof_parts=["Source", "host", "device"],
        )
        == "partially_verified"
    )


def test_temporal_status_overrides_path_verification():
    assert (
        _path_proof_state(
            temporal_status="HISTORICAL",
            verdict_state="direct",
            tone="neutral",
            proof_parts=_FULL,
        )
        == "historical"
    )


def test_normal_five_stage_panel_has_intrinsic_height_not_fixed_scrollbox():
    popup = (
        Path(__file__).parents[1]
        / "src/michi/presentation/qml/player/SignalTruthPopup.qml"
    ).read_text()
    assert "desiredHeight: panel.implicitHeight" in popup
    assert "height: Math.min(safeOverlayHeight," in popup
    assert "maxPopupHeight > 0 ? maxPopupHeight : safeOverlayHeight" in popup
    assert "ScrollView {" not in popup
    assert "interactive: contentHeight > height + 1" in popup
