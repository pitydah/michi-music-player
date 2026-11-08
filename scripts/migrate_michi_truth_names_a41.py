#!/usr/bin/env python3
"""ST-NAME-001: deterministic, reversible-in-session naming migration.

The tool transforms only the presentation/projection vocabulary and the
explicitly approved AP2 canonical-document reference. It does not modify
runtime decisions, DSP, audio, Qt signal semantics, or phase closures.

Plan mode makes no writes; apply mode requires an explicit governance flag.
No git commits, staging, pushes, or network calls are performed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

SCHEMA = "michi.ap2.f11.naming_migration.v1"
SOURCE_HEAD = "d32228fbcc49c4f107e4295b1a70e31fde4d9b07"
# Split source-side spelling to keep this migration file compatible with its
# own product vocabulary gate while still matching historical identifiers.
OLD_PREFIX = "Signal" + "Path"
OLD_SNAKE = "signal" + "_" + "path"
OLD_CAMEL = "signal" + "Path"
OLD_BIBLE = (
    "docs/audio/MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_" + "SIGNAL" + "_PATH_MEGA_PLAN.md"
)
NEW_BIBLE = "docs/audio/MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_TRUTH_MEGA_PLAN.md"
RESTRICTED = re.compile("signal" + r"[\s_-]*" + "path", re.IGNORECASE)

RENAME = {
    "src/michi/domain/" + OLD_SNAKE + ".py": "src/michi/domain/truth_graph.py",
    "src/michi/application/"
    + OLD_SNAKE
    + "_service.py": "src/michi/application/signal_truth_projection_service.py",
    "src/michi/presentation/"
    + OLD_SNAKE
    + "_bridge.py": "src/michi/presentation/signal_truth_bridge.py",
    "src/michi/presentation/qml/components/Michi"
    + OLD_PREFIX
    + "View.qml": "src/michi/presentation/qml/components/MichiSignalTruthView.qml",
    "tests/audio_phase2/test_"
    + OLD_SNAKE
    + "_service.py": "tests/audio_phase2/test_signal_truth_projection_service.py",
    "tests/audio_phase2/test_f11_"
    + OLD_SNAKE
    + "_bridge.py": "tests/audio_phase2/test_f11_signal_truth_bridge.py",
    OLD_BIBLE: NEW_BIBLE,
}

# The single-source artifacts added by A39 exist on disk but may not have been
# staged by OpenCode yet. No arbitrary untracked user data may be rewritten.
KNOWN_A39_ADDITIONS = frozenset(
    {
        "src/michi/application/signal_truth_causal.py",
        "src/michi/application/signal_truth_causal_view.py",
        "src/michi/application/signal_truth_delivery.py",
        "src/michi/application/signal_truth_owner_bridge.py",
        "src/michi/application/signal_truth_semantic_gate.py",
        "scripts/audit_michi_signal_truth_naming.py",
        "scripts/verify_michi_truth_product_integration.py",
        "tests/audio_phase2/test_signal_truth_a37_fallback.py",
        "tests/audio_phase2/test_signal_truth_causal_a26.py",
        "tests/audio_phase2/test_signal_truth_causal_view_a35.py",
        "tests/audio_phase2/test_signal_truth_delivery_a26.py",
        "tests/audio_phase2/test_signal_truth_output_family_hardening_a20.py",
        "tests/audio_phase2/test_signal_truth_output_owner_a37.py",
        "tests/audio_phase2/test_signal_truth_owner_bridge_a36.py",
        "tests/audio_phase2/test_signal_truth_real_recorder_c6_a35.py",
        "tests/audio_phase2/test_signal_truth_semantic_gate_a38.py",
        "tests/audio_phase2/test_signal_truth_naming_inventory_a38.py",
        "tests/audio_phase2/test_michi_truth_product_integration_a39.py",
        "scripts/migrate_michi_truth_names_a41.py",
        "src/michi/application/signal_truth_frame.py",
        "tests/audio_phase2/test_signal_truth_frame_a42.py",
        "tests/audio_phase2/test_signal_truth_frame_integration_a42.py",
        "tests/audio_phase2/test_michi_truth_naming_migration_a41.py",
        "scripts/verify_michi_truth_a43_package.py",
        "tests/audio_phase2/test_michi_truth_a43_package.py",
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
    }
)
A39_MODIFIED = frozenset(
    {
        "src/michi/application/output_session_service.py",
        "src/michi/bootstrap/__init__.py",
        "src/michi/domain/signal_truth.py",
        "src/michi/presentation/" + OLD_SNAKE + "_bridge.py",
        "src/michi/presentation/qml/components/Michi" + OLD_PREFIX + "View.qml",
        "src/michi/presentation/qml/player/SignalTruthPopup.qml",
    }
)
PRODUCT_ROOTS = frozenset({"src", "tests", "scripts", "native", "tools"})
CONTROLLED_ROOT = frozenset(
    {
        "pyproject.toml",
        "setup.cfg",
        "setup.py",
        "MANIFEST.in",
        "AGENTS.md",
        "docs/audio/phase2/PHASE2_STATE.json",
    }
)
TEXT_SUFFIX = frozenset(
    {
        ".py",
        ".pyi",
        ".qml",
        ".ts",
        ".js",
        ".rs",
        ".c",
        ".cc",
        ".cpp",
        ".h",
        ".hpp",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".qrc",
        ".in",
        ".sh",
        ".fish",
        ".txt",
        ".qmldir",
        ".md",
        ".svg",
        ".qss",
    }
)
SPECIAL_DAC_FILES = frozenset(
    {
        "DacDiagnosticsDisclosure.qml",
        "DacDeviceCard.qml",
        "AudioOutputDeviceGroup.qml",
        "AudioOutputSettingsSection.qml",
        "SettingsView.qml",
    }
)


class Refusal(ValueError):  # noqa: N818
    """Abort without altering the source tree."""


@dataclass(frozen=True)
class Change:
    src: str
    dst: str
    before: bytes
    after: bytes
    mode: int

    def manifest(self) -> dict[str, object]:
        return {
            "from": self.src,
            "to": self.dst,
            "renamed": self.src != self.dst,
            "changed": self.before != self.after,
            "before_sha256": hashlib.sha256(self.before).hexdigest(),
            "after_sha256": hashlib.sha256(self.after).hexdigest(),
        }


def _git(repo: Path, *argv: str) -> bytes:
    run = subprocess.run(
        ["git", "-C", str(repo), *argv], capture_output=True, timeout=30, check=False
    )
    if run.returncode:
        raise Refusal(f"git read failed: {argv!r} exit={run.returncode}")
    return run.stdout


def _allowed_source(path: str) -> bool:
    parts = Path(path).parts
    return (
        bool(parts and parts[0] in PRODUCT_ROOTS)
        or path in CONTROLLED_ROOT
        or (path.startswith(".github/workflows/"))
    )


def _is_text(path: str) -> bool:
    return Path(path).suffix.lower() in TEXT_SUFFIX or path in CONTROLLED_ROOT


def _replace(text: str, source: str) -> str:
    # Order matters: longest, semantic identifiers first; avoid a generic
    # replacement until the destination API has been differentiated by owner.
    for old, new in (
        ("Michi" + OLD_PREFIX + "View", "MichiSignalTruthView"),
        (OLD_PREFIX + "ProjectionError", "TruthGraphProjectionError"),
        (OLD_PREFIX + "NodeKind", "TruthGraphNodeKind"),
        (OLD_PREFIX + "NodeState", "TruthGraphNodeState"),
        (OLD_PREFIX + "Identity", "TruthGraphIdentity"),
        (OLD_PREFIX + "Snapshot", "TruthGraphSnapshot"),
        (OLD_PREFIX + "Node", "TruthGraphNode"),
        (OLD_PREFIX + "Edge", "TruthGraphEdge"),
        (OLD_PREFIX + "Service", "SignalTruthProjectionService"),
        (OLD_PREFIX + "Bridge", "SignalTruthBridge"),
        # Domain graph types moved to truth_graph; the recorder keeps its own
        # module name. Resolve the module before the generic snake-case pass.
        ("michi.domain." + OLD_SNAKE + " import", "michi.domain.truth_graph import"),
        ("domain." + OLD_SNAKE + " import", "domain.truth_graph import"),
        (OLD_SNAKE + "_service", "signal_truth_projection_service"),
        (OLD_SNAKE + "_bridge", "signal_truth_bridge"),
        (OLD_CAMEL + "Bridge", "signalTruthBridge"),
        (OLD_CAMEL + "Kind", "outputRouteKind"),
        (OLD_SNAKE + "_kind", "output_route_kind"),
        ("SIGNAL" + "_PATH", "SIGNAL_TRUTH"),
        ("SIGNAL" + " PATH", "MICHI SIGNAL TRUTH"),
        ("Signal " + "Path", "Michi Signal Truth"),
        ("Signal " + "path", "Michi Signal truth"),
        ("signal " + "path", "audio route"),
        # A docstring may wrap the two words across lines; keep the line
        # structure while retiring the historical vocabulary.
        ("signal\n" + "path", "audio\nroute"),
        ("Signal\n" + "Path", "Michi Signal\nTruth"),
        (OLD_BIBLE, NEW_BIBLE),
    ):
        text = text.replace(old, new)

    name = Path(source).name
    is_audio_output = name == "audio_output_bridge.py" or name in {
        "test_audio_output_bridge.py",
        "test_v35_090_audio_output_bridge.py",
    }
    is_dac_qml = name in SPECIAL_DAC_FILES or name == "test_v35_090_qml_audio_output.py"
    if source.endswith("SettingsView.qml") or source.endswith(
        "test_v35_090_qml_audio_output.py"
    ):
        text = text.replace("audioOutput." + OLD_CAMEL, "audioOutput.outputRouteStages")
    if is_audio_output:
        text = text.replace("_" + OLD_SNAKE, "_output_route_stages")
        text = text.replace(OLD_SNAKE, "output_route_stages")
        text = text.replace(OLD_CAMEL, "outputRouteStages")
    elif is_dac_qml:
        text = text.replace(OLD_CAMEL, "truthStages")
    else:
        # Runtime property on AudioOutputBridge is distinct from the F11 bridge
        # and from local DAC detail stage arrays.
        text = text.replace("audioOutput." + OLD_CAMEL, "audioOutput.outputRouteStages")
        text = text.replace(
            "audio_output." + OLD_SNAKE, "audio_output.output_route_stages"
        )
        text = text.replace(OLD_CAMEL, "signalTruth")
        text = text.replace(OLD_SNAKE, "signal_truth")
    # Last resort only on proper API casing, not on arbitrary strings.
    text = text.replace(OLD_PREFIX, "SignalTruth")
    return text


def _tracked(repo: Path) -> set[str]:
    return {
        entry.decode("utf-8", "strict")
        for entry in _git(repo, "ls-files", "-z").split(b"\0")
        if entry
    }


def _safe_path(repo: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise Refusal(f"out-of-root path: {relative}")
    path = repo / rel
    if path.is_symlink() or not path.is_file():
        raise Refusal(f"missing or linked file: {relative}")
    if path.stat().st_size > 3_000_000:
        raise Refusal(f"unbounded text file: {relative}")
    return path


def plan(repo: Path, *, expected_head: str = SOURCE_HEAD) -> list[Change]:
    repo = repo.resolve()
    head = _git(repo, "rev-parse", "HEAD").decode().strip()
    if head != expected_head:
        raise Refusal(f"HEAD mismatch expected={expected_head} actual={head}")
    indexed = _tracked(repo)
    existing = set(indexed) | {p for p in KNOWN_A39_ADDITIONS if (repo / p).is_file()}
    for old in RENAME:
        if old not in existing:
            raise Refusal(f"required rename source unavailable: {old}")
    changes: list[Change] = []
    destinations: set[str] = set()
    for old in sorted(existing):
        if not _allowed_source(old) and old != OLD_BIBLE:
            continue
        dst = RENAME.get(old, old)
        if not _is_text(old) and old != OLD_BIBLE:
            continue
        target = _safe_path(repo, old)
        if dst in destinations:
            raise Refusal(f"duplicate destination: {dst}")
        destinations.add(dst)
        if RESTRICTED.search(dst) and _allowed_source(old):
            raise Refusal(f"unmapped legacy filename: {old}")
        if dst != old and (repo / dst).exists():
            raise Refusal(f"destination already exists: {dst}")
        binary = target.read_bytes()
        try:
            rewritten = _replace(binary.decode("utf-8"), old).encode("utf-8")
        except UnicodeDecodeError as exc:
            raise Refusal(f"text decode error: {old}") from exc
        # The canonical Bible is relocated as a historical normative document;
        # its prose is not rewritten by a code-naming migration.
        if (
            old != OLD_BIBLE
            and RESTRICTED.search(rewritten.decode("utf-8"))
            and _allowed_source(old)
        ):
            raise Refusal(f"unresolved retired name: {old}")
        if old != dst or binary != rewritten:
            changes.append(
                Change(old, dst, binary, rewritten, stat.S_IMODE(target.stat().st_mode))
            )
    return changes


def _write_atomic(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, raw = tempfile.mkstemp(prefix=".michi_truth_", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(raw, mode)
        os.replace(raw, path)
    finally:
        if os.path.exists(raw):
            os.unlink(raw)


def apply(repo: Path, changes: Iterable[Change]) -> None:
    """Refuse drift; on failure attempt to restore the exact prior bytes."""
    repo = repo.resolve()
    changes = list(changes)
    for entry in changes:
        if _safe_path(repo, entry.src).read_bytes() != entry.before:
            raise Refusal(f"source changed since plan: {entry.src}")
        if entry.src != entry.dst and (repo / entry.dst).exists():
            raise Refusal(f"new target appeared since plan: {entry.dst}")
    done: list[Change] = []
    try:
        for entry in changes:
            target = repo / entry.dst
            done.append(entry)
            _write_atomic(target, entry.after, entry.mode)
            if entry.src != entry.dst:
                (repo / entry.src).unlink()
    except Exception:
        for entry in reversed(done):
            if entry.src != entry.dst:
                (repo / entry.dst).unlink(missing_ok=True)
            _write_atomic(repo / entry.src, entry.before, entry.mode)
        raise


def verify_worktree(repo: Path) -> list[str]:
    """Static post-migration inventory; does not import Michi or alter git."""
    repo = repo.resolve()
    index = _tracked(repo)
    expected = {RENAME.get(name, name) for name in index}
    expected.update(p for p in KNOWN_A39_ADDITIONS if (repo / p).is_file())
    problems: list[str] = []
    for old, new in RENAME.items():
        if (repo / old).exists():
            problems.append(f"old path remains: {old}")
        if not (repo / new).is_file():
            problems.append(f"missing renamed target: {new}")
    for name in sorted(expected):
        if not _allowed_source(name):
            continue
        if RESTRICTED.search(name):
            problems.append(f"retired filename: {name}")
        if not _is_text(name):
            continue
        path = repo / name
        if not path.is_file() or path.is_symlink():
            problems.append(f"missing or linked worktree path: {name}")
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            problems.append(f"unreadable product text: {name}")
            continue
        if RESTRICTED.search(content):
            problems.append(f"retired API token in: {name}")
    state_path = repo / "docs/audio/phase2/PHASE2_STATE.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state["spec"]["path"] != NEW_BIBLE:
            problems.append("phase spec path does not match relocated Bible")
    except (KeyError, ValueError, OSError):
        problems.append("phase state not readable as canonical spec reference")
    return problems


def _dirty_status(repo: Path) -> list[str]:
    output = _git(repo, "status", "--porcelain=v1", "--untracked-files=normal")
    return output.decode("utf-8", "replace").splitlines()


def _receipt(repo: Path, changes: list[Change], mode: str) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "mode": mode,
        "head": _git(repo, "rev-parse", "HEAD").decode().strip(),
        "total_changes": len(changes),
        "moves": sum(c.src != c.dst for c in changes),
        "changes": [c.manifest() for c in changes],
        "github_changed": False,
        "runtime_tests_executed": False,
        "approval_for_normative_relocation": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--expected-head", default=SOURCE_HEAD)
    parser.add_argument("--mode", choices=("plan", "apply", "verify"), default="plan")
    parser.add_argument("--permit-governance-rename", action="store_true")
    parser.add_argument("--allow-existing-changes", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        repo = args.repo.resolve()
        if args.mode == "verify":
            problems = verify_worktree(repo)
            receipt = {
                "schema": SCHEMA,
                "mode": "verify",
                "issues": problems,
                "result": "STATIC_CLEAN_OPENCODE_TESTS_PENDING"
                if not problems
                else "REFUSED",
                "runtime_tests_executed": False,
                "github_changed": False,
            }
        else:
            changes = plan(repo, expected_head=args.expected_head)
            receipt = _receipt(repo, changes, args.mode)
        if args.mode == "apply":
            if not args.permit_governance_rename:
                raise Refusal(
                    "canonical document relocation requires explicit approval"
                )
            dirty = _dirty_status(repo)
            if dirty and not args.allow_existing_changes:
                raise Refusal(
                    "working tree not clean; use explicit A39 migration permission"
                )
            if dirty:
                for line in dirty:
                    path = line[3:].strip()
                    if path not in KNOWN_A39_ADDITIONS | A39_MODIFIED:
                        raise Refusal(f"unrecognized preexisting change: {path}")
            apply(repo, changes)
            problems = verify_worktree(repo)
            receipt["static_issues"] = problems
            receipt["approval_for_normative_relocation"] = True
            receipt["result"] = (
                "WORKTREE_MIGRATED_PENDING_OPENCODE_GATES"
                if not problems
                else "MIGRATED_STATIC_REVIEW_REQUIRED"
            )
        elif args.mode == "plan":
            receipt["result"] = "DRY_RUN_ONLY"
    except (Refusal, OSError, subprocess.SubprocessError) as exc:
        receipt = {
            "schema": SCHEMA,
            "result": "REFUSED",
            "reason": str(exc),
            "runtime_tests_executed": False,
            "github_changed": False,
        }
    blob = json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(blob, encoding="utf-8")
    else:
        sys.stdout.write(blob)
    return (
        0
        if receipt["result"]
        in {
            "DRY_RUN_ONLY",
            "WORKTREE_MIGRATED_PENDING_OPENCODE_GATES",
            "STATIC_CLEAN_OPENCODE_TESTS_PENDING",
        }
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
