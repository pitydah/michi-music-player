#!/usr/bin/env python3
"""Audit capability truthfulness across the runtime layer.

Checks the four capability sources for hardcoded/static announcements and
verifies every announced capability has a backing service registered in
SERVICE_MANIFEST with a healthy lifecycle entry:

  1. ui_qml_bridge/capability_bridge.py       — real probes (has_* keys)
  2. ui_qml_bridge/service_capabilities.py    — static state computation
  3. michi_ai/v2/intent/capability_resolver.py — evidence-based resolver
  4. michi_ai/context/ai_snapshot_service.py   — Michi AI snapshot

FASE 11 — FALSE-SUCCESS scan (semantic, AST-based): flags functions in
``core/`` and ``ui_qml_bridge/`` that return a success envelope without
performing work:

  - ``return {"ok": True, ...}`` dict literal whose enclosing function body
    has NO side-effect-ish call (delegation to ``self._x`` / service methods,
    ``.execute(``/``.write(``/``.save(``/``.emit(``/``.update(``/
    ``.insert(``/``.delete(``/readback calls) AND no return of a sub-call
    result.
  - bare ``return True`` at the end of a function (name suggests an
    operation: set/apply/save/start/stop/create/delete/update/play/pair/
    transfer/sync/repair/confirm) that ALSO returns ok-dicts.

Findings are classified as VIOLATION (fail), DOCUMENTED (allowlisted
(module, function) with a reason), or QUERY (pure read/transform semantics —
reported as info, never a violation).

FAILS (exit 1) when:
  - A hardcoded ``True`` capability dict is found (dict literal with a string
    key valued ``True`` that is not evidence-gated and not documented
    metadata).
  - A capability is announced for a key with no backing service in the
    manifest (probe/alias tables are authoritative).
  - A capability is backed only by services whose descriptor lifecycle is
    LEGACY_COMPONENT.
  - A false-success candidate (ok:True envelope without work) is not
    documented in the FALSE_SUCCESS_ALLOWLIST and not a pure query.

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

# ── FASE 11: false-success scan ────────────────────────────────────────────
# Semantic heuristic: a function whose body performs NO side-effect-ish call
# (delegation to self._x services, mutation of self state, write/execute/emit
# family) and returns a literal ``{"ok": True, ...}`` envelope is a candidate
# false success. Pure queries/transforms (parse/format/get/validate/preview/
# snapshot) are classified QUERY (info). Everything else must be documented
# here (module, function) with a reason, else it FAILS.

FALSE_SUCCESS_SCAN_DIRS = ("core", "ui_qml_bridge")

# Attributes that count as side-effect-ish calls (write/execute/emit/readback
# family plus common module-level helpers such as shutil.copy2 / json.dump).
_SIDE_EFFECT_ATTRS = frozenset({
    "execute", "write", "save", "emit", "update", "insert", "delete",
    "get_state", "get", "readback", "commit", "run", "start", "stop", "play",
    "pause", "add", "remove", "create", "apply", "scan", "refresh", "connect",
    "send", "open", "openUrl", "close", "rename", "move", "copy", "copy2",
    "copyfile", "export", "import", "sync", "repair", "confirm", "pair",
    "transfer", "terminate", "kill", "killpg", "flush", "fetch", "set",
    "push", "enqueue", "schedule", "submit", "store", "persist", "append",
    "extend", "pop", "backfill", "initialize", "register", "launch", "spawn",
    "resume", "cancel", "retry", "rollback", "restore", "request", "notify",
    "broadcast", "load", "reload", "attach", "detach", "begin", "end",
    "checkout", "query", "select", "dump", "dumps", "discard", "put",
    "write_text", "write_bytes", "unlink", "mkdir", "makedirs", "rmtree",
    "sort", "reverse", "clear", "setdefault", "collect", "process", "poll",
    "wait", "communicate", "replace", "truncate", "writelines", "Popen",
    "setText", "update_item", "add_to", "setValue", "setGroup",
})

# Name calls whose verb prefixes indicate work (write_tags, set_, analyse_file,
# classify_audio_quality, …).
_SIDE_EFFECT_NAME_PREFIXES = (
    "write", "save", "store", "persist", "emit", "send", "push", "execute",
    "run", "create", "delete", "remove", "update", "insert", "append", "copy",
    "move", "rename", "open", "close", "launch", "spawn", "start", "stop",
    "kill", "terminate", "add", "put", "set", "clear", "backfill", "export",
    "import", "sync", "repair", "confirm", "transfer", "pair", "request",
    "notify", "broadcast", "register", "apply", "attach", "detach", "commit",
    "rollback", "restore", "flush", "fetch", "load", "save", "enqueue",
    "schedule", "submit", "collect", "process", "initialize", "resume",
    "cancel", "retry", "refresh", "scan", "play", "pause", "generate",
    "analys", "classif", "read", "write_", "set_",
)

# Function names suggesting pure query/transform semantics — never flagged.
_QUERY_NAME_RE = re.compile(
    r"^(get_|is_|has_|list_|find_|search_|read_|count_|parse_|format_|"
    r"build_|make_|render_|serialize_|describe_|_ok$|snapshot|preview|"
    r"validate|confirmDestructive|locate_file|supported|rip_plan|"
    r"_result_to_dict|copy_version|copyVersion)",
)

# Documented false-success candidates: (module, function) → reason. Every
# entry was reviewed during FASE 11 (semantic audit); none performs hidden
# work — they are honest deferred responses, legacy compat shims, lifecycle
# no-ops or documented debt to be wired in later stabilization waves.
FALSE_SUCCESS_ALLOWLIST: dict[tuple[str, str], str] = {
    ("album_enrichment_service.py", "fetch_metadata"):
        "Honest DEFERRED_PHYSICAL response ('Requires MusicBrainz provider').",
    ("album_enrichment_service.py", "fetch_cover"):
        "Honest DEFERRED_PHYSICAL response ('Requires CoverArtArchive provider').",
    ("album_service.py", "search_cover"):
        "Honest deferred response ('Cover search requires network provider').",
    ("artist_enrichment_service.py", "fetch_image"):
        "Honest DEFERRED_PHYSICAL response.",
    ("artist_enrichment_service.py", "fetch_biography"):
        "Honest DEFERRED_PHYSICAL response.",
    ("artist_enrichment_service.py", "resolve_aliases"):
        "Honest DEFERRED_PHYSICAL response.",
    ("cover_art_service.py", "search_cover"):
        "Honest deferred response ('Requires network provider').",
    ("disc_lab_bridge.py", "cover"):
        "Honest DEFERRED_PHYSICAL response ('Cover search requires MusicBrainz "
        "provider').",
    ("micro_server_service.py", "check_compatibility"):
        "Honest DEFERRED_PHYSICAL response (LEGACY module).",
    ("device_sync_service.py", "selection"):
        "Legacy bridge-compat shim on the F8 facade: echo-only policy getter; "
        "the sync pipeline does not read it.",
    ("device_sync_service.py", "transcode_policy"):
        "Legacy bridge-compat shim (F8): echo-only policy setter.",
    ("device_sync_service.py", "naming_policy"):
        "Legacy bridge-compat shim (F8): echo-only policy setter.",
    ("device_sync_service.py", "set_naming_pattern"):
        "Legacy bridge-compat shim (F8): echo-only policy setter.",
    ("device_sync_service.py", "collision_policy"):
        "Legacy bridge-compat shim (F8): echo-only policy setter.",
    ("device_sync_service.py", "set_collision_strategy"):
        "Legacy bridge-compat shim (F8): echo-only policy setter.",
    ("device_sync_service.py", "size_estimate"):
        "Legacy bridge-compat shim (F8): echo-only estimator.",
    ("devices_bridge.py", "selection"):
        "Legacy shim mirroring device_sync_service.selection.",
    ("history_query_service.py", "set_history_enabled"):
        "WIRED (debt D4): persists history/enabled via settings_manager; "
        "record_play refuses new entries with HISTORY_DISABLED.",
    ("history_query_service.py", "set_history_limit"):
        "WIRED (debt D4): persists history/limit; fetch caps results and "
        "record_play prunes the oldest entries.",
    ("home_audio_service.py", "start"):
        "Lifecycle no-op: network starts only via explicit enable_* methods; "
        "start() reports route count (admin/idempotent).",
    ("home_audio_service.py", "cancel"):
        "Lifecycle no-op counterpart of start(); routes are managed via "
        "start_route/stop_route.",
    ("playlist_service.py", "cancel_import"):
        "WIRED (debt D1): cancels playlist_import jobs via the real "
        "job_service.cancel_job; honest NO_ACTIVE_IMPORT otherwise.",
    ("playlists_bridge.py", "cancelPlaylistImport"):
        "Bridge fallback when no playlist service is wired (no-op guard).",
    ("queue_service.py", "save_as_playlist"):
        "Legacy dead API: the real save flows through QueueBridge → "
        "PlaylistBridge; method kept for compat.",
    ("settings_adapters.py", "verify"):
        "Documented default contract: adapters that only persist have no live "
        "runtime target; bridges override with real readback.",
    ("library_bridge.py", "setMusicFolder"):
        "Real effect via settings alias set_ (QSettings write).",
    ("nowplaying_bridge.py", "_ok"):
        "Envelope helper — constructs the ok:True result dict itself.",
}


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


# ── FASE 11: false-success helpers ─────────────────────────────────────────

def _side_effect_score(fn: ast.FunctionDef) -> int:
    """Count side-effect-ish operations in a function body.

    Counts: calls on ``self._x``/``self._x.y`` (delegation/mutation), calls
    whose attribute is in the write/execute/emit family, Name calls whose id
    starts with a work verb, and assignments/deletes on ``self`` state.
    """
    score = 0
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                base = func.value
                is_self_call = (
                    (isinstance(base, ast.Name) and base.id == "self")
                    or (isinstance(base, ast.Attribute)
                        and isinstance(base.value, ast.Name)
                        and base.value.id == "self")
                )
                if is_self_call or func.attr in _SIDE_EFFECT_ATTRS:
                    score += 1
            elif isinstance(func, ast.Name) \
                    and (func.id in ("open", "print")
                         or func.id.startswith(_SIDE_EFFECT_NAME_PREFIXES)):
                score += 1
        elif isinstance(node, (ast.Assign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                is_self_mutation = (
                    (isinstance(target, ast.Attribute)
                     and isinstance(target.value, ast.Name)
                     and target.value.id == "self")
                    or (isinstance(target, ast.Subscript)
                        and isinstance(target.value, ast.Attribute)
                        and isinstance(target.value.value, ast.Name)
                        and target.value.value.id == "self")
                )
                if is_self_mutation:
                    score += 1
        elif isinstance(node, ast.Delete):
            for target in node.targets:
                if isinstance(target, ast.Subscript) \
                        and isinstance(target.value, ast.Attribute) \
                        and isinstance(target.value.value, ast.Name) \
                        and target.value.value.id == "self":
                    score += 1
    return score


def _returns_subcall_result(fn: ast.FunctionDef) -> bool:
    """True when any return statement returns a call result (real outcome)."""
    for node in ast.walk(fn):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
            return True
    return False


def _ok_true_dict_returns(fn: ast.FunctionDef) -> list[ast.Return]:
    """Return statements whose value is a dict literal with ``ok: True``."""
    hits: list[ast.Return] = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Dict):
            continue
        for key, value in zip(node.value.keys, node.value.values, strict=False):
            if isinstance(key, ast.Constant) and key.value == "ok" \
                    and isinstance(value, ast.Constant) and value.value is True:
                hits.append(node)
                break
    return hits


def _false_success_findings() -> tuple[list[dict], list[dict], list[dict]]:
    """(violations, documented, query-info) for ok:True envelopes without work.

    Scans ``core/`` + ``ui_qml_bridge/`` (productive service/bridge layer).
    """
    violations: list[dict] = []
    documented: list[dict] = []
    query_info: list[dict] = []
    seen: set[tuple[str, str, int]] = set()

    for directory in FALSE_SUCCESS_SCAN_DIRS:
        base = HERE / directory
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts or "build" in path.parts \
                    or "test" in path.parts:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
            except (SyntaxError, OSError):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                hits = _ok_true_dict_returns(node)
                if not hits:
                    continue
                key = (path.name, node.name)
                if key in seen:
                    continue
                seen.add(key)
                if _side_effect_score(node) > 0 or _returns_subcall_result(node):
                    continue
                if _QUERY_NAME_RE.match(node.name):
                    query_info.append({
                        "file": path.name,
                        "lineno": hits[0].lineno,
                        "function": node.name,
                        "reason": "pure query/transform semantics (no mutation "
                                  "expected)",
                    })
                    continue
                allow = FALSE_SUCCESS_ALLOWLIST.get(key)
                if allow:
                    documented.append({
                        "file": path.name,
                        "lineno": hits[0].lineno,
                        "function": node.name,
                        "reason": allow,
                    })
                else:
                    violations.append({
                        "file": path.name,
                        "lineno": hits[0].lineno,
                        "function": node.name,
                        "reason": "ok:True envelope with no side-effect call "
                                  "and no sub-call result",
                    })

    # A2: bare ``return True`` in operation-named functions that ALSO return
    # ok-dicts (fallback success inside a dict-returning API).
    op_verb_re = re.compile(
        r"(set|apply|save|start|stop|create|delete|update|play|pair|transfer|"
        r"sync|repair|confirm)",
        re.IGNORECASE,
    )
    for directory in FALSE_SUCCESS_SCAN_DIRS:
        base = HERE / directory
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts or "build" in path.parts \
                    or "test" in path.parts:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
            except (SyntaxError, OSError):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if not op_verb_re.search(node.name):
                    continue
                if not node.body or not isinstance(node.body[-1], ast.Return):
                    continue
                last = node.body[-1]
                if not isinstance(last.value, ast.Constant) \
                        or last.value.value is not True:
                    continue
                if not _ok_true_dict_returns(node):
                    continue
                key = (path.name, node.name)
                if key in seen:
                    continue
                seen.add(key)
                allow = FALSE_SUCCESS_ALLOWLIST.get(key)
                row = {
                    "file": path.name,
                    "lineno": last.lineno,
                    "function": node.name,
                    "reason": allow or "bare return True fallback in an "
                                        "operation-named function returning dicts",
                }
                if allow:
                    documented.append(row)
                else:
                    violations.append(row)
    return violations, documented, query_info


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
    false_success, false_success_doc, false_success_query = \
        _false_success_findings()

    return {
        "generated_by": "tools/audit_capability_truthfulness.py",
        "announced_capabilities": len(announced),
        "manifest_capability_entries": len(manifest),
        "healthy_capabilities": healthy,
        "unbacked_capabilities": unbacked,
        "legacy_backed_capabilities": legacy_backed,
        "hardcoded_true_violations": hardcoded,
        "hardcoded_true_info": hardcoded_info,
        "false_success_violations": false_success,
        "false_success_documented": false_success_doc,
        "false_success_query": false_success_query,
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
                         or report["hardcoded_true_violations"]
                         or report["false_success_violations"]) else 1

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
    print(f"FASE 11 — false-success violations: "
          f"{len(report['false_success_violations'])}")
    for row in report["false_success_violations"]:
        print(f"  - {row['file']}:{row['lineno']} {row['function']} — "
              f"{row['reason']}")
    print(f"FASE 11 — false-success documented (allowlist): "
          f"{len(report['false_success_documented'])}")
    for row in report["false_success_documented"]:
        print(f"  - {row['file']}:{row['lineno']} {row['function']} — "
              f"{row['reason']}")
    print(f"FASE 11 — false-success QUERY (pure semantics, info): "
          f"{len(report['false_success_query'])}")
    for row in report["false_success_query"]:
        print(f"  - {row['file']}:{row['lineno']} {row['function']} — "
              f"{row['reason']}")

    if report["unbacked_capabilities"] or report["legacy_backed_capabilities"] \
            or report["hardcoded_true_violations"] \
            or report["false_success_violations"]:
        print("FAIL: capability truthfulness violations found.")
        return 1
    print("OK: every announced capability is manifest-backed with a healthy "
          "lifecycle; no hardcoded True capabilities; no undocumented false "
          "successes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
