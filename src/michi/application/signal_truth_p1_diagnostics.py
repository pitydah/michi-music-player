"""AP2-F11 A48: privacy-preserving, opt-in diagnostics projection only.

Strict allowlisting, bounded depth, and no raw identifiers, paths, names or
free-form strings. No file I/O or network access. The owning UI implements
consent and display, and the caller serializes the returned JSON itself.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping

_REASON = re.compile(r"^(?:ST|F11|AP2)_[A-Z0-9_]{1,90}$")
_SCOPES = {"ACTIVE", "PENDING", "HISTORICAL", "NOT_ACTIVE", "NONE"}
_FAMILY = {
    "direct_pcm",
    "managed_pcm",
    "shared_pcm",
    "dsd_to_pcm",
    "native_dsd",
    "dop",
    "unknown",
}
_PROOF = {
    "UNPROVEN",
    "PARTIAL",
    "UNKNOWN",
    "CONTRADICTED",
    "MATCHED_PARTIAL",
    "MATCHED_COMPLETE",
}
_BOUNDARY = {
    "NONE",
    "SOURCE",
    "DECODE",
    "PROCESSING_HOST",
    "ALSA",
    "USB_SUBMITTED",
    "REMOTE_REPORTED",
    "DIGITAL_TAP",
    "UNKNOWN",
}
_METRICS = frozenset(
    {
        "sample_peak_dbfs",
        "true_peak_dbtp",
        "integrated_lufs",
        "clipped_samples",
        "xrun_events",
        "processing_speed",
        "owner_to_ui_ms",
        "frame_dispatch_ms",
    }
)


def _known(value: object, allowed: set[str] | frozenset[str], *, fallback: str) -> str:
    return value if type(value) is str and value in allowed else fallback


def _reasons(value: object) -> list[str]:
    if not isinstance(value, (tuple, list)):
        return []
    return list(
        dict.fromkeys(s for s in value[:64] if type(s) is str and _REASON.fullmatch(s))
    )


def _metric_rows(metrics: object) -> list[dict[str, object]]:
    if not isinstance(metrics, Mapping):
        return []
    rows = []
    for name in sorted(_METRICS):
        metric = metrics.get(name)
        if hasattr(metric, "to_json"):
            metric = metric.to_json()
        if not isinstance(metric, Mapping):
            continue
        state = _known(
            metric.get("state"),
            {"OBSERVED", "PARTIAL", "UNOBSERVED"},
            fallback="UNOBSERVED",
        )
        raw_value = metric.get("value")
        value = None
        if state != "UNOBSERVED" and type(raw_value) in (int, float):
            from math import isfinite

            if isfinite(raw_value) and -1_000_000 <= raw_value <= 1_000_000:
                value = round(float(raw_value), 5)
        count = metric.get("count")
        missing = metric.get("missing")
        rows.append(
            {
                "metric": name,
                "state": state if value is not None else "UNOBSERVED",
                "value": value,
                "count": count if type(count) is int and 0 <= count <= 2048 else 0,
                "missing": missing
                if type(missing) is int and 0 <= missing <= 1000000
                else 0,
            }
        )
    return rows


def build_diagnostic_report(
    *,
    frame: Mapping[str, object],
    metrics: object = None,
    consent: bool,
    include_metric_samples: bool = False,
) -> dict[str, object]:
    """Build only nonidentifying facts; ignore all caller-provided other keys.

    `consent=True` is mandatory; no raw audio, paths, usernames, device IDs,
    network addresses, track metadata, free-form error text or DSP coefficients.
    `include_metric_samples` only controls aggregate counters, never PCM.
    """
    if consent is not True:
        raise PermissionError("explicit diagnostics consent required")
    if not isinstance(frame, Mapping):
        raise TypeError("read model mapping required")
    scope = _known(frame.get("status"), _SCOPES, fallback="NOT_ACTIVE")
    family = _known(
        frame.get("audioFamily", frame.get("family")), _FAMILY, fallback="unknown"
    )
    proof = _known(frame.get("fidelityClaim"), _PROOF, fallback="UNPROVEN")
    # The UI DTO is not M11.5's evidence authority. Never copy a MATCHED_* or
    # PARTIAL proof into an exported claim without an owner-certified object.
    if proof in {"MATCHED_COMPLETE", "MATCHED_PARTIAL", "PARTIAL"}:
        proof = "UNPROVEN"
    boundary = _known(frame.get("lastProvenBoundary"), _BOUNDARY, fallback="UNKNOWN")
    operation_count = frame.get("operationCount", 0)
    stage_count = frame.get("stageCount", 0)
    report: dict[str, object] = {
        "schema": "michi.signal_truth.diagnostics.public.v1",
        "redaction_policy": "ALLOWLIST_NO_IDENTIFIERS",
        "scope": scope,
        "family": family,
        "fidelity_claim": proof,
        "observed_boundary": boundary,
        "operation_count": operation_count
        if type(operation_count) is int and 0 <= operation_count <= 256
        else 0,
        "stage_count": stage_count
        if type(stage_count) is int and 0 <= stage_count <= 256
        else 0,
        "reasons": _reasons(frame.get("reasonCodes")),
        "measurements": _metric_rows(metrics)
        if include_metric_samples and scope == "ACTIVE"
        else [],
        "physical_dac_verified": False,
    }
    # Prevent silent object serialization / unbounded free-form data growth.
    if len(json.dumps(report, ensure_ascii=True, allow_nan=False).encode()) > 32_768:
        raise ValueError("public report too large")
    return report
