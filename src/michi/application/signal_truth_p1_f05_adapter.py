"""A49: read-only live F05/Settings capability bridge, no DSP modifications.

Backend STRATEGY support is not an installed node, and a Settings factory
preset is not Profiles CRUD. Never treat a bridge draft as an adopted effect.
"""

from __future__ import annotations

from collections.abc import Mapping

from michi.application.signal_truth_p1_capabilities import project_capabilities


def project_f05_capabilities(
    f05: Mapping[str, object],
    *,
    quick_eq_can_apply: bool = False,
    settings_receipt: Mapping[str, object] | None = None,
) -> list[dict[str, object]]:
    """Only expose owner-confirmed UX affordances; all proof remains separate.

    `processing_truth()` is the real F05 owner readback. Do not synthesize
    adopted `effective_execution_id`: F05 alone cannot attest current
    OutputSession execution. Settings' profile CRUD must have its own explicit
    owner attestation (unavailable in the audited PR245 composition).
    """
    strategies = f05.get("strategies") if isinstance(f05, Mapping) else None
    if not isinstance(strategies, (tuple, list, set, frozenset)):
        strategies = ()
    names = {str(x).upper() for x in strategies if isinstance(x, str)}
    queried = f05.get("capability_state") == "queried"
    quick = (
        queried
        and quick_eq_can_apply is True
        and {"BIQUAD_CASCADE", "GAIN"}.issubset(names)
    )
    receipts: dict[str, dict[str, object]] = {
        "parametric_eq": {
            "supported": queried and {"BIQUAD_CASCADE", "GAIN"}.issubset(names),
            "wired": quick,
            "owner": "F05",
            "state": "UNVERIFIED",
            "readback_proven": False,
        },
        "advanced_peq": {
            "supported": "BIQUAD_CASCADE" in names and queried,
            "wired": False,
            "owner": "F05",
        },
        "fir_convolution": {
            "supported": "CONVOLUTION_FIR" in names and queried,
            "wired": False,
            "owner": "F05",
        },
        "graphic_eq": {
            "supported": "GRAPHIC_EQ_NBANDS" in names and queried,
            "wired": False,
            "owner": "F05",
        },
    }
    if (
        isinstance(settings_receipt, Mapping)
        and settings_receipt.get("owner") == "SETTINGS"
        and settings_receipt.get("profile_crud_wired") is True
        and settings_receipt.get("readback_proven") is True
    ):
        receipts["profile_library"] = {
            "supported": True,
            "wired": True,
            "owner": "SETTINGS",
        }
    # No execution correlation is claimed here. Positive F05 readback may
    # show up elsewhere only after OutputSession proves cross-owner adoption.
    return [
        view.to_qml()
        for view in project_capabilities(
            receipts, execution_id=None, owner_execution_correlated=False
        )
    ]
