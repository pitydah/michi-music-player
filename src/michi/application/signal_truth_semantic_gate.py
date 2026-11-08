"""AP2-F11 A38: evidence-preserving F03 canonical semantics gate.

This is NOT a classifier or another projector. The F03 owner supplies the
semantic projection; this module checks exact identity, verdict and reason
partition before a Qt-owned frame is allowed to display any positive claim.
Only an allowlisted OBSERVATION of F03 nodes crosses into UI; raw facts and
potentially identifying ALSA locators do not cross this bridge boundary.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
from typing import Any

_F03_NODES = ("source", "decode", "engine", "device")
_REFUSAL = "ST_A38_F03_SEMANTIC_REFUSAL"
_OBSERVATION_STATES = frozenset(
    {"observed", "not_observed", "not_observable", "unknown", "stale", "conflicted"}
)


def _value(raw: object) -> str:
    """Use typed enum VALUE, never text of an enum's representation."""
    return str(getattr(raw, "value", raw) or "").strip().lower()


def _identity_of(identity: object) -> tuple[object, ...]:
    names = (
        "plan_id",
        "execution_generation",
        "port_generation",
        "binding_generation",
        "stable_device_id",
        "stable_endpoint_signature",
    )
    return tuple(getattr(identity, name) for name in names)


def _refuse(frame: Mapping[str, Any], reason: str) -> dict[str, Any]:
    """A failed semantic join can only DEGRADE output, not classify a route."""
    out = dict(frame)
    out["canonicalF03State"] = "REFUSED"
    out["canonicalF03Reason"] = reason
    out["canonicalF03Nodes"] = []
    out["pathVerdict"] = "unknown"
    out["reasonCodes"] = []
    out["proofLevel"] = "Not verified"
    out["sourceIdentity"] = ""
    out["identity"] = {}
    out["sourceQualityClass"] = "unknown"
    out["sourceFormatLabel"] = "Origen no verificado"
    out["sourceRateDepthLabel"] = "Formato no confirmado"
    out["pathProofState"] = {
        "ACTIVE": "no_path",
        "PENDING": "pending",
        "HISTORICAL": "historical",
    }.get(frame.get("status"), "no_path")
    out["pathProofLabel"] = "Observación no correlacionada"
    out["headlineTone"] = "warning"
    out["headline"] = "Ruta no verificada"
    out["indicatorState"] = "unknown"
    out["indicatorTooltip"] = "Michi Signal Truth: proyección F03 no correlacionada"
    out["qualityAccessibleText"] = "La evidencia no supera la comprobación F03"
    stages = []
    for stage in frame.get("stages", ()):
        row = dict(stage)
        if row.get("state") in {"observed", "transformed"}:
            row["state"] = "unknown"
        # No stale positive detail survives an identity or F03 refusal.
        row["detailRows"] = []
        row["detail"] = "Evidencia sin vínculo verificable"
        row["summary"] = "Sin evidencia correlacionada"
        stages.append(row)
    out["stages"] = stages
    return out


def reconcile_f03_semantics(
    frame: Mapping[str, Any],
    snapshot: object | None,
    *,
    capture_revision: int,
    observed_revision: int,
    projector: Callable[[object], object],
) -> dict[str, Any]:
    """Reconcile ONE recorder capture against the existing F03 projection.

    A38 only reads fields defined by F03. It does not guess DSP effectiveness,
    stage topology, source quality, ALSA samples or physical DAC fidelity.
    It refuses if the capture changed or F03 omits/repeats a canonical reason.
    """
    if snapshot is None:
        result = dict(frame)
        result["canonicalF03State"] = "NO_CAPTURE"
        result["canonicalF03Reason"] = ""
        result["canonicalF03Nodes"] = []
        # A historical frame with no snapshot must not remain 'verified'.
        if result.get("pathProofState") == "verified":
            return _refuse(frame, "ST_A38_NO_CANONICAL_CAPTURE")
        return result
    if (
        type(capture_revision) is not int
        or type(observed_revision) is not int
        or capture_revision != observed_revision
    ):
        return _refuse(frame, "ST_A38_CAPTURE_REVISION_CHANGED")
    try:
        canonical = projector(snapshot)
        if _identity_of(canonical.identity) != _identity_of(snapshot.identity):
            raise ValueError("identity")
        verdict = _value(snapshot.verdict)
        reasons = tuple(
            str(getattr(reason, "value", reason)) for reason in snapshot.reasons
        )
        if canonical.verdict != verdict or tuple(canonical.reasons) != reasons:
            raise ValueError("verdict_or_reasons")
        nodes = tuple(canonical.nodes)
        if tuple(_value(node.kind) for node in nodes) != _F03_NODES:
            raise ValueError("four_nodes")
        if tuple(str(node.node_id) for node in nodes) != _F03_NODES:
            raise ValueError("node_identity")
        states = tuple(_value(node.state) for node in nodes)
        if not set(states).issubset(_OBSERVATION_STATES):
            raise ValueError("node_state")
        assigned = Counter(reason for node in nodes for reason in node.reason_codes)
        if assigned != Counter(reasons):
            raise ValueError("reason_partition")
    except Exception:  # passive semantic refusal; details may contain private paths
        return _refuse(frame, _REFUSAL)

    out = dict(frame)
    out["canonicalF03State"] = "RECONCILED"
    out["canonicalF03Reason"] = ""
    out["canonicalF03Nodes"] = [
        {"kind": kind, "state": state}
        for kind, state in zip(_F03_NODES, states, strict=False)
    ]
    out["pathVerdict"] = verdict
    out["reasonCodes"] = list(reasons)
    stage_state_by_f03 = {
        kind: state for kind, state in zip(_F03_NODES, states, strict=False)
    }
    stages = []
    for stage in frame.get("stages", ()):
        row = dict(stage)
        kind = str(row.get("id") or "")
        # F03 Engine is NOT QML Processing or Output; only gate matching
        # source/decode/device views. DSP is governed by the F05 adoption port.
        if kind in {"source", "decode", "device"}:
            state = stage_state_by_f03[kind]
            if state == "conflicted":
                row["state"] = "error"
            elif state != "observed" and row.get("state") == "observed":
                row["state"] = "unknown"
        stages.append(row)
    out["stages"] = stages
    # 'verified path' is an overclaim for F11. The F03 device state reports
    # observation at its bounded transport interface, NOT bit-perfect or DAC.
    if out.get("status") == "ACTIVE" and out.get("pathProofState") == "verified":
        out["pathProofState"] = "partially_verified"
        out["pathProofLabel"] = (
            "Ruta observada hasta ALSA"
            if stage_state_by_f03["device"] == "observed"
            else "Observación parcial"
        )
    if verdict == "contradicted" and out.get("status") == "ACTIVE":
        out["headlineTone"] = "error"
        out["indicatorState"] = "error"
        out["indicatorTooltip"] = "Michi Signal Truth: contradicción de salida F03"
    return out


def mask_unlinked_output_family(frame: Mapping[str, Any]) -> dict[str, Any]:
    """F03 PCM route must not masquerade as a separate OutputSession family.

    A native/DoP/managed owner can attach its OWN limited receipt later, but
    cannot inherit source, decoded, ALSA or verdict from a possibly old Direct
    recording. The output-family overlay is applied AFTER this redaction.
    """
    result = _refuse(frame, "ST_A38_F03_EXECUTION_LINK_NOT_PROVEN")
    result["canonicalF03State"] = "OWNER_LINK_REQUIRED"
    result["headline"] = "Ruta pendiente de correlación"
    result["headlineTone"] = "warning"
    for stage in result.get("stages", ()):
        if stage.get("id") in {"source", "decode", "output", "device"}:
            stage["state"] = "unknown"
            stage["summary"] = "Evidencia anterior no vinculada a esta salida"
            stage["detail"] = "Esperando recibo de ejecución del propietario"
            stage["detailRows"] = []
    return result
