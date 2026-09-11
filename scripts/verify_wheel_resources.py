from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZipFile

_RUNTIME_SUFFIXES = {".qml", ".svg", ".png", ".jpg", ".jpeg", ".webp"}
_RUNTIME_NAMES = {"qmldir"}
_EXCLUDED_SOURCE_DIRS = {"__pycache__", "dev"}


def _is_runtime_resource(path: Path) -> bool:
    return path.name in _RUNTIME_NAMES or path.suffix.lower() in _RUNTIME_SUFFIXES


def expected_runtime_resources(source_root: Path) -> set[str]:
    presentation_root = source_root / "src" / "michi" / "presentation"
    expected: set[str] = set()
    for path in presentation_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _EXCLUDED_SOURCE_DIRS for part in path.parts):
            continue
        if not _is_runtime_resource(path):
            continue
        member = str(path.relative_to(source_root / "src")).replace("\\", "/")
        expected.add(member)
    return expected


# POST-R4 P7: directorios de DESARROLLO prohibidos en el wheel (el
# runtime productivo jamás los importa). Si un día `dev` necesita viajar,
# la exclusión se revisa con evidencia de consumer productivo.
_FORBIDDEN_SOURCE_DIRS = {"dev"}


def wheel_runtime_resources(wheel: Path) -> set[str]:
    with ZipFile(wheel) as archive:
        return {
            name
            for name in archive.namelist()
            if name.startswith("michi/presentation/")
            and _is_runtime_resource(Path(name))
        }


def wheel_forbidden_resources(wheel: Path) -> list[str]:
    """Recursos de desarrollo que NO deben empaquetarse (dev ∩ wheel)."""
    with ZipFile(wheel) as archive:
        return sorted(
            name
            for name in archive.namelist()
            if name.startswith("michi/presentation/")
            and any(f"/{d}/" in f"/{name}" for d in _FORBIDDEN_SOURCE_DIRS)
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--source-root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    expected = expected_runtime_resources(args.source_root.resolve())
    actual = wheel_runtime_resources(args.wheel.resolve())
    missing = sorted(expected - actual)

    if missing:
        print("Missing productive runtime resources from wheel:")
        for item in missing:
            print(f"  {item}")
        return 1

    # POST-R4 P7: DIRECCIÓN 2 — recursos de desarrollo prohibidos fuera.
    forbidden = wheel_forbidden_resources(args.wheel.resolve())
    if forbidden:
        print("Forbidden development resources PRESENT in wheel:")
        for item in forbidden:
            print(f"  {item}")
        return 1

    print(
        "Runtime-resource wheel parity PASS: "
        f"{len(expected)} required resources present, "
        f"{len(forbidden)} forbidden dev resources"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
