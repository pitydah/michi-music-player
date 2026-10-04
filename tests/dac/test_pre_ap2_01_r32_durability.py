"""R32 hardened durability — chunked receipts, verified export, WIP isolation.

Covers MICHI_M11_4_HARDENED_PHYSICAL_CAMPAIGN_R11_1 section 6: the 8-hour soak
must never depend on one live gzip stream; receipts are sealed into hashed
chunks that survive a crash, and the canonical sidecar is exported and
independently verified only at finalization.
"""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import itertools
import json
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture(scope="module")
def lab():
    path = Path(__file__).parents[2] / "scripts" / "dac_m11_4_pcm_lab.py"
    spec = importlib.util.spec_from_file_location("dac_m11_4_pcm_lab", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _identity(port: int) -> dict:
    return {"execution_generation": 1, "port_generation": port}


def _play_result(lab, port: int) -> dict:
    return {
        "status": lab.PlaybackStatus.PLAYING.value,
        "error_message": None,
        "signal_truth_reasons": [],
        "signal_truth": {
            "identity": _identity(port),
            "decoded": {"rate_hz": 44100},
            "plan": {"requested": {"rate_hz": 44100}},
            "alsa": {"rate_hz": 44100},
            "verdict": {"state": "direct_container_adapted"},
        },
    }


def _wire_soak(
    lab,
    monkeypatch,
    tmp_path: Path,
    *,
    duration: float,
    chunk_limit: int,
    crash_at=None,
):
    counter = itertools.count()

    def fake_play(*_args):
        index = next(counter)
        if crash_at is not None and index == crash_at:
            raise RuntimeError("simulated soak crash")
        return _play_result(lab, port=index + 1)

    monkeypatch.setattr(
        lab, "_container", lambda *_args: SimpleNamespace(shutdown=lambda: None)
    )
    monkeypatch.setattr(lab, "_play", fake_play)
    monkeypatch.setattr(lab, "_stop", lambda *_args: None)
    monkeypatch.setattr(lab, "_process_rss_kb", lambda: 100000)
    monkeypatch.setattr(lab, "_resolve_usb_sysfs_node", lambda *_args, **_kw: tmp_path)
    monkeypatch.setattr(
        lab,
        "_read_usb_health_snapshot",
        lambda _node: {"busnum": 1, "devnum": 2, "urbnum": 100},
    )
    monkeypatch.setattr(
        lab,
        "_usb_health_evidence",
        lambda *_args, **_kw: {"available": True, "error_count": 0},
    )
    ticks = itertools.count()
    monkeypatch.setattr(lab.time, "monotonic", lambda: round(next(ticks) * 0.01, 2))
    monkeypatch.setattr(lab, "SOAK_RECEIPT_CHUNK_LIMIT", chunk_limit)
    recorded: dict = {}
    monkeypatch.setattr(lab, "_record", lambda _path, **kwargs: recorded.update(kwargs))
    args = Namespace(
        duration_seconds=duration,
        device_id="usb:1111:2222:1-2",
        locator="hw:CARD=DAC,DEV=0",
        media=[tmp_path / "track.wav"],
        mode="compatible",
        checkpoint_every=1000,
        manifest=tmp_path / "manifest.json",
        usb_sysfs_path=None,
        fail_fast=False,
        wip_dir=tmp_path / "wip",
    )
    return args, recorded


def test_r32_soak_seals_chunks_and_exports_verified_sidecar(
    lab, tmp_path, monkeypatch
) -> None:
    args, recorded = _wire_soak(lab, monkeypatch, tmp_path, duration=0.4, chunk_limit=3)

    assert lab.command_soak(args) == 0

    facts = recorded["facts"]
    total = facts["receipts_total"]
    assert total == facts["cycles"] > 0
    chunk_dir = Path(facts["receipts_chunk_dir"])
    assert chunk_dir == tmp_path / "wip" / "receipts"
    chunk_files = sorted(chunk_dir.glob("chunk-*.jsonl"))
    expected_chunks = total // 3 + (1 if total % 3 else 0)
    assert len(chunk_files) == expected_chunks == len(facts["receipts_chunks"])
    for seal in facts["receipts_chunks"]:
        digest = hashlib.sha256((chunk_dir / seal["file"]).read_bytes()).hexdigest()
        assert seal["sha256"] == digest
    sidecar = Path(facts["receipts_file"])
    assert sidecar.is_file()
    assert facts["receipts_export_verified"] is True
    assert (
        facts["receipts_file_sha256"]
        == hashlib.sha256(sidecar.read_bytes()).hexdigest()
    )
    with gzip.open(sidecar, "rt", encoding="utf-8") as handle:
        lines = [json.loads(line) for line in handle if line.strip()]
    assert len(lines) == total


def test_r32_soak_crash_keeps_sealed_chunks_and_never_exports(
    lab, tmp_path, monkeypatch
) -> None:
    args, recorded = _wire_soak(
        lab, monkeypatch, tmp_path, duration=10.0, chunk_limit=2, crash_at=5
    )

    with pytest.raises(RuntimeError):
        lab.command_soak(args)

    chunk_dir = tmp_path / "wip" / "receipts"
    chunk_files = sorted(chunk_dir.glob("chunk-*.jsonl"))
    assert len(chunk_files) == 2, "five completed receipts make two sealed chunks"
    evidence = lab._evidence_module()
    assert evidence.ReceiptChunks(chunk_dir).validate_seals() == []
    sidecar_dir = tmp_path / "receipts"
    assert not any(sidecar_dir.iterdir()), "a crash must never export a sidecar"
    assert recorded == {}, "a crash must never import soak facts"


def test_r32_soak_refuses_reused_wip(lab, tmp_path, monkeypatch) -> None:
    wip_receipts = tmp_path / "wip" / "receipts"
    wip_receipts.mkdir(parents=True)
    (wip_receipts / "active.jsonl").write_text("{}\n", encoding="utf-8")
    containers: list[int] = []
    monkeypatch.setattr(
        lab,
        "_container",
        lambda *_args: containers.append(1) or SimpleNamespace(shutdown=lambda: None),
    )
    args = Namespace(
        duration_seconds=1.0,
        device_id="usb:1111:2222:1-2",
        locator="hw:CARD=DAC,DEV=0",
        media=[tmp_path / "track.wav"],
        mode="compatible",
        checkpoint_every=1000,
        manifest=tmp_path / "manifest.json",
        usb_sysfs_path=None,
        fail_fast=False,
        wip_dir=tmp_path / "wip",
    )

    with pytest.raises(SystemExit, match="STOP_R32_WIP_NOT_EMPTY"):
        lab.command_soak(args)

    assert containers == [], "the guard must run before any device is opened"


def test_r32_soak_writes_heartbeat_and_run_dir_receipts(
    lab, tmp_path, monkeypatch
) -> None:
    run_dir = tmp_path / "run"
    monkeypatch.setenv("M11_4_RUN_DIR", str(run_dir))
    args, recorded = _wire_soak(
        lab, monkeypatch, tmp_path, duration=0.3, chunk_limit=100000
    )
    args.wip_dir = None

    assert lab.command_soak(args) == 0

    progress = json.loads((run_dir / "progress.json").read_text(encoding="utf-8"))
    assert progress["phase"] == "r32-soak"
    assert Path(recorded["facts"]["receipts_chunk_dir"]) == run_dir / "receipts"
    assert (run_dir / "receipts" / "chunk-000001.jsonl").is_file()
