"""AP2-F11 A48: capability-gated advanced DSP UI affordances (read-only).

Never makes a draft effective, constructs a DSP graph or enables future-only
features from labels. Only the existing F05/Settings owner can attest wiring.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

_CAPABILITY_ACTIONS = {
    "parametric_eq": ("OPEN_PROCESSING", "F05"),
    "advanced_peq": ("OPEN_PROCESSING", "F05"),
    "fir_convolution": ("OPEN_PROCESSING", "F05"),
    "profile_library": ("OPEN_PROCESSING", "SETTINGS"),
    "graphic_eq": ("OPEN_PROCESSING", "F05"),
    "true_peak_meter": ("NONE", "METER"),
    "loudness_meter": ("NONE", "METER"),
}


@dataclass(frozen=True, slots=True)
class CapabilityView:
    capability: str
    state: str
    action: str
    reason: str
    applied: bool

    def to_qml(self) -> dict[str, object]:
        return {
            "id": self.capability,
            "state": self.state,
            "configAction": self.action,
            "reasonCode": self.reason,
            "effective": self.applied,
        }


def project_capabilities(
    owner_receipts: Mapping[str, Mapping[str, object]] | None,
    *,
    execution_id: str | None = None,
    owner_execution_correlated: bool = False,
) -> tuple[CapabilityView, ...]:
    """Unknown/future capability remains disabled unless explicitly wired.

    `applied` requires separate currently effective owner readback scoped to
    `execution_id`; SELECTED/DRAFT/SUPPORTED never suffices.
    """
    receipts = owner_receipts or {}
    out = []
    for feature, (intent, required_owner) in _CAPABILITY_ACTIONS.items():
        evidence = receipts.get(feature)
        if not isinstance(evidence, Mapping):
            out.append(
                CapabilityView(
                    feature, "UNOBSERVED", "NONE", "ST_P1_CAPABILITY_UNREPORTED", False
                )
            )
            continue
        if evidence.get("supported") is not True:
            out.append(
                CapabilityView(
                    feature,
                    "UNAVAILABLE",
                    "NONE",
                    "ST_P1_CAPABILITY_UNSUPPORTED",
                    False,
                )
            )
            continue
        if evidence.get("wired") is not True:
            out.append(
                CapabilityView(
                    feature, "DISABLED", "NONE", "ST_P1_CAPABILITY_NOT_WIRED", False
                )
            )
            continue
        if evidence.get("owner") != required_owner:
            out.append(
                CapabilityView(
                    feature, "DISABLED", "NONE", "ST_P1_CAPABILITY_OWNER_UNKNOWN", False
                )
            )
            continue
        applied = (
            owner_execution_correlated is True
            and required_owner == "F05"
            and bool(execution_id)
            and evidence.get("effective_execution_id") == execution_id
            and evidence.get("readback_proven") is True
            and evidence.get("state") == "EFFECTIVE"
        )
        out.append(
            CapabilityView(
                feature, "AVAILABLE", intent, "ST_P1_CAPABILITY_AVAILABLE", applied
            )
        )
    return tuple(out)
