#!/usr/bin/env python3
"""AP2-F11 A47: offline P0 contract verifier (NOT a runtime truth authority).

Validates candidate envelopes against the versioned Signal Truth contract and
implements an independent mathematical coverage oracle for *test fixtures*.
No DAC access, no Qt, no recorder mutation, no claim of product qualification.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

SCHEMA = "michi.signal_truth.p0.v1"
MAX_OPS = 24
MAX_SEGS = 4096
MAX_FRAME_SPAN = 2**48
KIND = frozenset(
    {
        "decode",
        "resample",
        "channel-remap",
        "peq",
        "fir",
        "gain",
        "headroom",
        "dither",
        "requantize",
        "mix",
        "dsd-to-pcm",
        "dop-pack",
    }
)
TRANSPORT = frozenset(
    {"direct_pcm", "managed_pcm", "shared_pcm", "dsd_to_pcm", "native_dsd", "dop"}
)
OP_STATES = frozenset(
    {"REQUESTED", "BUILT", "RUNTIME_OBSERVED", "ADOPTED", "UNOBSERVED", "REVOKED"}
)
EVIDENCE = frozenset(
    {
        "SOURCE_METADATA",
        "CONFIGURED",
        "REQUESTED",
        "ACKNOWLEDGED",
        "READBACK_CONFIRMED",
        "ADOPTED_BY_AUDIO",
        "RUNTIME_NEGOTIATED",
        "SAMPLE_COMPARISON",
        "ENDPOINT_SELF_REPORTED",
        "UNKNOWN",
    }
)
RECEIVER = frozenset(
    {
        "UNKNOWN",
        "USB_ACK",
        "ENDPOINT_SELF_REPORTED",
        "ALSA_NEGOTIATED",
        "EXTERNALLY_MEASURED",
    }
)
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@-]{0,95}$")


class Coverage(StrEnum):
    MATCHED_COMPLETE = "MATCHED_COMPLETE"
    MATCHED_PARTIAL = "MATCHED_PARTIAL"
    MISMATCH = "MISMATCH"
    INCONCLUSIVE = "INCONCLUSIVE"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"


@dataclass(frozen=True, slots=True)
class CoverageResult:
    verdict: Coverage
    boundary: str
    compared_channel_frames: int
    expected_channel_frames: int
    gaps: int
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "verdict": self.verdict.value,
            "boundary": self.boundary,
            "compared_channel_frames": self.compared_channel_frames,
            "expected_channel_frames": self.expected_channel_frames,
            "gaps": self.gaps,
            "reason": self.reason,
            "physical_dac_verified": False,
        }


def _positive(v: object) -> bool:
    return type(v) is int and v > 0


def _nonneg(v: object) -> bool:
    return type(v) is int and v >= 0


def _id(v: object) -> bool:
    return isinstance(v, str) and bool(ID.fullmatch(v))


def _fmt(fmt: object, *, family: str) -> bool:
    if not isinstance(fmt, Mapping) or fmt.get("family") != family:
        return False
    if family == "PCM":
        return (
            (fmt.get("rate_hz") is None or _positive(fmt.get("rate_hz")))
            and (fmt.get("channels") is None or _positive(fmt.get("channels")))
            and (
                fmt.get("significant_bits") is None
                or _positive(fmt.get("significant_bits"))
            )
        )
    if family == "DSD":
        return (
            fmt.get("dsd_rate") is None or _id(fmt.get("dsd_rate"))
        ) and "significant_bits" not in fmt
    return False


def _acyclic(ops: list[Mapping[str, Any]]) -> bool:
    links = {o["operation_instance_id"]: tuple(o.get("predecessors", ())) for o in ops}
    status: dict[str, int] = {}

    def visit(u: str) -> bool:
        if status.get(u) == 1:
            return False
        if status.get(u) == 2:
            return True
        status[u] = 1
        for v in links[u]:
            if v not in links or v == u or not visit(v):
                return False
        status[u] = 2
        return True

    return all(visit(u) for u in links)


def validate_envelope(raw: object) -> tuple[str, ...]:
    """Schema/causal *shape* only. A valid payload is never evidence of DAC proof."""
    errors: list[str] = []
    if not isinstance(raw, Mapping):
        return ("P0_NOT_A_MAPPING",)
    if raw.get("schema") != SCHEMA:
        errors.append("P0_SCHEMA_VERSION")
    if not isinstance(raw.get("status"), str) or raw.get("status") not in {
        "ACTIVE",
        "PENDING",
        "HISTORICAL",
        "NOT_ACTIVE",
    }:
        errors.append("P0_TEMPORAL")
    ident = raw.get("identity")
    required = (
        "output_plan_id",
        "execution_generation",
        "port_generation",
        "binding_generation",
        "media_epoch",
        "route_epoch",
        "branch_id",
        "endpoint_stable_id",
    )
    if not isinstance(ident, Mapping) or any(
        not (
            _positive(ident.get(key))
            if key.endswith("generation") or key.endswith("epoch")
            else _id(ident.get(key))
        )
        for key in required
    ):
        errors.append("P0_IDENTITY_FENCE")
    family = raw.get("family")
    if not isinstance(family, Mapping):
        errors.append("P0_FAMILY_MISSING")
        family = {}
    tr = family.get("transport")
    src, sink = family.get("source_family"), family.get("sink_family")
    if not isinstance(tr, str) or tr not in TRANSPORT:
        errors.append("P0_TRANSPORT_UNSUPPORTED")
    expected = {
        "direct_pcm": ("PCM", "PCM"),
        "managed_pcm": ("PCM", "PCM"),
        "shared_pcm": ("PCM", "PCM"),
        "dsd_to_pcm": ("DSD", "PCM"),
        "native_dsd": ("DSD", "DSD"),
        "dop": ("DSD", "DSD"),
    }
    if isinstance(tr, str) and tr in expected and (src, sink) != expected[tr]:
        errors.append("P0_FAMILY_DOMAIN_MISMATCH")
    if (
        not isinstance(family.get("receiver_evidence"), str)
        or family.get("receiver_evidence") not in RECEIVER
    ):
        errors.append("P0_RECEIVER_EVIDENCE")
    carrier = family.get("carrier")
    if tr == "dop":
        if (
            not isinstance(carrier, Mapping)
            or carrier.get("family") != "PCM_CARRIER"
            or not _positive(carrier.get("rate_hz"))
        ):
            errors.append("P0_DOP_CARRIER_UNOBSERVED")
    elif carrier is not None:
        errors.append("P0_CARRIER_MUST_BE_NULL")
    if tr == "native_dsd" and family.get("decoded_pcm") is not None:
        errors.append("P0_NATIVE_DSD_FAKE_PCM")
    if tr == "dop" and family.get("decoded_pcm") is not None:
        errors.append("P0_DOP_FAKE_PCM")
    if (
        tr == "dsd_to_pcm"
        and family.get("state") == "RUNNING_REPORTED"
        and (
            family.get("pcm_host_receipt") is None
            or not _id(family.get("pcm_host_receipt"))
        )
    ):
        errors.append("P0_DSD_PCM_HOST_RECEIPT_REQUIRED")
    if (
        tr == "shared_pcm"
        and family.get("alsa_negotiated") is not None
        and not _id(family.get("alsa_receipt_id"))
    ):
        # Shared mode cannot claim a raw ALSA hw_params receipt by inference.
        errors.append("P0_SHARED_ALSA_PROOF_UNSCOPED")
    if not isinstance(family.get("state"), str) or family.get("state") not in {
        "UNOBSERVED",
        "PREPARING",
        "READY_REPORTED",
        "RUNNING_REPORTED",
        "TERMINATED",
    }:
        errors.append("P0_FAMILY_STATE")
    if family.get("state") == "RUNNING_REPORTED" and not _id(
        family.get("owner_receipt_id")
    ):
        errors.append("P0_OUTPUT_OWNER_RECEIPT_MISSING")
    if family.get("receiver_evidence") == "EXTERNALLY_MEASURED" and not _id(
        family.get("external_measurement_id")
    ):
        errors.append("P0_EXTERNAL_MEASUREMENT_ID")
    ops = raw.get("operations")
    if not isinstance(ops, list) or len(ops) > MAX_OPS:
        errors.append("P0_OPERATION_COUNT")
        ops = []
    ids: set[str] = set()
    safe: list[Mapping[str, Any]] = []
    for n, op in enumerate(ops):
        if not isinstance(op, Mapping):
            errors.append(f"P0_OP_{n}_INVALID")
            continue
        oid = op.get("operation_instance_id")
        if not _id(oid) or oid in ids:
            errors.append(f"P0_OP_{n}_IDENTITY_OR_DUPLICATE")
            continue
        ids.add(oid)
        safe.append(op)
        if (
            not isinstance(op.get("kind"), str)
            or op.get("kind") not in KIND
            or not isinstance(op.get("state"), str)
            or op.get("state") not in OP_STATES
        ):
            errors.append(f"P0_OP_{n}_KIND_OR_STATE")
        if not _id(op.get("producer_id")) or not _id(op.get("evidence_ref")):
            errors.append(f"P0_OP_{n}_PROVENANCE")
        if (
            not isinstance(ident, Mapping)
            or op.get("branch_id") != ident.get("branch_id")
            or (op.get("execution_generation") != ident.get("execution_generation"))
        ):
            errors.append(f"P0_OP_{n}_EPOCH_MISMATCH")
        predecessors = op.get("predecessors", [])
        if not isinstance(predecessors, list) or any(not _id(v) for v in predecessors):
            errors.append(f"P0_OP_{n}_EDGES")
        elif predecessors and not _id(op.get("order_evidence_ref")):
            errors.append(f"P0_OP_{n}_UNPROVEN_ORDER")
        if (
            not isinstance(op.get("evidence_class"), str)
            or op.get("evidence_class") not in EVIDENCE
        ):
            errors.append(f"P0_OP_{n}_EVIDENCE_CLASS")
        if op.get("state") == "ADOPTED" and not _id(op.get("adoption_receipt_id")):
            errors.append(f"P0_OP_{n}_ADOPTION_UNPROVEN")
        inp, out = op.get("input_format"), op.get("output_format")
        if inp is not None and not _fmt(
            inp, family=inp.get("family") if isinstance(inp, Mapping) else ""
        ):
            errors.append(f"P0_OP_{n}_INPUT_FORMAT")
        if out is not None and not _fmt(
            out, family=out.get("family") if isinstance(out, Mapping) else ""
        ):
            errors.append(f"P0_OP_{n}_OUTPUT_FORMAT")
    if len(safe) == len(ops) and not _acyclic(safe):
        errors.append("P0_OPERATION_DAG_INVALID")
    proof = raw.get("fidelity")
    if not isinstance(proof, Mapping):
        errors.append("P0_FIDELITY_MISSING")
    else:
        # Positive sample claims are made ONLY by M11.5 after independent
        # evidence collection. This offline plan verifier cannot issue them.
        if proof.get("claim") != "UNPROVEN":
            errors.append("P0_FIDELITY_M11_5_OWNER_REQUIRED")
        if proof.get("dac_analog_verified") is not False:
            errors.append("P0_ANALOG_CERTIFICATION_FORBIDDEN")
    return tuple(dict.fromkeys(errors))


def evaluate_pcm_coverage(spec: object) -> CoverageResult:
    """Independent exact-fixture coverage audit limited to a named *digital* tap.

    Does not establish that any segment was honestly sampled from an audio
    engine; M11.5 must independently authenticate producer and instrumentation.
    """

    def bad(result, reason):
        return CoverageResult(result, boundary, 0, expected, expected, reason)

    if not isinstance(spec, Mapping):
        return CoverageResult(
            Coverage.INCONCLUSIVE, "UNSPECIFIED", 0, 0, 0, "P0_NO_SPEC"
        )
    boundary = str(spec.get("boundary") or "UNSPECIFIED")
    start, end, channels = (
        spec.get("frame_start"),
        spec.get("frame_end"),
        spec.get("channels"),
    )
    if spec.get("family") != "PCM":
        return CoverageResult(
            Coverage.UNSUPPORTED, boundary, 0, 0, 0, "P0_NON_PCM_ORACLE"
        )
    if not (
        _nonneg(start)
        and _positive(end)
        and start < end
        and end - start <= MAX_FRAME_SPAN
        and isinstance(channels, list)
        and 1 <= len(channels) <= 64
        and all(_id(c) for c in channels)
        and len(set(channels)) == len(channels)
    ):
        return CoverageResult(Coverage.INCONCLUSIVE, boundary, 0, 0, 0, "P0_BAD_SCOPE")
    expected = (end - start) * len(channels)
    if not _id(spec.get("execution_id")) or not _id(spec.get("tap_id")):
        return bad(Coverage.INCONCLUSIVE, "P0_TAP_OR_EXECUTION_MISSING")
    if spec.get("method") != "SAMPLE_EXACT" or not _id(spec.get("source_trace_id")):
        return bad(Coverage.INCONCLUSIVE, "P0_NOT_EXACT_SAMPLES")
    segments = spec.get("segments")
    if not isinstance(segments, list) or len(segments) > MAX_SEGS:
        return bad(Coverage.INCONCLUSIVE, "P0_SEGMENT_LIMIT")
    by_ch: dict[str, list[tuple[int, int, bool]]] = {c: [] for c in channels}
    for seg in segments:
        if not isinstance(seg, Mapping):
            return bad(Coverage.INCONCLUSIVE, "P0_BAD_SEGMENT")
        c, a, b, exact = (
            seg.get(x) for x in ("channel", "start", "end", "exact_equal")
        )
        if (
            not isinstance(c, str)
            or c not in by_ch
            or not (_nonneg(a) and _positive(b) and start <= a < b <= end)
            or type(exact) is not bool
        ):
            return bad(Coverage.CONTRADICTED, "P0_SEGMENT_OUTSIDE_SCOPE")
        by_ch[c].append((a, b, exact))
    compared = 0
    gaps = 0
    mismatch = False
    for c in channels:
        prev = start
        for a, b, eq in sorted(by_ch[c]):
            if a < prev:
                return CoverageResult(
                    Coverage.CONTRADICTED,
                    boundary,
                    compared,
                    expected,
                    max(0, expected - compared),
                    "P0_OVERLAPPING_SPANS",
                )
            gaps += a - prev
            compared += b - a
            mismatch |= not eq
            prev = b
        gaps += end - prev
    dropped = spec.get("dropped_frames", 0)
    if not _nonneg(dropped):
        return bad(Coverage.INCONCLUSIVE, "P0_DROP_COUNT_INVALID")
    if dropped:
        gaps = max(gaps, dropped)
    if mismatch:
        state = Coverage.MISMATCH
    elif compared == 0:
        state = Coverage.INCONCLUSIVE
    elif gaps or compared != expected:
        state = Coverage.MATCHED_PARTIAL
    else:
        state = Coverage.MATCHED_COMPLETE
    return CoverageResult(
        state,
        boundary,
        compared,
        expected,
        gaps,
        "P0_DIGITAL_TAP_ONLY"
        if state is Coverage.MATCHED_COMPLETE
        else "P0_COVERAGE_LIMITED",
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("envelope", type=Path)
    p.add_argument("--coverage", type=Path)
    args = p.parse_args()
    try:
        data = json.loads(args.envelope.read_text(encoding="utf-8"))
        findings = validate_envelope(data)
        coverage = (
            evaluate_pcm_coverage(
                json.loads(args.coverage.read_text(encoding="utf-8"))
            ).to_dict()
            if args.coverage
            else None
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        findings, coverage = ("P0_INPUT_UNREADABLE",), None
    result = {
        "schema": "michi.signal_truth.p0.validation.v1",
        "shape_status": "CANDIDATE_SCHEMA_VALID" if not findings else "REFUSED",
        "errors": list(findings),
        "product_runtime_status": "NOT_RUN",
        "ci_exact_sha": "NOT_RUN",
        "dac_physical_status": "NOT_RUN",
        "coverage_fixture": coverage,
        "approved_for_unattended_apply": False,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not findings else 2


if __name__ == "__main__":
    raise SystemExit(main())
