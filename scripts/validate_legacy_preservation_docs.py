#!/usr/bin/env python3
"""Validate legacy preservation documentation.

Reads legacy_functional_inventory.yaml and checks:
- YAML syntax
- All mentioned paths exist
- No legacy files are missing from inventory
- No functions documented without files
- All QML/bridge/core paths mentioned exist
"""
import os
import sys
import yaml

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INVENTORY_PATH = os.path.join(BASE, "docs", "migration", "legacy_functional_inventory.yaml")

errors = []

def main():
    if not os.path.isfile(INVENTORY_PATH):
        print(f"ERROR: Inventory not found at {INVENTORY_PATH}")
        sys.exit(1)

    with open(INVENTORY_PATH) as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"ERROR: Invalid YAML: {e}")
            sys.exit(1)

    if data is None:
        print("ERROR: Empty YAML file")
        sys.exit(1)

    print(f"✅ YAML parsed successfully. Schema version: {data.get('schema_version', 'unknown')}")

    # Validate file paths
    if "files" in data:
        for entry in data["files"]:
            path = entry.get("path", "")
            full = os.path.join(BASE, path)
            if not os.path.exists(full):
                errors.append(f"FILE_NOT_FOUND: {path}")

    # Validate QML/bridge/core paths in functions
    if "functions" in data:
        for fn in data["functions"]:
            repl = fn.get("replacement", {})
            for key in ("qml_files", "bridges", "core_services"):
                for path in repl.get(key, []):
                    full = os.path.join(BASE, path)
                    if not os.path.exists(full):
                        errors.append(f"REF_FILE_NOT_FOUND [{fn['id']}].{key}: {path}")

    # Find legacy files not in inventory
    legacy_dir = os.path.join(BASE, "legacy_widgets")
    inventoried = set()
    for entry in data.get("files", []):
        p = entry.get("path", "")
        if p.startswith("legacy_widgets/"):
            inventoried.add(p)

    if os.path.isdir(legacy_dir):
        for root, _dirs, files in os.walk(legacy_dir):
            for f in files:
                if not f.endswith(".py"):
                    continue
                rel = os.path.relpath(os.path.join(root, f), BASE)
                if rel not in inventoried:
                    errors.append(f"MISSING_FROM_INVENTORY: {rel}")

    # Check for functions without file references
    for fn in data.get("functions", []):
        legacy = fn.get("legacy", {})
        if not legacy.get("files") and not legacy.get("entry_points"):
            errors.append(f"FUNCTION_NO_FILES: {fn['id']} ({fn.get('name', 'unknown')}) has no legacy files")

    if errors:
        print(f"\n❌ {len(errors)} validation errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print(f"✅ All {len(data.get('files', []))} file paths validated")
    print(f"✅ All {len(data.get('functions', []))} function references validated")
    print("✅ No legacy files missing from inventory")
    print("✅ LEGACY PRESERVATION DOCS VALIDATED SUCCESSFULLY")

if __name__ == "__main__":
    main()
