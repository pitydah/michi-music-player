#!/usr/bin/env python3
"""QML Hybrid Dependency Audit — detects hybrid patterns in ui_qml_bridge/.

Categories:
  REQUIRED_FALLBACK   — bridge that imports from ui.* (QtWidgets modules)
  MIGRATION_PENDING   — bridge without full QML parity
  UNSAFE_HYBRID       — SQL in bridges / threaded DB access / _svc after constructor
  DUPLICATED_LOGIC    — bridge duplicates existing QML or service
  REMOVABLE           — bridge can be removed (QML equivalent exists)
"""
from __future__ import annotations

import ast
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("hybrid_audit")

REPO = Path(__file__).resolve().parent.parent
BRIDGE_DIR = REPO / "ui_qml_bridge"
QML_DIR = REPO / "ui_qml"
TEST_DIR = REPO / "tests" / "qml"

SQL_PATTERN = re.compile(r'\b(SELECT|INSERT\s+INTO|UPDATE\s+\w+|DELETE\s+FROM)\b', re.IGNORECASE)
SQL_COMMENT = re.compile(r'^\s*#|"""|\'\'\'')
UI_IMPORT_PATTERN = re.compile(r"from\s+ui\s*\.|import\s+ui\s*\.")
QWIDGET_CLASSES = {"QWidget", "QDialog", "QMainWindow"}
DIALOG_CLASSES = {"QFileDialog", "QMessageBox", "QColorDialog"}


AuditResult = dict[str, Any]


def _find_bridge_files() -> list[Path]:
    return sorted(BRIDGE_DIR.rglob("*.py"))


def _is_duplicated_logic(bridge_name: str, bridge_path: Path, tree: ast.AST) -> bool:
    qml_equiv = _find_qml_equivalent(bridge_name)
    if not qml_equiv:
        return False
    common_services = _find_common_service_duplication(bridge_name)
    return bool(common_services)


def _extract_features(path: Path) -> set[str]:
    features: set[str] = set()
    try:
        text = path.read_text()
        if "return {\"ok\": True" in text or "return {\"ok\": True" in text:
            features.add("mock_action")
        if SQL_PATTERN.search(text):
            features.add("sql_inline")
        for cls in QWIDGET_CLASSES:
            if cls in text:
                features.add("qwidget_ref")
        for cls in DIALOG_CLASSES:
            if cls in text:
                features.add("dialog_ref")
        if "from ui." in text or "import ui." in text:
            features.add("ui_import")
        if "threading.Thread" in text or "QThread" in text:
            features.add("thread_usage")
        if re.search(r"\._svc\b|\._service\b|\._lib\b", text):
            features.add("patched_private_attr")
    except Exception:
        pass
    return features


def _find_qml_equivalent(name: str) -> Path | None:
    stem = name.replace("_bridge", "").replace("_", "")
    for qml_file in QML_DIR.rglob("*.qml"):
        qml_stem = qml_file.stem.lower().replace("_", "").replace(" ", "")
        if stem in qml_stem or qml_stem in stem:
            excluded = ("main", "michiapp", "qmldir")
            if qml_file.stem.lower() not in excluded:
                return qml_file
    return None


def _find_common_service_duplication(name: str) -> list[str]:
    text = (BRIDGE_DIR / f"{name}.py").read_text() if (BRIDGE_DIR / f"{name}.py").exists() else ""
    services = re.findall(r"self\._(\w+)\s*=", text)
    common = [s for s in services if s in ("db", "player", "lib", "svc", "wm", "nav")]
    return common


def _has_tests(name: str) -> bool:
    test_stem = f"test_{name}"
    if any(test_stem in f.stem for f in TEST_DIR.rglob("*.py")):
        return True
    actual_stem = name.replace("_bridge", "")
    return any(actual_stem in f.stem for f in TEST_DIR.rglob("*.py"))


def _has_qml_actions(name: str) -> bool:
    bridge_stem = name.replace("_bridge", "").replace("_", "")
    for qml_file in QML_DIR.rglob("*.qml"):
        qml_stem = qml_file.stem.lower().replace("_", "").replace(" ", "")
        if bridge_stem in qml_stem or qml_stem in bridge_stem:
            text = qml_file.read_text()
            if re.search(r"on[A-Z]\w+\s*:", text) or re.search(r"Slot\s+", text):
                return True
    return False


def _find_sql_in_bridges() -> list[dict]:
    results: list[dict] = []
    for path in _find_bridge_files():
        rel = str(path.relative_to(REPO))
        text = path.read_text()
        lines = text.splitlines()
        in_docstring = False
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                in_docstring = not in_docstring
                continue
            if in_docstring or stripped.startswith("#"):
                continue
            if SQL_PATTERN.search(stripped):
                results.append({
                    "file": rel, "line": i,
                    "category": "UNSAFE_HYBRID",
                    "reason": stripped[:80],
                })
    return results


def _find_ui_imports() -> list[dict]:
    results: list[dict] = []
    for path in _find_bridge_files():
        rel = path.relative_to(REPO)
        text = path.read_text()
        for i, line in enumerate(text.splitlines(), 1):
            if "from ui." in line or "import ui." in line:
                results.append({
                    "file": str(rel), "line": i, "code": line.strip()[:80],
                    "category": "REQUIRED_FALLBACK",
                })
    return results


def _find_qwidget_refs() -> list[dict]:
    results: list[dict] = []
    for path in _find_bridge_files():
        rel = path.relative_to(REPO)
        text = path.read_text()
        for cls_name in QWIDGET_CLASSES | DIALOG_CLASSES:
            for i, line in enumerate(text.splitlines(), 1):
                if cls_name in line and not line.strip().startswith("#"):
                    results.append({
                        "file": str(rel), "line": i, "code": line.strip()[:80],
                        "category": "REQUIRED_FALLBACK",
                    })
    return results


def _find_bridges_without_services() -> list[dict]:
    results: list[dict] = []
    EXEMPT = {"__init__.py", "error_catalog.py", "context_bindings.py", "context_registrar.py",
              "route_registry.py", "command_bus.py", "action_registry.py", "service_bundle.py",
              "service_capabilities.py", "page_state_store.py", "qml_main.py"}
    for path in _find_bridge_files():
        rel = str(path.relative_to(REPO))
        if path.name in EXEMPT:
            continue
        text = path.read_text()
        has_service_ref = bool(re.search(r"self\._(svc|service|db|player|wm|ctrl|manager|ctx|factory|nav|cover|lib|src|sel|radio|qe|search)", text))
        if not has_service_ref and "QObject" in text:
            results.append({
                "file": rel,
                "category": "REMOVABLE",
                "reason": "No service dependency",
            })
    return results


def _find_duplicated_services() -> list[dict]:
    results: list[dict] = []
    for path in _find_bridge_files():
        rel = path.relative_to(REPO)
        name = path.stem
        if _is_duplicated_logic(name, path, ast.parse(path.read_text())):
            qml_equiv = _find_qml_equivalent(name)
            results.append({
                "file": str(rel),
                "category": "DUPLICATED_LOGIC",
                "reason": f"QML equivalent exists: {qml_equiv.name if qml_equiv else 'unknown'}",
            })
    return results


def _find_routes_without_tests() -> list[dict]:
    results: list[dict] = []
    for path in _find_bridge_files():
        rel = path.relative_to(REPO)
        name = path.stem
        if not _has_tests(name):
            results.append({
                "file": str(rel),
                "category": "MIGRATION_PENDING",
                "reason": "No test coverage",
            })
    return results


def _find_pages_without_actions() -> list[dict]:
    results: list[dict] = []
    for path in _find_bridge_files():
        rel = path.relative_to(REPO)
        name = path.stem
        if not _has_qml_actions(name):
            results.append({
                "file": str(rel),
                "category": "MIGRATION_PENDING",
                "reason": "QML page without actions",
            })
    return results


_MOCK_OK_PATTERN = re.compile(r'\breturn\s*\{.*"ok"\s*:\s*True')


def _find_mock_actions() -> list[dict]:
    results: list[dict] = []
    for path in _find_bridge_files():
        rel = str(path.relative_to(REPO))
        text = path.read_text()
        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            if _MOCK_OK_PATTERN.search(stripped):
                results.append({
                    "file": rel, "line": i,
                    "category": "REMOVABLE",
                    "reason": f"Simulated action: {stripped[:60]}",
                })
    return results


def _find_patched_private_attrs() -> list[dict]:
    results: list[dict] = []
    for path in _find_bridge_files():
        rel = str(path.relative_to(REPO))
        if rel in ("ui_qml_bridge/__init__.py",):
            continue
        text = path.read_text()
        init_end = _find_init_end(text)
        for m in re.finditer(r"(self\._\w+)\s*=\s*(?:self\.)?", text):
            attr = m.group(1)
            if not re.search(r"_(svc|service|lib|ctrl|manager)\b", attr):
                continue
            pos = m.start()
            if init_end is not None and pos < init_end:
                continue
            results.append({
                "file": rel,
                "category": "UNSAFE_HYBRID",
                "reason": f"Patched private attr {attr} (post-constructor)",
            })
    return results


def _find_init_end(text: str) -> int | None:
    lines = text.splitlines()
    depth = 0
    in_init = False
    for idx, line in enumerate(lines):
        if "def __init__" in line and "):" in line:
            in_init = True
            depth = 1
            continue
        if in_init:
            stripped = line.strip()
            if stripped.startswith("def "):
                in_init = False
                depth = 0
                continue
            depth += stripped.count("(") - stripped.count(")")
            if depth <= 0:
                in_init = False
                return sum(len(ln) + 1 for ln in lines[:idx + 1])
    return None


def _find_thread_unsafe_db() -> list[dict]:
    results: list[dict] = []
    for path in _find_bridge_files():
        rel = path.relative_to(REPO)
        text = path.read_text()
        if "threading" in text and ("conn.execute" in text or "conn.cursor" in text):
            results.append({
                "file": str(rel),
                "category": "UNSAFE_HYBRID",
                "reason": "Thread + DB access (may be unsafe)",
            })
    return results


def _find_access_sql_in_bridges() -> list[dict]:
    return _find_sql_in_bridges()


def run_audit() -> dict[str, Any]:
    results: dict[str, list[dict]] = {
        "REQUIRED_FALLBACK": [],
        "MIGRATION_PENDING": [],
        "UNSAFE_HYBRID": [],
        "DUPLICATED_LOGIC": [],
        "REMOVABLE": [],
    }
    results["REQUIRED_FALLBACK"].extend(_find_ui_imports())
    results["REQUIRED_FALLBACK"].extend(_find_qwidget_refs())
    results["MIGRATION_PENDING"].extend(_find_routes_without_tests())
    results["MIGRATION_PENDING"].extend(_find_pages_without_actions())
    results["UNSAFE_HYBRID"].extend(_find_sql_in_bridges())
    results["UNSAFE_HYBRID"].extend(_find_patched_private_attrs())
    results["UNSAFE_HYBRID"].extend(_find_thread_unsafe_db())
    results["UNSAFE_HYBRID"].extend(_find_access_sql_in_bridges())
    results["DUPLICATED_LOGIC"].extend(_find_duplicated_services())
    results["REMOVABLE"].extend(_find_bridges_without_services())
    results["REMOVABLE"].extend(_find_mock_actions())

    for cat in results:
        seen = set()
        unique = []
        for item in results[cat]:
            key = (item["file"], item.get("line", 0), item.get("reason", ""))
            if key not in seen:
                seen.add(key)
                unique.append(item)
        results[cat] = unique

    return results


def print_report(results: dict[str, list[dict]]):
    print("\n" + "=" * 70)
    print("QML HYBRID DEPENDENCY AUDIT REPORT")
    print("=" * 70)
    for cat in ("REQUIRED_FALLBACK", "UNSAFE_HYBRID", "DUPLICATED_LOGIC", "MIGRATION_PENDING", "REMOVABLE"):
        items = results.get(cat, [])
        print(f"\n{cat} ({len(items)} items):")
        if not items:
            print("  (none)")
        for item in items:
            file = item["file"]
            line = item.get("line", "")
            reason = item.get("reason", item.get("code", item.get("sql", "")))
            loc = f":{line}" if line else ""
            print(f"  - {file}{loc}  [{reason}]")
    counts = {cat: len(items) for cat, items in results.items()}
    total = sum(counts.values())
    print(f"\n{'=' * 70}")
    print(f"TOTAL: {total} issues across {len([c for c in counts.values() if c > 0])} categories")
    print(f"Counts: {json.dumps(counts)}")
    return counts


def main():
    results = run_audit()
    counts = print_report(results)
    reports_dir = REPO / "artifacts"
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / "hybrid_audit_results.json"
    with open(out_path, "w") as f:
        json.dump({"counts": counts, "results": results}, f, indent=2, ensure_ascii=False)
    print(f"\nFull results saved to {out_path}")
    has_blockers = (
        len(results.get("UNSAFE_HYBRID", [])) > 0
        or len(results.get("REMOVABLE", [])) > 0
    )
    if has_blockers:
        logger.warning("Audit found UNSAFE_HYBRID or REMOVABLE items requiring action.")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
