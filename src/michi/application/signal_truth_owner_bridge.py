"""AP2-F11 A36: conservative read-only OutputSession -> C6 adapter.

No new playback owner, QObject, recorder or classifier. The existing Qt bridge
calls this on its owner thread *after* the F03 TruthFrame has been built.
OutputSessionService supplies transition_snapshot and active_execution_id.
All weak/ambiguous states are downgraded; no owner adoption proof is forged.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from michi.application.signal_truth_causal_view import build_c6_qml_overlay
from michi.application.signal_truth_delivery import (
    DisplayClaim,
    PublicationLedger,
    project_family_delivery,
)

_ALIASES = {
    "pcm_managed": "managed",
    "managed": "managed",
    "dsd_to_pcm": "dsd_pcm",
    "dsd_pcm": "dsd_pcm",
    "native_dsd": "native_dsd",
    "dop": "dop",
}


def _enum_value(raw: object) -> str:
    value = str(getattr(raw, "value", raw) or "").strip().lower()
    return value.split(".")[-1]


def read_output_owner_scope(output_session: object) -> dict[str, object]:
    """Normalize a *real* OutputSessionService snapshot; never synthesize IDs.

    OutputSession active_execution_id is valid for READY or RUNNING. The
    transition snapshot may change mid-read, so compare readbacks and refuse.
    Direct/Shared are intentionally outside this adapter's receipt contract.
    """
    try:
        first_id = output_session.active_execution_id
        first = output_session.transition_snapshot()
        second_id = output_session.active_execution_id
        second = output_session.transition_snapshot()
        if not isinstance(first, Mapping) or dict(first) != dict(second):
            raise ValueError("output session changed during read")
        if not isinstance(first_id, str) or first_id != second_id:
            raise ValueError("active execution changed during read")
        state = _enum_value(first.get("state"))
        family = _ALIASES.get(_enum_value(first.get("family")), "unknown")
        epoch = first.get("generation")
        execution = first.get("execution_id")
        plan_id = first.get("plan_id")
        if (
            family == "unknown"
            or state not in {"ready", "running"}
            or type(epoch) is not int
            or epoch <= 0
            or not first_id
            or first_id != execution
            or not isinstance(plan_id, str)
            or not plan_id
        ):
            raise ValueError("owner lacks a stable execution scope")
        return {
            "family": family,
            "state": state,
            "execution_id": first_id,
            "plan_id": plan_id,
            "generation": epoch,
            "stable_device_id": str(first.get("stable_device_id") or ""),
            "binding_generation": first.get("binding_generation"),
            "host_generation": first.get("host_generation"),
        }
    except Exception:
        # The exact exception text may contain private data: do not propagate.
        raise ValueError("ST_A36_OWNER_SCOPE_UNVERIFIED") from None


def overlay_from_output_session(
    *,
    frame_payload: Mapping[str, Any],
    recorder: object,
    output_session: object,
    f05_truth_reader: Callable[[], Mapping[str, object]],
    ledger: PublicationLedger | None = None,
) -> dict[str, Any]:
    """Use the output owner's existing binding and A35 conservative overlay.

    No ledger: always UNVERIFIED (never accept stale RUNNING). Adoption and
    continuity are NOT manufactured. A future owner port can supply them only
    after an approved F05/OutputSession contract amendment.
    """

    def scope() -> dict[str, object]:
        return read_output_owner_scope(output_session)

    def binding(snapshot: object) -> str | None:
        current = scope()
        try:
            return recorder.resolve_active_execution_link(
                snapshot,
                execution_id=current["execution_id"],
                output_plan_id=current["plan_id"],
            )
        except (AttributeError, ValueError, TypeError):
            return None

    def delivery(owner: Mapping[str, object]) -> DisplayClaim:
        if ledger is None:
            return DisplayClaim.UNVERIFIED
        try:
            return project_family_delivery(
                ledger,
                recorder=recorder,
                family=str(owner["family"]),
                execution_id=str(owner["execution_id"]),
                owner_epoch=int(owner["generation"]),
            )
        except (AttributeError, ValueError, TypeError):
            return DisplayClaim.UNVERIFIED

    return build_c6_qml_overlay(
        frame_payload=frame_payload,
        recorder=recorder,
        owner_scope_reader=scope,
        f05_truth_reader=f05_truth_reader,
        linked_execution_reader=binding,
        family_delivery_reader=delivery,
    )
