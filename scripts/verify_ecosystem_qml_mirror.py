#!/usr/bin/env python3
"""Verify that the Player's Ecosystem QML is an exact mirror of the package copy.

The Player tree at ``src/michi/presentation/qml/ecosystem`` is the canonical,
tested integration surface.  ``src/michi_ecosystem/qml/ecosystem`` is shipped
for standalone package compatibility.  They must never diverge silently.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

CANONICAL = Path("src/michi/presentation/qml/ecosystem")
MIRROR = Path("src/michi_ecosystem/qml/ecosystem")


def inventory(root: Path) -> dict[str, str]:
    """Return relative QML paths mapped to their SHA-256 digests."""
    if not root.is_dir():
        raise FileNotFoundError(f"QML directory does not exist: {root}")
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*.qml"))
        if path.is_file()
    }


def compare(canonical: Path, mirror: Path) -> list[str]:
    """Return human-readable differences between the two QML trees."""
    left = inventory(canonical)
    right = inventory(mirror)
    problems: list[str] = []
    for name in sorted(left.keys() - right.keys()):
        problems.append(f"missing from mirror: {name}")
    for name in sorted(right.keys() - left.keys()):
        problems.append(f"unexpected in mirror: {name}")
    for name in sorted(left.keys() & right.keys()):
        if left[name] != right[name]:
            problems.append(f"content differs: {name}")
    return problems


def synchronize(canonical: Path, mirror: Path) -> None:
    """Replace the mirror with the canonical QML files."""
    if mirror.exists():
        shutil.rmtree(mirror)
    shutil.copytree(canonical, mirror)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--sync",
        action="store_true",
        help="replace the package mirror with the canonical Player QML tree",
    )
    args = parser.parse_args(argv)
    canonical = args.repo.resolve() / CANONICAL
    mirror = args.repo.resolve() / MIRROR
    try:
        if args.sync:
            synchronize(canonical, mirror)
        problems = compare(canonical, mirror)
    except (OSError, FileNotFoundError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 2

    count = len(inventory(canonical))
    if args.json:
        print(
            json.dumps(
                {
                    "canonical": str(CANONICAL),
                    "mirror": str(MIRROR),
                    "files": count,
                    "problems": problems,
                    "status": "PASS" if not problems else "FAIL",
                },
                indent=2,
            )
        )
    elif problems:
        for problem in problems:
            print(f"[FAIL] {problem}", file=sys.stderr)
    else:
        print(f"[PASS] Ecosystem QML mirror is exact ({count} files)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
