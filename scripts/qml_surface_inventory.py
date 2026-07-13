#!/usr/bin/env python3
"""Surface inventory: bridges, routes, pages, models, context bindings."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
UI_QML = REPO / "ui_qml"
BRIDGE = REPO / "ui_qml_bridge"
MODELS = REPO / "ui_qml/models"

from ui_qml_bridge.context_bindings import QML_CONTEXT_BINDINGS  # noqa: E402
from ui_qml_bridge.route_registry import ROUTES  # noqa: E402


def _collect_pages() -> list[str]:
    pages = []
    for f in sorted((UI_QML / "pages").rglob("*.qml")):
        rel = f.relative_to(UI_QML)
        pages.append(str(rel))
    return pages


def _collect_models() -> list[str]:
    return sorted(f.name for f in MODELS.glob("*.py") if f.name != "__init__.py" and not f.name.startswith("test_"))


def _collect_bridges() -> list[str]:
    bridges = set()
    for f in BRIDGE.glob("*.py"):
        if f.name.startswith("_") or f.name == "test_" or f.name == "error_catalog.py":
            continue
        bridges.add(f.stem)
    return sorted(bridges)


def _collect_all_tests() -> list[str]:
    tests = set()
    for pyfile in sorted((REPO / "tests/qml").rglob("test_*.py")):
        content = pyfile.read_text()
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("def test_"):
                tests.add(line.split("(")[0].replace("def ", "").strip())
    return sorted(tests)


def main():
    inventory = {
        "context_bindings": {k: v for k, v in sorted(QML_CONTEXT_BINDINGS.items())},
        "routes": {k: {"title": v.get("title", ""), "source": v.get("source", ""),
                        "category": v.get("category", ""), "status": v.get("status", "")}
                    for k, v in sorted(ROUTES.items())},
        "pages": _collect_pages(),
        "models": _collect_models(),
        "bridges": _collect_bridges(),
        "tests": _collect_all_tests(),
    }

    out = REPO / "docs" / "qml_surface_inventory.json"
    out.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n")
    print(f"Surface inventory: {len(inventory['context_bindings'])} bindings, "
          f"{len(inventory['routes'])} routes, {len(inventory['pages'])} pages, "
          f"{len(inventory['models'])} models, {len(inventory['bridges'])} bridges, "
          f"{len(inventory['tests'])} tests")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
