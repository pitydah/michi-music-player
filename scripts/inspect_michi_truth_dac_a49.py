#!/usr/bin/env python3
"""A49 capability-scoped DAC receipt intake: structural inspection only.

No JSON document proves audibility, bit-perfect, DoP receiver interpretation,
or exact hardware capability merely by claiming PASS. Real DAC qualification
requires qualified operator evidence, ALSA readback, source and device scope.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

FAMILIES = ("direct", "managed", "shared", "native_dsd", "dop", "dsd_pcm")


def inspect_receipts(receipts: object) -> dict[str, object]:
    records = receipts if isinstance(receipts, list) else []
    rows = []
    for family in FAMILIES:
        scoped = [
            r for r in records if isinstance(r, dict) and r.get("family") == family
        ]
        valid = []
        for r in scoped:
            must = (
                "device_id",
                "base_commit_sha",
                "capture_sha256",
                "observed_at",
                "source_family",
                "output_owner_receipt",
                "execution_id",
            )
            if any(not isinstance(r.get(k), str) or not r.get(k).strip() for k in must):
                continue
            if len(r["capture_sha256"]) != 64 or not all(
                x in "0123456789abcdef" for x in r["capture_sha256"].lower()
            ):
                continue
            if family in ("dop", "native_dsd") and not r.get("dsd_executor_readback"):
                continue
            if family in ("direct", "managed", "dsd_pcm") and not r.get(
                "negotiated_transport"
            ):
                continue
            valid.append(r)
        rows.append(
            {
                "family": family,
                "candidate_receipt_count": len(scoped),
                "structurally_complete_count": len(valid),
                "state": ("UNVERIFIED_RECEIPTS_PRESENT" if valid else "NOT_RUN"),
                "physical_certification": "NOT_RUN",
                "receiver_interpretation": "NOT_RUN"
                if family == "dop"
                else "NOT_APPLICABLE",
            }
        )
    return {
        "schema": "michi.f11.a49.dac_receipt_intake.v1",
        "qualification": "NO_GO",
        "coverage": rows,
        "warning": (
            "File metadata and hashes are not independent hardware certification"
        ),
    }


def main(argv: list[str] | None = None) -> dict[str, object]:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--receipts", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    raw = (
        json.loads(args.receipts.read_text())
        if args.receipts and args.receipts.is_file()
        else []
    )
    result = inspect_receipts(raw)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


if __name__ == "__main__":
    result = main()
    print(
        json.dumps(
            {
                "qualification": result["qualification"],
                "families": len(result["coverage"]),
            }
        )
    )
    raise SystemExit(2)
