#!/usr/bin/env python3
"""AP2-F11 ST-NAME-001: tracked-source inventory, non-mutating.

Default is an inventory suitable for an incomplete migration (exit 0 if the
inventory succeeded). --enforce becomes a blocking quality gate only AFTER the
canonical R11 naming amendment is approved and the atomic rename is prepared.
Never edits files, writes to Git, or examines undocumented private inputs.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

_PRODUCT_DIRS = frozenset({"src", "tests", "scripts", "native", "tools"})
_EXTRA_FILES = frozenset(
    {
        "pyproject.toml",
        "MANIFEST.in",
        "setup.py",
        "setup.cfg",
        ".github/workflows/ci.yml",
        ".github/workflows/release.yml",
    }
)
_TEXT_EXTS = frozenset(
    {
        ".py",
        ".pyi",
        ".qml",
        ".js",
        ".ts",
        ".rs",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".json",
        ".yaml",
        ".yml",
        ".qrc",
        ".toml",
        ".sh",
        ".fish",
        ".txt",
        ".in",
        ".qmldir",
    }
)
_RESTRICTED = re.compile("signal" + r"[\s_-]*" + "path", re.IGNORECASE)
_OLD_BIBLE = (
    "docs/audio/MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_" + "SIGNAL" + "_" + "PATH_MEGA_PLAN.md"
)
_MAX_BYTES = 2_000_000


def _source_scoped(path: Path) -> bool:
    return (bool(path.parts) and path.parts[0] in _PRODUCT_DIRS) or (
        path.as_posix() in _EXTRA_FILES
    )


def inspect_tracked(repo: Path) -> dict[str, object]:
    """Deterministic read-only inventory; no untracked files or symlink reads."""
    output = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "-z"],
        capture_output=True,
        check=True,
        timeout=30,
    ).stdout
    paths = sorted(
        Path(item.decode("utf-8", errors="strict"))
        for item in output.split(b"\0")
        if item
    )
    hits: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []
    for rel in paths:
        name = rel.as_posix()
        if name == _OLD_BIBLE:
            hits.append({"kind": "CANONICAL_DOCUMENT_RELOCATION", "path": name})
        if not _source_scoped(rel):
            continue
        if _RESTRICTED.search(name):
            hits.append({"kind": "PRODUCT_PATH", "path": name})
        if rel.suffix.lower() not in _TEXT_EXTS and name not in _EXTRA_FILES:
            continue
        target = repo / rel
        if not target.is_file() or target.is_symlink():
            errors.append({"kind": "MISSING_OR_SYMLINK", "path": name})
            continue
        if target.stat().st_size > _MAX_BYTES:
            errors.append({"kind": "OVERSIZE_TEXT_FILE", "path": name})
            continue
        try:
            rows = target.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            errors.append({"kind": "TEXT_READ_FAILED", "path": name})
            continue
        for number, row in enumerate(rows, start=1):
            if _RESTRICTED.search(row):
                hits.append({"kind": "PRODUCT_CONTENT", "path": name, "line": number})
    return {
        "schema": "michi.ap2.f11.naming_inventory.v1",
        "tracked_count": len(paths),
        "hits": hits,
        "errors": errors,
        "result": "ERROR" if errors else "MIGRATION_REQUIRED" if hits else "CLEAN",
        "mode": "READ_ONLY_INVENTORY",
        "binary_wheel_verified": False,
        "canonical_owner_approved": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument(
        "--enforce", action="store_true", help="fail if any old product name remains"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="optional inventory path outside repository",
    )
    args = parser.parse_args(argv)
    try:
        report = inspect_tracked(args.repo.resolve())
    except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
        report = {
            "schema": "michi.ap2.f11.naming_inventory.v1",
            "result": "ERROR",
            "error_kind": type(exc).__name__,
        }
    text = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output is None:
        sys.stdout.write(text)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    if report["result"] == "ERROR":
        return 2
    if args.enforce and report["result"] != "CLEAN":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
