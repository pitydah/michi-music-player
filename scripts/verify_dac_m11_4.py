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
        (sys.executable, "-m", "pytest", "tests", "-q"),
    ),
)

REQUIRED_DAC_WHEEL_MEMBERS = frozenset(
    {
        "michi/presentation/audio_output_bridge.py",
        "michi/presentation/qml/player/AudioOutputPopup.qml",
        "michi/presentation/qml/views/AudioOutputSettingsSection.qml",
        "michi/application/audio_device_registry.py",
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
            *ARTIFACTS.glob("michi_music_player-*.whl"),
        )
        if path.name not in {"dac_m11_4_verdict.json", "dac_m11_4_verdict.md"}
    )
    report = {
        "schema_version": 1,
        "commit": commit,
        "spec_revision": SPEC_REVISION,
        "automated_verdict": verdict,
        "physical_verdict": "NOT_RUN",
        "gates": [asdict(item) for item in results],
        "artifacts": artifact_paths,
        "generated_at_utc": generated,
    }
    json_path = ARTIFACTS / "dac_m11_4_verdict.json"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# M11.4 automated software verdict",
        "",
        f"- Commit: `{commit}`",
        f"- Spec revision: `{SPEC_REVISION}`",
        f"- Automated verdict: **{verdict}**",
        "- Physical verdict: **NOT_RUN**",
        "- Scope: automated software evidence only; not Michi-Verified "
        "or physical proof.",
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
