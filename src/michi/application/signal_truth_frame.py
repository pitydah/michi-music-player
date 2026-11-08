"""A46: dynamic-stage-safe, immutable UI read-model for the F03/owner view.

The existing SignalTruthProjectionService/F03 projection and the C6 OutputSession
owner are the ONLY semantic authorities.  This module cannot record, classify
samples, infer physical DAC behavior, or control playback.  It validates their
already-reconciled presentation and freezes the result for simultaneous Qt/QML
consumers.  In particular a truthy request is never promoted to observed DSP.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

_STAGE_IDS = ("source", "decode", "processing", "output", "device")
# Real F11 SignalPathBridge can report runtime additions after processing.
# They are presentation receipts, NOT independently certified DSP adoption or
# causal order. Future repeatable operations require instance-scoped receipts.
_DYNAMIC_STAGE_IDS = frozenset(("resample", "channel-remap", "fir"))
_MAX_STAGES = 24
_MAX_OPERATIONS = 24
_OP_KINDS = frozenset(
    (
        "resample",
        "channel-remap",
        "peq",
        "fir",
        "gain",
        "headroom",
        "dither",
        "requantize",
        "mix",
        "decode",
        "dsd-to-pcm",
        "dop-pack",
    )
)
_OP_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@-]{0,95}$")
_STAGE_STATES = frozenset(("observed", "transformed", "unknown", "pending", "error"))
_TEMPORAL = frozenset(("ACTIVE", "PENDING", "HISTORICAL", "NOT_ACTIVE"))
_PROOF = frozenset(
    ("no_path", "pending", "historical", "contradicted", "partially_verified")
)
_OWNER_STATES = frozenset(("RUNNING_REPORTED", "READY_REPORTED"))
_F03_GOOD = "RECONCILED"
_ACTIONS = frozenset(
    ("NONE", "OPEN_ENGINE", "OPEN_PROCESSING", "OPEN_OUTPUT", "OPEN_DEVICE_SETUP")
)
_F03_MASKED = frozenset(("OWNER_LINK_REQUIRED", "NO_CAPTURE", "REFUSED"))
# A42 publishes only presentation fields. No raw snapshots, locators or secrets.
_FIELDS = frozenset(
    (
        "status",
        "captureRevision",
        "canonicalF03State",
        "canonicalF03Reason",
        "canonicalF03Nodes",
        "pathVerdict",
        "reasonCodes",
        "stages",
        "identity",
        "audioFamily",
        "familyEvidenceState",
        "familyEvidenceText",
        "familyEvidenceReasons",
        "dspExecutionState",
        "dspExecutionText",
        "presentationWarning",
        "headline",
        "headlineTone",
        "pathProofState",
        "pathProofLabel",
        "indicatorState",
        "indicatorTooltip",
        "proofLevel",
        "qualityAccessibleText",
        "sourceQualityClass",
        "sourceFormatLabel",
        "sourceRateDepthLabel",
        "sourceIdentity",
        "operationsObservedUnordered",
        "operationOrderVerified",
        "configurationActions",
        "operationInstances",
        "operationPresentationWarning",
    )
)


def _safe_scalar(value: object, *, max_len: int = 512) -> str:
    if not isinstance(value, str):
        return ""
    return value[:max_len]


def _safe_rows(rows: object) -> list[list[str]]:
    if not isinstance(rows, (list, tuple)):
        return []
    accepted: list[list[str]] = []
    for row in list(rows)[:16]:
        if isinstance(row, (list, tuple)) and len(row) == 2:
            accepted.append([_safe_scalar(row[0], max_len=80), _safe_scalar(row[1])])
    return accepted


def _clear_unproved(frame: dict[str, Any], reason: str) -> None:
    """Downgrade stale proof together, not only an indicator label."""
    frame["pathProofState"] = (
        "no_path"
        if frame["status"] == "ACTIVE"
        else (
            "historical"
            if frame["status"] == "HISTORICAL"
            else "pending"
            if frame["status"] == "PENDING"
            else "no_path"
        )
    )
    frame["pathProofLabel"] = "Sin evidencia correlacionada"
    frame["indicatorState"] = "unknown"
    frame["indicatorTooltip"] = "Signal Truth: evidencia no correlacionada"
    frame["sourceIdentity"] = ""
    frame["identity"] = {}
    frame["pathVerdict"] = "unknown"
    frame["reasonCodes"] = []
    frame["canonicalF03Nodes"] = []
    frame["headline"] = "Ruta no verificada"
    frame["headlineTone"] = "warning"
    frame["dspExecutionState"] = "UNOBSERVED"
    frame["dspExecutionText"] = "DSP no confirmado en esta ejecución"
    frame["familyEvidenceState"] = "UNOBSERVED"
    frame["familyEvidenceText"] = "Evidencia de ejecución no correlacionada"
    frame["presentationWarning"] = reason
    frame["qualityAccessibleText"] = "Evidencia de ejecución no correlacionada"
    frame["operationsObservedUnordered"] = []
    for stage in frame["stages"]:
        stage["state"] = "unknown"
        stage["summary"] = "Sin evidencia correlacionada"
        stage["detail"] = "La captura no está vinculada al propietario vigente"
        stage["detailRows"] = []
        stage["reasonCodes"] = []


def _stages(raw: object) -> list[dict[str, Any]]:
    """Preserve F11's five anchors plus observed optional runtime stages.

    F03 still has FOUR semantic nodes. F11 may insert resample, channel-remap
    and FIR between Processing and Output. An additional UI stage is not a
    new classifier or a verified ordering proof. Reject forged/duplicate/oddly
    ordered IDs instead of discarding a valid, bounded 5+N projection.
    """
    if not isinstance(raw, (list, tuple)) or not (5 <= len(raw) <= _MAX_STAGES):
        return []
    ids: list[str] = []
    anchor_index = 0
    seen_dynamic: set[str] = set()
    for row in raw:
        if not isinstance(row, Mapping):
            return []
        sid = row.get("id")
        if type(sid) is not str:
            return []
        if anchor_index < len(_STAGE_IDS) and sid == _STAGE_IDS[anchor_index]:
            anchor_index += 1
        elif (
            anchor_index == 3 and sid in _DYNAMIC_STAGE_IDS and sid not in seen_dynamic
        ):
            seen_dynamic.add(sid)
        else:
            return []
        ids.append(sid)
    if anchor_index != len(_STAGE_IDS):
        return []

    count = len(ids)
    stages: list[dict[str, Any]] = []
    for index, row in enumerate(raw):
        sid = ids[index]
        raw_codes = row.get("reasonCodes", ())
        stage: dict[str, Any] = {
            "id": sid,
            "title": _safe_scalar(row.get("title")),
            "summary": _safe_scalar(row.get("summary")),
            "state": row.get("state")
            if isinstance(row.get("state"), str) and row.get("state") in _STAGE_STATES
            else "unknown",
            "detail": _safe_scalar(row.get("detail"), max_len=1024),
            "configAction": _safe_scalar(row.get("configAction"), max_len=48),
            "reasonCodes": [r[:80] for r in raw_codes if isinstance(r, str)][:24]
            if isinstance(raw_codes, (tuple, list))
            else [],
            "detailRows": _safe_rows(row.get("detailRows")),
            "expanded": False,
            "expandable": bool(row.get("expandable", True)),
            "historical": bool(row.get("historical", False)),
            "index": index,
            "count": count,
            "first": index == 0,
            "last": index == count - 1,
        }
        stages.append(stage)
    return stages


def _operation_instances(
    raw: object, *, generation: object
) -> tuple[list[dict[str, Any]], str]:
    """A47 passive disclosure of repeated producer-reported operations.

    Never derives execution, adoption or causal order. This is a display DTO,
    not a second runtime classifier. A future owner-issued operation certificate
    is required before any per-operation EFFECTIVE badge or DAG edges appear.
    """
    if raw is None:
        return [], ""
    if not isinstance(raw, (list, tuple)) or len(raw) > _MAX_OPERATIONS:
        return [], "ST_A47_OPERATION_COUNT_REFUSED"
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in raw:
        if not isinstance(candidate, Mapping):
            return [], "ST_A47_OPERATION_MALFORMED"
        oid = candidate.get("operation_instance_id")
        kind = candidate.get("kind")
        branch = candidate.get("branch_id")
        producer = candidate.get("producer_id")
        evidence = candidate.get("evidence_ref")
        if not (
            isinstance(oid, str)
            and _OP_ID.fullmatch(oid)
            and isinstance(kind, str)
            and kind in _OP_KINDS
            and branch == "main"
            and isinstance(producer, str)
            and _OP_ID.fullmatch(producer)
            and isinstance(evidence, str)
            and _OP_ID.fullmatch(evidence)
            and type(generation) is int
            and generation > 0
            and type(candidate.get("execution_generation")) is int
            and candidate["execution_generation"] == generation
        ):
            return [], "ST_A47_OPERATION_IDENTITY_OR_PROVENANCE"
        if oid in seen:
            return [], "ST_A47_OPERATION_ID_DUPLICATE"
        seen.add(oid)
        # Do not carry addresses, paths, raw parameters, provider tokens,
        # internal graph objects or untrusted application-wide QML actions.
        rows.append(
            {
                "operationInstanceId": oid,
                "kind": kind,
                "branchId": branch,
                "producerId": producer,
                "evidenceRef": evidence,
                "evidenceState": "REPORTED_UNCONFIRMED",
                "adoptionState": "UNVERIFIED",
                "orderVerified": False,
                "predecessors": [],
                "reasonCodes": [
                    code[:80]
                    for code in candidate.get("reasonCodes", ())
                    if isinstance(code, str)
                ][:16]
                if isinstance(candidate.get("reasonCodes"), (tuple, list))
                else [],
            }
        )
    return rows, ""


def _empty_stage_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": sid,
            "title": title,
            "summary": "No observado",
            "state": "unknown",
            "detail": "Sin evidencia correlacionada",
            "configAction": "NONE",
            "reasonCodes": [],
            "detailRows": [],
            "expanded": False,
            "expandable": False,
            "historical": False,
            "index": i,
            "count": len(_STAGE_IDS),
            "first": i == 0,
            "last": i == len(_STAGE_IDS) - 1,
        }
        for i, (sid, title) in enumerate(
            zip(
                _STAGE_IDS,
                (
                    "Fuente",
                    "Decodificación",
                    "Procesamiento",
                    "Salida",
                    "DAC / dispositivo",
                ),
                strict=False,
            )
        )
    ]


def _normalize(frame: Mapping[str, Any]) -> dict[str, Any]:
    status = frame.get("status")
    if not isinstance(status, str) or status not in _TEMPORAL:
        status = "NOT_ACTIVE"
    revision = frame.get("captureRevision")
    revision_ok = type(revision) is int and revision >= 0
    parsed_stages = _stages(frame.get("stages"))
    topology_ok = bool(
        parsed_stages
    )  # _stages validates mandatory anchors and 0..N extras
    data: dict[str, Any] = {
        "status": status,
        "captureRevision": revision if revision_ok else 0,
        "stages": parsed_stages if topology_ok else _empty_stage_rows(),
        "pathProofState": frame.get("pathProofState"),
        "canonicalF03State": _safe_scalar(frame.get("canonicalF03State"), max_len=60),
        "familyEvidenceState": _safe_scalar(
            frame.get("familyEvidenceState"), max_len=60
        ),
        "dspExecutionState": _safe_scalar(frame.get("dspExecutionState"), max_len=60),
        "audioFamily": _safe_scalar(frame.get("audioFamily"), max_len=48),
    }
    for field in (
        _FIELDS
        - data.keys()
        - {
            "stages",
            "identity",
            "reasonCodes",
            "canonicalF03Nodes",
            "familyEvidenceReasons",
            "configurationActions",
            "operationsObservedUnordered",
            "operationInstances",
            "operationPresentationWarning",
        }
    ):
        if field in frame:
            data[field] = _safe_scalar(frame[field], max_len=1024)
    data[
        "identity"
    ] = {}  # Identity is never copied unless F03 reconciliation succeeded.
    data["reasonCodes"] = []
    data["canonicalF03Nodes"] = []
    data["familyEvidenceReasons"] = [
        code
        for code in (frame.get("familyEvidenceReasons") or ())
        if isinstance(code, str)
    ][:16]
    data["operationsObservedUnordered"] = [
        _safe_scalar(text)
        for text in (frame.get("operationsObservedUnordered") or ())
        if isinstance(text, str)
    ][:16]
    data["configurationActions"] = [
        _safe_scalar(a, max_len=48)
        for a in (frame.get("configurationActions") or ())
        if isinstance(a, str)
    ][:12]
    data["operationOrderVerified"] = False
    data["fidelityClaim"] = "UNPROVEN"
    data["sourceIdentity"] = data.get("sourceIdentity", "")
    if any(part in data["sourceIdentity"] for part in ("/", "\\", "://")):
        data["sourceIdentity"] = ""
    data["configurationActions"] = [
        a for a in data["configurationActions"] if a in _ACTIONS
    ]
    for row in data["stages"]:
        if row["configAction"] not in _ACTIONS:
            row["configAction"] = "NONE"
    data["pathProofState"] = (
        data["pathProofState"]
        if isinstance(data["pathProofState"], str) and data["pathProofState"] in _PROOF
        else "no_path"
    )
    if status == "ACTIVE" and data["canonicalF03State"] == _F03_GOOD:
        raw_nodes = frame.get("canonicalF03Nodes")
        if (
            isinstance(raw_nodes, (list, tuple))
            and len(raw_nodes) == 4
            and all(
                isinstance(n, Mapping) and n.get("kind") == kind
                for n, kind in zip(
                    raw_nodes,
                    ("source", "decode", "engine", "device"),
                    strict=False,
                )
            )
        ):
            data["canonicalF03Nodes"] = [
                {"kind": n["kind"], "state": _safe_scalar(n.get("state"), max_len=24)}
                for n in raw_nodes
            ]
            data["reasonCodes"] = [
                x for x in (frame.get("reasonCodes") or ()) if isinstance(x, str)
            ][:48]
            identity = frame.get("identity", {})
            # Only the bounded, F03-gated identity participates in display.
            if isinstance(identity, Mapping):
                data["identity"] = {
                    str(k): v
                    for k, v in identity.items()
                    if k
                    in {
                        "plan_id",
                        "execution_generation",
                        "port_generation",
                        "binding_generation",
                        "stable_device_id",
                        "stable_endpoint_signature",
                    }
                    and (isinstance(v, (str, int)) and type(v) is not bool)
                }
        else:
            _clear_unproved(data, "ST_A42_INVALID_F03_NODE_TOPOLOGY")
    # A historical frame is explicitly non-current: preserving its bounded F03
    # identity is how the existing F11 UI tells two past captures apart. This
    # never resurrects a current owner fact or a positive fidelity claim.
    if (
        status == "HISTORICAL"
        and data["canonicalF03State"] == _F03_GOOD
        and not data["identity"]
    ):
        identity = frame.get("identity", {})
        if isinstance(identity, Mapping):
            data["identity"] = {
                str(k): v
                for k, v in identity.items()
                if k
                in {
                    "plan_id",
                    "execution_generation",
                    "port_generation",
                    "binding_generation",
                    "stable_device_id",
                    "stable_endpoint_signature",
                }
                and (isinstance(v, (str, int)) and type(v) is not bool)
            }
    if not revision_ok:
        _clear_unproved(data, "ST_A42_INVALID_CAPTURE_REVISION")
    elif not topology_ok:
        _clear_unproved(data, "ST_A42_INVALID_UI_TOPOLOGY")
    elif status == "ACTIVE" and data["canonicalF03State"] != _F03_GOOD:
        # An OutputSession family may report READY/RUNNING without F03 linkage.
        # The pre-existing C6 overlay is the authority for those statuses; the
        # UI must NOT lift a source/decode/PCM path from an unrelated capture.
        if (
            data["familyEvidenceState"] in _OWNER_STATES
            and data["canonicalF03State"] in _F03_MASKED
        ):
            for row in data["stages"]:
                if row["id"] != "output":
                    # This includes dynamic F03 stages. An unlinked owner
                    # cannot inherit resampling/FIR claims from a PCM snapshot.
                    row["state"] = "unknown"
                    row["detailRows"] = []
                    row["reasonCodes"] = []
            data["pathProofState"] = (
                "partially_verified"
                if data["familyEvidenceState"] == "RUNNING_REPORTED"
                else "pending"
            )
            data["pathProofLabel"] = "Recibo de salida; ruta completa no correlacionada"
        else:
            _clear_unproved(data, "ST_A42_NO_CANONICAL_F03_OR_OWNER_LINK")
    elif status == "HISTORICAL":
        data["pathProofState"] = "historical"
        data["dspExecutionState"] = "UNOBSERVED"
        data["familyEvidenceState"] = "UNOBSERVED"
        for row in data["stages"]:
            row["historical"] = True
            if row["state"] == "transformed":
                row["state"] = "unknown"
    elif status in {"PENDING", "NOT_ACTIVE"}:
        data["pathProofState"] = "pending" if status == "PENDING" else "no_path"
        data["dspExecutionState"] = "UNOBSERVED"
        data["familyEvidenceState"] = "UNOBSERVED"
        for row in data["stages"]:
            if row["state"] in {"observed", "transformed"}:
                row["state"] = "pending" if status == "PENDING" else "unknown"
                row["detailRows"] = []
    # A42/A49 owner overlays explicitly publish dspExecutionState. A legacy
    # F11 Direct projection has no owner overlay: its matching F05 receipt and
    # processing event remain the only DSP claim until an OutputSession family
    # adopts it. Do not erase that pre-existing proof merely because the A49
    # field is absent.
    if (
        "dspExecutionState" in frame
        and data["dspExecutionState"] != "CURRENT_EXECUTION_CONFIRMED"
    ):
        for row in data["stages"]:
            if row["id"] in {"processing", "fir"} and row["state"] == "transformed":
                # The FIR graph factory is evidence of a graph component,
                # not proof that this execution adopted/processed DSP frames.
                row["state"] = "unknown"
                row["detailRows"] = []
                if row["id"] == "fir":
                    row["summary"] = "FIR presente en grafo; adopción no acreditada"
                    row["detail"] = (
                        "Factoria informada por el motor; efectividad pendiente"
                    )
    if data["status"] != "ACTIVE" or data["canonicalF03State"] != _F03_GOOD:
        data["operationsObservedUnordered"] = []
    # A47: operationInstance IDs permit multiple SRC/PEQ/FIR kinds, but only
    # F03-reconciled ACTIVE captures may expose them. Every positive adoption
    # and order claim remains UNVERIFIED until signed by their real owners.
    data["operationInstances"] = []
    data["operationPresentationWarning"] = ""
    if status == "ACTIVE" and data["canonicalF03State"] == _F03_GOOD and topology_ok:
        generation = data["identity"].get("execution_generation")
        rows, warning = _operation_instances(
            frame.get("operationInstances"), generation=generation
        )
        data["operationInstances"] = rows
        data["operationPresentationWarning"] = warning
    elif frame.get("operationInstances"):
        data["operationPresentationWarning"] = "ST_A47_OPERATION_SCOPE_NOT_ACTIVE"
    # Even a complete F03 reading does not certify sample preservation.
    if data["pathProofState"] == "partially_verified":
        data["pathProofLabel"] = data.get("pathProofLabel") or "Observación parcial"
    return data


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return value


@dataclass(frozen=True, slots=True)
class TruthFrame:
    """Immutable snapshot; serialization returns detached, allowlisted QML DTOs."""

    revision: int
    temporal: str
    _payload: Mapping[str, Any]

    @classmethod
    def from_reconciled(cls, payload: Mapping[str, Any]) -> TruthFrame:
        normalized = _normalize(payload)
        return cls(
            normalized["captureRevision"], normalized["status"], _freeze(normalized)
        )

    def to_qml(self) -> dict[str, Any]:
        return _thaw(self._payload)


def publish_truth_frame(reconciled: Mapping[str, Any]) -> dict[str, Any]:
    """Single adapter called after F03 and OutputSession readbacks on Qt owner."""
    return TruthFrame.from_reconciled(reconciled).to_qml()
