#!/usr/bin/env python3
"""Read-only AP2-F11 integration baseline and product nomenclature inventory.

This tool is designed to be copied into ``scripts/`` on an authorized branch.
It does not rewrite product files, phase manifests, evidence or Git history.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA = "michi.signal_truth.m0_inventory.v1"
ROOT_CONFIGS = frozenset(("pyproject.toml", "setup.py", "setup.cfg", "MANIFEST.in"))
WORKFLOW_PREFIX = ".github/workflows/"
TEXT_SUFFIXES = frozenset(
    (
        ".py",
        ".pyi",
        ".qml",
        ".qmldir",
        ".js",
        ".ts",
        ".rs",
        ".c",
        ".cc",
        ".cpp",
        ".h",
        ".hpp",
        ".json",
        ".toml",
        ".yml",
        ".yaml",
        ".qrc",
        ".sh",
        ".fish",
        ".in",
        ".txt",
        ".cmake",
    )
)
# A source-lexicon guard must not contain its own disallowed lexeme verbatim.
RESERVED_LEXEME = re.compile(
    "signal"
    + "path"
    + "|"
    + "signal"
    + r"[_-]"
    + "path"
    + "|"
    + "signal"
    + r"\s+"
    + "path"
    + r"\b",
    re.IGNORECASE,
)
EMITTER_RE = re.compile(
    r"\.((?:begin|commit|discard)_candidate|observe|retire_active|terminate|"
    r"record_(?:output_family_event|processing_event|processing_measurement))\s*\("
)
SUBSCRIBER_RE = re.compile(r"\.(subscribe|unsubscribe)\s*\(")
QT_RE = re.compile(
    r"(?:setContextProperty|\.connect\(|\.emit\(|QMetaObject\.invokeMethod|"
    r"QTimer\.singleShot|Qt\.QueuedConnection)"
)
PROBE_RE = re.compile(
    r"(?:signal_truth|SignalTruthRecorder|SignalTruthBridge|signalTruthBridge|"
    r"OutputFamilyEvent|ProcessingTruthEvent)"
)


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(
        ("git", "-C", str(repo), *args), check=True, capture_output=True
    ).stdout


def tracked_paths(repo: Path) -> list[str]:
    raw = git(repo, "ls-files", "-z")
    return sorted(p.decode("utf-8", "strict") for p in raw.split(b"\0") if p)


def category(rel: str) -> str:
    if rel.startswith("src/"):
        return "product"
    if rel.startswith("tests/"):
        return "tests"
    if rel.startswith("scripts/"):
        return "scripts"
    if rel.startswith("native/"):
        return "native"
    if rel.startswith("tools/"):
        return "tools"
    if rel.startswith(WORKFLOW_PREFIX):
        return "ci_workflows"
    if rel in ROOT_CONFIGS:
        return "build_config"
    if rel.startswith("docs/"):
        return "documentation"
    if rel.startswith("evidence/"):
        return "historical_evidence"
    return "other"


def controlled(rel: str) -> bool:
    return category(rel) in {
        "product",
        "tests",
        "scripts",
        "native",
        "tools",
        "ci_workflows",
        "build_config",
    }


def is_text(rel: str) -> bool:
    return Path(rel).suffix.lower() in TEXT_SUFFIXES or rel in ROOT_CONFIGS


def analyze_python(content: str, rel: str) -> tuple[list[dict[str, Any]], list[str]]:
    imports: list[dict[str, Any]] = []
    parse_errors: list[str] = []
    try:
        tree = ast.parse(content, filename=rel)
    except SyntaxError as error:
        parse_errors.append(f"{error.msg} at {error.lineno}")
        return imports, parse_errors
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("michi"):
                    imports.append({"line": node.lineno, "module": alias.name})
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and (node.module.startswith("michi") or node.level)
        ):
            imports.append(
                {"line": node.lineno, "module": "." * node.level + node.module}
            )
    return sorted(imports, key=lambda x: (x["line"], x["module"])), parse_errors


def scan(repo: Path) -> dict[str, Any]:
    repo = repo.resolve()
    names = tracked_paths(repo)
    try:
        head = git(repo, "rev-parse", "HEAD").decode().strip()
        dirty = bool(git(repo, "status", "--porcelain", "--untracked-files=no").strip())
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("cannot resolve Git HEAD") from exc
    findings: list[dict[str, Any]] = []
    producers: list[dict[str, Any]] = []
    subscriptions: list[dict[str, Any]] = []
    qt_calls: list[dict[str, Any]] = []
    imports: list[dict[str, Any]] = []
    unusual: list[dict[str, str]] = []
    categories = Counter(category(s) for s in names)
    qml_count = sum(p.endswith(".qml") for p in names)
    for rel in names:
        if controlled(rel) and RESERVED_LEXEME.search(rel):
            findings.append({"kind": "filename", "path": rel, "line": None})
        if not controlled(rel) or not is_text(rel):
            continue
        source = repo / rel
        # Fail closed on missing tracked files, but never follow symlinks out of repo.
        if not source.is_file() or source.is_symlink():
            unusual.append({"kind": "missing_or_symlink", "path": rel})
            continue
        try:
            data = source.read_bytes()
            if b"\x00" in data:
                unusual.append({"kind": "unexpected_binary", "path": rel})
                continue
            decoded = data.decode("utf-8", errors="strict")
        except (UnicodeError, OSError):
            unusual.append({"kind": "decode_failure", "path": rel})
            continue
        if rel.endswith(".py"):
            extracted, parse_errors = analyze_python(decoded, rel)
            imports.extend({"path": rel, **item} for item in extracted)
            unusual.extend(
                {"kind": "python_parse_failure", "path": rel, "detail": msg}
                for msg in parse_errors
            )
        for number, line in enumerate(decoded.splitlines(), 1):
            if RESERVED_LEXEME.search(line):
                findings.append({"kind": "content", "path": rel, "line": number})
            if category(rel) in ("product", "tests"):
                for match in EMITTER_RE.finditer(line):
                    producers.append(
                        {"path": rel, "line": number, "method": match.group(1)}
                    )
                for match in SUBSCRIBER_RE.finditer(line):
                    subscriptions.append(
                        {"path": rel, "line": number, "method": match.group(1)}
                    )
                if QT_RE.search(line) and PROBE_RE.search(decoded):
                    qt_calls.append({"path": rel, "line": number})
    state_file = repo / "docs/audio/phase2/PHASE2_STATE.json"
    state: dict[str, Any] = {"status": "not_present"}
    if state_file.is_file():
        try:
            obj = json.loads(state_file.read_text(encoding="utf-8"))
            spec_name = obj.get("spec", {}).get("path")
            spec = repo / spec_name if isinstance(spec_name, str) else None
            spec_exists = bool(spec is not None and spec.is_file())
            state = {
                "status": "present",
                "active_phases": obj.get("active_phases"),
                "f11": obj.get("phases", {}).get("AP2-F11"),
                "spec_path": spec_name,
                "spec_exists": spec_exists,
                "spec_current_sha256": (
                    hashlib.sha256(spec.read_bytes()).hexdigest()
                    if spec_exists
                    else None
                ),
                "sha256_at_last_transition": obj.get("spec", {}).get(
                    "sha256_at_last_transition"
                ),
                "note": (
                    "transition hash is historical; do not rewrite merely "
                    "because current bytes differ"
                ),
            }
        except (ValueError, OSError) as error:
            state = {"status": "invalid", "error": type(error).__name__}
    blockers = []
    if state.get("status") != "present" or not state.get("spec_exists"):
        blockers.append("M0_SPEC_UNRESOLVED")
    if unusual:
        blockers.append("M0_UNREADABLE_TRACKED_SOURCE")
    return {
        "schema": SCHEMA,
        "source": "local_git_checkout_read_only",
        "head": head,
        "tracked_files": len(names),
        "tracked_dirty": dirty,
        "category_count": dict(sorted(categories.items())),
        "qml_files": qml_count,
        "nomenclature": {"matches": len(findings), "locations": findings},
        "evidence_producer_calls": producers,
        "evidence_subscriptions": subscriptions,
        "qt_boundary_call_sites": qt_calls,
        "michi_imports": imports,
        "scan_warnings": unusual,
        "phase2": state,
        "blockers": blockers,
        "evidence_state": "STATIC_ONLY_NO_RUNTIME_TESTS",
    }


def write_outputs(out: Path, report: dict[str, Any]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    target = out / "F11_M0_INTEGRATION_INVENTORY.json"
    target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = [
        "# AP2-F11 / M0 — Static integration inventory",
        "",
        f"- Git HEAD: `{report['head']}`",
        f"- Tracked files: {report['tracked_files']}",
        f"- Product naming matches: {report['nomenclature']['matches']}",
        f"- Candidate producer callsites: {len(report['evidence_producer_calls'])}",
        f"- Candidate subscription callsites: {len(report['evidence_subscriptions'])}",
        f"- F11 phase: {report['phase2'].get('f11', 'UNKNOWN')}",
        "- Blockers: "
        + (", ".join(report["blockers"]) if report["blockers"] else "none"),
        "",
        "This is a lexical/static audit, **not** runtime/CI/hardware certification.",
        "Check JSON for complete path:line inventories. The owner/worker thread for",
        "each producer requires manual callgraph review and tests.",
    ]
    (out / "F11_M0_INTEGRATION_INVENTORY.md").write_text(
        "\n".join(summary) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description="Read-only baseline for AP2-F11")
    cli.add_argument("--repo", type=Path, default=Path.cwd())
    cli.add_argument("--out", type=Path, default=Path("/tmp/michi-f11-m0"))
    cli.add_argument("--gate", choices=("baseline", "naming"), default="baseline")
    args = cli.parse_args(argv)
    try:
        report = scan(args.repo)
    except (subprocess.CalledProcessError, RuntimeError) as error:
        print(f"STOP_M0_GIT_UNAVAILABLE: {error}", file=sys.stderr)
        return 4
    write_outputs(args.out, report)
    violations = report["nomenclature"]["matches"]
    if report["blockers"]:
        print("STOP_M0_STATIC_REVIEW: " + ",".join(report["blockers"]), file=sys.stderr)
        return 3
    if args.gate == "naming" and violations:
        print(f"STOP_M0_NAMING: {violations} violations", file=sys.stderr)
        return 2
    print(
        f"M0_STATIC_PASS head={report['head']} "
        f"naming_hits={violations} gate={args.gate}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
