#!/usr/bin/env python3
"""QML Physical Playback Runner — guides 21 real physical checks.

Usage:
    python scripts/qml_physical_runner.py          # interactive guided mode
    python scripts/qml_physical_runner.py --check  # verify artifact exists
    python scripts/qml_physical_runner.py --autofail <reason>  # mark all FAILED

Records results in artifacts/qml-physical-results.json.
States: PENDING, RUNNING, VERIFIED, FAILED, BLOCKED_HARDWARE.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = REPO / "artifacts"
ARTIFACT_PATH = ARTIFACT_DIR / "qml-physical-results.json"

CHECKS = [
    {"id": "mp3_playback",      "label": "MP3 playback",         "desc": "Click MP3 → audio audible"},
    {"id": "flac_playback",     "label": "FLAC playback",        "desc": "Click FLAC → audio audible"},
    {"id": "wav_playback",      "label": "WAV playback",         "desc": "Click WAV → audio audible"},
    {"id": "cover_display",     "label": "Cover display",        "desc": "Album art visible in NowPlayingBar"},
    {"id": "placeholder",       "label": "Placeholder display",  "desc": "Monogram placeholder for tracks without cover"},
    {"id": "play",              "label": "Play",                 "desc": "Space or play button starts playback"},
    {"id": "pause",             "label": "Pause",                "desc": "Space or pause button stops audio"},
    {"id": "seek",              "label": "Seek",                 "desc": "Drag progress slider → position changes"},
    {"id": "volume",            "label": "Volume",               "desc": "Volume slider changes audio level"},
    {"id": "mute",              "label": "Mute",                 "desc": "Mute button silences / restores"},
    {"id": "next",              "label": "Next",                 "desc": "Next button → next track plays"},
    {"id": "previous",          "label": "Previous",             "desc": "Previous button → previous track plays"},
    {"id": "shuffle",           "label": "Shuffle",              "desc": "Shuffle toggle changes order mode"},
    {"id": "repeat",            "label": "Repeat",               "desc": "Repeat toggle changes repeat mode"},
    {"id": "queue",             "label": "Queue",                "desc": "Queue list visible with tracks"},
    {"id": "queue_play",        "label": "Queue play",           "desc": "Click queue item → plays that track"},
    {"id": "lyrics",            "label": "Lyrics",               "desc": "Lyrics visible for current track"},
    {"id": "radio",             "label": "Radio",                "desc": "Radio stations list visible"},
    {"id": "radio_play",        "label": "Radio play",           "desc": "Radio stream playback audible"},
    {"id": "eq",                "label": "EQ",                   "desc": "EQ presets load and apply"},
    {"id": "settings",          "label": "Settings",             "desc": "Settings page renders correctly"},
]


def _get_git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, text=True).strip()
    except Exception:
        return "unknown"


def _get_platform() -> str:
    import platform
    return f"{platform.system()} {platform.release()}"


def _ask_bool(prompt: str) -> bool:
    while True:
        ans = input(f"{prompt} [y/n] ").strip().lower()
        if ans in ("y", "yes", "s", "si", "sí"):
            return True
        if ans in ("n", "no"):
            return False


def run_interactive():
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  Michi Music Player — QML Physical Playback Runner")
    print("=" * 60)
    print()
    print(f"  {len(CHECKS)} checks  |  States: PENDING → RUNNING → VERIFIED/FAILED/BLOCKED")
    print()

    sha = _get_git_sha()
    date = time.strftime("%Y-%m-%dT%H:%M:%S")
    platform = _get_platform()
    backend = input("Backend de audio (PipeWire/PulseAudio/ALSA): ").strip()
    device = input("Dispositivo de salida: ").strip()
    version = input("Versión de Michi: ").strip() or "0.2.0a0"

    results = []
    print()

    for c in CHECKS:
        print(f"\n--- [{c['id']}] {c['label']} ---")
        print(f"    {c['desc']}")
        passed = _ask_bool("  ¿Funciona correctamente?")
        evidence = ""
        if passed:
            evidence = input("  Evidencia manual (ej: 'slider se mueve, audio cambia'): ").strip()
        else:
            evidence = input("  Evidencia / motivo de fallo: ").strip()
            if not evidence:
                evidence = "No verificado manualmente"
        results.append({
            "id": c["id"],
            "label": c["label"],
            "passed": passed,
            "evidence": evidence,
        })

    passed_count = sum(1 for r in results if r["passed"])
    total = len(results)

    if passed_count == total:
        status = "VERIFIED"
    elif any(not r["passed"] for r in results if r["id"] in ("mp3_playback", "flac_playback", "wav_playback")):
        status = "BLOCKED_HARDWARE"
    else:
        status = "FAILED"

    artifact = {
        "status": status,
        "sha": sha,
        "date": date,
        "platform": platform,
        "backend": backend,
        "device": device,
        "version": version,
        "passed": passed_count,
        "total": total,
        "checks": results,
    }

    ARTIFACT_PATH.write_text(json.dumps(artifact, indent=2, ensure_ascii=False))
    print(f"\n{'=' * 60}")
    print(f"  Results written to {ARTIFACT_PATH}")
    print(f"  Status: {status} ({passed_count}/{total})")
    print(f"  SHA: {sha}")
    print(f"  Date: {date}")
    print(f"  Platform: {platform}")
    print(f"  Backend: {backend}")
    print(f"  Device: {device}")
    print(f"  Version: {version}")
    print(f"{'=' * 60}")

    return 0 if status == "VERIFIED" else (2 if status == "BLOCKED_HARDWARE" else 1)


def check_artifact():
    if not ARTIFACT_PATH.exists():
        print("NO ARTIFACT — ejecuta scripts/qml_physical_runner.py primero")
        return 1
    art = json.loads(ARTIFACT_PATH.read_text())
    print(f"Status: {art['status']}")
    print(f"Passed: {art['passed']}/{art['total']}")
    print(f"SHA: {art.get('sha', '?')}")
    print(f"Date: {art.get('date', '?')}")
    print(f"Platform: {art.get('platform', '?')}")
    print(f"Backend: {art.get('backend', '?')}")
    print(f"Device: {art.get('device', '?')}")
    return 0 if art["status"] == "VERIFIED" else 1


def autofail(reason: str):
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    results = [{"id": c["id"], "label": c["label"], "passed": False, "evidence": reason} for c in CHECKS]
    artifact = {
        "status": "BLOCKED_HARDWARE",
        "message": reason,
        "sha": _get_git_sha(),
        "date": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "platform": _get_platform(),
        "backend": "",
        "device": "",
        "version": "0.2.0a0",
        "passed": 0,
        "total": len(CHECKS),
        "checks": results,
    }
    ARTIFACT_PATH.write_text(json.dumps(artifact, indent=2, ensure_ascii=False))
    print(f"Wrote autofail artifact to {ARTIFACT_PATH}: {reason}")
    return 2


def main():
    if "--check" in sys.argv:
        return check_artifact()
    for arg in sys.argv[1:]:
        if arg.startswith("--autofail="):
            return autofail(arg.split("=", 1)[1])
    return run_interactive()


if __name__ == "__main__":
    sys.exit(main())
