#!/usr/bin/env python3
"""Audit capability truthfulness across the runtime layer.

Checks the four capability sources for hardcoded/static announcements and
verifies every announced capability has a backing service registered in
SERVICE_MANIFEST with a healthy lifecycle entry:

  1. ui_qml_bridge/capability_bridge.py       — real probes (has_* keys)
  2. ui_qml_bridge/service_capabilities.py    — static state computation
  3. michi_ai/v2/intent/capability_resolver.py — evidence-based resolver
  4. michi_ai/context/ai_snapshot_service.py   — Michi AI snapshot

FAILS (exit 1) when:
  - A hardcoded ``True`` capability dict is found (dict literal with a string
    key valued ``True`` that is not evidence-gated and not documented
    metadata).
  - A capability is announced for a key with no backing service in the
    manifest (probe/alias tables are authoritative).
  - A capability is backed only by services whose descriptor lifecycle is
    LEGACY_COMPONENT.

Usage:
  python tools/audit_capability_truthfulness.py
  python tools/audit_capability_truthfulness.py --json
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from core.service_manifest import SERVICE_MANIFEST, ServiceClass  # noqa: E402

CAPABILITY_SOURCES = (
    HERE / "ui_qml_bridge" / "capability_bridge.py",
    HERE / "ui_qml_bridge" / "service_capabilities.py",
    HERE / "michi_ai" / "v2" / "intent" / "capability_resolver.py",
    HERE / "michi_ai" / "context" / "ai_snapshot_service.py",
)

# Hardcoded-True allowlist: (file, lineno, reason). ``metadata`` fields inside
# a typed CapabilityStatus are not capability announcements.
HARDCODED_TRUE_ALLOWLIST = {
    ("capability_bridge.py", 377):
        "metadata={'running': True} is a status metadata field, not a "
        "capability announcement.",
}

# Evidence-gated True values (guarded by service presence / try blocks) are
# reported as INFO rows, never as violations. Keyed by (file, lineno).
EVIDENCE_GATED_TRUE = {
    ("ai_snapshot_service.py", 67):
        "available=True only after michi link doctor produced a summary "
        "(try-guarded evidence, not static).",
}

# Probe name → backing manifest service keys (capability_bridge probes).
PROBE_BACKING: dict[str, tuple[str, ...]] = {
    "has_fts5": ("connection_factory", "database"),
    "has_radio": ("radio_service",),
    "has_global_search": ("global_search_service",),
    "has_sync": ("device_sync_service", "mobile_sync_service"),
    "has_home_audio": ("home_audio_service",),
    "has_snapcast": ("snapserver_manager", "snapcast_control"),
    "has_mpd": ("mpd_service_manager",),
    "has_disc_service": ("cd_ripper_service",),
    "has_smart_tagging": ("smart_tagging_service",),
    "has_metadata_writer": ("metadata_editor_service", "library_mutation_service"),
}

# AI snapshot can_* keys → backing manifest service keys.
CAN_BACKING: dict[str, tuple[str, ...]] = {
    "can_search_library": ("global_search_service", "library_query_service"),
    "can_create_playlist": ("playlist_service",),
    "can_diagnose_ecosystem": ("diagnostics_service", "device_sync_service"),
    "can_analyze_audio": ("audio_lab_service",),
    "can_create_plans": ("michi_ai_service",),
}

# Bridge-level alias keys → backing manifest service keys
# (service_capabilities announces "devices"; the manifest declares
# "devices_sync" over the same services).
CAP_ALIASES: dict[str, tuple[str, ...]] = {
    "devices": ("device_sync_service", "device_registry", "mobile_sync_service"),
}

# Non-capability keys excluded from the hardcoded-True scan (result envelopes,
# status fields).
NON_CAPABILITY_KEYS = frozenset({
    "ok", "error", "message", "code", "reason", "summary", "count", "total",
    "checks", "available", "active", "peers", "syncing", "track", "tracks",
})


def _manifest_capability_map() -> dict[str, tuple[str, ...]]:
    """Capability name → manifest service keys declaring it."""
    caps: dict[str, list[str]] = {}
    for key, desc in SERVICE_MANIFEST.items():
        for cap in desc.capabilities:
            caps.setdefault(cap, []).append(key)
    return {name: tuple(keys) for name, keys in caps.items()}


def _announced_capability_keys() -> set[str]:
    """Static extraction of announced capability keys from the four sources."""
    announced: set[str] = set()
    for path in CAPABILITY_SOURCES:
        source = path.read_text(encoding="utf-8", errors="ignore")
        for match in re.finditer(r"[\"']([a-z_]+)[\"']", source):
            key = match.group(1)
            if re.match(r"^(has_|can_)[a-z_]+$", key) or key in {
                "library", "playback", "nowplaying", "mix", "lyrics",
                "connections_michilink", "home_audio", "snapcast",
                "devices_sync", "radio", "playlists", "eq", "settings",
                "audio_lab", "metadata", "smart_tagging", "disc_lab",
                "library_doctor", "diagnostics", "michi_ai", "theme",
                "navigation", "route_registry", "app_state",
                "command_palette", "cover", "notifications",
                "global_search", "connections", "devices",
                "output_profiles", "ai", "transmit", "genres", "context",
            }:
                announced.add(key)
    return announced


def _hardcoded_true_findings() -> tuple[list[dict], list[dict]]:
    """(violations, info rows) for literal True capability dict values."""
    violations: list[dict] = []
    info: list[dict] = []
    for path in CAPABILITY_SOURCES:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            hits = []
            for k, v in zip(node.keys, node.values, strict=False):
                if isinstance(k, ast.Constant) and isinstance(k.value, str) \
                        and isinstance(v, ast.Constant) and v.value is True \
                        and k.value not in NON_CAPABILITY_KEYS:
                    hits.append(k.value)
            if not hits:
                continue
            rel = path.name
            allow = HARDCODED_TRUE_ALLOWLIST.get((rel, node.lineno))
            gated = EVIDENCE_GATED_TRUE.get((rel, node.lineno))
            row = {"file": rel, "lineno": node.lineno, "keys": hits}
            if allow:
                row["status"] = "documented"
                row["reason"] = allow
                info.append(row)
            elif gated:
                row["status"] = "evidence_gated"
                row["reason"] = gated
                info.append(row)
            else:
                row["status"] = "violation"
                row["reason"] = "hardcoded True capability value"
                violations.append(row)
    return violations, info


def _resolve_backing(cap: str) -> tuple[str, ...]:
    """Manifest service keys backing a capability (or empty)."""
    manifest = _manifest_capability_map()
    if cap in manifest:
        return manifest[cap]
    if cap in PROBE_BACKING:
        return PROBE_BACKING[cap]
    if cap in CAN_BACKING:
        return CAN_BACKING[cap]
    if cap in CAP_ALIASES:
        return CAP_ALIASES[cap]
    return ()


def _legacy_backed(cap: str, backing: tuple[str, ...]) -> list[str]:
    return [
        key for key in backing
        if SERVICE_MANIFEST[key].service_class == ServiceClass.LEGACY_COMPONENT
    ]


def audit() -> dict:
    manifest = _manifest_capability_map()
    announced = _announced_capability_keys()

    unbacked: list[str] = []
    legacy_backed: list[dict] = []
    healthy: list[dict] = []
    for cap in sorted(announced):
        backing = _resolve_backing(cap)
        if not backing:
            unbacked.append(cap)
            continue
        legacy = _legacy_backed(cap, backing)
        row = {
            "capability": cap,
            "backing_services": list(backing),
            "in_manifest": True,
        }
        if legacy:
            row["legacy_backing"] = legacy
            legacy_backed.append(row)
        else:
            healthy.append(row)

    hardcoded, hardcoded_info = _hardcoded_true_findings()

    return {
        "generated_by": "tools/audit_capability_truthfulness.py",
        "announced_capabilities": len(announced),
        "manifest_capability_entries": len(manifest),
        "healthy_capabilities": healthy,
        "unbacked_capabilities": unbacked,
        "legacy_backed_capabilities": legacy_backed,
        "hardcoded_true_violations": hardcoded,
        "hardcoded_true_info": hardcoded_info,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Dump JSON report")
    args = parser.parse_args()

    report = audit()
    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if not (report["unbacked_capabilities"]
                         or report["legacy_backed_capabilities"]
                         or report["hardcoded_true_violations"]) else 1

    print(f"Announced capabilities: {report['announced_capabilities']} | "
          f"manifest capability entries: {report['manifest_capability_entries']}")
    print(f"Healthy (manifest-backed): {len(report['healthy_capabilities'])}")
    print(f"Unbacked: {report['unbacked_capabilities']}")
    print(f"Legacy-backed: {report['legacy_backed_capabilities']}")
    print(f"Hardcoded True violations: {len(report['hardcoded_true_violations'])}")
    for row in report["hardcoded_true_violations"]:
        print(f"  - {row['file']}:{row['lineno']} {row['keys']} — {row['reason']}")
    print(f"Hardcoded True INFO (documented/gated): "
          f"{len(report['hardcoded_true_info'])}")
    for row in report["hardcoded_true_info"]:
        print(f"  - {row['file']}:{row['lineno']} {row['keys']} — {row['reason']}")

    if report["unbacked_capabilities"] or report["legacy_backed_capabilities"] \
            or report["hardcoded_true_violations"]:
        print("FAIL: capability truthfulness violations found.")
        return 1
    print("OK: every announced capability is manifest-backed with a healthy "
          "lifecycle; no hardcoded True capabilities.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
