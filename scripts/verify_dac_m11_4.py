#!/usr/bin/env python3
"""Aggregate the automated M11.4/DAC-V35 software closure gates.

This command produces evidence, not physical qualification. A GO verdict means
only that the repository's automated software contract passed at one commit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
SPEC_REVISION = "V3.5"

REQUIRED_COLLECTED_MODULES = (
    "tests/dac/test_v35_100_software_closure.py",
    "tests/dac/test_v35_100r1_startup_resume.py",
    "tests/dac/test_v35_100r11_source_characterization.py",
    "tests/dac/test_v35_100r12_native_lifecycle.py",
    "tests/dac/test_v35_100r12_playback_refusal_ui.py",
    "tests/dac/test_v35_100r12_productive_qualification.py",
    "tests/dac/test_v35_010r1_universal_audio_discovery.py",
    "tests/test_v35_090_audio_output_bridge.py",
    "tests/test_v35_090_qml_audio_output.py",
)

MANDATORY_SKIP_PREFIXES = (
    "tests/dac/",
    "tests/test_v35_090_audio_output_bridge.py",
    "tests/test_v35_090_qml_audio_output.py",
    "tests/test_gstreamer_audio_port.py",
)

DAC_QML_SURFACES = (
    "src/michi/presentation/qml/views/AudioOutputSettingsSection.qml",
    "src/michi/presentation/qml/player/AudioOutputPopup.qml",
    "src/michi/presentation/qml/components/DacDeviceCard.qml",
    "src/michi/presentation/qml/components/DacDiagnosticsDisclosure.qml",
    "src/michi/presentation/qml/components/SignalTruthPanel.qml",
    "src/michi/presentation/qml/player/NowPlayingBar.qml",
)


@dataclass(frozen=True, slots=True)
class Gate:
    gate_id: str
    description: str
    command: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GateResult:
    gate_id: str
    description: str
    command: tuple[str, ...]
    status: str
    returncode: int | None
    duration_seconds: float
    log: str | None
    detail: str


TEST_GATES = (
    Gate(
        "repository-alignment",
        "Repository baseline and authority assumptions",
        (sys.executable, "scripts/verify_dac_repository_alignment.py"),
    ),
    Gate(
        "ruff-check",
        "Ruff static analysis",
        ("ruff", "check", "src", "tests", "scripts"),
    ),
    Gate(
        "ruff-format",
        "Ruff formatting",
        ("ruff", "format", "--check", "src", "tests", "scripts"),
    ),
    Gate(
        "dac-qml-lint",
        "Critical DAC QML syntax and type lint",
        (
            "pyside6-qmllint",
            "-I",
            "src/michi/presentation/qml",
            *DAC_QML_SURFACES,
        ),
    ),
    Gate(
        "required-test-collection",
        "Collect the complete suite and prove mandatory modules are visible",
        (sys.executable, "-m", "pytest", "tests", "--collect-only", "-q"),
    ),
    Gate(
        "dac-domain-runtime",
        "DAC domain, planning, execution, lifecycle, and Signal Truth",
        (sys.executable, "-m", "pytest", "tests/dac", "-q"),
    ),
    Gate(
        "engine-audioport-regressions",
        "AudioPort, GStreamer, router, and M11.3 regressions",
        (
            sys.executable,
            "-m",
            "pytest",
            "tests/test_gstreamer_audio_port.py",
            "tests/test_audio_engine_conformance.py",
            "tests/test_audio_engine_providers.py",
            "tests/test_audio_engine_registry.py",
            "tests/test_audio_ownership_gates.py",
            "tests/test_audio_transport_router.py",
            "tests/test_m11_3b_qt_runtime_composition.py",
            "tests/test_m11_3e_runtime_availability.py",
            "tests/test_m11_3f_engine_selection.py",
            "tests/test_m11_3g_engine_convergence.py",
            "-q",
        ),
    ),
    Gate(
        "playback-regressions",
        "PlaybackService and PlaybackSessionService regressions",
        (
            sys.executable,
            "-m",
            "pytest",
            "tests/test_playback_service.py",
            "tests/test_playback_session_service.py",
            "tests/test_playback_p0_convergence.py",
            "tests/test_queue_session_restore.py",
            "-q",
        ),
    ),
    Gate(
        "persistence-provenance",
        "Persistence migration, recovery, health, and provenance",
        (
            sys.executable,
            "-m",
            "pytest",
            "tests/test_schema_migration.py",
            "tests/test_persistence_startup.py",
            "tests/test_persistence_health.py",
            "tests/test_persistence_recovery.py",
            "tests/test_persistence_recovery_install.py",
            "tests/test_persistence_authoritative_decode.py",
            "-q",
        ),
    ),
    Gate(
        "dac-qml-runtime",
        "Audio output QML structure and offscreen runtime",
        (
            sys.executable,
            "-m",
            "pytest",
            "tests/test_v35_060_qml_volume.py",
            "tests/test_v35_090_audio_output_bridge.py",
            "tests/test_v35_090_qml_audio_output.py",
            "-q",
        ),
    ),
    Gate(
        "full-regression-suite",
        "Complete repository regression suite",
        (sys.executable, "-m", "pytest", "tests", "-q", "-rsxX"),
    ),
)

REQUIRED_DAC_WHEEL_MEMBERS = frozenset(
    {
        "michi/presentation/audio_output_bridge.py",
        "michi/presentation/qml/player/AudioOutputPopup.qml",
        "michi/presentation/qml/views/AudioOutputSettingsSection.qml",
        "michi/application/audio_device_registry.py",
        "michi/application/audio_device_semantics.py",
        "michi/presentation/qml/components/AudioOutputDeviceGroup.qml",
        "michi/application/audio_output_planner.py",
        "michi/application/audio_output_profile_service.py",
        "michi/application/audio_output_selection_coordinator.py",
        "michi/application/direct_output_lifecycle_coordinator.py",
        "michi/application/output_session_service.py",
        "michi/application/volume_policy_service.py",
        "michi/domain/signal_truth.py",
        "michi/infrastructure/audio_output/direct_output_executor.py",
    }
)

INSTALLED_IMPORTS = (
    "michi.application.audio_device_registry",
    "michi.application.audio_device_semantics",
    "michi.application.audio_output_planner",
    "michi.application.audio_output_profile_service",
    "michi.application.audio_output_selection_coordinator",
    "michi.application.direct_output_lifecycle_coordinator",
    "michi.application.output_session_service",
    "michi.application.volume_policy_service",
    "michi.domain.signal_truth",
    "michi.infrastructure.audio_output.direct_output_executor",
    "michi.presentation.audio_output_bridge",
)


def _git_head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() or "UNKNOWN"


def _working_tree_gate() -> tuple[bool, str]:
    completed = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return False, "could not inspect the git working tree"
    if completed.stdout.strip():
        return (
            False,
            "working tree is dirty; verdict cannot bind to the reported commit",
        )
    return True, "working tree is clean and verdict is commit-bound"


def _run_gate(gate: Gate, env: dict[str, str]) -> GateResult:
    log_path = ARTIFACTS / f"dac_m11_4_{gate.gate_id}.log"
    started = time.monotonic()
    completed = subprocess.run(
        gate.command,
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    duration = time.monotonic() - started
    output = completed.stdout
    if completed.stderr:
        output += ("\n" if output else "") + completed.stderr
    log_path.write_text(output, encoding="utf-8")
    status = "PASS" if completed.returncode == 0 else "FAIL"
    print(f"[{status}] {gate.gate_id} ({duration:.1f}s)")
    if status == "FAIL":
        print(f"  log: {log_path.relative_to(ROOT)}")
    return GateResult(
        gate_id=gate.gate_id,
        description=gate.description,
        command=gate.command,
        status=status,
        returncode=completed.returncode,
        duration_seconds=round(duration, 3),
        log=str(log_path.relative_to(ROOT)),
        detail="command completed" if status == "PASS" else "command failed",
    )


def _static_invariants() -> tuple[bool, str]:
    missing = [
        str(path.relative_to(ROOT))
        for path in (
            ROOT / "src/michi/presentation/qml/player/AudioOutputPopup.qml",
            ROOT / "src/michi/presentation/qml/views/AudioOutputSettingsSection.qml",
            ROOT / "src/michi/presentation/audio_output_bridge.py",
        )
        if not path.is_file()
    ]
    if missing:
        return False, f"missing required files: {missing}"

    qml_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            ROOT / "src/michi/presentation/qml/player/AudioOutputPopup.qml",
            ROOT / "src/michi/presentation/qml/views/AudioOutputSettingsSection.qml",
        )
    ).casefold()
    forbidden = [
        token for token in ("hw:card=", "plughw:", "card_index") if token in qml_sources
    ]
    if forbidden:
        return False, f"raw backend identity leaked into DAC QML: {forbidden}"

    bootstrap = (ROOT / "src/michi/bootstrap/__init__.py").read_text(encoding="utf-8")
    if bootstrap.count("GStreamerDirectOutputExecutor(") != 1:
        return False, "production graph must construct exactly one Direct executor"
    if "executors={AudioEngineId.GSTREAMER.value: direct_executor}" not in bootstrap:
        return (
            False,
            "OutputSessionService does not share the production Direct executor",
        )

    return True, "authority construction and forbidden-identity invariants hold"


def _read_gate_log(gate_id: str) -> str:
    path = ARTIFACTS / f"dac_m11_4_{gate_id}.log"
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _required_collection_gate(output: str) -> tuple[bool, str]:
    missing = [path for path in REQUIRED_COLLECTED_MODULES if path not in output]
    if missing:
        return False, f"mandatory test modules were not collected: {missing}"
    return True, f"all {len(REQUIRED_COLLECTED_MODULES)} mandatory modules collected"


def _pytest_counts(output: str) -> dict[str, int]:
    counts = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
        "errors": 0,
        "collected": 0,
    }
    for match in re.finditer(
        r"(?P<count>\d+)\s+(?P<kind>passed|failed|skipped|xfailed|xpassed|errors?)\b",
        output,
    ):
        kind = match.group("kind")
        if kind == "error":
            kind = "errors"
        counts[kind] = max(counts[kind], int(match.group("count")))
    collected = re.findall(r"(\d+)\s+(?:tests?\s+)?collected\b", output)
    if collected:
        counts["collected"] = int(collected[-1])
    return counts


def _skip_records(output: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    pattern = re.compile(
        r"^(?P<kind>SKIPPED|XFAIL|XPASS)(?:\s+\[\d+\])?\s+"
        r"(?P<location>tests/[^\s:]+)(?::\d+)?(?:::[^\s]+)?\s*[:-]?\s*"
        r"(?P<reason>.*)$"
    )
    for line in output.splitlines():
        match = pattern.match(line.strip())
        if match is None:
            continue
        location = match.group("location")
        reason = match.group("reason").strip() or "pytest did not provide a reason"
        mandatory = any(
            location.startswith(prefix) for prefix in MANDATORY_SKIP_PREFIXES
        )
        lowered = reason.casefold()
        if mandatory:
            classification = "mandatory_dac_software"
        elif any(
            token in lowered
            for token in (
                "dependency absent",
                "no disponible",
                "not found in path",
                "platform cannot",
                "live network",
                "opt-in",
            )
        ):
            classification = "environmental_optional"
        else:
            classification = "unrelated_legacy"
        records.append(
            {
                "kind": match.group("kind").lower(),
                "file": location,
                "reason": reason,
                "classification": classification,
            }
        )
    return records


def _mandatory_skip_gate(output: str) -> tuple[bool, str]:
    records = _skip_records(output)
    mandatory = [
        item
        for item in records
        if item["classification"] == "mandatory_dac_software"
        and item["kind"] in {"skipped", "xfail"}
    ]
    if mandatory:
        return False, f"mandatory DAC tests skipped/xfail: {mandatory}"
    return (
        True,
        f"mandatory DAC skips/xfails=0; classified other outcomes={len(records)}",
    )


def _claim_leak_gate(root: Path | None = None) -> tuple[bool, str]:
    scan_root = root or ROOT
    product_root = scan_root / "src" / "michi"
    terms = (
        "bit-perfect",
        "michi verified",
        "exclusive verified",
        "physical verified",
        "kernel verified",
        "hardware verified",
    )
    negative_markers = (
        " not ",
        " no ",
        "never ",
        "nunca ",
        "does not ",
        "cannot ",
        "sin claim",
    )
    leaks: list[str] = []
    if not product_root.exists():
        return False, "product source root is missing"
    for path in sorted(product_root.rglob("*")):
        if path.suffix not in {".py", ".qml"} or not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for line_number, line in enumerate(lines, start=1):
            normalized = f" {line.casefold()} "
            present_terms = [term for term in terms if term in normalized]
            if not present_terms:
                continue
            context = " ".join(lines[max(0, line_number - 3) : line_number]).casefold()
            first_term = min(context.rfind(term) for term in present_terms)
            clause_prefix = re.split(r"[.!?]", context[:first_term])[-1]
            if any(marker in f" {clause_prefix} " for marker in negative_markers):
                continue
            leaks.append(f"{path.relative_to(scan_root)}:{line_number}")
    if leaks:
        return False, f"current product-positive claim leaks: {leaks}"
    return True, "current product-positive claim leaks: 0"


def _status_consistency_gate(root: Path | None = None) -> tuple[bool, str]:
    scan_root = root or ROOT
    paths = {
        "canonical": scan_root
        / "docs/dac/MICHI_DAC_CANONICAL_EFFECTIVE_SPEC_KERNEL_DRIVER_METHOD_V3_5.md",
        "contract": scan_root / "docs/M11_4_AUDIOPHILE_OUTPUT_DAC.md",
        "matrix": scan_root / "docs/STATUS_MATRIX.md",
        "roadmap": scan_root / "docs/MASTER_ROADMAP_1.0.md",
        "readme": scan_root / "README.md",
    }
    try:
        text = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    except OSError as exc:
        return False, f"status source unavailable: {exc}"
    # R110 reached a bounded, device-scoped physical PASS, so every status
    # source must agree on that current status. The exact "= ..." token binds
    # the canonical status block rather than relying on loose text matches.
    required = {
        "canonical": (
            "DAC-V35-100R1.3.4 = CLOSED-AUTOMATED / GO",
            "DAC-V35-110 = PHYSICAL QUALIFICATION PASS (BOUNDED, device-scoped)",
        ),
        "contract": (
            "DAC-V35-100R1.3.4",
            "PHYSICAL QUALIFICATION PASS (BOUNDED",
        ),
        "matrix": (
            "M11.4 Audiophile Output & DAC",
            "PHYSICAL QUALIFICATION PASS (BOUNDED",
            "DAC-V35-100R1.3.4",
        ),
        "roadmap": (
            "M11.4 Audiophile Output/DAC",
            "PHYSICAL QUALIFICATION PASS (BOUNDED",
            "DAC-V35-100R1.3.4",
        ),
        "readme": ("DAC-V35-100R1.3.4", "PHYSICAL QUALIFICATION PASS (BOUNDED"),
    }
    missing = [
        f"{name}:{marker}"
        for name, markers in required.items()
        for marker in markers
        if marker not in text[name]
    ]
    work_package_done = re.search(
        r"\|\s*M11\.4 Audiophile Output & DAC Management\s*\|\s*DONE\s*\|",
        text["matrix"],
    )
    if work_package_done:
        missing.append("matrix:M11.4 work package must not be DONE before 110")
    stale_pending = [
        name
        for name in ("matrix", "roadmap", "readme")
        if re.search(r"\|\s*PHYSICAL QUALIFICATION IN PROGRESS\s*\|", text[name])
    ]
    if stale_pending:
        missing.append(f"stale pending status cell: {stale_pending}")
    if "DAC-V35-130\n= POST-STABLE ONLY" not in text["canonical"] and not re.search(
        r"DAC-V35-130.*POST-STABLE ONLY", text["canonical"]
    ):
        missing.append("canonical:DAC-V35-130 POST-STABLE ONLY")
    if missing:
        return False, f"current status contradictions/missing markers: {missing}"
    return True, "current status markers agree; M11.4 is physically qualified (bounded)"


def _source_characterization_contract_gate(
    root: Path | None = None,
) -> tuple[bool, str]:
    """Seal the pre-plan decoded-source and explicit-Stop production seams."""
    scan_root = root or ROOT
    paths = {
        "planner": scan_root / "src/michi/application/audio_output_planner.py",
        "resolver": scan_root / "src/michi/application/output_session_service.py",
        "gstreamer": scan_root / "src/michi/infrastructure/audio_engines/gstreamer.py",
        "bootstrap": scan_root / "src/michi/bootstrap/__init__.py",
        "playback": scan_root / "src/michi/application/playback_service.py",
        "persistence": scan_root / "src/michi/application/persistence_coordinator.py",
    }
    try:
        source = {
            name: path.read_text(encoding="utf-8") for name, path in paths.items()
        }
    except OSError as exc:
        return False, f"source-characterization contract unavailable: {exc}"
    required = {
        "planner": (
            "decoded_source: DecodedSourceSignal",
            "CandidateCarrierResolver()",
            "resolver.candidates(",
        ),
        "resolver": (
            "self._source_characterizer.characterize(path)",
            "decoded_source=decoded_source",
        ),
        "bootstrap": (
            "GStreamerSourceCharacterizer(",
            "source_characterizer=source_characterizer",
        ),
        "playback": (
            "subscribe_explicit_stop_accepted",
            "_explicit_stop_accepted_subscribers",
        ),
        "persistence": (
            "subscribe_explicit_stop_accepted",
            "explicit stop accepted",
        ),
    }
    missing = [
        f"{name}:{marker}"
        for name, markers in required.items()
        for marker in markers
        if marker not in source[name]
    ]
    gstreamer_method = source["gstreamer"].split("    def characterize_local_file(", 1)
    if len(gstreamer_method) != 2:
        missing.append("gstreamer:characterize_local_file")
    else:
        body = gstreamer_method[1].split("\n    def ", 1)[0]
        for marker in ('"fakesink"', "gst.State.NULL", "timeout_ns"):
            if marker not in body:
                missing.append(f"gstreamer:{marker}")
        if "alsasink" in body or "SignalTruth" in body:
            missing.append("gstreamer:characterization must not acquire/output truth")
    if missing:
        return False, f"source-characterization/Stop contract missing: {missing}"
    return (
        True,
        "decoded-source precedes pure planning; fake-sink probe and explicit Stop "
        "reconciliation are productively wired",
    )


def _verification_manifest_gate(root: Path | None = None) -> tuple[bool, str]:
    scan_root = root or ROOT
    path = scan_root / "tests/dac/test_v35_100_software_closure.py"
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        return False, f"verification manifest unavailable: {exc}"
    required = (
        '"conditional": ("DAC-V35-120",)',
        '"post_stable": ("DAC-V35-130",)',
        '"separate_promotion": ("DAC-V35-140",)',
    )
    missing = [item for item in required if item not in source]
    if missing:
        return False, f"verification scheduling classifications missing: {missing}"
    return True, "120 conditional; 130 post-stable; 140 separate promotion"


def _ci_commit_gate(commit: str, env: dict[str, str]) -> tuple[bool, str]:
    github_sha = env.get("GITHUB_SHA")
    if not github_sha:
        return True, "local run; no GITHUB_SHA binding requested"
    if github_sha != commit:
        return False, f"GITHUB_SHA {github_sha} != verifier commit {commit}"
    return True, f"remote artifact bound to GITHUB_SHA={github_sha}"


def _alignment_artifact_gate(commit: str) -> tuple[bool, str]:
    path = ARTIFACTS / "dac_repository_alignment.json"
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return False, f"alignment artifact unavailable or malformed: {exc}"
    if report.get("commit") != commit:
        return False, "alignment artifact does not bind to the verifier commit"
    if report.get("aligned") is not True:
        return False, "alignment artifact reports changed repository assumptions"
    return True, "alignment artifact is current and reports aligned=true"


def _built_wheel(output_dir: Path) -> Path | None:
    wheels = tuple(output_dir.glob("*.whl"))
    return wheels[0] if len(wheels) == 1 else None


def _wheel_members_gate(wheel: Path) -> tuple[bool, str]:
    with ZipFile(wheel) as archive:
        members = set(archive.namelist())
    missing = sorted(REQUIRED_DAC_WHEEL_MEMBERS - members)
    if missing:
        return False, f"wheel missing DAC runtime members: {missing}"
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    return (
        True,
        f"{len(REQUIRED_DAC_WHEEL_MEMBERS)} required DAC members present; "
        f"sha256={digest}",
    )


def _result_for_internal(
    gate_id: str, description: str, check: tuple[bool, str]
) -> GateResult:
    ok, detail = check
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {gate_id}: {detail}")
    return GateResult(
        gate_id, description, (), status, 0 if ok else 1, 0.0, None, detail
    )


def _skip_result(gate_id: str, description: str, detail: str) -> GateResult:
    print(f"[SKIP] {gate_id}: {detail}")
    return GateResult(gate_id, description, (), "SKIP", None, 0.0, None, detail)


def _write_reports(commit: str, results: list[GateResult]) -> None:
    verdict = "GO" if all(item.status == "PASS" for item in results) else "NO_GO"
    generated = datetime.now(UTC).isoformat()
    artifact_paths = sorted(
        str(path.relative_to(ROOT))
        for path in (
            *ARTIFACTS.glob("dac_m11_4_*"),
            *ARTIFACTS.glob("dac_repository_alignment.*"),
            *ARTIFACTS.glob("michi_music_player-*.whl"),
        )
        if path.name not in {"dac_m11_4_verdict.json", "dac_m11_4_verdict.md"}
    )
    test_counts: dict[str, dict[str, int]] = {}
    for item in results:
        if item.log is None:
            continue
        counts = _pytest_counts(_read_gate_log(item.gate_id))
        if any(counts.values()):
            test_counts[item.gate_id] = counts
    collection_output = _read_gate_log("required-test-collection")
    full_output = _read_gate_log("full-regression-suite")
    ci = {
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_sha": os.environ.get("GITHUB_SHA"),
    }
    report = {
        "schema_version": 1,
        "commit": commit,
        "spec_revision": SPEC_REVISION,
        "automated_verdict": verdict,
        "physical_verdict": "NOT_RUN",
        "gates": [asdict(item) for item in results],
        "test_counts": test_counts,
        "collection": {
            "required_modules": list(REQUIRED_COLLECTED_MODULES),
            "required_modules_collected": all(
                item in collection_output for item in REQUIRED_COLLECTED_MODULES
            ),
            "counts": _pytest_counts(collection_output),
        },
        "skip_classification": _skip_records(full_output),
        "artifacts": artifact_paths,
        "generated_at": generated,
        "generated_at_utc": generated,
        "ci": ci,
    }
    json_path = ARTIFACTS / "dac_m11_4_verdict.json"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    modules_collected = report["collection"]["required_modules_collected"]
    classified_skips = len(report["skip_classification"])
    lines = [
        "# M11.4 automated software verdict",
        "",
        f"- Commit: `{commit}`",
        f"- Spec revision: `{SPEC_REVISION}`",
        f"- Automated verdict: **{verdict}**",
        "- Physical verdict: **NOT_RUN**",
        "- Scope: automated software evidence only; not Michi-Verified "
        "or physical proof.",
        f"- Required modules collected: **{modules_collected}**",
        f"- Full-suite skips/xfails classified: **{classified_skips}**",
        "",
        "| Gate | Status | Detail |",
        "|---|---|---|",
    ]
    lines.extend(
        f"| `{item.gate_id}` | {item.status} | {item.detail} |" for item in results
    )
    lines += ["", f"Generated: `{generated}`", ""]
    (ARTIFACTS / "dac_m11_4_verdict.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-full-suite",
        action="store_true",
        help="Development-only: omit the full suite; the resulting verdict is NO_GO.",
    )
    args = parser.parse_args(argv)
    ARTIFACTS.mkdir(exist_ok=True)
    for stale in ARTIFACTS.glob("dac_m11_4_*"):
        if stale.is_file():
            stale.unlink()
    for stale_wheel in ARTIFACTS.glob("michi_music_player-*.whl"):
        stale_wheel.unlink()
    commit = _git_head()
    results: list[GateResult] = []

    results.append(
        _result_for_internal(
            "exact-commit-tree",
            "Verdict binds to an exact clean git commit",
            _working_tree_gate(),
        )
    )

    with tempfile.TemporaryDirectory(prefix="michi-dac-v35-100-") as state_dir:
        env = os.environ.copy()
        env.update(
            {
                "QT_QPA_PLATFORM": "offscreen",
                "XDG_CONFIG_HOME": str(Path(state_dir) / "config"),
                "XDG_DATA_HOME": str(Path(state_dir) / "data"),
                "XDG_CACHE_HOME": str(Path(state_dir) / "cache"),
            }
        )
        for gate in TEST_GATES:
            if args.no_full_suite and gate.gate_id == "full-regression-suite":
                results.append(
                    _skip_result(
                        gate.gate_id,
                        gate.description,
                        "omitted by --no-full-suite; closure cannot be GO",
                    )
                )
                continue
            results.append(_run_gate(gate, env))

        results.append(
            _result_for_internal(
                "alignment-artifact",
                "Alignment report agrees with the exact verifier commit",
                _alignment_artifact_gate(commit),
            )
        )
        results.append(
            _result_for_internal(
                "mandatory-module-collection",
                "Required DAC/startup/UI modules are collected",
                _required_collection_gate(_read_gate_log("required-test-collection")),
            )
        )
        results.append(
            _result_for_internal(
                "mandatory-skip-audit",
                "Mandatory DAC software tests cannot skip or xfail",
                _mandatory_skip_gate(_read_gate_log("full-regression-suite")),
            )
        )
        results.append(
            _result_for_internal(
                "product-claim-firewall",
                "Current product code/QML contains no positive verification claims",
                _claim_leak_gate(),
            )
        )
        results.append(
            _result_for_internal(
                "current-status-consistency",
                "Current M11.4/R1/110 status markers agree",
                _status_consistency_gate(),
            )
        )
        results.append(
            _result_for_internal(
                "source-characterization-contract",
                "Decoded-source planning and explicit Stop reconciliation",
                _source_characterization_contract_gate(),
            )
        )
        results.append(
            _result_for_internal(
                "verification-scheduling-manifest",
                "120/130/140 scheduling remains semantically distinct",
                _verification_manifest_gate(),
            )
        )
        results.append(
            _result_for_internal(
                "ci-commit-binding",
                "Remote verdict commit equals GitHub workflow SHA",
                _ci_commit_gate(commit, env),
            )
        )
        results.append(
            _result_for_internal(
                "canonical-invariants",
                "Canonical filenames, ownership, and forbidden-call invariants",
                _static_invariants(),
            )
        )

        wheel_output = Path(state_dir) / "wheel-dist"
        build = _run_gate(
            Gate(
                "wheel-build",
                "Build distributable wheel",
                (
                    sys.executable,
                    "-m",
                    "build",
                    "--outdir",
                    str(wheel_output),
                ),
            ),
            env,
        )
        results.append(build)
        built_wheel = _built_wheel(wheel_output) if build.status == "PASS" else None
        wheel = None
        if built_wheel is not None:
            wheel = ARTIFACTS / built_wheel.name
            shutil.copy2(built_wheel, wheel)
        if wheel is None:
            results.append(
                _skip_result(
                    "wheel-resource-parity", "Wheel resource parity", "no built wheel"
                )
            )
            results.append(
                _skip_result(
                    "dac-wheel-members", "Required DAC wheel members", "no built wheel"
                )
            )
            results.append(
                _skip_result(
                    "installed-wheel-dac-smoke",
                    "Installed DAC module smoke",
                    "no built wheel",
                )
            )
        else:
            results.append(
                _run_gate(
                    Gate(
                        "wheel-resource-parity",
                        "Productive runtime resource parity",
                        (
                            sys.executable,
                            "scripts/verify_wheel_resources.py",
                            str(wheel),
                        ),
                    ),
                    env,
                )
            )
            results.append(
                _result_for_internal(
                    "dac-wheel-members",
                    "Required DAC Python and QML members in wheel",
                    _wheel_members_gate(wheel),
                )
            )
            venv = Path(state_dir) / "wheel-smoke"
            install_command = (
                sys.executable,
                "-m",
                "venv",
                "--system-site-packages",
                str(venv),
            )
            venv_result = _run_gate(
                Gate(
                    "wheel-smoke-venv",
                    "Create isolated wheel smoke venv",
                    install_command,
                ),
                env,
            )
            results.append(venv_result)
            if venv_result.status == "PASS":
                python = venv / "bin" / "python"
                import_code = ";".join(
                    (
                        "import sys",
                        "from pathlib import Path",
                        "import michi",
                        "assert Path(michi.__file__).is_relative_to(Path(sys.prefix))",
                        *(f"import {name}" for name in INSTALLED_IMPORTS),
                    )
                )
                command = (
                    str(python),
                    "-m",
                    "pip",
                    "install",
                    "--no-deps",
                    "--force-reinstall",
                    str(wheel),
                )
                install_result = _run_gate(
                    Gate("wheel-smoke-install", "Install built wheel", command), env
                )
                results.append(install_result)
                if install_result.status == "PASS":
                    results.append(
                        _run_gate(
                            Gate(
                                "installed-wheel-dac-smoke",
                                "Import DAC modules from the installed wheel",
                                (str(python), "-c", import_code),
                            ),
                            env,
                        )
                    )
                else:
                    results.append(
                        _skip_result(
                            "installed-wheel-dac-smoke",
                            "Installed DAC module smoke",
                            "wheel installation failed",
                        )
                    )
            else:
                results.append(
                    _skip_result(
                        "installed-wheel-dac-smoke",
                        "Installed DAC module smoke",
                        "venv creation failed",
                    )
                )

    _write_reports(commit, results)
    verdict = "GO" if all(item.status == "PASS" for item in results) else "NO_GO"
    print(f"M11.4 automated verdict: {verdict}")
    print("Physical verdict: NOT_RUN")
    print("reports: artifacts/dac_m11_4_verdict.{json,md}")
    return 0 if verdict == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
