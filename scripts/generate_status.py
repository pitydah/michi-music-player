#!/usr/bin/env python3
"""Generate project status files automatically from real measurements."""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], timeout: int = 30) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout, cwd=PROJECT_ROOT).stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "ERROR"


def count_files(pattern: str) -> int:
    return len(list(PROJECT_ROOT.rglob(pattern)))


def count_test_functions(path: str) -> int:
    result = run(["python", "-m", "pytest", "--collect-only", "-q", path, "--timeout=10"])
    for line in result.split("\n"):
        if "selected" in line:
            try:
                return int(line.split()[0])
            except (ValueError, IndexError):
                pass
    return 0


def main():
    status = {
        "generated_at": datetime.now().isoformat(),
        "sha": run(["git", "rev-parse", "--short", "HEAD"]),
        "branch": run(["git", "branch", "--show-current"]),
        "commits_since_baseline": run(["git", "rev-list", "--count", "HEAD"]),
        "files": {
            "python": count_files("*.py"),
            "qml": count_files("*.qml"),
            "test_files": count_files("tests/**/test_*.py"),
        },
        "tests": {
            "core": count_test_functions("tests/"),
            "qml": count_test_functions("tests/qml/"),
        },
        "actions": {},
        "services": {},
    }

    # Count registered actions
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from ui_qml_bridge.action_registry import ActionRegistry
        ar = ActionRegistry()
        status["actions"]["total"] = len(ar._actions)
        status["actions"]["unique_ids"] = len(set(a.id for a in ar._actions.values() if hasattr(a, 'id')))
    except Exception as e:
        status["actions"]["error"] = str(e)

    # Count services from container
    try:
        import pkgutil
        service_count = 0
        for _importer, name, _ispkg in pkgutil.iter_modules([str(PROJECT_ROOT / "core")]):
            if 'service' in name.lower() and not name.startswith('_'):
                service_count += 1
        status["services"]["core_service_modules"] = service_count
    except Exception as e:
        status["services"]["error"] = str(e)

    # Write files
    artifacts_dir = PROJECT_ROOT / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # JSON
    json_path = artifacts_dir / "project-status.json"
    json_path.write_text(json.dumps(status, indent=2))
    print(f"Status JSON written: {json_path}")

    # Markdown
    md = f"""# Project Status (Auto-generated)

**Generated:** {status['generated_at']}
**SHA:** {status['sha']}
**Branch:** {status['branch']}

## Files
- Python files: {status['files']['python']}
- QML files: {status['files']['qml']}
- Test files: {status['files']['test_files']}

## Tests
- Core tests: {status['tests']['core']}
- QML tests: {status['tests']['qml']}

## Actions
- Total: {status.get('actions', {}).get('total', 'N/A')}

## Services
- Core modules: {status.get('services', {}).get('core_service_modules', 'N/A')}
"""
    md_path = PROJECT_ROOT / "STATUS.generated.md"
    md_path.write_text(md)
    print(f"Status MD written: {md_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
