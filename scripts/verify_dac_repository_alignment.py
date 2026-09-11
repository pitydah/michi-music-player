#!/usr/bin/env python3
"""DAC-V35-000 — repository / agent alignment (spec §399 + §0F).

Registra el estado del repositorio contra el baseline V3.5 y emite
``artifacts/dac_repository_alignment.json`` + ``.md``. Cualquier
diferencia con las asunciones gobernantes sale como
``CHANGED_ASSUMPTION`` — nunca en silencio (§399.5).

Gate: G-V35-000-C (report emitted) + G-V35-000-D (assumptions
reconciled antes del siguiente slice).

Uso:
    python scripts/verify_dac_repository_alignment.py
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "artifacts"

# §0F repository baseline seal.
BASELINE_HEAD = "1b5e3f84d84d45873147ae7ad1a633de086a7e85"
BASELINE_DATE = "2026-09-11"
BASELINE_SCHEMA_VERSION = 1

# §0F critical files (re-read if HEAD differs).
CRITICAL_FILES = (
    "src/michi/application/playback_service.py",
    "src/michi/application/playback_session_service.py",
    "src/michi/application/audio_transport_router.py",
    "src/michi/application/audio_engine_service.py",
    "src/michi/application/audio_engine_registry.py",
    "src/michi/application/ports.py",
    "src/michi/infrastructure/audio_engines/gstreamer.py",
    "src/michi/infrastructure/audio_engines/mpd.py",
    "src/michi/infrastructure/sqlite_settings.py",
    "src/michi/bootstrap/__init__.py",
    "src/michi/presentation/playback_bridge.py",
    "src/michi/presentation/qml/views/SettingsView.qml",
    "src/michi/presentation/qml/views/AudioEngineSettingsSection.qml",
    "pyproject.toml",
)

FINDINGS: list[dict] = []


def _check(check_id: str, ok: bool, detail: str, assumption: bool = False) -> None:
    FINDINGS.append(
        {
            "id": check_id,
            "ok": ok,
            "assumption": assumption,
            "detail": detail,
        }
    )


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return result.stdout.strip()


def _sha16(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def main() -> int:
    head = _git("rev-parse", "HEAD")
    dirty = bool(_git("status", "--porcelain"))

    # ── §0F baseline seal ────────────────────────────────────────────
    # El baseline se ancla en el commit del §0F; los WPs DAC avanzan el
    # HEAD legítimamente (la spec exige re-leer los archivos críticos,
    # no congelar el árbol). Divergencia real (no descendiente) = CHANGED.
    if head == BASELINE_HEAD:
        _check(
            "head-matches-baseline",
            True,
            f"HEAD={head} == baseline",
            assumption=True,
        )
    else:
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", BASELINE_HEAD, "HEAD"],
            cwd=ROOT,
            capture_output=True,
        )
        descends = ancestor.returncode == 0
        _check(
            "head-descends-from-baseline",
            descends,
            (
                f"HEAD={head} evolved from baseline={BASELINE_HEAD} "
                "via DAC work packages (critical files re-read)"
                if descends
                else f"HEAD={head} DIVERGED from baseline={BASELINE_HEAD}"
            ),
            assumption=True,
        )
    _check("working-tree", not dirty, "dirty" if dirty else "clean")

    # ── critical files: existencia + hash ────────────────────────────
    for rel in CRITICAL_FILES:
        path = ROOT / rel
        if path.is_file():
            _check(f"file:{rel}", True, f"sha256:{_sha16(path)}")
        else:
            _check(f"file:{rel}", False, "MISSING", assumption=True)

    # ── schema version ───────────────────────────────────────────────
    settings_src = (ROOT / "src/michi/infrastructure/sqlite_settings.py").read_text(
        encoding="utf-8"
    )
    match = re.search(r"CURRENT_SCHEMA_VERSION\s*=\s*(\d+)", settings_src)
    schema = int(match.group(1)) if match else -1
    _check(
        "settings-schema-version",
        schema == BASELINE_SCHEMA_VERSION,
        f"schema={schema} baseline={BASELINE_SCHEMA_VERSION}",
        assumption=True,
    )

    # ── minimum Python / PySide6 ─────────────────────────────────────
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    requires_python = pyproject.get("project", {}).get("requires-python", "")
    deps = " ".join(pyproject.get("project", {}).get("dependencies", []))
    pyside = next((d for d in deps.split() if d.startswith("PySide6")), "?")
    _check("python-floor", bool(requires_python), f"requires-python={requires_python}")
    _check("pyside-floor", pyside != "?", f"{pyside}")

    # ── AudioEngineSettingsSection remains separate ──────────────────
    engine_qml = (
        ROOT / "src/michi/presentation/qml/views/AudioEngineSettingsSection.qml"
    )
    settings_view = (
        ROOT / "src/michi/presentation/qml/views/SettingsView.qml"
    ).read_text(encoding="utf-8")
    _check(
        "engine-section-separate",
        engine_qml.is_file() and "AudioEngineSettingsSection" in settings_view,
        "AudioEngineSettingsSection present and referenced by SettingsView",
        assumption=True,
    )

    # ── volume path: PlaybackBridge -> PlaybackService -> AudioPort ──
    bridge_src = (ROOT / "src/michi/presentation/playback_bridge.py").read_text(
        encoding="utf-8"
    )
    service_src = (ROOT / "src/michi/application/playback_service.py").read_text(
        encoding="utf-8"
    )
    router_src = (ROOT / "src/michi/application/audio_transport_router.py").read_text(
        encoding="utf-8"
    )
    bridge_ok = bool(
        re.search(r"def set_volume.*?self\._service\.set_volume", bridge_src, re.S)
    )
    service_ok = bool(re.search(r"self\._audio\.set_volume", service_src))
    router_ok = "def set_volume" in router_src
    _check(
        "volume-path",
        bridge_ok and service_ok and router_ok,
        f"bridge->service={bridge_ok} service->audio={service_ok} router={router_ok}",
        assumption=True,
    )

    # ── GStreamer adapter stays playbin3-based ───────────────────────
    gst_src = (ROOT / "src/michi/infrastructure/audio_engines/gstreamer.py").read_text(
        encoding="utf-8"
    )
    _check(
        "gstreamer-playbin3",
        "playbin3" in gst_src,
        "playbin3 present",
        assumption=True,
    )

    changed = [f for f in FINDINGS if f["assumption"] and not f["ok"]]
    aligned = not changed

    OUT_DIR.mkdir(exist_ok=True)
    report = {
        "schema_version": 1,
        "spec_revision": "V3.5",
        "work_package": "DAC-V35-000",
        "commit": head,
        "baseline_head": BASELINE_HEAD,
        "working_tree_dirty": dirty,
        "aligned": aligned,
        "changed_assumptions": changed,
        "findings": FINDINGS,
        "generated_at_utc": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "dac_repository_alignment.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# DAC-V35-000 — repository alignment report",
        "",
        f"- commit: `{head}`",
        f"- baseline: `{BASELINE_HEAD}` ({BASELINE_DATE})",
        f"- working tree: {'dirty' if dirty else 'clean'}",
        f"- aligned: **{'YES' if aligned else 'NO'}**",
        "",
        "## Findings",
        "",
        "| check | ok | detail |",
        "|---|---|---|",
    ]
    for finding in FINDINGS:
        mark = "OK" if finding["ok"] else "CHANGED"
        lines.append(f"| {finding['id']} | {mark} | {finding['detail']} |")
    if changed:
        lines += ["", "## CHANGED_ASSUMPTION (reconcile before next slice)", ""]
        lines += [f"- {c['id']}: {c['detail']}" for c in changed]
    (OUT_DIR / "dac_repository_alignment.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    print(f"HEAD: {head}")
    print(f"working tree: {'dirty' if dirty else 'clean'}")
    print(f"aligned: {'YES' if aligned else 'NO'}")
    for finding in FINDINGS:
        mark = "OK" if finding["ok"] else "CHANGED"
        print(f"  [{mark}] {finding['id']}: {finding['detail']}")
    print("report: artifacts/dac_repository_alignment.{json,md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
