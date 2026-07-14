#!/usr/bin/env python3
"""Audit bridges for productive composition violations."""
import ast
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BRIDGE_DIR = REPO / "ui_qml_bridge"

SQL_KEYWORDS = {"SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP"}
PRIVATE_ATTR_PATTERNS = {"._service", "._svc", "._lib", "._qe"}


def find_bridges_with_direct_db_conn():
    results = []
    for pyfile in sorted(BRIDGE_DIR.rglob("*.py")):
        if pyfile.name == "__init__.py":
            continue
        try:
            tree = ast.parse(pyfile.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute):
                continue
            if isinstance(node.value, ast.Name) and node.value.id == "db" and node.attr in ("conn", "connection"):
                results.append((pyfile.name, node.lineno))
            if isinstance(node.value, ast.Attribute) and isinstance(node.value.value, ast.Name):
                val = f"{node.value.value.id}.{node.value.attr}"
                if val in ("db.conn", "db.connection"):
                    results.append((pyfile.name, node.lineno))
    return results


def find_bridges_with_inline_sql():
    results = []
    for pyfile in sorted(BRIDGE_DIR.rglob("*.py")):
        if pyfile.name == "__init__.py":
            continue
        content = pyfile.read_text()
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                upper = node.value.strip().upper()
                for kw in SQL_KEYWORDS:
                    if upper.startswith(kw) and len(upper) > 10:
                        results.append((pyfile.name, node.lineno, node.value.strip()[:80]))
                        break
    return results


def find_post_construction_private_patching():
    results = []
    for pyfile in sorted(BRIDGE_DIR.rglob("*.py")):
        if pyfile.name == "__init__.py":
            continue
        content = pyfile.read_text()
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id != "self":
                    lhs = f"{target.value.id}.{target.attr}"
                    if not lhs.startswith("_"):
                        continue
                    for pat in PRIVATE_ATTR_PATTERNS:
                        if pat in f".{lhs}":
                            results.append((pyfile.name, node.lineno, lhs))
    return sorted(set(results))


def find_services_only_used_by_tests():
    service_files = []
    for pyfile in sorted((REPO / "core").rglob("*.py")):
        if pyfile.name == "__init__.py":
            continue
        if "_service" in pyfile.name or pyfile.name.startswith("service_"):
            service_files.append(pyfile)

    import_counts: dict[str, list[str]] = defaultdict(list)

    for pyfile in sorted(REPO.rglob("*.py")):
        if ".venv" in str(pyfile) or "__pycache__" in str(pyfile):
            continue
        try:
            tree = ast.parse(pyfile.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for sf in service_files:
                        mod = sf.stem
                        if mod in alias.name or alias.name in mod:
                            import_counts[mod].append(pyfile.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    for sf in service_files:
                        mod = sf.stem
                        if mod in node.module or alias.name == mod:
                            import_counts[mod].append(pyfile.name)

    test_only = []
    for sf in service_files:
        mod = sf.stem
        files = set(import_counts.get(mod, []))
        non_test = [f for f in files if not f.startswith("test_")]
        if not non_test and files:
            test_only.append((mod, sorted(files)))
        elif not files:
            test_only.append((mod, []))

    return test_only


def main() -> int:
    print("=" * 70)
    print("QML Productive Service Audit")
    print("=" * 70)

    direct_db = find_bridges_with_direct_db_conn()
    if direct_db:
        print(f"\nWarning: Bridges accessing db.conn directly ({len(direct_db)}):")
        for f, line in direct_db:
            print(f"  {f}:{line}")
    else:
        print("\nOK: No bridges access db.conn directly")

    inline_sql = find_bridges_with_inline_sql()
    if inline_sql:
        print(f"\nWarning: Bridges with inline SQL ({len(inline_sql)}):")
        for f, line, snippet in inline_sql[:10]:
            print(f"  {f}:{line} -> {snippet}")
        if len(inline_sql) > 10:
            print(f"  ... and {len(inline_sql) - 10} more")
    else:
        print("\nOK: No bridges with inline SQL")

    private_patches = find_post_construction_private_patching()
    if private_patches:
        print(f"\nWarning: Post-construction private attribute patching ({len(private_patches)}):")
        for f, line, lhs in private_patches:
            print(f"  {f}:{line} -> {lhs}")
    else:
        print("\nOK: No post-construction private attribute patching")

    test_only = find_services_only_used_by_tests()
    if test_only:
        print(f"\nServices only used by tests ({len(test_only)}):")
        for mod, files in test_only:
            print(f"  {mod}: {', '.join(files) if files else 'unused'}")
    else:
        print("\nOK: No services only used by tests")

    print("\nAudit complete.")
    return 0 if not (direct_db or inline_sql or private_patches) else 1


if __name__ == "__main__":
    sys.exit(main())
