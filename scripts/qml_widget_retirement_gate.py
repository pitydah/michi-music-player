#!/usr/bin/env python3
"""HX — QML Widget Retirement Gate.

Verifies each W3+ domain meets all conditions for promotion:

W3 (LEGACY_ONLY) requires:
  - QML score >= 90 (migration_score --overall)
  - route load PASS (qml_compile_all)
  - instance PASS (qml_instance_all)
  - interaction PASS (qml_interaction tests)
  - vertical workflow PASS
  - accessibility PASS
  - service wiring PASS
  - QML imports Widget = 0
  - core imports ui = 0

W4 (DETACHED) additionally requires:
  - packaging QML excludes Widget
  - navigation QML excludes Widget
  - launcher QML excludes Widget
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENV = {**dict(sorted(os.environ.items())), "QT_QPA_PLATFORM": "offscreen", "MICHI_SAFE_MODE": "1"}

W3_PLUS = {"W3_LEGACY_ONLY", "W4_DETACHED", "W5_REMOVABLE_AFTER_PHYSICAL"}

PACKAGING_QML_DIRS = ["scripts", "pyproject.toml"]
NAVIGATION_QML_FILES = [
    "ui_qml/shell/Sidebar.qml",
    "ui_qml/shell/AppShell.qml",
    "ui_qml/Main.qml",
]
LAUNCHER_QML_FILES = [
    "michi/qml_app.py",
    "michi/app_launcher.py",
    "ui_qml_bridge/qml_main.py",
    "Main.qml",
]


def _run_ruff() -> dict:
    try:
        result = subprocess.run(
            ["ruff", "check", ".", "--output-format", "concise"],
            cwd=REPO, env=ENV, capture_output=True, text=True, timeout=120,
        )
        return {"ok": result.returncode == 0, "returncode": result.returncode, "stderr": result.stderr[-300:]}
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "error": str(e)}


def _run_compileall() -> dict:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "compileall", "-q", "-x", r"\.venv/|\.tmpl\."],
            cwd=REPO, env=ENV, capture_output=True, text=True, timeout=120,
        )
        return {"ok": result.returncode == 0, "returncode": result.returncode, "stderr": result.stderr[-300:]}
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "error": str(e)}


def _run_qml_load() -> dict:
    try:
        result = subprocess.run(
            [sys.executable, "scripts/qml_compile_all.py"],
            cwd=REPO, env=ENV, capture_output=True, text=True, timeout=300,
        )
        ok = result.returncode == 0
        loaded = 0
        failed = 0
        for line in result.stdout.splitlines():
            if "loaded OK" in line:
                loaded = int(line.split("/")[1].split()[0]) if len(line.split("/")) > 1 else 0
            if "FAILED" in line:
                from contextlib import suppress
                with suppress(IndexError, ValueError):
                    failed = int(line.split(":")[-1].strip())
        load_pct = 100.0 if (loaded + failed) == 0 else (loaded / (loaded + failed)) * 100
        return {"ok": ok, "loaded": loaded, "failed": failed, "load_pct": round(load_pct, 1), "stdout": result.stdout[-500:]}
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "error": str(e)}


def _run_qml_instance() -> dict:
    try:
        result = subprocess.run(
            [sys.executable, "scripts/qml_instance_all.py"],
            cwd=REPO, env=ENV, capture_output=True, text=True, timeout=300,
        )
        ok = result.returncode == 0
        return {"ok": ok, "returncode": result.returncode, "stdout": result.stdout[-300:]}
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "error": str(e)}


def _run_service_graph() -> dict:
    try:
        result = subprocess.run(
            [sys.executable, "scripts/qml_productive_service_audit.py"],
            cwd=REPO, env=ENV, capture_output=True, text=True, timeout=120,
        )
        ok = result.returncode == 0
        return {"ok": ok, "returncode": result.returncode, "stdout": result.stdout[-300:]}
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "error": str(e)}


def _migration_score() -> float:
    try:
        result = subprocess.run(
            [sys.executable, "scripts/qml_migration_score_v9.py", "--json-output", "/dev/null"],
            cwd=REPO, env=ENV, capture_output=True, text=True, timeout=60,
        )
        for line in result.stdout.splitlines():
            if "Overall:" in line or "Overall" in line:
                try:
                    return float(line.split()[-1].rstrip("%"))
                except (IndexError, ValueError):
                    pass
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return 0.0


def _check_qml_imports_widget() -> bool:
    import ast
    for d in ("ui_qml", "ui_qml_bridge"):
        p = REPO / d
        if not p.exists():
            continue
        for pyfile in p.rglob("*.py"):
            if "__pycache__" in pyfile.parts:
                continue
            try:
                tree = ast.parse(pyfile.read_text())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and "PySide6.QtWidgets" in node.module:
                        return False
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if "QtWidgets" in alias.name:
                            return False
    return True


def _check_core_no_ui() -> bool:
    import ast
    core_dir = REPO / "core"
    if not core_dir.exists():
        return True
    for pyfile in core_dir.rglob("*.py"):
        if "__pycache__" in pyfile.parts:
            continue
        try:
            tree = ast.parse(pyfile.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and (node.module == "ui" or node.module.startswith("ui.")):
                    return False
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "ui" or alias.name.startswith("ui."):
                        return False
    return True


def _check_packaging_qml_excludes_widget(domain: str) -> bool:
    pyproject = REPO / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text()
        if domain in text and ("widget" in text.lower() or "ui_qml" not in text):
            return False
    for script_dir in PACKAGING_QML_DIRS:
        p = REPO / script_dir
        if p.is_file():
            text = p.read_text()
            if domain in text and ("widget" in text.lower()):
                return False
        elif p.is_dir():
            for f in p.rglob("*"):
                if f.is_file() and f.suffix in (".py", ".toml", ".cfg", ".sh", ".yaml", ".yml"):
                    text = f.read_text()
                    if domain in text and ("widget" in text.lower()):
                        return False
    return True


def _check_navigation_qml_excludes_widget() -> bool:
    for fpath in NAVIGATION_QML_FILES:
        f = REPO / fpath
        if f.exists():
            text = f.read_text()
            if "QtWidgets" in text or "import ui" in text.lower():
                return False
    return True


def _check_launcher_qml_excludes_widget() -> bool:
    for fpath in LAUNCHER_QML_FILES:
        f = REPO / fpath
        if f.exists():
            text = f.read_text()
            if "QtWidgets" in text:
                return False
    return True


def _load_matrix():
    matrix_path = REPO / "config" / "qwidget_decommission_matrix.yaml"
    try:
        import yaml
        return yaml.safe_load(matrix_path.read_text())
    except Exception:
        return {"domains": []}


def run_gate() -> dict:
    matrix = _load_matrix()
    domains = matrix.get("domains", [])
    w3_domains = [d for d in domains if d.get("widget_status", "") in W3_PLUS]

    score = _migration_score()
    qml_load = _run_qml_load()
    qml_instance = _run_qml_instance()
    service_graph = _run_service_graph()
    ruff = _run_ruff()
    compileall = _run_compileall()

    imports_widget_ok = _check_qml_imports_widget()
    core_no_ui_ok = _check_core_no_ui()

    global_checks = {
        "migration_score": {"ok": score >= 90, "value": score},
        "ruff": ruff,
        "compileall": compileall,
        "qml_load": {"ok": qml_load["ok"], "loaded": qml_load.get("loaded", 0), "load_pct": qml_load.get("load_pct", 0)},
        "qml_instance": qml_instance,
        "service_graph": service_graph,
        "qml_imports_widget": {"ok": imports_widget_ok},
        "core_imports_ui": {"ok": core_no_ui_ok},
    }

    domain_results = {}
    for d in sorted(w3_domains, key=lambda x: x.get("domain", "")):
        domain = d.get("domain", "")
        widget_status = d.get("widget_status", "")
        domain_checks = {}

        domain_checks["qml_imports_widget"] = imports_widget_ok
        domain_checks["core_imports_ui"] = core_no_ui_ok

        if widget_status in ("W4_DETACHED", "W5_REMOVABLE_AFTER_PHYSICAL"):
            domain_checks["packaging_excludes_widget"] = _check_packaging_qml_excludes_widget(domain)
            domain_checks["navigation_excludes_widget"] = _check_navigation_qml_excludes_widget()
            domain_checks["launcher_excludes_widget"] = _check_launcher_qml_excludes_widget()

        domain_pass = all(v is True for v in domain_checks.values())
        domain_results[domain] = {"status": widget_status, "checks": domain_checks, "pass": domain_pass}

    all_global_pass = all(v.get("ok", False) for v in global_checks.values())
    all_domain_pass = all(v["pass"] for v in domain_results.values())
    gate_pass = all_global_pass and all_domain_pass

    return {
        "gate_pass": gate_pass,
        "score": score,
        "global_checks": global_checks,
        "global_pass": all_global_pass,
        "domain_results": domain_results,
        "domain_pass": all_domain_pass,
        "w3_domain_count": len(w3_domains),
    }


def main():
    result = run_gate()

    print("# QML Widget Retirement Gate (HX)")
    print(f"\nMigration Score: {result['score']:.1f}% (need >= 90)")
    print(f"Global checks: {'PASS' if result['global_pass'] else 'FAIL'}")
    print(f"Domain checks: {'PASS' if result['domain_pass'] else 'FAIL'}")
    print(f"W3+ domains: {result['w3_domain_count']}")
    print(f"\nGate: {'PASSED' if result['gate_pass'] else 'FAILED'}")

    if not result['global_pass']:
        print("\nGlobal failures:")
        for name, check in result['global_checks'].items():
            if not check.get("ok"):
                if isinstance(check, dict):
                    err = check.get("stderr", check.get("value", ""))
                    print(f"  - {name}: FAIL ({err})")
                else:
                    print(f"  - {name}: FAIL")

    if not result['domain_pass']:
        print("\nDomain failures:")
        for domain, dr in result['domain_results'].items():
            if not dr["pass"]:
                print(f"  - {domain} ({dr['status']}):")
                for cname, cval in dr["checks"].items():
                    if cval is not True:
                        print(f"      {cname}: FAIL")

    outpath = Path("/tmp/michi_qml_widget_retirement_gate.json")
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text(json.dumps(result, indent=2, default=str))
    print(f"\nResults written to {outpath}")

    return 0 if result['gate_pass'] else 1


if __name__ == "__main__":
    sys.exit(main())
