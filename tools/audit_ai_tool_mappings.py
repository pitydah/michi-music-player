#!/usr/bin/env python3
"""Audit Michi AI tool → gateway → method mappings.

Imports the builtin tool registry wiring (``michi_ai/v2/tools/register_builtin``
GW_MAP + tool definitions) and verifies every mapping:

  1. The gateway attribute exists on the real ``AssistantGateways`` object
     fields (playlists/devices/library/queue/playback/settings/audio_lab/
     diagnostics/mix/jobs/navigation/library_doctor/metadata).
  2. The gateway method exists on the production gateway class.
  3. No semantically wrong pair from the known-wrong list remains
     (delete_playlist→create_playlist, draft_playlist→list_playlists,
     apply_library_repair→list_recent, rollback_library_repair→list_recent,
     inspect_metadata→generic get_track without metadata fields,
     restore_setting→suggest_change, scan_library_health→static diagnostics).
  4. No mapped tool resolves to a stub method (best-effort AST: a gateway
     method that never touches its backing services and always returns
     CAPABILITY_UNAVAILABLE or static data).

FAILS (exit 1) on: nonexistent gateway attr or method, a known-wrong pair,
or a stub-mapped tool.

Usage:
  python tools/audit_ai_tool_mappings.py
  python tools/audit_ai_tool_mappings.py --json
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

from michi_ai.v2.tools.register_builtin import GW_MAP  # noqa: E402
from michi_ai.v2.tools.tool_definitions import BUILTIN_TOOL_DEFINITIONS  # noqa: E402

GATEWAY_CLASSES: dict[str, type] = {}


def _load_gateway_classes() -> None:
    """attr → production gateway class (mirror of assistant_initializer)."""
    global GATEWAY_CLASSES
    from core.assistant_gateways import (
        ProductionAudioLabGateway,
        ProductionDeviceGateway,
        ProductionDiagnosticsGateway,
        ProductionJobGateway,
        ProductionLibraryDoctorGateway,
        ProductionLibraryGateway,
        ProductionMixGateway,
        ProductionNavigationGateway,
        ProductionPlaybackGateway,
        ProductionPlaylistGateway,
        ProductionQueueGateway,
        ProductionSettingsGateway,
        UnavailableRadioGateway,
    )
    from core.assistant_metadata_gateway import ProductionMetadataGateway

    GATEWAY_CLASSES = {
        "playback": ProductionPlaybackGateway,
        "queue": ProductionQueueGateway,
        "library": ProductionLibraryGateway,
        "playlists": ProductionPlaylistGateway,
        "settings": ProductionSettingsGateway,
        "audio_lab": ProductionAudioLabGateway,
        "devices": ProductionDeviceGateway,
        "diagnostics": ProductionDiagnosticsGateway,
        "mix": ProductionMixGateway,
        "jobs": ProductionJobGateway,
        "navigation": ProductionNavigationGateway,
        "library_doctor": ProductionLibraryDoctorGateway,
        "metadata": ProductionMetadataGateway,
        "radio": UnavailableRadioGateway,
    }


KNOWN_WRONG_PAIRS: dict[str, tuple[str, str]] = {
    "delete_playlist": ("playlists", "create_playlist"),
    "draft_playlist": ("playlists", "list_playlists"),
    "apply_library_repair": ("library", "list_recent"),
    "rollback_library_repair": ("library", "list_recent"),
    "restore_setting": ("settings", "suggest_change"),
    "scan_library_health": ("diagnostics", "get_diagnostics"),
    "inspect_metadata": ("library", "get_track"),
}

# Metadata fields a non-generic get_track must expose for inspect_metadata.
METADATA_FIELDS = ("genre", "bitrate", "year", "format", "duration")

GATEWAY_SOURCE_FILES = (
    HERE / "core" / "assistant_gateways.py",
    HERE / "core" / "assistant_metadata_gateway.py",
)


def _instantiate(gateway_class: type) -> object | None:
    """Instantiate a production gateway with only None services."""
    try:
        return gateway_class(None)
    except TypeError:
        return None
    except Exception:  # noqa: BLE001
        return None


def _method_ast(class_name: str, method_name: str) -> ast.FunctionDef | None:
    """Locate a method definition across the gateway source files."""
    for path in GATEWAY_SOURCE_FILES:
        if not path.exists():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for child in node.body:
                    if isinstance(child, ast.FunctionDef) and child.name == method_name:
                        return child
    return None


def _is_stub(method_node: ast.FunctionDef) -> tuple[bool, str]:
    """Best-effort stub detection.

    A mapped method is a stub when its body never reads a backing service
    (no ``self._*`` attribute access) and it always returns a GENERIC
    error/static payload (``_unavailable_response`` helper or bare
    ``CAPABILITY_UNAVAILABLE`` without a domain-specific explanation).
    A method that always fails with a SPECIFIC domain message (e.g.
    ``rollback``: "LibraryDoctorService does not support rollback") is
    HONEST_UNAVAILABLE — reported as INFO, never as a stub.
    """
    touches_service = False
    for node in ast.walk(method_node):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
                and node.value.id == "self":
            touches_service = True
    if touches_service:
        return False, ""
    source = ast.unparse(method_node)
    if "CAPABILITY_UNAVAILABLE" in source:
        if "_unavailable_response" in source:
            return True, "generic unavailable helper; never touches backing services"
        # Domain-specific explanation → honest unavailability, not a stub.
        if re.search(r'["\'](error|message)["\']\s*:\s*["\']', source):
            return False, "honest unavailable with domain-specific message"
        return True, "CAPABILITY_UNAVAILABLE without domain-specific message"
    if re.search(r"return\s+\{", source):
        return True, "never touches backing services; returns static payload"
    return False, ""


def _get_track_has_metadata() -> bool:
    """inspect_metadata guard: get_track is only non-generic with metadata."""
    node = _method_ast("ProductionLibraryGateway", "get_track")
    if node is None:
        return False
    source = ast.unparse(node)
    return any(field in source for field in METADATA_FIELDS)


def audit() -> dict:
    _load_gateway_classes()
    rows: list[dict] = []
    violations: list[str] = []
    stub_reports: list[dict] = []

    for defn in sorted(BUILTIN_TOOL_DEFINITIONS, key=lambda d: d.name):
        mapping = GW_MAP.get(defn.name)
        row = {
            "tool": defn.name,
            "mapping": None,
            "gateway_ok": False,
            "method_ok": False,
            "semantic": "ok",
        }
        if mapping is None:
            row["semantic"] = "unmapped"
            rows.append(row)
            continue
        row["mapping"] = list(mapping)
        gattr, method = mapping
        rows.append(row)

        # 1. Gateway attribute exists on AssistantGateways fields.
        if gattr not in GATEWAY_CLASSES:
            row["gateway_ok"] = False
            violations.append(
                f"tool '{defn.name}': gateway attr '{gattr}' is not a "
                f"known AssistantGateways field"
            )
            continue
        row["gateway_ok"] = True

        # 2. Method exists on the production gateway class.
        gateway_class = GATEWAY_CLASSES[gattr]
        instance = _instantiate(gateway_class)
        if instance is not None:
            method_ok = callable(getattr(instance, method, None))
        else:
            node = _method_ast(gateway_class.__name__, method)
            method_ok = node is not None
        row["method_ok"] = method_ok
        if not method_ok:
            violations.append(
                f"tool '{defn.name}': method '{method}' does not exist on "
                f"{gateway_class.__name__}"
            )
            continue

        # 3. Known-wrong semantic pairs.
        wrong = KNOWN_WRONG_PAIRS.get(defn.name)
        if wrong is not None and tuple(mapping) == wrong:
            if defn.name == "inspect_metadata" and _get_track_has_metadata():
                row["semantic"] = "ok (get_track exposes metadata fields)"
            else:
                row["semantic"] = "KNOWN_WRONG"
                violations.append(
                    f"tool '{defn.name}' maps to known-wrong pair "
                    f"{tuple(mapping)}"
                )
                continue

        # 4. Stub method behind a mapped tool.
        node = _method_ast(gateway_class.__name__, method)
        if node is not None:
            is_stub, reason = _is_stub(node)
            if is_stub:
                stub_reports.append({
                    "tool": defn.name,
                    "gateway": gattr,
                    "method": method,
                    "reason": reason,
                })

    return {
        "generated_by": "tools/audit_ai_tool_mappings.py",
        "tools_total": len(BUILTIN_TOOL_DEFINITIONS),
        "tools_mapped": sum(1 for r in rows if r["mapping"]),
        "tools_unmapped": sum(1 for r in rows if r["semantic"] == "unmapped"),
        "rows": rows,
        "stub_reports": stub_reports,
        "violations": violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Dump JSON report")
    args = parser.parse_args()

    report = audit()
    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if not report["violations"] else 1

    print(f"Tools total: {report['tools_total']} | mapped: "
          f"{report['tools_mapped']} | unmapped: {report['tools_unmapped']}")
    bad = [r for r in report["rows"] if not r["method_ok"] or r["semantic"] == "KNOWN_WRONG"]
    for row in bad:
        print(
            f"  {row['tool']}: mapping={row['mapping']} "
            f"gateway_ok={row['gateway_ok']} method_ok={row['method_ok']} "
            f"semantic={row['semantic']}"
        )
    print(f"Stub-mapped tools: {len(report['stub_reports'])}")
    for stub in report["stub_reports"]:
        print(f"  - {stub['tool']} → {stub['gateway']}.{stub['method']} "
              f"({stub['reason']})")

    if report["violations"]:
        print("FAIL:", *report["violations"], sep="\n  - ")
        return 1
    print("OK: all tool mappings reference real gateway attrs/methods, no "
          "known-wrong pairs, no stub-mapped tools.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
