"""A41 contract tests for transactional preparation of ST-NAME-001."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import migrate_michi_truth_names_a41 as mig  # noqa: E402


def git(repo: Path, *parts: str) -> str:
    r = subprocess.run(
        ("git", "-C", str(repo), *parts), capture_output=True, text=True, check=True
    )
    return r.stdout.strip()


def seeded(repo: Path) -> tuple[Path, str]:
    repo.mkdir(exist_ok=True)
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Michi Test")
    git(repo, "config", "user.email", "fixture@example.invalid")
    specs = {
        "src/michi/domain/" + mig.OLD_SNAKE + ".py": "class Signal"
        + "PathNodeKind: pass\nclass Signal"
        + "PathSnapshot: pass\n",
        "src/michi/application/" + mig.OLD_SNAKE + "_service.py": "from michi.domain."
        + mig.OLD_SNAKE
        + " import Signal"
        + "PathSnapshot\nclass Signal"
        + "PathService: pass\n",
        "src/michi/presentation/" + mig.OLD_SNAKE + "_bridge.py": "class Signal"
        + "PathBridge: pass\n",
        "src/michi/presentation/qml/components/Michi"
        + mig.OLD_PREFIX
        + "View.qml": "import QtQuick\nItem { objectName: 'Michi"
        + mig.OLD_PREFIX
        + "View' }\n",
        "tests/audio_phase2/test_"
        + mig.OLD_SNAKE
        + "_service.py": "def test_projection(): assert 'Signal" + "PathSnapshot'\n",
        "tests/audio_phase2/test_f11_"
        + mig.OLD_SNAKE
        + "_bridge.py": "def test_owner(): assert 'Signal" + "PathBridge'\n",
        mig.OLD_BIBLE: "# Canonical AP2-F11\n",
        "AGENTS.md": "Read " + mig.OLD_BIBLE + "\n",
        "docs/audio/phase2/PHASE2_STATE.json": '{"spec": {"path": "'
        + mig.OLD_BIBLE
        + '", "sha256_at_last_transition": "historical"}}\n',
        "src/michi/presentation/audio_output_bridge.py": f"{mig.OLD_SNAKE}_kind = 'managed'\n"  # noqa: E501
        f"{mig.OLD_SNAKE} = self._{mig.OLD_SNAKE}(truth)\n"  # noqa: E501
        f"return {{'{mig.OLD_CAMEL}': {mig.OLD_SNAKE}, '{mig.OLD_CAMEL}Kind': {mig.OLD_SNAKE}_kind}}\n",  # noqa: E501
        "src/michi/presentation/qml/components/AudioOutputDeviceGroup.qml": f"Item {{ property var {mig.OLD_CAMEL}: []; {mig.OLD_CAMEL}: root.{mig.OLD_CAMEL} }}\n",  # noqa: E501
        "src/michi/presentation/qml/views/SettingsView.qml": f"Item {{ {mig.OLD_CAMEL}: audioOutput.{mig.OLD_CAMEL} }}\n",  # noqa: E501
        "src/michi/presentation/qml/player/NowPlayingBar.qml": f"Item {{ property var {mig.OLD_CAMEL}Bridge: null }}\n",  # noqa: E501
        "src/michi/bootstrap/__init__.py": "from michi.presentation."
        + mig.OLD_SNAKE
        + "_bridge import Signal"
        + "PathBridge\n"
        "ctx.setContextProperty('" + mig.OLD_CAMEL + "', spb)\n",
        ".github/workflows/ci.yml": "path: tests/audio_phase2/test_f11_"
        + mig.OLD_SNAKE
        + "_bridge.py\n",
        "tests/test_audio_output_bridge.py": "def test_out(): assert '"
        + mig.OLD_CAMEL
        + "Kind' and '"
        + mig.OLD_CAMEL
        + "'\n",
    }
    for rel, data in specs.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(data, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "fixture")
    return repo, git(repo, "rev-parse", "HEAD")


def test_plan_is_read_only_and_deterministic(tmp_path):
    repo, head = seeded(tmp_path / "r")
    before = git(repo, "status", "--porcelain")
    x = mig.plan(repo, expected_head=head)
    y = mig.plan(repo, expected_head=head)
    assert [c.manifest() for c in x] == [c.manifest() for c in y]
    assert len([c for c in x if c.src != c.dst]) == 7
    assert before == git(repo, "status", "--porcelain") == ""


def test_rename_is_semantic_and_no_alias_survives(tmp_path):
    repo, head = seeded(tmp_path / "r")
    mig.apply(repo, mig.plan(repo, expected_head=head))
    assert (repo / "src/michi/domain/truth_graph.py").exists()
    assert (repo / "src/michi/application/signal_truth_projection_service.py").exists()
    assert (repo / "src/michi/presentation/signal_truth_bridge.py").exists()
    assert (
        repo / "src/michi/presentation/qml/components/MichiSignalTruthView.qml"
    ).exists()
    assert not (repo / ("src/michi/domain/" + mig.OLD_SNAKE + ".py")).exists()
    text = (repo / "src/michi/presentation/audio_output_bridge.py").read_text()
    assert "outputRouteStages" in text and "outputRouteKind" in text
    assert "_output_route_stages" in text
    assert (
        "truthStages: audioOutput.outputRouteStages"
        in (repo / "src/michi/presentation/qml/views/SettingsView.qml").read_text()
    )
    assert (
        "signalTruthBridge"
        in (repo / "src/michi/presentation/qml/player/NowPlayingBar.qml").read_text()
    )
    assert (
        "signal_truth_bridge" in (repo / "src/michi/bootstrap/__init__.py").read_text()
    )
    assert "signalTruth'" in (repo / "src/michi/bootstrap/__init__.py").read_text()
    assert "historical" in (repo / "docs/audio/phase2/PHASE2_STATE.json").read_text()
    assert mig.NEW_BIBLE in (repo / "docs/audio/phase2/PHASE2_STATE.json").read_text()
    for root in ("src", "tests", "AGENTS.md", ".github"):
        pp = repo / root
        files = pp.rglob("*") if pp.is_dir() else (pp,)
        for p in files:
            if p.is_file():
                assert not mig.RESTRICTED.search(p.read_text()), p


def test_refuses_wrong_head(tmp_path):
    repo, head = seeded(tmp_path / "r")
    with pytest.raises(mig.Refusal, match="HEAD mismatch"):
        mig.plan(repo, expected_head="b" * 40)
    assert git(repo, "rev-parse", "HEAD") == head


def test_refuses_missing_source_without_writes(tmp_path):
    repo, head = seeded(tmp_path / "r")
    (repo / mig.OLD_BIBLE).unlink()
    with pytest.raises(mig.Refusal, match="missing or linked file"):
        mig.plan(repo, expected_head=head)


def test_refuses_destination_collision(tmp_path):
    repo, head = seeded(tmp_path / "r")
    other = repo / "src/michi/domain/truth_graph.py"
    other.write_text("protected data")
    with pytest.raises(mig.Refusal, match="destination already exists"):
        mig.plan(repo, expected_head=head)
    assert other.read_text() == "protected data"


def test_detects_source_changed_after_plan(tmp_path):
    repo, head = seeded(tmp_path / "r")
    changes = mig.plan(repo, expected_head=head)
    (repo / "src/michi/presentation/audio_output_bridge.py").write_text("mutated")
    with pytest.raises(mig.Refusal, match="source changed"):
        mig.apply(repo, changes)


def test_application_transaction_rolls_back(tmp_path, monkeypatch):
    repo, head = seeded(tmp_path / "r")
    changes = mig.plan(repo, expected_head=head)
    original = {c.src: (repo / c.src).read_bytes() for c in changes}
    actual_writer = mig._write_atomic
    count = 0

    def sabotaged(path, data, mode):
        nonlocal count
        count += 1
        if count == 5:
            raise OSError("simulated disk failure")
        return actual_writer(path, data, mode)

    monkeypatch.setattr(mig, "_write_atomic", sabotaged)
    with pytest.raises(OSError, match="simulated disk failure"):
        mig.apply(repo, changes)
    assert all((repo / src).read_bytes() == data for src, data in original.items())
    assert all(not (repo / c.dst).exists() for c in changes if c.dst != c.src)


def test_cli_requires_governance_permit(tmp_path):
    repo, head = seeded(tmp_path / "r")
    receipt = tmp_path / "receipt.json"
    rc = mig.main(
        [
            "--repo",
            str(repo),
            "--expected-head",
            head,
            "--mode",
            "apply",
            "--output",
            str(receipt),
        ]
    )
    assert rc == 2
    assert "REFUSED" in receipt.read_text()
    assert git(repo, "status", "--porcelain") == ""


def test_cli_plan_succeeds_and_does_not_touch_branch(tmp_path):
    repo, head = seeded(tmp_path / "r")
    rc = mig.main(["--repo", str(repo), "--expected-head", head])
    assert rc == 0
    assert git(repo, "rev-parse", "HEAD") == head


def test_migration_sources_are_naming_gate_clean():
    for path in (Path(mig.__file__), Path(__file__)):
        assert not mig.RESTRICTED.search(path.read_text()), path


def test_cli_explicit_governance_permit_applies_without_commit(tmp_path):
    repo, head = seeded(tmp_path / "r")
    rc = mig.main(
        [
            "--repo",
            str(repo),
            "--expected-head",
            head,
            "--mode",
            "apply",
            "--permit-governance-rename",
        ]
    )
    assert rc == 0
    assert git(repo, "rev-parse", "HEAD") == head
    assert (repo / mig.NEW_BIBLE).is_file()


def test_unknown_retired_product_filename_refused(tmp_path):
    repo, head = seeded(tmp_path / "r")
    name = "src/michi/presentation/extra_" + mig.OLD_SNAKE + ".py"
    path = repo / name
    path.write_text("answer = 1\n")
    git(repo, "add", name)
    git(repo, "commit", "-qm", "new known filename")
    with pytest.raises(mig.Refusal, match="unmapped legacy filename"):
        mig.plan(repo, expected_head=git(repo, "rev-parse", "HEAD"))


def test_migration_canonical_basename_without_parent_prefix():
    script = (
        'CANONICAL_NAME = "MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_'
        + "SIGNAL"
        + '_PATH_MEGA_PLAN.md"\n'
    )
    migrated = mig._replace(script, "scripts/phase2_context.py")
    assert "SIGNAL_TRUTH_MEGA_PLAN.md" in migrated
    assert not mig.RESTRICTED.search(migrated)


def test_qml_dac_harness_stage_prop_renamed_without_changing_bridge():
    source = f"section.setProperty('{mig.OLD_CAMEL}', PY_ROWS)\n"
    result = mig._replace(source, "tests/test_v35_090_qml_audio_output.py")
    assert "setProperty('truthStages', PY_ROWS)" in result
    assert not mig.RESTRICTED.search(result)


def test_verify_static_migration_without_staging(tmp_path):
    repo, head = seeded(tmp_path / "r")
    mig.apply(repo, mig.plan(repo, expected_head=head))
    assert mig.verify_worktree(repo) == []
    assert mig.main(["--repo", str(repo), "--mode", "verify"]) == 0


def test_verify_fails_on_reintroduced_legacy_token(tmp_path):
    repo, head = seeded(tmp_path / "r")
    mig.apply(repo, mig.plan(repo, expected_head=head))
    moved = repo / "src/michi/presentation/signal_truth_bridge.py"
    moved.write_text(moved.read_text() + "# legacy " + mig.OLD_SNAKE + "\n")
    assert any("retired API token" in problem for problem in mig.verify_worktree(repo))
    assert mig.main(["--repo", str(repo), "--mode", "verify"]) == 2
