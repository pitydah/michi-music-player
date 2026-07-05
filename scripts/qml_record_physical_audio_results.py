#!/usr/bin/env python3
"""Record physical audio test results with structured evidence.

Usage:
    python scripts/qml_record_physical_audio_results.py          # interactive
    python scripts/qml_record_physical_audio_results.py --json-only  # skip md
"""
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
JSON_PATH = REPO / "docs" / "qml_physical_audio_results.json"
MD_PATH = REPO / "docs" / "QML_PHYSICAL_AUDIO_REPORT.md"

CHECKS = [
    {"id": "play_mp3", "label": "Reproducir MP3", "desc": "Click en archivo MP3"},
    {"id": "play_flac", "label": "Reproducir FLAC", "desc": "Click en archivo FLAC"},
    {"id": "play_wav", "label": "Reproducir WAV", "desc": "Click en archivo WAV"},
    {"id": "cover_art", "label": "Carátula visible", "desc": "Cover en NowPlayingBar"},
    {"id": "placeholder", "label": "Placeholder sin cover", "desc": "Monograma sin carátula"},
    {"id": "pause", "label": "Pausa/Reanudar", "desc": "Espacio o botón play/pause"},
    {"id": "seek", "label": "Seek", "desc": "Arrastrar slider de progreso"},
    {"id": "volume", "label": "Volumen", "desc": "Slider de volumen cambia nivel"},
    {"id": "mute", "label": "Mute", "desc": "Botón mute silencia/restaura"},
    {"id": "next", "label": "Siguiente", "desc": "Botón next cambia canción"},
    {"id": "previous", "label": "Anterior", "desc": "Botón prev cambia canción"},
    {"id": "shuffle", "label": "Aleatorio", "desc": "Toggle shuffle cambia modo"},
    {"id": "repeat", "label": "Repetir", "desc": "Toggle repeat cambia modo"},
    {"id": "queue", "label": "Cola visible", "desc": "Lista de reproducción visible"},
    {"id": "queue_play", "label": "Reproducir desde cola", "desc": "Click en item de cola"},
    {"id": "lyrics", "label": "Letras", "desc": "Letra visible para canción"},
    {"id": "radio", "label": "Radio carga", "desc": "Emisoras visibles"},
    {"id": "radio_play", "label": "Radio reproduce", "desc": "Stream de radio suena"},
    {"id": "eq", "label": "EQ", "desc": "Presets cargan y aplican"},
    {"id": "settings", "label": "Ajustes", "desc": "Pestañas de ajustes visibles"},
    {"id": "resize", "label": "Redimensionar", "desc": "Ventana se adapta al tamaño"},
]


def _ask_bool(prompt: str) -> bool:
    while True:
        ans = input(f"{prompt} [y/n] ").strip().lower()
        if ans in ("y", "yes", "s", "si", "sí"):
            return True
        if ans in ("n", "no"):
            return False


def main():
    print("=== Michi Music Player — Physical Audio Test ===")
    print(f"Total checks: {len(CHECKS)}\n")

    results = []
    for c in CHECKS:
        print(f"[{c['id']}] {c['label']}: {c['desc']}")
        passed = _ask_bool("  ¿Funciona?")
        notes = ""
        if not passed:
            notes = input("  Notas (opcional): ").strip()
        results.append({"id": c["id"], "passed": passed, "notes": notes})
        print()

    passed_count = sum(1 for r in results if r["passed"])
    total = len(results)

    # Platform info
    platform = input("Plataforma (ej: Linux 6.8, KDE Plasma 6): ").strip()
    display = input("Servidor de pantalla (Wayland/X11): ").strip()
    backend = input("Backend de audio (PipeWire/PulseAudio): ").strip()
    output_dev = input("Dispositivo de salida: ").strip()

    status = "VERIFIED" if passed_count >= 21 else ("PARTIAL" if passed_count >= 18 else "FAILED")

    data = {
        "status": status,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "operator": input("Operador: ").strip(),
        "platform": platform,
        "display_server": display,
        "backend": backend,
        "output_device": output_dev,
        "formats": {
            "mp3": {"tested": any(r["id"] == "play_mp3" and r["passed"] for r in results),
                    "passed": any(r["id"] == "play_mp3" and r["passed"] for r in results),
                    "file": ""},
            "flac": {"tested": any(r["id"] == "play_flac" and r["passed"] for r in results),
                     "passed": any(r["id"] == "play_flac" and r["passed"] for r in results),
                     "file": ""},
            "wav": {"tested": any(r["id"] == "play_wav" and r["passed"] for r in results),
                    "passed": any(r["id"] == "play_wav" and r["passed"] for r in results),
                    "file": ""},
        },
        "checks": results,
        "passed": passed_count,
        "total": total,
        "log": "",
    }

    JSON_PATH.write_text(json.dumps(data, indent=2))
    print(f"\nResults written to {JSON_PATH}")

    # Generate markdown
    lines = [
        "# QML Physical Audio Report",
        "",
        f"**Status:** {status}",
        f"**Date:** {data['timestamp']}",
        f"**Platform:** {platform}",
        f"**Display:** {display}",
        f"**Audio backend:** {backend}",
        f"**Output device:** {output_dev}",
        "",
        f"**Passed:** {passed_count}/{total}",
        "",
        "## Results",
        "",
        "| Check | Result | Notes |",
        "|---|---|---|",
    ]
    for r in results:
        icon = "✅" if r["passed"] else "❌"
        lines.append(f"| {r['id']} | {icon} | {r['notes']} |")

    lines.extend([
        "",
        "## Formats",
        f"- MP3: {'✅' if data['formats']['mp3']['passed'] else '❌'}",
        f"- FLAC: {'✅' if data['formats']['flac']['passed'] else '❌'}",
        f"- WAV: {'✅' if data['formats']['wav']['passed'] else '❌'}",
        "",
        "## Requirements for VERIFIED",
        "- Status = VERIFIED (21/21)",
        f"- Backend: {backend} {'✅' if backend else '❌'}",
        f"- Output device: {output_dev} {'✅' if output_dev else '❌'}",
        f"- MP3 tested: {'✅' if data['formats']['mp3']['tested'] else '❌'}",
        f"- FLAC tested: {'✅' if data['formats']['flac']['tested'] else '❌'}",
        f"- WAV tested: {'✅' if data['formats']['wav']['tested'] else '❌'}",
        f"- Play/Pause: {'✅' if any(r['id'] == 'pause' and r['passed'] for r in results) else '❌'}",
        f"- Seek: {'✅' if any(r['id'] == 'seek' and r['passed'] for r in results) else '❌'}",
        f"- Volume: {'✅' if any(r['id'] == 'volume' and r['passed'] for r in results) else '❌'}",
        f"- Mute: {'✅' if any(r['id'] == 'mute' and r['passed'] for r in results) else '❌'}",
        f"- Next/Previous: {'✅' if any(r['id'] == 'next' and r['passed'] for r in results) else '❌'}",
        f"- Queue: {'✅' if any(r['id'] == 'queue' and r['passed'] for r in results) else '❌'}",
        f"- Runtime without crash: {'✅' if data.get('runtime_without_crash') else '❌'}",
        "",
    ])

    MD_PATH.write_text("\n".join(lines))
    print(f"Report written to {MD_PATH}")
    print(f"\nStatus: {status} ({passed_count}/{total})")

    return 0 if passed_count >= 21 else (1 if passed_count >= 18 else 2)


if __name__ == "__main__":
    sys.exit(main())
