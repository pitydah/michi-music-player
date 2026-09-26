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


def evaluate_device_manifest(payload: dict[str, Any]) -> DeviceClosureVerdict:
    if payload.get("schema_version") != 1:
        raise PcmClosureEvidenceError("unsupported closure manifest schema")
    _required_text(payload, "execution_git_head")
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
                "experiments": dict(item.experiment_status),
                "reasons": list(item.reasons),
            }
            for item in summary.devices
        ],
    }
