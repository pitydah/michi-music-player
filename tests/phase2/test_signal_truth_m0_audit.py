"""Synthetic executable acceptance tests for the static M0 tool."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.audit_michi_truth_m0 import (
    analyze_python,
    category,
    controlled,
    main,
    scan,
)


def init_repo(tmp_path: Path, *, status: str = "ACTIVE") -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    subprocess.run(["git", "init", "-q", str(r)], check=True)
    subprocess.run(
        ["git", "-C", str(r), "config", "user.email", "test@invalid.test"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(r), "config", "user.name", "Audit Test"], check=True
    )
    spec = "docs/audio/MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_TRUTH_MEGA_PLAN.md"
    write(r, spec, "# F11\n")
    write(
        r,
        "docs/audio/phase2/PHASE2_STATE.json",
        json.dumps(
            {
                "active_phases": ["AP2-F11"],
                "phases": {"AP2-F11": status},
                "spec": {"path": spec, "sha256_at_last_transition": "historical-value"},
            }
        ),
    )
    write(
        r, "src/michi/domain/signal_truth.py", "class SignalTruthRecorder:\n    pass\n"
    )
    write(
        r,
        "src/michi/presentation/signal_truth_bridge.py",
        """from michi.domain.signal_truth import SignalTruthRecorder
class SignalTruthBridge:
    def register(self, recorder):
        recorder.subscribe(self.changed)
    def changed(self):
        pass
""",
    )
    write(
        r,
        "tests/test_something.py",
        "from michi.domain.signal_truth import SignalTruthRecorder\n",
    )
    subprocess.run(["git", "-C", str(r), "add", "."], check=True)
    subprocess.run(["git", "-C", str(r), "commit", "-qm", "fixtures"], check=True)
    return r


def write(root: Path, rel: str, body: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


def test_clean_checkout_passes_baseline_and_naming(tmp_path):
    repo = init_repo(tmp_path)
    out = tmp_path / "output"
    assert main(["--repo", str(repo), "--out", str(out), "--gate", "naming"]) == 0
    x = json.loads((out / "F11_M0_INTEGRATION_INVENTORY.json").read_text())
    assert x["nomenclature"]["matches"] == 0
    assert x["phase2"]["f11"] == "ACTIVE"
    assert x["phase2"]["sha256_at_last_transition"] == "historical-value"
    assert x["phase2"]["spec_current_sha256"] != "historical-value"
    assert x["evidence_subscriptions"][0]["method"] == "subscribe"
    assert x["michi_imports"]
    assert (out / "F11_M0_INTEGRATION_INVENTORY.md").is_file()


def test_naming_gate_fails_but_baseline_succeeds(tmp_path):
    repo = init_repo(tmp_path)
    banned = "signal" + "_" + "path"
    write(
        repo,
        f"src/michi/domain/{banned}.py",
        "class " + "Signal" + "PathLegacy:\n    pass\n",
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    out = tmp_path / "output"
    assert main(["--repo", str(repo), "--out", str(out)]) == 0
    assert main(["--repo", str(repo), "--out", str(out), "--gate", "naming"]) == 2
    x = json.loads((out / "F11_M0_INTEGRATION_INVENTORY.json").read_text())
    assert {v["kind"] for v in x["nomenclature"]["locations"]} == {
        "content",
        "filename",
    }


def test_qml_and_ci_are_scanned(tmp_path):
    repo = init_repo(tmp_path)
    write(
        repo,
        "src/michi/presentation/qml/Screen.qml",
        "property var " + "signal" + "PathBridge: null\n",
    )
    write(repo, ".github/workflows/ci.yml", "run: echo " + "signal" + "_path" + "\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    found = scan(repo)["nomenclature"]["locations"]
    assert {v["path"] for v in found} == {
        "src/michi/presentation/qml/Screen.qml",
        ".github/workflows/ci.yml",
    }


def test_docs_excluded_from_product_policy(tmp_path):
    repo = init_repo(tmp_path)
    write(
        repo,
        "docs/old_notes.md",
        "Historical third-party " + "Signal" + " Path" + " research",
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    assert scan(repo)["nomenclature"]["matches"] == 0


def test_historical_evidence_script_not_automatically_product(tmp_path):
    repo = init_repo(tmp_path)
    write(
        repo,
        "evidence/historical_tool.py",
        "# " + "Signal" + " Path" + " old evidence\n",
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    assert scan(repo)["nomenclature"]["matches"] == 0


def test_spec_absence_blocks_baseline(tmp_path):
    repo = init_repo(tmp_path)
    (
        repo / "docs/audio/MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_TRUTH_MEGA_PLAN.md"
    ).unlink()
    assert main(["--repo", str(repo), "--out", str(tmp_path / "out")]) == 3


def test_python_imports_and_parsing():
    imports, errors = analyze_python(
        "from michi.domain.signal_truth import SignalTruthRecorder\n", "a.py"
    )
    assert imports[0]["module"] == "michi.domain.signal_truth"
    assert not errors
    imports, errors = analyze_python("def oops(:\n", "bad.py")
    assert errors and not imports


def test_category_and_controlled():
    assert category("src/michi/app.py") == "product"
    assert category("docs/f11.md") == "documentation"
    assert category("evidence/old.py") == "historical_evidence"
    assert controlled(".github/workflows/ci.yml")
    assert not controlled("docs/f11.md")


def test_new_producer_discovered(tmp_path):
    repo = init_repo(tmp_path)
    p = "src/michi/application/output_session_service.py"
    write(
        repo, p, "def emit(recorder):\n    recorder.record_output_family_event(event)\n"
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    out = scan(repo)["evidence_producer_calls"]
    assert any(
        x["path"] == p and x["method"] == "record_output_family_event" for x in out
    )


def test_untracked_files_do_not_enter_inventory(tmp_path):
    repo = init_repo(tmp_path)
    write(repo, "src/michi/_scratch.py", "# " + "signal" + "_path" + "\n")
    assert scan(repo)["nomenclature"]["matches"] == 0


def test_deterministic_inventory(tmp_path):
    repo = init_repo(tmp_path)
    a = scan(repo)
    b = scan(repo)
    assert a == b


def test_invalid_phase_manifest_stops(tmp_path):
    repo = init_repo(tmp_path)
    write(repo, "docs/audio/phase2/PHASE2_STATE.json", "{bad")
    assert "M0_SPEC_UNRESOLVED" in scan(repo)["blockers"]


def test_tracked_symlink_is_flagged(tmp_path):
    repo = init_repo(tmp_path)
    p = repo / "src/michi/unsafe.py"
    p.symlink_to("/etc/hosts")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    assert any(x["kind"] == "missing_or_symlink" for x in scan(repo)["scan_warnings"])


def test_no_git_fails(tmp_path):
    assert main(["--repo", str(tmp_path), "--out", str(tmp_path / "out")]) == 4


def test_qml_keyword_signal_followed_by_path_action_is_not_product_brand(tmp_path):
    repo = init_repo(tmp_path)
    write(
        repo,
        "src/michi/presentation/qml/views/Output.qml",
        "signal pathModeSelectionRequested(string mode)\n",
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    assert scan(repo)["nomenclature"]["matches"] == 0


def test_descriptive_phrase_without_suffix_is_still_blocked(tmp_path):
    repo = init_repo(tmp_path)
    write(
        repo,
        "src/michi/presentation/qml/views/Output.qml",
        "// " + "Signal" + " Path" + "\n",
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    assert scan(repo)["nomenclature"]["matches"] == 1
