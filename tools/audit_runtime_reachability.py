#!/usr/bin/env python3
"""Audit runtime service reachability against the declarative manifest.

Produces a per-service report (class, file, productive instantiation, container
key, lifecycle, dependencies, consumers, bridges, AI tools, capabilities, unit
tests, vertical tests, status) and FAILS (exit 1) when:

  1. A productive service is ORPHAN (no consumers, no bridge, no AI tool, no test)
  2. A canonical duplicate exists (two or more productive classes with the same
     name — designation table shared with
     tests/architecture/test_no_duplicate_service_class_names.py)
  3. A bridge calls a method that does not exist on the service it references
     (best-effort AST check over the wiring in bridge_factory.py; calls guarded
     by ``hasattr`` dynamic dispatch are skipped)
  4. A required service is bound to None (container validate)

Data sources:
  - core/service_manifest.py (SERVICE_MANIFEST — source of truth)
  - core/composition/*.py + core/application_bootstrap.py (registrations and
    instantiations)
  - ui_qml_bridge/bridge_factory.py (real bridge → service wiring)
  - michi_ai/v2/tools/register_builtin.py (GW_MAP tool mappings)
  - tests/ (unit) + tests/integration + tests/architecture (vertical)

Usage:
  python tools/audit_runtime_reachability.py
  python tools/audit_runtime_reachability.py --output docs/audits/REACHABILITY_REPORT.md
  python tools/audit_runtime_reachability.py --json
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from core.service_manifest import SERVICE_MANIFEST, ServiceClass  # noqa: E402

COMPOSITION_FILES = (
    HERE / "core" / "composition" / "infrastructure.py",
    HERE / "core" / "composition" / "playback.py",
    HERE / "core" / "composition" / "library.py",
    HERE / "core" / "composition" / "audio_lab.py",
    HERE / "core" / "composition" / "ecosystem.py",
    HERE / "core" / "composition" / "settings.py",
    HERE / "core" / "composition" / "intelligence.py",
    HERE / "core" / "application_bootstrap.py",
)

SCAN_DIRS = (
    "core", "library", "streaming", "recognition", "integrations",
    "sync", "audio", "recommendation", "metadata", "ui_qml_bridge",
)

BRIDGE_DIR = HERE / "ui_qml_bridge"
TESTS_DIR = HERE / "tests"

# Additional parallel-layer designations only visible when scanning the extra
# dirs (audio/, metadata/) beyond the architecture test's scan list.
EXTRA_COEXISTING_DUPLICATES: dict[str, tuple[str, ...]] = {
    "PlaybackState": (
        "audio/player.py",
        "audio/fake_player.py",
    ),
    "MetadataProposal": (
        "core/metadata_editor_service.py",
        "metadata/review/schemas.py",
    ),
}

# Services that are legitimately passive/leaf and may lack explicit consumers
# or a dedicated test file. Each entry carries the evidence for why it is not
# an orphan (audit RUNTIME_SERVICE_AUDIT_CURRENT §6).
DOCUMENTED_EXCEPTIONS: dict[str, str] = {
    "paths": "XDG path resolver used by every layer; passive by design.",
    "read_connection_factory": "Read-only connection factory consumed by capability_bridge (declared consumer).",
    "settings_manager": "QSettings wrapper consumed by settings_service/coordinator.",
    "library_filtered_query_service": "Pure alias of library_query_service (same object).",
    "knowledge_broker": "Standalone; production wiring unverified (audit S4).",
    "provider_manager": "Registry consumed by DetectionService (recognition domain).",
    "hybrid_audio_manager": "Application service owned by PlayerService.",
    "mpd_service_manager": "Process manager owned by MpdBackend.",
    "page_state_store": "UI state store consumed by shell.",
    "bridge_factory": "Factory consumed by ApplicationBootstrap.create_bridges.",
    "action_registry_binder": "Factory consumed by shell wiring.",
    "selection_context_bridge": "UI state store consumed by QML shell.",
    "job_bridge": "UI adapter consumed by library/audio_lab screens.",
    "job_manager": "LEGACY component retired in S2.",
    "audio_lab_job_adapter": "LEGACY component retired in S2.",
    "mpris_adapter": "UI adapter owned by desktop integration (MPRIS).",
    "runtime_persistence": "Session persistence; consumed by shell.",
    "confirmation_service": "Shared confirmation flow; consumed by intelligence/UI.",
    "action_registry": "Registry consumed by ActionRegistryBinder and UI.",
    "event_bus": "Shared pub/sub consumed across layers.",
    "worker_manager": "Executor consumed by jobs, bridges and services.",
    "query_executor": "Executor consumed by services and bridges.",
    "connection_factory": "Alias of database object for legacy consumers.",
    "writer_coordinator": "State store for coordinated writes; consumed by services.",
    "track_repository": "Passive repository consumed via query services.",
    "album_repository": "Passive repository consumed via query services.",
    "artist_repository": "Passive repository consumed via query services.",
}


def registered_keys() -> set[str]:
    """Container keys registered by the composition builders (static scan)."""
    pattern = re.compile(r"register\(\s*(['\"])(?P<key>[a-z_0-9]+)\1\s*,")
    keys: set[str] = set()
    for path in COMPOSITION_FILES:
        source = path.read_text(encoding="utf-8")
        for match in pattern.finditer(source):
            keys.add(match.group("key"))
    return keys


def _composition_ast() -> list[tuple[Path, ast.Module]]:
    trees: list[tuple[Path, ast.Module]] = []
    for path in COMPOSITION_FILES:
        try:
            trees.append((path, ast.parse(path.read_text(encoding="utf-8"))))
        except (SyntaxError, OSError):
            continue
    return trees


def _register_exprs() -> dict[str, ast.expr]:
    """Map container key → the expression passed to register().

    Exception fallbacks (``register("key", None)``) are skipped in favor of
    the real construction expression for the same key.
    """
    exprs: dict[str, ast.expr] = {}
    for _path, tree in _composition_ast():
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call = node.value
                func = call.func
                if isinstance(func, ast.Attribute) and func.attr == "register" \
                        and len(call.args) >= 2 and isinstance(call.args[0], ast.Constant):
                    key = call.args[0].value
                    value = call.args[1]
                    if isinstance(value, ast.Constant):
                        continue
                    exprs[key] = value
    return exprs


def class_for_key(key: str) -> str | None:
    """Resolve the concrete class constructed for a container key.

    Follows local variable assignments and cross-key aliasing
    (e.g. ``library_filtered_query_service`` registered with the same object
    as ``library_query_service``).
    """
    exprs = _register_exprs()

    def _resolve(expr: ast.expr | None, seen: set[str] | None = None) -> str | None:
        if expr is None:
            return None
        if isinstance(expr, ast.Call):
            func = expr.func
            if isinstance(func, ast.Name):
                return func.id
            if isinstance(func, ast.Attribute):
                return func.attr
        if isinstance(expr, ast.Name):
            name = expr.id
            # 1. Variable assigned in a composition file
            #    (e.g. ``job_service = JobService(...)`` then
            #    ``register("job_service", job_service)``).
            for _path, tree in _composition_ast():
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign) and len(node.targets) == 1:
                        target = node.targets[0]
                        if isinstance(target, ast.Name) and target.id == name:
                            return _resolve(node.value, seen)
            # 2. Alias of another container key (same object).
            if name in exprs:
                if seen and name in seen:
                    return None
                return _resolve(exprs[name], (seen or set()) | {name})
        return None

    return _resolve(exprs.get(key))


def _all_python_files() -> list[Path]:
    files: list[Path] = []
    for directory in SCAN_DIRS:
        base = HERE / directory
        if not base.exists():
            continue
        files.extend(p for p in base.rglob("*.py") if "__pycache__" not in p.parts)
    return files


def class_methods(class_name: str) -> set[str] | None:
    """Method names of ``class <class_name>`` across the tree (AST).

    Handles module-level re-export aliases (``JobService = DurableJobService``)
    by following the alias target. Returns None when the class is unknown.
    """
    method_sets: list[set[str]] = []
    for path in _all_python_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except (SyntaxError, OSError):
            continue
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                methods = {
                    child.name
                    for child in ast.walk(node)
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and child != node and child.col_offset >= node.col_offset
                }
                method_sets.append(methods)
            elif isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and target.id == class_name:
                    value = node.value
                    if isinstance(value, ast.Name):
                        nested = class_methods(value.id)
                        if nested is not None:
                            method_sets.append(nested)
    if not method_sets:
        return None
    return set().union(*method_sets)


def bridge_wiring() -> dict[str, dict[str, str]]:
    """bridge file name → {param name → container key} from bridge_factory.

    Derived from ``BridgeClass(param=self._get("key"), ...)`` kwargs in every
    ``create_*_bridge`` method, which is the single real wiring point.
    """
    wiring: dict[str, dict[str, str]] = {}
    factory = BRIDGE_DIR / "bridge_factory.py"
    try:
        tree = ast.parse(factory.read_text(encoding="utf-8"))
    except (SyntaxError, OSError):
        return wiring
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith("create_"):
            continue
        for stmt in ast.walk(node):
            if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
                continue
            target = stmt.targets[0]
            if not isinstance(target, ast.Name) or not target.id.startswith("_"):
                continue
            value = stmt.value
            if not isinstance(value, ast.Call):
                continue
            func = value.func
            if not (isinstance(func, ast.Name) and "Bridge" in func.id):
                continue
            params: dict[str, str] = {}
            for kw in value.keywords:
                if kw.arg is None or not isinstance(kw.value, ast.Call):
                    continue
                inner = kw.value
                inner_func = inner.func
                if isinstance(inner_func, ast.Attribute) and inner_func.attr == "_get" \
                        and inner.args and isinstance(inner.args[0], ast.Constant):
                    params[kw.arg] = str(inner.args[0].value)
            module_name = next(
                (imp.module.split(".")[-1] for imp in ast.walk(node)
                 if isinstance(imp, ast.ImportFrom) and imp.module
                 and imp.module.startswith("ui_qml_bridge")
                 and any(a.name == func.id for a in imp.names)),
                None,
            )
            if module_name:
                wiring[module_name] = params
    return wiring


def bridge_consumers(key: str, class_name: str | None) -> list[str]:
    """Bridge files referencing the container key or the class name."""
    consumers: list[str] = []
    if not BRIDGE_DIR.exists():
        return consumers
    for path in sorted(BRIDGE_DIR.glob("*.py")):
        source = path.read_text(encoding="utf-8", errors="ignore")
        if key in source or (class_name and class_name in source):
            consumers.append(path.name)
    return consumers


def ai_tool_count(class_name: str | None, key: str) -> int:
    """Number of GW_MAP tool mappings whose gateway domain this service backs.

    Only services that feed an AssistantGateways domain count: playback,
    queue, library query, playlists, settings, audio lab, mix, library
    doctor, devices/sync, diagnostics, jobs, navigation, metadata. Shared
    infrastructure (database, event bus, worker manager) backs nothing
    directly and reports 0.
    """
    try:
        from michi_ai.v2.tools.register_builtin import GW_MAP
    except Exception:
        return 0
    key_to_domain = {
        "playback_service": "playback",
        "queue_service": "queue",
        "library_query_service": "library",
        "global_search_service": "library",
        "track_action_service": "playback",
        "playlist_service": "playlists",
        "settings_service": "settings",
        "audio_lab_service": "audio_lab",
        "mix_service": "mix",
        "library_doctor_service": "library_doctor",
        "device_sync_service": "devices",
        "diagnostics_service": "diagnostics",
        "job_service": "jobs",
        "navigation_service": "navigation",
        "metadata_service": "metadata",
        "metadata_editor_service": "metadata",
        "favorite_service": "library",
        "library_mutation_service": "library",
    }
    domain = key_to_domain.get(key)
    if domain is None:
        return 0
    return sum(1 for gattr, _method in GW_MAP.values() if gattr == domain)


def test_files(class_name: str) -> tuple[list[str], list[str]]:
    """(unit test files, vertical test files) mentioning the class name."""
    unit: list[str] = []
    vertical: list[str] = []
    if not class_name or not TESTS_DIR.exists():
        return unit, vertical
    for path in sorted(TESTS_DIR.rglob("test_*.py")):
        rel = path.relative_to(TESTS_DIR).as_posix()
        if rel.startswith("qml"):
            continue
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if class_name in source:
            if rel.startswith("integration") or rel.startswith("architecture"):
                vertical.append(rel)
            else:
                unit.append(rel)
    return unit, vertical


def productive_duplicates() -> dict[str, list[str]]:
    """Class names defined by more than one file, classified by productivity.

    Classification (master prompt S12): a definition is PRODUCTIVE when it is
    instantiated by composition or bridges (constructor call in
    core/composition/*.py, core/application_bootstrap.py, ui_qml_bridge/*.py);
    otherwise it is legacy (LEGACY marker, DeprecationWarning, or static-helper
    namespace not registered as a service).
    """
    try:
        from tests.architecture.test_no_duplicate_service_class_names import (
            COEXISTING_DUPLICATES,
            SERVICE_DUPLICATES,
        )
    except Exception:
        COEXISTING_DUPLICATES = {}
        SERVICE_DUPLICATES = {}

    coexisting = dict(COEXISTING_DUPLICATES)
    coexisting.update(EXTRA_COEXISTING_DUPLICATES)

    pattern = re.compile(r"^class\s+(\w+)\b", re.M)
    by_name: dict[str, list[str]] = {}
    for path in _all_python_files():
        if "build" in path.parts:
            continue
        source = path.read_text(encoding="utf-8", errors="ignore")
        for match in pattern.finditer(source):
            by_name.setdefault(match.group(1), []).append(
                path.relative_to(HERE).as_posix()
            )

    instantiation_sources: list[str] = []
    for path in COMPOSITION_FILES:
        instantiation_sources.append(path.read_text(encoding="utf-8", errors="ignore"))
    if BRIDGE_DIR.exists():
        instantiation_sources.extend(
            p.read_text(encoding="utf-8", errors="ignore")
            for p in BRIDGE_DIR.rglob("*.py")
        )
    instantiation_text = "\n".join(instantiation_sources)

    # Mirrors the legacy-designation the architecture test enforces.
    legacy_by_designation: set[str] = set()
    for _name, (_prod, legacy) in SERVICE_DUPLICATES.items():
        legacy_by_designation.update(legacy)

    def _is_productive(file: str, class_name: str) -> bool:
        if file in legacy_by_designation:
            return False
        return re.search(rf"\b{re.escape(class_name)}\s*\(", instantiation_text) is not None

    result: dict[str, dict[str, list[str]]] = {}
    for name, files in sorted(by_name.items()):
        if len(files) < 2:
            continue
        if name in coexisting:
            continue
        prod = [f for f in files if _is_productive(f, name)]
        legacy = [f for f in files if not _is_productive(f, name)]
        result[name] = {"productive": prod, "legacy": legacy}
    return result


def bridge_method_mismatches() -> list[str]:
    """Best-effort check: bridge calls to methods missing on the service.

    The param → container key mapping comes from bridge_factory.py (the real
    wiring); attr → param comes from each bridge ``__init__``. Calls guarded
    by ``hasattr(self._attr, 'method')`` are dynamic dispatch and are skipped.
    Unresolvable steps are skipped (best-effort by design).
    """
    mismatches: list[str] = []
    wiring = bridge_wiring()
    if not BRIDGE_DIR.exists():
        return mismatches
    for path in sorted(BRIDGE_DIR.glob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            # attr → param assignment map from __init__
            attr_to_param: dict[str, str] = {}
            for child in ast.walk(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        and child.name == "__init__":
                    for stmt in ast.walk(child):
                        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                            target = stmt.targets[0]
                            if isinstance(target, ast.Attribute) and isinstance(stmt.value, ast.Name):
                                attr_to_param[target.attr] = stmt.value.id
            # attr → container key (param must appear in the bridge wiring)
            attr_key: dict[str, str] = {}
            module_wiring = wiring.get(path.stem, {})
            for attr, param in attr_to_param.items():
                if param in module_wiring:
                    attr_key[attr] = module_wiring[param]
            if not attr_key:
                continue

            def _guarded(attr: str, method: str, klass: ast.ClassDef) -> bool:
                for ancestor in ast.walk(klass):
                    if not isinstance(ancestor, (ast.If, ast.IfExp)):
                        continue
                    test = ancestor.test
                    for sub in ast.walk(test):
                        if isinstance(sub, ast.Call):
                            f = sub.func
                            if isinstance(f, ast.Attribute) and f.attr == "hasattr" \
                                    and len(sub.args) == 2:
                                first = sub.args[0]
                                second = sub.args[1]
                                if isinstance(first, ast.Attribute) \
                                        and first.attr == attr \
                                        and isinstance(second, ast.Constant) \
                                        and second.value == method:
                                    return True
                return False

            for child in ast.walk(node):
                if not isinstance(child, ast.Call):
                    continue
                func = child.func
                if not (isinstance(func, ast.Attribute)
                        and isinstance(func.value, ast.Attribute)):
                    continue
                attr, method = func.value.attr, func.attr
                key = attr_key.get(attr)
                if key is None:
                    continue
                cls = class_for_key(key)
                if cls is None:
                    continue
                if _guarded(attr, method, node):
                    continue
                methods = class_methods(cls)
                if methods is None:
                    continue
                # Delegating wrappers (LibraryFilteredQueryService) expose
                # every inner method via __getattr__ — no static contract.
                if "__getattr__" in methods or "__getattribute__" in methods:
                    continue
                if method not in methods:
                    mismatches.append(
                        f"{path.name}:{child.lineno} {attr}.{method}() "
                        f"— key '{key}' ({cls}) has no such method"
                    )
    return mismatches


def compute_status(
    key: str,
    desc,
    is_registered: bool,
    consumers: list[str],
    ai_tools: int,
    unit_tests: list[str],
    vertical_tests: list[str],
) -> str:
    """Derive a status from the audit status enum."""
    if desc.service_class == ServiceClass.LEGACY_COMPONENT:
        return "LEGACY"
    if not is_registered and not desc.consumers and not consumers \
            and ai_tools == 0 and not unit_tests:
        return "ORPHAN"
    if vertical_tests:
        return "PRODUCTIVE"
    if unit_tests or consumers or ai_tools or desc.consumers:
        return "UNTESTED_VERTICAL"
    return "ORPHAN"


def build_report() -> dict:
    registered = registered_keys()
    rows: list[dict] = []
    orphans: list[str] = []
    for key, desc in sorted(SERVICE_MANIFEST.items()):
        class_name = class_for_key(key)
        unit, vertical = test_files(class_name) if class_name else ([], [])
        bridges = bridge_consumers(key, class_name)
        ai_tools = ai_tool_count(class_name, key)
        status = compute_status(
            key, desc, key in registered, bridges, ai_tools, unit, vertical
        )
        rows.append({
            "key": key,
            "class": class_name or "unknown",
            "registered": key in registered,
            "lifecycle": desc.lifecycle.value,
            "priority": desc.priority.value,
            "dependencies": list(desc.dependencies),
            "consumers": list(desc.consumers),
            "bridges": bridges,
            "ai_tools": ai_tools,
            "capabilities": list(desc.capabilities),
            "unit_tests": unit,
            "vertical_tests": vertical,
            "status": status,
        })
        if status == "ORPHAN" and key not in DOCUMENTED_EXCEPTIONS:
            orphans.append(key)
    return {
        "generated_by": "tools/audit_runtime_reachability.py",
        "manifest_entries": len(SERVICE_MANIFEST),
        "registered_keys": len(registered),
        "orphans": orphans,
        "documented_exceptions": sorted(DOCUMENTED_EXCEPTIONS),
        "duplicates": productive_duplicates(),
        "bridge_mismatches": bridge_method_mismatches(),
        "required_none": _required_none_check(),
        "rows": rows,
        "status_counts": dict(Counter(r["status"] for r in rows)),
    }


def _required_none_check() -> list[str]:
    """Container-level check: required services must never be None."""
    problems: list[str] = []
    try:
        from core.application_bootstrap import ApplicationBootstrap

        bootstrap = ApplicationBootstrap()
        bootstrap.build()
        problems.extend(bootstrap.container.validate_no_none_required())
        problems.extend(bootstrap.container.validate())
    except Exception as exc:  # noqa: BLE001 — tool reports, never crashes
        problems.append(f"container validation could not run: {exc}")
    return problems


def render_markdown(report: dict) -> str:
    lines = [
        "# Reporte de Reachabilidad de Servicios en Tiempo de Ejecución",
        "",
        f"Generado por `tools/audit_runtime_reachability.py` — "
        f"{report['manifest_entries']} entradas de manifest, "
        f"{report['registered_keys']} claves registradas.",
        "",
        "## Resumen de estados",
        "",
        "| Estado | Cantidad |",
        "|--------|----------|",
    ]
    for status, count in sorted(report["status_counts"].items()):
        lines.append(f"| {status} | {count} |")
    lines += [
        "",
        "## Servicios",
        "",
        "| Clave | Clase | Estado | Lifecycle | Consumidores | Bridges | "
        "AI tools | Tests unit | Tests vertical |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in report["rows"]:
        lines.append(
            f"| {row['key']} | {row['class']} | {row['status']} | "
            f"{row['lifecycle']} | {len(row['consumers'])} | "
            f"{len(row['bridges'])} | {row['ai_tools']} | "
            f"{len(row['unit_tests'])} | {len(row['vertical_tests'])} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="Write markdown report to this path")
    parser.add_argument("--json", action="store_true", help="Dump JSON report")
    args = parser.parse_args()

    report = build_report()

    if args.json:
        print(json.dumps(report, indent=2, default=list))
    else:
        print(render_markdown(report))

    failures: list[str] = []
    if report["orphans"]:
        failures.append(f"ORPHAN productive services: {report['orphans']}")
    dup_failures = [
        f"{name}: productive={dup['productive']} legacy={dup['legacy']}"
        for name, dup in report["duplicates"].items()
        if len(dup["productive"]) > 1
    ]
    if dup_failures:
        failures.append(f"canonical duplicates: {dup_failures}")
    if report["bridge_mismatches"]:
        failures.append(
            f"bridge/service contract mismatches: {report['bridge_mismatches']}"
        )
    if report["required_none"]:
        failures.append(
            f"required services bound to None: {report['required_none']}"
        )

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_markdown(report), encoding="utf-8")
        print(f"Report written to {out}")

    if failures:
        print("FAIL:", *failures, sep="\n  - ")
        return 1
    print("OK: no reachability violations (orphans, duplicates, contract "
          "mismatches, required-None bindings).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
