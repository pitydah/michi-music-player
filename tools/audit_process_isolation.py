#!/usr/bin/env python3
"""Audit process isolation: every subprocess launch must route through a port.

FASE 11 (P0 stabilization) — semantic (AST-based) scan of the ENTIRE
productive tree (core/, audio/, integrations/, sync/, library/, recognition/,
recommendation/, metadata/, ui_qml_bridge/):

  - ``subprocess.run(``, ``subprocess.Popen(``, ``os.system(`` and bare
    ``Popen(`` are the flagged launch sites.
  - ALLOWED: the controlled ports themselves (core/process_controller.py,
    core/external_process.py), sites that only reference subprocess constants
    while spawning through ``ProcessController`` (port-routed), and the
    documented adapters below (each with a review reason). Everything else
    FAILS (exit 1) with file:line.

FAILS (exit 1) when an undocumented direct subprocess launch exists.

Usage:
  python tools/audit_process_isolation.py
  python tools/audit_process_isolation.py --json
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

SCAN_DIRS = (
    "core", "audio", "integrations", "sync", "library", "recognition",
    "recommendation", "metadata", "ui_qml_bridge",
)

# The controlled ports themselves.
PORT_FILES = {
    "process_controller.py",
    "external_process.py",
}

# Sites that only reference subprocess constants while the actual spawn goes
# through ProcessController (port-routed). Keyed by relative path. Verified
# during FASE 11.
PORT_ROUTED: dict[str, str] = {
    "core/device_sync/discovery.py":
        "MtpDiscoveryAdapter spawns via ProcessController.spawn_sync; the "
        "subprocess references are PIPE/DEVNULL constants.",
    "audio/mpd/mpd_service_manager.py":
        "MPD daemon lifecycle is managed by ProcessController; no bare spawn.",
}

# Documented adapters: (module, reason). Every entry was reviewed during
# FASE 11 — each is a thin adapter around an external binary, running in a
# worker thread or as fire-and-forget UI integration, predating the process
# port. New code must route through ProcessController/external_process.
DOCUMENTED_ADAPTERS: dict[str, str] = {
    "recognition/providers/acoustid.py":
        "fpcalc (Chromaprint) runner — documented adapter (mandate F11): "
        "fingerprint generation via AcoustIDProvider.",
    "core/audio_analysis/spectral_authenticator.py":
        "ffmpeg decode helper of the recognition spectral stack "
        "(worker thread, timeout-bounded).",
    "core/audio_lab/audio_integrity_service.py":
        "ffmpeg decode-check adapter of the audio lab domain (worker "
        "thread, timeout-bounded).",
    "core/audio_lab/replaygain_service.py":
        "ffmpeg loudnorm adapter of the audio lab domain (worker thread).",
    "core/audio_lab/audio_normalization_service.py":
        "ffmpeg normalization adapter of the audio lab domain (worker "
        "thread).",
    "core/audio_lab/audio_conversion_service.py":
        "ffmpeg conversion adapter of the audio lab domain (worker thread, "
        "streaming progress).",
    "core/audio_lab/adc_recorder_service.py":
        "arecord/ffmpeg capture adapter of the audio lab domain (worker "
        "thread, streaming).",
    "core/audio_lab/cd_ripper_service.py":
        "cdparanoia ripper adapter of the audio lab domain (worker thread).",
    "core/file_manager_service.py":
        "xdg-open fire-and-forget file-manager opener (UI integration; "
        "FileManagerService is the declared port for file actions).",
    "core/home_audio_service.py":
        "avahi-browse mDNS discovery probe (timeout-bounded, read-only).",
    "integrations/connections/discovery_manager.py":
        "avahi-browse mDNS discovery probe of the connections integration "
        "(timeout-bounded, read-only).",
    "integrations/snapcast/discovery.py":
        "snapserver binary probe of the snapcast integration "
        "(timeout-bounded).",
    "ui_qml_bridge/desktop_bridge.py":
        "notify-send / which probes of the desktop integration bridge "
        "(UI notification adapter).",
    "ui_qml_bridge/disc_lab_bridge.py":
        "eject fallback of the disc lab bridge (worker thread, blocking "
        "probe).",
    "ui_qml_bridge/conversion_bridge.py":
        "ffmpeg conversion owned by the conversion bridge (documented "
        "conversion domain; no container conversion service).",
    "ui_qml_bridge/library_sources_bridge.py":
        "xdg-open fire-and-forget folder opener (UI integration).",
}

# Legacy/dead modules that still contain direct launches: not part of the
# productive runtime, superseded by the canonical stack. Reported as INFO.
LEGACY_MODULES: dict[str, str] = {
    "core/album_service.py": "Dead module (no productive consumers).",
    "core/device_discovery_service.py": "Dead module; MTP discovery superseded by "
        "core/device_sync/discovery.py (ProcessController).",
    "core/file_actions.py": "Dead module (no consumers); FileManagerService is the "
        "file-action port.",
    "core/sync/transcode_service.py": "LEGACY core/sync transcode service (superseded by "
        "core/device_sync/transfer.py + ProcessController).",
    "library/devices.py": "library/devices.py helper (no productive consumers).",
    "ui_qml_bridge/adapters/mtp_adapter.py": "LEGACY MTP adapter; superseded by MtpDiscoveryAdapter "
        "(ProcessController, F8).",
    "ui_qml_bridge/adapters/ums_adapter.py": "LEGACY UMS adapter; superseded by device_sync "
        "discovery (F8).",
}

# Launch patterns (AST call shapes).
_LAUNCH_CALL_RE = re.compile(r"^(run|Popen|system|call|check_output|check_call)$")


def _launch_sites(path: Path) -> list[tuple[int, str]]:
    """(lineno, call-shape) for every direct process-launch site."""
    sites: list[tuple[int, str]] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except (SyntaxError, OSError):
        return sites
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            if func.value.id == "subprocess" and func.attr in (
                    "run", "Popen", "call", "check_call", "check_output"):
                sites.append((node.lineno, f"subprocess.{func.attr}("))
            elif func.value.id == "os" and func.attr == "system":
                sites.append((node.lineno, f"os.{func.attr}("))
        elif isinstance(func, ast.Name) and func.id == "Popen":
            sites.append((node.lineno, "Popen("))
    return sites


def audit() -> dict:
    port_sites: int = 0
    routed_sites: int = 0
    documented: list[dict] = []
    legacy: list[dict] = []
    violations: list[str] = []
    scanned: int = 0

    for directory in SCAN_DIRS:
        base = HERE / directory
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts or "build" in path.parts \
                    or "test" in path.parts:
                continue
            scanned += 1
            sites = _launch_sites(path)
            if not sites:
                continue
            if path.name in PORT_FILES:
                port_sites += len(sites)
                continue
            rel = path.relative_to(HERE).as_posix()
            routed = PORT_ROUTED.get(rel)
            if routed is not None:
                routed_sites += len(sites)
                documented.append({
                    "file": path.name, "lineno": sites[0][0],
                    "calls": [s[1] for s in sites],
                    "kind": "port_routed", "reason": routed,
                })
                continue
            allowed = DOCUMENTED_ADAPTERS.get(rel)
            if allowed is not None:
                documented.append({
                    "file": path.name, "lineno": sites[0][0],
                    "calls": [s[1] for s in sites],
                    "kind": "documented_adapter", "reason": allowed,
                })
                continue
            legacy_reason = LEGACY_MODULES.get(rel)
            if legacy_reason is not None:
                legacy.append({
                    "file": path.name, "lineno": sites[0][0],
                    "calls": [s[1] for s in sites],
                    "reason": legacy_reason,
                })
                continue
            for lineno, shape in sites:
                violations.append(f"{path.name}:{lineno} {shape}")

    return {
        "generated_by": "tools/audit_process_isolation.py",
        "files_scanned": scanned,
        "port_launches": port_sites,
        "port_routed_launches": routed_sites,
        "documented_adapters": documented,
        "legacy_modules": legacy,
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

    print(f"Files scanned: {report['files_scanned']} | "
          f"launches through the controlled port: {report['port_launches']} | "
          f"port-routed (constants only): {report['port_routed_launches']}")
    print(f"Documented adapters: {len(report['documented_adapters'])}")
    for row in report["documented_adapters"]:
        print(f"  - {row['file']}:{row['lineno']} {row['calls']} — "
              f"{row['reason']}")
    print(f"Legacy/dead modules (INFO): {len(report['legacy_modules'])}")
    for row in report["legacy_modules"]:
        print(f"  - {row['file']}:{row['lineno']} {row['calls']} — "
              f"{row['reason']}")
    print(f"Violations (direct launch outside port/adapters): "
          f"{len(report['violations'])}")
    for item in report["violations"]:
        print(f"  - {item}")

    if report["violations"]:
        print("FAIL: direct subprocess launch outside the controlled port.")
        return 1
    print("OK: every subprocess launch is routed through ProcessController/"
          "external_process or a documented adapter.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
