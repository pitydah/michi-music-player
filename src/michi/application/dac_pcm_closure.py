"""M11.4 final PCM physical-closure evidence model.

Pure logic only: no Qt, ALSA, GStreamer, filesystem probing or mutable runtime
authority. Field tooling writes device manifests; this module validates and
summarizes them without upgrading evidence beyond what was actually observed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_PCM_EXPERIMENTS = ("R24", "R25", "R32", "R35", "R36")
ALLOWED_EXPERIMENT_STATUSES = {
    "PASS",
    "FAIL",
    "NOT_RUN",
    "NOT_APPLICABLE",
    "REQUIRES_OPERATOR_CONFIRMATION",
}
PASSING_DEVICE_VERDICT = "PASS"
INCOMPLETE_DEVICE_VERDICT = "INCOMPLETE"
FAILED_DEVICE_VERDICT = "FAIL"

PHYSICAL_NOT_RUN = "NOT_RUN"
PHYSICAL_INCOMPLETE = "INCOMPLETE"
PHYSICAL_FAIL = "FAIL"
PHYSICAL_PASS_BOUNDED = "PASS_BOUNDED"
PHYSICAL_PASS_MULTI_HARDWARE = "PASS_MULTI_HARDWARE"


class PcmClosureEvidenceError(ValueError):
    """Malformed or internally contradictory physical-closure evidence."""


@dataclass(frozen=True, slots=True)
class DeviceIdentityEvidence:
    stable_device_id: str
    locator: str
    vendor_id: str
    product_id: str
    bcd_device: str
    manufacturer: str
    product: str
    descriptor_hash: str

    @property
    def material_fingerprint(self) -> tuple[str, ...]:
        return (
            self.vendor_id.casefold(),
            self.product_id.casefold(),
            self.bcd_device.casefold(),
            self.manufacturer.casefold(),
            self.product.casefold(),
            self.descriptor_hash.casefold(),
        )


@dataclass(frozen=True, slots=True)
class DeviceClosureVerdict:
    identity: DeviceIdentityEvidence
    experiment_status: tuple[tuple[str, str], ...]
    verdict: str
    reasons: tuple[str, ...]
    implementation_head: str = ""
    evidence_execution_head: str = ""
    manifest_created_at: str = ""


@dataclass(frozen=True, slots=True)
class PcmClosureSummary:
    implementation_scope: str
    physical_verdict: str
    multi_hardware_proven: bool
    devices: tuple[DeviceClosureVerdict, ...]
    bit_perfect_claimed: bool = False
    m11_5_in_scope: bool = False
    dac_v35_120_in_scope: bool = False
    dac_v35_130_in_scope: bool = False
    dac_v35_140_in_scope: bool = False


@dataclass(frozen=True, slots=True)
class ClosureObligation:
    """One explicit closure obligation with its remaining gaps.

    A green test suite does not prove a product obligation, so the canonical
    verifier must not infer COMPLETE from passing gates. Each obligation is
    declared here with the concrete gap that is still open; the verdict is
    COMPLETE only when every obligation is genuinely satisfied.
    """

    key: str
    label: str
    complete: bool
    gaps: tuple[str, ...] = ()


#: Product obligations for M11.4 PCM. Flipping one to complete requires the
#: code, the tests and the evidence that prove it - never a passing gate alone.
IMPLEMENTATION_OBLIGATIONS: tuple[ClosureObligation, ...] = (
    ClosureObligation(
        "normal_dac_playback",
        "Choosing a DAC from the normal surface routes playback through it",
        True,
    ),
    ClosureObligation(
        "failure_recovery_ux",
        "The refusal carries its recovery intents on the normal surface",
        True,
    ),
    ClosureObligation(
        "startup_refusal_publication",
        "A refused startup resume publishes its typed failure",
        True,
    ),
    ClosureObligation(
        "evidence_provenance",
        "Evidence provenance is internally coherent per event",
        True,
    ),
    ClosureObligation(
        "resync_delay_runtime",
        "OutputPlan.resync_delay_ms has a real runtime effect",
        True,
    ),
    ClosureObligation(
        "resync_timing_safety",
        "The resync deadline cannot strand the pipeline and its evidence is fresh",
        False,
        (
            "coarse QTimer can wake early and the callback does not re-arm, "
            "which can leave the pipeline PAUSED",
            "resync_actual_hold_ms is not reset per execution and can expose "
            "a previous track's hold",
        ),
    ),
    ClosureObligation(
        "resync_eos_replay",
        "EOS replay under a nonzero delay keeps the configured hold",
        False,
        ("fail-closed typed refusal; the post-EOS hold is not implemented",),
    ),
    ClosureObligation(
        "try_compatible_retries",
        "Try Compatible Direct actually retries the refused request",
        True,
    ),
    ClosureObligation(
        "active_track_reroute",
        "Selecting a DAC reroutes the track that is already playing",
        True,
    ),
    ClosureObligation(
        "handover_purpose_separated",
        "Live handover is not a startup restore and never confirms a resume",
        True,
    ),
    ClosureObligation(
        "handover_state_contract",
        "Handover preserves position and only resumes when it was playing",
        True,
    ),
    ClosureObligation(
        "documentation_state_alignment",
        "Governance state is not mixed with the physical evidence verdict",
        True,
    ),
)

#: Physical-closure tooling obligations. A lab script existing and one manifest
#: being present is NOT tooling completeness.
TOOLING_OBLIGATIONS: tuple[ClosureObligation, ...] = (
    ClosureObligation("R24", "Clock authority tooling", True),
    ClosureObligation(
        "R25",
        "Rate-transition tooling",
        False,
        (
            "real sweep aggregation and minimum-delay selection",
            "first-sample evidence reference/method requirement",
            "the lab does not consume the runtime's measured actual hold",
        ),
    ),
    ClosureObligation(
        "R32",
        "Soak tooling",
        False,
        (
            "growth/pump/USB/transition evidence must be part of PASS",
            "transition_failures accounting is a no-op",
            "ownership is read from provider.pipelines, not current_port",
            "USB counters are not device-bound",
        ),
    ),
    ClosureObligation(
        "R35",
        "Tail/drain tooling",
        False,
        (
            "all four canonical fixtures required before PASS",
            "capture artifact/hash validation",
        ),
    ),
    ClosureObligation(
        "R36",
        "XRUN and recovery tooling",
        False,
        (
            "operator workflow for suspend/resume and device failure",
            "measured recovery, continuity and loop facts",
        ),
    ),
)


#: Cross-cutting finalization obligations for the experimental program.
FINALIZATION_OBLIGATIONS: tuple[ClosureObligation, ...] = (
    ClosureObligation(
        "lab_semantic_checks",
        "_semantic_pass_check reflects the canonical R25/R32/R35/R36 contracts",
        False,
        ("nominal PASS can still omit the required structured facts",),
    ),
    ClosureObligation(
        "lab_tests",
        "the field lab itself is covered by tests",
        False,
        ("no test executes scripts/dac_m11_4_pcm_lab.py",),
    ),
    ClosureObligation(
        "docs_reconciled",
        "M11_4 contract matches the real tooling state",
        False,
        ("environment-doc reconciliation pending",),
    ),
    ClosureObligation(
        "finalization_wiring",
        "Finalization obligations participate in the closure verdict",
        False,
        ("the verifier imports only implementation and tooling obligations",),
    ),
)


def closure_verdict(obligations: tuple[ClosureObligation, ...]) -> str:
    return "COMPLETE" if all(item.complete for item in obligations) else "INCOMPLETE"


def closure_gaps(obligations: tuple[ClosureObligation, ...]) -> tuple[str, ...]:
    return tuple(
        f"{item.key}: {gap}"
        for item in obligations
        if not item.complete
        for gap in item.gaps
    )


def obligation_report(
    obligations: tuple[ClosureObligation, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "key": item.key,
            "label": item.label,
            "complete": item.complete,
            "gaps": list(item.gaps),
        }
        for item in obligations
    ]


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PcmClosureEvidenceError(
            f"cannot read closure manifest {path}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise PcmClosureEvidenceError(f"closure manifest must be a JSON object: {path}")
    return payload


def _required_text(mapping: dict[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PcmClosureEvidenceError(f"missing non-empty {key!r}")
    return value.strip()


def _identity(payload: dict[str, Any]) -> DeviceIdentityEvidence:
    raw = payload.get("device")
    if not isinstance(raw, dict):
        raise PcmClosureEvidenceError("manifest.device must be an object")
    return DeviceIdentityEvidence(
        stable_device_id=_required_text(raw, "stable_device_id"),
        locator=_required_text(raw, "locator"),
        vendor_id=str(raw.get("vendor_id") or ""),
        product_id=str(raw.get("product_id") or ""),
        bcd_device=str(raw.get("bcd_device") or ""),
        manufacturer=str(raw.get("manufacturer") or ""),
        product=str(raw.get("product") or ""),
        descriptor_hash=str(raw.get("descriptor_hash") or ""),
    )


def _experiment_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    experiments = payload.get("experiments")
    if not isinstance(experiments, dict):
        raise PcmClosureEvidenceError("manifest.experiments must be an object")
    normalized: dict[str, dict[str, Any]] = {}
    for experiment in REQUIRED_PCM_EXPERIMENTS:
        item = experiments.get(experiment)
        if not isinstance(item, dict):
            raise PcmClosureEvidenceError(f"missing experiment {experiment}")
        status = str(item.get("status") or "").upper()
        if status not in ALLOWED_EXPERIMENT_STATUSES:
            raise PcmClosureEvidenceError(f"{experiment} has invalid status {status!r}")
        normalized[experiment] = item
    return normalized


def _pass_has_evidence(experiment: str, item: dict[str, Any]) -> bool:
    evidence = item.get("evidence")
    return (
        item.get("executed") is True
        and isinstance(evidence, list)
        and bool(evidence)
        and all(isinstance(entry, str) and entry.strip() for entry in evidence)
    )


def _semantic_pass_check(experiment: str, item: dict[str, Any]) -> str | None:
    """Return a contradiction reason for a nominal PASS, otherwise None."""
    if not _pass_has_evidence(experiment, item):
        return "PASS lacks executed=true plus non-empty evidence references"

    facts = item.get("facts")
    if not isinstance(facts, dict):
        return "PASS lacks structured facts"

    if experiment == "R24":
        if facts.get("sink_provides_clock") is not True:
            return "R24 did not prove that the sink provides a clock"
        if facts.get("sink_clock_is_pipeline_clock") is not True:
            return "R24 did not prove that the sink clock is the pipeline clock"
        if facts.get("resampling_observed") is True:
            return "R24 observed resampling"
    elif experiment == "R25":
        required_edges = {
            "44100->44100",
            "44100->48000",
            "48000->44100",
            "44100->96000",
            "96000->192000",
            "192000->44100",
        }
        observed = {
            str(edge)
            for edge in facts.get("transition_edges", [])
            if isinstance(edge, str)
        }
        missing = sorted(required_edges - observed)
        if missing:
            return f"R25 missing transition edges: {missing}"
        if facts.get("first_sample_result") != "PASS":
            return "R25 first-sample integrity is not PASS"
        if facts.get("stale_generation_observed") is True:
            return "R25 observed stale-generation truth"
    elif experiment == "R32":
        duration = facts.get("duration_seconds")
        if not isinstance(duration, (int, float)) or duration < 28800:
            return "R32 PASS requires at least 28800 seconds (8 h verified soak)"
        if int(facts.get("xrun_count", 0)) != 0:
            return "R32 observed XRUNs"
        if int(facts.get("runtime_error_count", 0)) != 0:
            return "R32 observed runtime errors"
    elif experiment == "R35":
        if facts.get("tail_result") != "PASS":
            return "R35 tail/drain integrity is not PASS"
        if facts.get("evidence_kind") not in {"capture", "operator"}:
            return "R35 requires capture or explicit operator evidence"
    elif experiment == "R36":
        if facts.get("fault_injected") is not True:
            return "R36 did not inject a real XRUN"
        if facts.get("xrun_observed") is not True:
            return "R36 did not observe the injected XRUN"
        if facts.get("false_verified_after_xrun") is True:
            return "R36 retained a false verified state after XRUN"
        if facts.get("recovery_loop_observed") is True:
            return "R36 observed a recovery loop"
    return None


def _manifest_provenance(payload: dict[str, Any]) -> tuple[str, str, str]:
    """Bind evidence to the code that produced it, never to the current tree.

    A manifest is committed AFTER the run that produced it, so requiring its
    recorded head to equal the current HEAD would make every archived manifest
    stale by construction. The contract is instead:

    - ``implementation_head``: the product commit the evidence is bound to;
    - ``events[].collected_head``: the head that collected each observation;
    - ``evidence_execution_head``: the head of the LAST collected event (or the
      implementation head while the manifest has no events yet).

    The manifest is therefore coherent only when its top-level execution head
    agrees with its own events. Appending evidence collected from a different
    head is exactly what must show up, never hide, in the archive.
    """
    manifest_schema = payload.get("manifest_schema", 1)
    if manifest_schema not in (1, 2):
        raise PcmClosureEvidenceError("unsupported closure manifest schema")
    if manifest_schema == 1:
        head = _required_text(payload, "execution_git_head")
        return head, head, ""
    implementation_head = _required_text(payload, "implementation_head")
    execution_head = _required_text(payload, "evidence_execution_head")
    created_at = _required_text(payload, "manifest_created_at")
    if len(implementation_head) != 40 or len(execution_head) != 40:
        raise PcmClosureEvidenceError("closure manifest heads must be full commit ids")
    legacy = payload.get("execution_git_head")
    if legacy is not None and legacy != implementation_head:
        raise PcmClosureEvidenceError(
            "execution_git_head contradicts the declared provenance"
        )
    # Per-event provenance: every recorded observation names the head that
    # collected it, and the manifest-level execution head must agree with the
    # LAST event. A manifest whose top level disagrees with its own events is a
    # provenance contradiction rather than a valid archive.
    events = payload.get("events", [])
    if events is None:
        events = []
    if not isinstance(events, list):
        raise PcmClosureEvidenceError("manifest.events must be a list")
    collected: list[str] = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise PcmClosureEvidenceError(f"manifest.events[{index}] must be an object")
        head = event.get("collected_head")
        if not isinstance(head, str) or len(head) != 40:
            raise PcmClosureEvidenceError(
                f"manifest.events[{index}] is missing a full collected_head"
            )
        collected.append(head)
    expected_execution_head = collected[-1] if collected else implementation_head
    if execution_head != expected_execution_head:
        raise PcmClosureEvidenceError(
            "evidence_execution_head must equal the last collected event head "
            f"({expected_execution_head[:8]}), not {execution_head[:8]}"
        )
    return implementation_head, execution_head, created_at


def evaluate_device_manifest(payload: dict[str, Any]) -> DeviceClosureVerdict:
    if payload.get("schema_version") != 1:
        raise PcmClosureEvidenceError("unsupported closure manifest schema")
    implementation_head, execution_head, created_at = _manifest_provenance(payload)
    _required_text(payload, "environment_fingerprint")
    identity = _identity(payload)
    experiments = _experiment_map(payload)

    reasons: list[str] = []
    statuses: list[tuple[str, str]] = []
    has_fail = False
    all_pass = True
    for experiment in REQUIRED_PCM_EXPERIMENTS:
        item = experiments[experiment]
        status = str(item["status"]).upper()
        statuses.append((experiment, status))
        if status == "FAIL":
            has_fail = True
            all_pass = False
            reasons.append(f"{experiment}=FAIL")
            continue
        if status != "PASS":
            all_pass = False
            reasons.append(f"{experiment}={status}")
            continue
        contradiction = _semantic_pass_check(experiment, item)
        if contradiction is not None:
            has_fail = True
            all_pass = False
            reasons.append(f"{experiment}: {contradiction}")

    verdict = (
        FAILED_DEVICE_VERDICT
        if has_fail
        else PASSING_DEVICE_VERDICT
        if all_pass
        else INCOMPLETE_DEVICE_VERDICT
    )
    return DeviceClosureVerdict(
        identity=identity,
        experiment_status=tuple(statuses),
        verdict=verdict,
        reasons=tuple(reasons),
        implementation_head=implementation_head,
        evidence_execution_head=execution_head,
        manifest_created_at=created_at,
    )


def materially_distinct(
    left: DeviceIdentityEvidence, right: DeviceIdentityEvidence
) -> bool:
    """Conservative proof that two manifests do not describe the same DAC."""
    if left.stable_device_id == right.stable_device_id:
        return False
    left_pair = (left.vendor_id.casefold(), left.product_id.casefold())
    right_pair = (right.vendor_id.casefold(), right.product_id.casefold())
    if all(left_pair) and all(right_pair) and left_pair != right_pair:
        return True
    if (
        left.descriptor_hash
        and right.descriptor_hash
        and left.descriptor_hash != right.descriptor_hash
    ):
        return True
    left_named = (left.manufacturer.casefold(), left.product.casefold())
    right_named = (right.manufacturer.casefold(), right.product.casefold())
    return all(left_named) and all(right_named) and left_named != right_named


def summarize_manifests(payloads: list[dict[str, Any]]) -> PcmClosureSummary:
    devices = tuple(evaluate_device_manifest(payload) for payload in payloads)
    if not devices:
        physical = PHYSICAL_NOT_RUN
        multi = False
    elif any(item.verdict == FAILED_DEVICE_VERDICT for item in devices):
        physical = PHYSICAL_FAIL
        multi = False
    else:
        passed = [item for item in devices if item.verdict == PASSING_DEVICE_VERDICT]
        multi = any(
            materially_distinct(left.identity, right.identity)
            for index, left in enumerate(passed)
            for right in passed[index + 1 :]
        )
        if multi:
            physical = PHYSICAL_PASS_MULTI_HARDWARE
        elif passed:
            physical = PHYSICAL_PASS_BOUNDED
        else:
            physical = PHYSICAL_INCOMPLETE

    return PcmClosureSummary(
        implementation_scope="M11.4_PCM",
        physical_verdict=physical,
        multi_hardware_proven=multi,
        devices=devices,
    )


def summary_to_dict(summary: PcmClosureSummary) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "implementation_scope": summary.implementation_scope,
        "physical_verdict": summary.physical_verdict,
        "multi_hardware_proven": summary.multi_hardware_proven,
        "bit_perfect_claimed": summary.bit_perfect_claimed,
        "out_of_scope": {
            "M11.5": not summary.m11_5_in_scope,
            "DAC-V35-120": not summary.dac_v35_120_in_scope,
            "DAC-V35-130": not summary.dac_v35_130_in_scope,
            "DAC-V35-140": not summary.dac_v35_140_in_scope,
        },
        "devices": [
            {
                "stable_device_id": item.identity.stable_device_id,
                "locator": item.identity.locator,
                "verdict": item.verdict,
                "implementation_head": item.implementation_head,
                "evidence_execution_head": item.evidence_execution_head,
                "manifest_created_at": item.manifest_created_at,
                "experiments": dict(item.experiment_status),
                "reasons": list(item.reasons),
            }
            for item in summary.devices
        ],
    }
