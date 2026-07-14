#!/usr/bin/env python3
"""QWidget decommission audit — classifies each domain by widget replacement status."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MATRIX = REPO / "docs" / "qwidget_decommission_matrix.yaml"

W_LABELS = {
    "W0_ACTIVE": "Widget is primary implementation",
    "W1_FROZEN": "No new widget features",
    "W2_THIN_ADAPTER": "Widget consumes core services only",
    "W3_LEGACY_ONLY": "Widget via legacy launcher only",
    "W4_DETACHED": "Widget outside QML imports/packaging",
    "W5_REMOVABLE_AFTER_PHYSICAL": "Removable after physical validation",
}


def main():
    try:
        import yaml
        matrix = yaml.safe_load(MATRIX.read_text()) if MATRIX.suffix == ".yaml" else json.loads(MATRIX.read_text())
    except Exception:
        print("ERROR: cannot load decommission matrix")
        return 1

    domains = matrix.get("domains", [])
    counts = {k: 0 for k in W_LABELS}
    print("# QWidget Decommission Audit\n")
    for d in sorted(domains, key=lambda x: x.get("domain", "")):
        status = d.get("widget_status", "W0_ACTIVE")
        counts[status] = counts.get(status, 0) + 1
        qml_route = d.get("qml_route", "?")
        d.get("widget_file", "?")
        flag = "✅" if status in ("W3_LEGACY_ONLY", "W4_DETACHED", "W5_REMOVABLE_AFTER_PHYSICAL") else "⬜"
        removal = d.get("removal_blockers", [])
        blocker = f" (BLOCKED: {', '.join(removal)})" if removal else ""
        print(f"  {flag} {d['domain']:20s} {status:30s} QML: {qml_route}{blocker}")

    w3_plus = sum(v for k, v in counts.items() if k in ("W3_LEGACY_ONLY", "W4_DETACHED", "W5_REMOVABLE_AFTER_PHYSICAL"))
    total = sum(counts.values())
    pct = w3_plus / total * 100 if total else 0
    print(f"\n  W3+: {w3_plus}/{total} = {pct:.0f}%  (target: >= 60%)\n")
    for k, v in sorted(counts.items()):
        print(f"    {k}: {v} ({W_LABELS.get(k, '?')})")

    if pct >= 60:
        print("\n  ✅ TARGET MET: >= 60% of widget views are W3+")
    else:
        print(f"\n  ❌ TARGET NOT MET: {pct:.0f}% < 60%")
    return 0


if __name__ == "__main__":
    exit(main())
