#!/usr/bin/env python3
"""QML Integration Preflight — detects conflicts across 4 branch manifests.
Does NOT execute merges.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load_manifest(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        with open(p) as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return {}


def _collect(manifest: dict, key: str) -> set:
    items = manifest.get(key, [])
    if isinstance(items, list):
        return set(items)
    if isinstance(items, dict):
        return set(items.keys())
    return set()


def _collect_nested(manifest: dict, outer: str, inner: str) -> set:
    items = manifest.get(outer, {})
    result = set()
    for v in items.values():
        vals = v.get(inner, [])
        if isinstance(vals, list):
            result.update(vals)
        elif isinstance(vals, dict):
            result.update(vals.keys())
    return result


def run_preflight(manifests: dict[str, str]) -> dict:
    loaded = {name: load_manifest(path) for name, path in manifests.items()}

    overlaps: set[str] = set()
    central_files: set[str] = set()
    name_conflicts: set[str] = set()
    dup_contexts: set[str] = set()
    dup_services: set[str] = set()
    dup_bridges: set[str] = set()

    all_routes: dict[str, set[str]] = {}
    for name, m in loaded.items():
        all_routes[name] = _collect(m, "routes")

    items_list = list(all_routes.items())
    for i, (_, r1) in enumerate(items_list):
        for _, r2 in items_list[i + 1:]:
            shared = r1 & r2
            if shared:
                overlaps.update(shared)

    all_files: dict[str, set[str]] = {}
    for name, m in loaded.items():
        all_files[name] = _collect(m, "files")

    for files in all_files.values():
        for f in files:
            if "core/" in f or "service_container" in f or "application_bootstrap" in f:
                central_files.add(f)

    all_names: dict[str, set[str]] = {}
    for name, m in loaded.items():
        all_names[name] = _collect(m, "names")

    nm_items = list(all_names.items())
    for i, (_, nm1) in enumerate(nm_items):
        for _, nm2 in nm_items[i + 1:]:
            shared = nm1 & nm2
            if shared:
                name_conflicts.update(shared)

    all_contexts: dict[str, set[str]] = {}
    for name, m in loaded.items():
        all_contexts[name] = _collect_nested(m, "contexts", "names")

    ctx_items = list(all_contexts.items())
    for i, (_, c1) in enumerate(ctx_items):
        for _, c2 in ctx_items[i + 1:]:
            shared = c1 & c2
            if shared:
                dup_contexts.update(shared)

    all_services: dict[str, set[str]] = {}
    for name, m in loaded.items():
        all_services[name] = _collect(m, "services")

    svc_items = list(all_services.items())
    for i, (_, s1) in enumerate(svc_items):
        for _, s2 in svc_items[i + 1:]:
            shared = s1 & s2
            if shared:
                dup_services.update(shared)

    all_bridges: dict[str, set[str]] = {}
    for name, m in loaded.items():
        all_bridges[name] = _collect(m, "bridges")

    br_items = list(all_bridges.items())
    for i, (_, b1) in enumerate(br_items):
        for _, b2 in br_items[i + 1:]:
            shared = b1 & b2
            if shared:
                dup_bridges.update(shared)

    issues = []
    if overlaps:
        issues.append({"type": "ROUTE_OVERLAP", "details": sorted(overlaps)})
    if central_files:
        issues.append({"type": "CENTRAL_FILE_MODIFIED", "details": sorted(central_files)})
    if name_conflicts:
        issues.append({"type": "NAME_CONFLICT", "details": sorted(name_conflicts)})
    if dup_contexts:
        issues.append({"type": "DUPLICATE_CONTEXT", "details": sorted(dup_contexts)})
    if dup_services:
        issues.append({"type": "DUPLICATE_SERVICE", "details": sorted(dup_services)})
    if dup_bridges:
        issues.append({"type": "DUPLICATE_BRIDGE", "details": sorted(dup_bridges)})

    return {
        "passed": len(issues) == 0,
        "issue_count": len(issues),
        "issues": issues,
        "manifests_loaded": list(manifests.keys()),
        "summary": {
            "route_overlaps": sorted(overlaps),
            "central_files_modified": sorted(central_files),
            "name_conflicts": sorted(name_conflicts),
            "duplicate_contexts": sorted(dup_contexts),
            "duplicate_services": sorted(dup_services),
            "duplicate_bridges": sorted(dup_bridges),
        },
    }


def main():
    manifests = {
        "michi-core-convergence": str(REPO / "docs" / "integration" / "michi-core-convergence.yaml"),
        "main": str(REPO / "docs" / "qml_migration_manifest_v9.json"),
        "wave": str(REPO / "docs" / "qml_migration_manifest_v8.json"),
    }
    result = run_preflight(manifests)
    outpath = Path("/tmp/qml_integration_preflight.json")
    outpath.write_text(json.dumps(result, indent=2, default=str))
    print(f"Results written to {outpath}")

    print(f"\n{'='*60}")
    print("  QML Integration Preflight")
    print(f"{'='*60}")
    print(f"  Manifests loaded: {result['manifests_loaded']}")
    for issue in result["issues"]:
        print(f"\n  {issue['type']}: {len(issue['details'])}")
        for d in issue["details"][:5]:
            print(f"    - {d}")
        if len(issue["details"]) > 5:
            print(f"    ... and {len(issue['details']) - 5} more")
    print(f"\n  Isssues: {result['issue_count']}")
    print(f"  OVERALL: {'PASSED' if result['passed'] else 'FAILED'}")
    return 0 if result.get("passed", False) else 1


if __name__ == "__main__":
    sys.exit(main())
