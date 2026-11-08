"""AP2-F11 C6: passive family/DSP evidence overlay for Michi Signal Truth.

This module never decides a DAC verdict, mutates audio ownership, or infers
receiver behavior from DoP/Native carrier facts. An owner proof is only valid
when supplied by the OutputSession owner, not reconstructed in UI code.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

_FAMILY_ALIASES = {
    "pcm_managed": "managed",
    "managed_pcm": "managed",
    "managed": "managed",
    "dsd_to_pcm": "dsd_pcm",
    "dsd_pcm": "dsd_pcm",
    "dsd→pcm": "dsd_pcm",
    "native_dsd": "native_dsd",
    "dop": "dop",
    "pcm_direct": "direct",
    "direct": "direct",
    "shared": "shared",
}
_TERMINAL = frozenset({"released", "unavailable"})


def _value(value: object) -> str:
    # StrEnum and Enum: use the stable value, never a human-readable label.
    return str(getattr(value, "value", value) or "").strip().casefold()


def _family(value: object) -> str:
    raw = _value(value)
    if raw.startswith("audiofamily."):
        raw = raw.split(".", 1)[1]
    return _FAMILY_ALIASES.get(raw, "unknown")


def _positive_int(value: object) -> int | None:
    # bool is an int subclass and must not be treated as a generation.
    if type(value) is int and value > 0:
        return value
    return None


@dataclass(frozen=True, slots=True)
class OutputAdoptionProof:
    """Owner-issued, exact-execution DSP adoption claim; proposal ST03-02.

    Must originate in OutputSessionService after the matching host F05
    finalize/commit. A UI-generated dict or matching plan ID is not proof.
    """

    execution_id: str
    family: str
    output_generation: int
    binding_generation: int
    host_generation: int
    pipeline_generation: int
    processing_plan_id: str
    processing_generation: int
    native_runtime_identity: str
    finalized: bool


@dataclass(frozen=True, slots=True)
class RecorderContinuity:
    """Proposal ST03-03: issued by the canonical recorder, NOT by the bridge."""

    capture_epoch: int
    sequence: int
    continuous: bool
    latest_state_included: bool
    capture_revision: int
    execution_id: str


@dataclass(frozen=True, slots=True)
class FamilyDspView:
    family: str
    family_state: str
    family_text: str
    dsp_state: str
    dsp_text: str
    execution_id: str
    capture_revision: int
    reasons: tuple[str, ...]
    decode_override: str
    output_detail: str

    def to_qml(self) -> dict[str, object]:
        return {
            "audioFamily": self.family,
            "familyEvidenceState": self.family_state,
            "familyEvidenceText": self.family_text,
            "dspExecutionState": self.dsp_state,
            "dspExecutionText": self.dsp_text,
            "familyEvidenceReasons": list(self.reasons),
        }


def project_causal_family(
    *,
    capture: object,
    owner: Mapping[str, object],
    f05_truth: Mapping[str, object],
    expected_execution_id: str | None,
    adoption: OutputAdoptionProof | None = None,
    continuity: RecorderContinuity | None = None,
    delivery_claim: object | None = None,
) -> FamilyDspView:
    """Pure read model over one recorder capture and the CURRENT owner scope.

    The caller must perform the owner-thread double-read/fence described in
    C6-04. A revision number is NOT a continuity or adoption certificate.
    """
    revision = int(getattr(capture, "revision", 0) or 0)
    events: Sequence[object] = getattr(capture, "output_family_events", ())
    dsp_events: Sequence[object] = getattr(capture, "processing_events", ())
    family = _family(owner.get("family"))
    state = _value(owner.get("state"))
    execution_id = str(owner.get("execution_id") or "")
    owner_device = str(owner.get("stable_device_id") or "")
    reasons: list[str] = []
    linked_execution = (
        bool(expected_execution_id)
        and bool(execution_id)
        and expected_execution_id == execution_id
    )
    last_family_event: object | None = None
    if not linked_execution:
        reasons.append("ST_C6_F03_OWNER_EXECUTION_LINK_MISSING")
    if not execution_id or family == "unknown":
        reasons.append("ST_C6_OWNER_SCOPE_MISSING")
    elif linked_execution:
        # Latest relevant owner event wins; another execution cannot inherit it.
        for event in reversed(events):
            if (
                _family(getattr(event, "family", None)) == family
                and str(getattr(event, "execution_id", "") or "") == execution_id
            ):
                last_family_event = event
                break

    family_state = "UNOBSERVED"
    family_text = "Familia de salida sin recibo correlacionado"
    if last_family_event is not None:
        event_state = _value(getattr(last_family_event, "state", None))
        event_device = str(getattr(last_family_event, "device_id", "") or "")
        if owner_device and event_device and owner_device != event_device:
            family_state = "CONFLICTED"
            family_text = "Identidad de dispositivo contradictoria"
            reasons.append("ST_C6_DEVICE_ID_CONFLICT")
        elif event_state in _TERMINAL:
            family_state = "TERMINATED"
            family_text = "Último recibo de la ejecución: terminal"
            reasons.append("ST_C6_TERMINAL_REVOKED")
        elif event_state == "running" and state == "running":
            family_state = "RUNNING_REPORTED"
            family_text = "Sesión de salida informada como RUNNING"
        elif event_state == "ready" and state in {"ready", "running"}:
            family_state = "READY_REPORTED"
            family_text = "Preparada: no certifica reproducción ni recepción DAC"
        elif event_state == "preparing" and state in {
            "acquiring",
            "configuring",
            "ready",
        }:
            family_state = "PREPARING"
            family_text = "Ruta en preparación, no efectiva"
        else:
            family_state = "UNOBSERVED"
            family_text = "Estado del recibo y del propietario no concordantes"
            reasons.append("ST_C6_FAMILY_STATE_MISMATCH")
    elif linked_execution:
        reasons.append("ST_C6_OUTPUT_RECEIPT_MISSING")

    # The family event can be retained after OutputSession attempted a newer
    # terminal that was not published. If the A26 owner ledger is supplied,
    # its negative receipt prevails over that stale event.
    delivery_state = _value(delivery_claim)
    expected_delivery = {
        "RUNNING_REPORTED": "observed_running",
        "READY_REPORTED": "observed_ready",
    }
    if (
        family_state in expected_delivery
        and delivery_claim is not None
        and delivery_state != expected_delivery[family_state]
    ):
        family_state = "UNOBSERVED"
        family_text = "Publicación de la salida no certificada por su propietario"
        reasons.append("ST_C6_OUTPUT_DELIVERY_NOT_CERTIFIED")

    # F05 motor-only evidence. Never compare output plan ID with DSP plan ID.
    dsp_state = "UNOBSERVED"
    dsp_text = "DSP no correlacionado con la ejecución"
    effective_plan = str(f05_truth.get("effective_plan_id") or "")
    effective_revision = _positive_int(f05_truth.get("effective_revision"))
    engine_runtime = str(f05_truth.get("runtime_identity") or "")
    current_event: object | None = None
    revoked_after_effective = False
    later: list[object] = []
    # Event order in one lock-consistent recorder capture is authoritative
    # within its retained window. A later same-pipeline event always wins.
    # Even an unscoped terminal invalidates a prior positive claim.
    for event in reversed(dsp_events):
        es = _value(getattr(event, "state", None))
        if es in {"unavailable", "bypassed", "preparing", "requested"} and (
            _positive_int(getattr(event, "pipeline_generation", None)) is None
        ):
            revoked_after_effective = True
            break
        if es == "effective" and (
            getattr(event, "plan_id", None) == effective_plan
            and _positive_int(getattr(event, "processing_generation", None))
            == effective_revision
        ):
            pipeline = _positive_int(getattr(event, "pipeline_generation", None))
            if pipeline is None:
                break
            if any(
                _positive_int(getattr(future, "pipeline_generation", None)) == pipeline
                for future in later
            ):
                revoked_after_effective = True
            else:
                current_event = event
            break
        later.append(event)
    engine_confirmed = (
        not revoked_after_effective
        and current_event is not None
        and _value(f05_truth.get("effective_state")) == "effective"
        and f05_truth.get("readback_proven") is True
        and bool(effective_plan and effective_revision and engine_runtime)
        and getattr(current_event, "readback_proven", False) is True
        and str(getattr(current_event, "runtime_identity", "") or "") == engine_runtime
        and _positive_int(getattr(current_event, "host_generation", None)) is not None
        and _positive_int(getattr(current_event, "pipeline_generation", None))
        is not None
    )
    if engine_confirmed:
        dsp_state = "MOTOR_EFFECTIVE"
        dsp_text = "Readback DSP efectivo en F05; ejecución aún no acreditada"

    # Only an OutputSession owner-issued adoption + recorder continuity can
    # promote MOTOR_EFFECTIVE to CURRENT_EXECUTION_CONFIRMED.
    if engine_confirmed and adoption is not None:
        matches = (
            linked_execution
            and adoption.finalized is True
            and adoption.execution_id == execution_id
            and _family(adoption.family) == family
            and _positive_int(adoption.output_generation)
            == _positive_int(owner.get("generation"))
            and _positive_int(adoption.binding_generation)
            == _positive_int(owner.get("binding_generation"))
            and _positive_int(adoption.host_generation)
            == _positive_int(owner.get("host_generation"))
            == _positive_int(getattr(current_event, "host_generation", None))
            and _positive_int(adoption.pipeline_generation)
            == _positive_int(getattr(current_event, "pipeline_generation", None))
            and adoption.processing_plan_id == effective_plan
            and adoption.processing_generation == effective_revision
            and adoption.native_runtime_identity == engine_runtime
            and family_state == "RUNNING_REPORTED"
            and family in {"managed", "dsd_pcm"}
        )
        if not matches:
            reasons.append("ST_C6_ADOPTION_SCOPE_MISMATCH")
        elif continuity is None or not (
            continuity.capture_epoch > 0
            and continuity.sequence > 0
            and continuity.continuous
            and continuity.latest_state_included
            and continuity.capture_revision == revision
            and continuity.execution_id == execution_id
        ):
            reasons.append("ST_C6_RECORDER_CONTINUITY_NOT_CERTIFIED")
        elif _value(delivery_claim) != "observed_running":
            # A recorder append is not proof that OutputSession's latest
            # terminal attempt was delivered. A26 owner ledger must say so.
            reasons.append("ST_C6_OUTPUT_DELIVERY_NOT_CERTIFIED")
        else:
            dsp_state = "CURRENT_EXECUTION_CONFIRMED"
            dsp_text = "DSP adoptado y acreditado para la ejecución actual"
    elif engine_confirmed:
        reasons.append("ST_C6_OUTPUT_ADOPTION_NOT_PROVEN")
    elif dsp_events:
        reasons.append("ST_C6_DSP_READBACK_UNCORRELATED")

    # Family-specific text is careful about physical boundaries. Never
    # synthesize PCM from Native DSD or DoP source/transport events.
    decode_override = ""
    output_detail = family_text
    if family == "native_dsd":
        decode_override = "DSD nativo: no hay decodificación PCM acreditada"
        output_detail += "; interpretación por el DAC no observada"
    elif family == "dop":
        decode_override = "Fuente DSD; portadora PCM DoP no equivale a PCM musical"
        output_detail += "; el DAC receptor no ha sido verificado"
    elif family == "dsd_pcm":
        decode_override = "Conversión DSD→PCM: consultar recibo del host"
        output_detail += "; DSP solo si readback F05 y adopción coinciden"
    elif family == "managed":
        output_detail += "; ruta Managed no demuestra bit-perfect"

    # A terminal event always revokes the current-execution claim.
    if (
        family_state != "RUNNING_REPORTED"
        and dsp_state == "CURRENT_EXECUTION_CONFIRMED"
    ):
        dsp_state = "UNOBSERVED"
        dsp_text = "Última ejecución no vigente; DSP revocado"
    if family_state in {"TERMINATED", "CONFLICTED"}:
        dsp_state = "UNOBSERVED"
        dsp_text = "No hay adopción DSP acreditada para una ruta vigente"

    return FamilyDspView(
        family,
        family_state,
        family_text,
        dsp_state,
        dsp_text,
        execution_id,
        revision,
        tuple(dict.fromkeys(reasons)),
        decode_override,
        output_detail,
    )


def overlay_qml_stages(
    original_stages: Sequence[Mapping[str, Any]], view: FamilyDspView
) -> list[dict[str, Any]]:
    """A32 F03 stage-preserving decoration. Never changes verdict/reasons."""
    stages = [dict(stage) for stage in original_stages]
    for stage in stages:
        sid = str(stage.get("id") or "")
        if sid == "decode" and view.decode_override:
            stage["summary"] = view.decode_override
            stage["state"] = "unknown"
            stage["detail"] = view.decode_override
            if view.family in {"native_dsd", "dop"}:
                # F03's PCM-oriented rows cannot be relabeled as DSD/DoP
                # decoder receipts. Preserve reason codes, not fictitious PCM.
                stage["detailRows"] = []
        elif sid == "processing":
            stage["summary"] = view.dsp_text
            stage["state"] = (
                "transformed"
                if view.dsp_state == "CURRENT_EXECUTION_CONFIRMED"
                else "unknown"
            )
        elif sid == "output":
            stage["detail"] = view.output_detail
            if view.family in {"native_dsd", "dop"}:
                # DoP PCM carrier is not musical PCM or DAC interpretation;
                # older generic ALSA/PCM detail rows are not portable.
                stage["detailRows"] = []
            if view.family_state in {"CONFLICTED", "TERMINATED"}:
                stage["state"] = (
                    "error" if view.family_state == "CONFLICTED" else "unknown"
                )
            elif view.family_state not in {"RUNNING_REPORTED", "READY_REPORTED"}:
                stage["state"] = "unknown"
    return stages


def build_c6_qml_overlay(
    *,
    frame_payload: Mapping[str, Any],
    recorder: object,
    owner_scope_reader: Any,
    f05_truth_reader: Any,
    linked_execution_reader: Any = None,
    adoption_reader: Any = None,
    continuity_reader: Any = None,
    family_delivery_reader: Any = None,
) -> dict[str, Any]:
    """One owner-thread, stable-read decoration of A32's existing QML DTO.

    The caller must invoke this ONLY on the existing Qt owner thread.
    `linked_execution_reader` must be an authoritative F03-to-Output owner
    binding, NOT a plan-ID equality or a derived UI value. If absent, C6
    remains UNOBSERVED; no current-execution DSP claim can be promoted.
    """
    payload = dict(frame_payload)
    if payload.get("status") != "ACTIVE":
        # Never attach current OutputSession events to historical F03 evidence.
        payload.update(
            {
                "audioFamily": "unknown",
                "familyEvidenceState": "UNOBSERVED",
                "familyEvidenceText": "Sin vínculo con una ejecución activa",
                "dspExecutionState": "UNOBSERVED",
                "dspExecutionText": "Sin DSP actual acreditado",
                "familyEvidenceReasons": [],
            }
        )
        return payload

    try:
        before = recorder.read_capture_state()
        owner_before = dict(owner_scope_reader())
        f05 = dict(f05_truth_reader())
        expected_id = (
            linked_execution_reader(before.active)
            if callable(linked_execution_reader) and before.active is not None
            else None
        )
        proof = adoption_reader() if callable(adoption_reader) else None
        continuity = continuity_reader() if callable(continuity_reader) else None
        delivery_claim = (
            family_delivery_reader(owner_before)
            if callable(family_delivery_reader)
            else None
        )
        view = project_causal_family(
            capture=before,
            owner=owner_before,
            f05_truth=f05,
            expected_execution_id=expected_id,
            adoption=proof,
            continuity=continuity,
            delivery_claim=delivery_claim,
        )
        after = recorder.read_capture_state()
        owner_after = dict(owner_scope_reader())
        f05_after = dict(f05_truth_reader())
    except Exception:  # passive projection must never interrupt audio or Qt
        payload.update(
            {
                "audioFamily": "unknown",
                "familyEvidenceState": "UNOBSERVED",
                "familyEvidenceText": "Lectura de propietarios no disponible",
                "dspExecutionState": "UNOBSERVED",
                "dspExecutionText": "Sin adopción DSP acreditada",
                "familyEvidenceReasons": ["ST_C6_OWNER_READ_FAILED"],
                "presentationWarning": "ST_C6_OWNER_READ_FAILED",
            }
        )
        return payload
    if (
        before.revision != after.revision
        or owner_before != owner_after
        or f05 != f05_after
        or frame_payload.get("captureRevision") != before.revision
    ):
        # Do not attach possibly foreign family receipts to F03's five stages.
        payload.update(
            {
                "audioFamily": "unknown",
                "familyEvidenceState": "UNOBSERVED",
                "familyEvidenceText": "La captura cambió durante la lectura",
                "dspExecutionState": "UNOBSERVED",
                "dspExecutionText": "No hay lectura estable de la ejecución",
                "familyEvidenceReasons": ["ST_C6_CROSS_OWNER_READ_UNSTABLE"],
                "presentationWarning": "ST_C6_CROSS_OWNER_READ_UNSTABLE",
            }
        )
        return payload
    payload["stages"] = overlay_qml_stages(payload.get("stages", ()), view)
    payload.update(view.to_qml())
    return payload
