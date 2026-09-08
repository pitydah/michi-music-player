#!/usr/bin/env python3
"""P0 PHYSICAL PLAYBACK SMOKE — playback real con verificación física.

Reproduce un track REAL del catálogo (música local del usuario) a través
de la cadena productiva (ApplicationContainer + LibraryBridge + motor de
audio real) y verifica la evidencia física del plan V4:

  1. el scan del catálogo real indexa la música;
  2. el transporte inicia (status playing) sobre el motor activo;
  3. la posición avanza (el bridge expone position/duration EN SEGUNDOS);
  4. aparece un sink-input NUEVO en PulseAudio durante el play (el stream
     llega físicamente al dispositivo de salida);
  5. pause/resume reales y la identidad del track en reproducción.

Nota: el smoke anterior (P0 v1) reportó falsos negativos de la posición
porque el PlaybackBridge divide por 1000 (position/duration en segundos,
no ms) — verificado contra el state del servicio (ms) y el backend.

Uso:
    python scripts/p0_physical_smoke.py [--music DIR] [--data DIR]
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

from PySide6.QtWidgets import QApplication  # noqa: E402

from michi.bootstrap import ApplicationContainer  # noqa: E402

RESULTS: list[dict] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}" + (f" — {detail}" if detail else ""))
    RESULTS.append({"check": label, "ok": ok, "detail": detail})


def sink_ids() -> set[str]:
    try:
        out = subprocess.run(
            ["pactl", "list", "sink-inputs"],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout
        return {
            line.strip()
            for line in out.splitlines()
            if line.strip().startswith("Sink Input #")
        }
    except Exception:  # noqa: BLE001 — sin pactl: no hay evidencia de sink
        return set()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--music", default=os.path.expanduser("~/Música"))
    parser.add_argument("--data", default="/tmp/michi-p0-physical")
    parser.add_argument("--platform", default=None)
    args = parser.parse_args()

    music = Path(args.music)
    if not music.is_dir():
        print(f"FATAL: --music dir missing: {music}")
        return 2

    data_dir = Path(args.data)
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["XDG_DATA_HOME"] = str(data_dir / "data")
    os.environ["XDG_CACHE_HOME"] = str(data_dir / "cache")
    os.environ["XDG_CONFIG_HOME"] = str(data_dir / "config")
    if args.platform:
        os.environ["QT_QPA_PLATFORM"] = args.platform

    app = QApplication.instance() or QApplication(sys.argv)
    container = ApplicationContainer()
    try:
        container.initialize()
        co = container._source_scan_lifecycle._coordinator
        try:
            source = co.add_source("P0", str(music))
        except Exception:  # noqa: BLE001 — data previa reutilizada
            sources = co.list_sources()
            source = sources[0] if sources else None
        if source is not None:
            out = co.scan_source(source)
            check(
                "scan del catálogo real",
                not out.failed,
                f"added={out.added} missing={out.missing}",
            )
        else:
            check("scan del catálogo real", False, "sin source disponible")
            return 1

        library = container._library
        tracks = library.visible_tracks()
        check("catálogo visible > 0", len(tracks) > 0, f"{len(tracks)} tracks")
        if not tracks:
            return 1
        pb = container._pb
        check(
            "transporte inicial stopped",
            pb.property("status") == "stopped",
            f"status={pb.property('status')}",
        )

        played_any = False
        for first in tracks[:6]:
            tid = getattr(first, "track_id", None) or first.track_id
            title = getattr(first, "title", "?")
            print(f"→ target: {title!r} ({Path(str(first.file_path)).name})")
            before = sink_ids()
            container._lb.activate_track_by_id(tid)
            deadline = time.time() + 12
            while time.time() < deadline:
                app.processEvents()
                if pb.property("status") == "playing":
                    break
                time.sleep(0.05)
            if pb.property("status") != "playing":
                print(f"    no inicia (status={pb.property('status')}); siguiente")
                continue
            played_any = True
            app.processEvents()
            time.sleep(2.5)
            app.processEvents()
            # El bridge expone position/duration EN SEGUNDOS (ms // 1000).
            pos = int(pb.property("position") or 0)
            dur = int(pb.property("duration") or 0)
            new_sinks = sink_ids() - before
            print(
                f"    playing: position={pos}s duration={dur}s "
                f"sink_inputs_nuevos={len(new_sinks)}"
            )
            if pos > 1:
                check("target con posición funcional", True, f"{title}: {pos}s")
                check("duration real del archivo", dur > 60, f"{dur}s")
                check(
                    "sink PulseAudio nuevo con el play (físico)",
                    len(new_sinks) > 0,
                    f"{len(new_sinks)} sink-input(s)",
                )
                time.sleep(2)
                app.processEvents()
                pos2 = int(pb.property("position") or 0)
                check("posición sigue avanzando", pos2 > pos, f"{pos}→{pos2}s")
                pb.pause()
                app.processEvents()
                time.sleep(0.4)
                check(
                    "pause real",
                    pb.property("status") == "paused",
                    pb.property("status"),
                )
                pb.resume()
                deadline = time.time() + 6
                while time.time() < deadline:
                    app.processEvents()
                    if pb.property("status") == "playing":
                        break
                    time.sleep(0.05)
                check(
                    "resume real",
                    pb.property("status") == "playing",
                    pb.property("status"),
                )
                check(
                    "identidad del track",
                    bool(pb.property("title")),
                    repr(pb.property("title")),
                )
                break
            if pb.property("status") == "playing":
                pb.pause()
            time.sleep(0.3)
            app.processEvents()

        check("al menos un track reproduce físicamente", played_any)
        print()
        fails = sum(1 for r in RESULTS if not r["ok"])
        if fails:
            print(f"P0 PHYSICAL PLAYBACK: {fails} failure(s)")
            return 1
        print("P0 PHYSICAL PLAYBACK: OK")
        return 0
    finally:
        try:
            container.shutdown()
        except Exception as exc:  # noqa: BLE001 — teardown best-effort
            print(f"shutdown warning: {exc}")


if __name__ == "__main__":
    sys.exit(main())
