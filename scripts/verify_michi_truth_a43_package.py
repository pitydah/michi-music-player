#!/usr/bin/env python3
"""A43/D19: read-only exact-checkout package verifier for AP2-F11.

The source checkout is NEVER edited. A private local clone is used to
reconstruct 'base HEAD + ONE cumulative patch + A41 naming migration'.
The comparison is content- and path-exact, not a misleading reverse-check
against pre-rename filenames. No commit, PR, push, remote or playback action.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import os
import re
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

EXPECTED_HEAD = "d32228fbcc49c4f107e4295b1a70e31fde4d9b07"
MIGRATOR = "scripts/migrate_michi_truth_names_a41.py"
FILE_LIMIT = 10_000
PATCH_LIMIT = 8_000_000
ALLOWED_ROOTS = frozenset(
    {"src", "tests", "scripts", "docs", ".github", "native", "tools"}
)


@dataclass(frozen=True)
class PackageResult:
    status: str
    issues: tuple[str, ...]
    checked_files: int = 0
    patch_sha256: str = ""


def _run(*argv: str, cwd: Path, timeout: int = 90) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv, cwd=cwd, capture_output=True, text=True, check=False, timeout=timeout
    )


def parse_patch(patch: Path) -> tuple[str, ...]:
    """Reject malformed/overlapping destinations before touching any worktree."""
    if not patch.is_file() or not 0 < patch.stat().st_size <= PATCH_LIMIT:
        raise ValueError("A43_PATCH_MISSING_OR_UNBOUNDED")
    text = patch.read_text(encoding="utf-8")
    if not text.startswith("diff --git a/") or "\x00" in text:
        raise ValueError("A43_PATCH_FORMAT_REFUSED")
    found = re.findall(r"^diff --git a/([^\n]+?) b/([^\n]+)$", text, re.M)
    if not found or len(found) < 29:
        raise ValueError("A43_PATCH_NOT_CUMULATIVE")
    dsts: list[str] = []
    for a, b in found:
        path = Path(b)
        if (
            a != b
            or path.is_absolute()
            or not path.parts
            or path.parts[0] not in ALLOWED_ROOTS
            or ".." in path.parts
            or str(path) != b
            or b.startswith(".git/")
        ):
            raise ValueError("A43_PATCH_PATH_REFUSED")
        dsts.append(b)
    if len(set(dsts)) != len(dsts):
        raise ValueError("A43_PATCH_OVERLAPPING_DIFFS")
    required = {
        MIGRATOR,
        "scripts/verify_michi_truth_product_integration.py",
        "src/michi/application/signal_truth_frame.py",
        "tests/audio_phase2/test_signal_truth_frame_a42.py",
    }
    if not required <= set(dsts):
        raise ValueError("A43_PATCH_MISSING_REQUIRED_CONTRACT")
    return tuple(dsts)


def _load_migrator(path: Path):
    spec = importlib.util.spec_from_file_location("michi_a43_naming_candidate", path)
    if spec is None or spec.loader is None:
        raise ValueError("A43_NAMING_LOADER_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _all_files(root: Path) -> dict[str, Path]:
    """Include untracked candidate files; ignore only known tool-generated caches."""
    result: dict[str, Path] = {}
    for base, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = [
            d
            for d in dirs
            if d
            not in {
                ".git",
                "__pycache__",
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
            }
        ]
        for name in names:
            path = Path(base) / name
            rel = path.relative_to(root).as_posix()
            if name.endswith((".pyc", ".pyo")):
                continue
            if not path.is_file() or path.is_symlink():
                raise ValueError("A43_NONREGULAR_FILE")
            result[rel] = path
            if len(result) > FILE_LIMIT:
                raise ValueError("A43_TOO_MANY_FILES")
    return result


def compare_tree(expected: Path, actual: Path) -> tuple[str, ...]:
    left, right = _all_files(expected), _all_files(actual)
    issues: list[str] = []
    for rel in sorted(left.keys() - right.keys()):
        issues.append(f"A43_MISSING:{rel}")
    for rel in sorted(right.keys() - left.keys()):
        issues.append(f"A43_UNEXPECTED:{rel}")
    for rel in sorted(left.keys() & right.keys()):
        left_file, right_file = left[rel], right[rel]
        if left_file.read_bytes() != right_file.read_bytes():
            issues.append(f"A43_CONTENT_DRIFT:{rel}")
        elif stat.S_IMODE(left_file.stat().st_mode) != stat.S_IMODE(
            right_file.stat().st_mode
        ):
            issues.append(f"A43_MODE_DRIFT:{rel}")
    return tuple(issues[:100])  # bounded receipt, no private content


def validate_package_contract(repo: Path) -> tuple[str, ...]:
    """Post-rename references, QML assets, Python import topology (static only)."""
    issues: list[str] = []
    required = (
        "src/michi/domain/truth_graph.py",
        "src/michi/application/signal_truth_projection_service.py",
        "src/michi/application/signal_truth_frame.py",
        "src/michi/presentation/signal_truth_bridge.py",
        "src/michi/presentation/qml/components/MichiSignalTruthView.qml",
        "src/michi/presentation/qml/player/SignalTruthPopup.qml",
        "tests/audio_phase2/test_signal_truth_projection_service.py",
        "tests/audio_phase2/test_f11_signal_truth_bridge.py",
        "scripts/verify_michi_truth_product_integration.py",
        "scripts/verify_michi_truth_a43_package.py",
        "scripts/verify_michi_truth_a44_handoff.py",
        "tests/audio_phase2/test_michi_truth_a44_handoff.py",
        "docs/audio/phase2/F11_SIGNAL_TRUTH_A44_HANDOFF.md",
        "tests/audio_phase2/test_signal_truth_dynamic_stages_a46.py",
        "tests/audio_phase2/test_michi_truth_r15c_matrix_a46.py",
        "docs/audio/phase2/F11_SIGNAL_TRUTH_A46_DYNAMIC_STAGE_CONTRACT.md",
        "docs/audio/phase2/F11_SIGNAL_TRUTH_A46_R15C_COVERAGE.json",
        "scripts/verify_michi_truth_p0_contract.py",
        "tests/audio_phase2/test_michi_truth_p0_contract_a47.py",
        "docs/audio/phase2/F11_SIGNAL_TRUTH_A47_P0_CANONICAL.md",
        "docs/audio/phase2/F11_SIGNAL_TRUTH_A47_P0_ACCEPTANCE.json",
    )
    for name in required:
        if not (repo / name).is_file():
            issues.append("A43_REQUIRED_PATH_MISSING:" + name)
    popup = repo / "src/michi/presentation/qml/player/SignalTruthPopup.qml"
    if popup.is_file():
        content = popup.read_text(encoding="utf-8")
        if (
            "signalTruthBridge.truthFrame" not in content
            or "canonicalTruthFrame.stages" not in content
        ):
            issues.append("A43_QML_TRUTH_FRAME_WIRING_MISSING")
    # A symbol in a QRC/qmldir/manifest may outlive the file rename. No
    # unapproved copy of the renderer is permitted.
    retired = re.compile("signal" + r"[\s_-]*" + "path", re.IGNORECASE)
    for name, path in _all_files(repo).items():
        if name.startswith("src/") and path.suffix == ".py":
            try:
                syntax = ast.parse(path.read_text(encoding="utf-8"), filename=name)
            except (SyntaxError, UnicodeError):
                issues.append("A43_PYTHON_SYNTAX_ERROR:" + name)
                continue
            for node in ast.walk(syntax):
                if (
                    isinstance(node, ast.ImportFrom)
                    and node.module
                    and node.module.startswith("michi.")
                ):
                    module = node.module
                    if (
                        module
                        in {
                            "michi.domain.truth_graph",
                            "michi.application.signal_truth_projection_service",
                            "michi.application.signal_truth_frame",
                            "michi.presentation.signal_truth_bridge",
                        }
                        and not (
                            repo / "src" / (module.replace(".", "/") + ".py")
                        ).is_file()
                    ):
                        issues.append("A43_PYTHON_MODULE_MISSING:" + name)
        if (
            path.suffix in {".qrc", ".qmldir", ".toml"}
            or path.name
            in {
                "MANIFEST.in",
                "setup.cfg",
                "setup.py",
            }
        ) and retired.search(path.read_text(encoding="utf-8", errors="replace")):
            issues.append("A43_PACKAGING_RETIRED_REFERENCE:" + name)
    return tuple(issues[:100])


def verify_migrated_package(
    repo: Path, patch: Path, *, expected_head: str = EXPECTED_HEAD
) -> PackageResult:
    """Compare migrated candidate to an independently rebuilt LOCAL mirror.

    Only valid with exact checked-out HEAD and sufficient source inventory.
    The real repo is opened READ-ONLY. The clone is private and throwaway.
    Requires an authorized migration performed separately by the operator.
    """
    repo, patch = repo.resolve(), patch.resolve()
    digest = hashlib.sha256(patch.read_bytes()).hexdigest() if patch.is_file() else ""
    try:
        parse_patch(patch)
        head = _run("git", "rev-parse", "HEAD", cwd=repo)
        if (
            head.returncode
            or head.stdout.strip() != expected_head
            or expected_head != EXPECTED_HEAD
        ):
            return PackageResult(
                "REFUSED", ("A43_HEAD_NOT_PINNED",), patch_sha256=digest
            )
        tracked = _run("git", "ls-files", "-z", cwd=repo)
        if (
            tracked.returncode
            or len([s for s in tracked.stdout.split("\x00") if s]) < 1000
        ):
            return PackageResult(
                "REFUSED", ("A43_NOT_FULL_CHECKOUT",), patch_sha256=digest
            )
        # Only the local HEAD is cloned. No network, no remote operations.
        with tempfile.TemporaryDirectory(prefix="michi_a43_mirror_") as directory:
            target = Path(directory) / "expected"
            clone = _run(
                "git",
                "clone",
                "--local",
                "--no-hardlinks",
                "--quiet",
                "--",
                str(repo),
                str(target),
                cwd=repo,
                timeout=120,
            )
            if clone.returncode:
                return PackageResult(
                    "REFUSED", ("A43_LOCAL_CLONE_FAILED",), patch_sha256=digest
                )
            checkout = _run(
                "git", "checkout", "--quiet", "--detach", expected_head, cwd=target
            )
            if checkout.returncode:
                return PackageResult(
                    "REFUSED", ("A43_LOCAL_HEAD_UNAVAILABLE",), patch_sha256=digest
                )
            pre = _run("git", "apply", "--check", str(patch), cwd=target)
            if pre.returncode:
                return PackageResult(
                    "REFUSED", ("A43_PATCH_PREIMAGE_FAILED",), patch_sha256=digest
                )
            applied = _run("git", "apply", str(patch), cwd=target)
            if applied.returncode:
                return PackageResult(
                    "REFUSED", ("A43_PATCH_APPLY_FAILED",), patch_sha256=digest
                )
            reverse = _run(
                "git", "apply", "--reverse", "--check", str(patch), cwd=target
            )
            if reverse.returncode:
                return PackageResult(
                    "REFUSED", ("A43_PATCH_NOT_REVERSIBLE",), patch_sha256=digest
                )
            mig = _load_migrator(target / MIGRATOR)
            transformations = mig.plan(target, expected_head=expected_head)
            if len([c for c in transformations if c.src != c.dst]) != 7:
                return PackageResult(
                    "REFUSED", ("A43_NAMING_MOVES_INCOMPLETE",), patch_sha256=digest
                )
            # Migration of the isolated mirror does NOT authorize relocation
            # of the canonical Bible in the user's working checkout.
            mig.apply(target, transformations)
            inv = tuple(mig.verify_worktree(target))
            if inv:
                return PackageResult(
                    "REFUSED", ("A43_MIRROR_NAMING_INVALID",), patch_sha256=digest
                )
            package_issues = validate_package_contract(target)
            if package_issues:
                return PackageResult("REFUSED", package_issues, patch_sha256=digest)
            differences = compare_tree(target, repo)
            if differences:
                return PackageResult(
                    "REFUSED", differences, len(_all_files(target)), digest
                )
            return PackageResult(
                "MATCHED_PENDING_PRODUCT_GATES", (), len(_all_files(target)), digest
            )
    except (
        OSError,
        ValueError,
        UnicodeError,
        subprocess.TimeoutExpired,
        ImportError,
        RuntimeError,
    ) as exc:
        # Never leak workspace paths/private data from exception messages.
        return PackageResult(
            "REFUSED", (f"A43_VERIFY_ERROR_{type(exc).__name__}",), patch_sha256=digest
        )


if __name__ == "__main__":
    raise SystemExit(
        "Run through verify_michi_truth_product_integration.py --verify-migrated"
    )
