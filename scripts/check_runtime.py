#!/usr/bin/env python3
"""Runtime checker — verifies critical and optional dependencies for Michi Music Player."""
import sys
import os
import shutil
import importlib.util


def ok(label, *, critical=True):
    print(f"  ✅ {label}")


def warn(label, *, critical=True):
    tag = "CRÍTICO" if critical else "OPCIONAL"
    print(f"  ⚠️  [{tag}] {label}")


def fail(label, *, critical=True):
    tag = "CRÍTICO" if critical else "OPCIONAL"
    print(f"  ❌ [{tag}] {label}")


def check():
    errors = 0

    print("=== Python ===")
    v = sys.version_info
    print(f"  Python {v.major}.{v.minor}.{v.micro}")
    if (v.major, v.minor) < (3, 11):
        fail("Python >=3.11 requerido", critical=True)
        errors += 1
    else:
        ok("Python >=3.11")

    print("\n=== Core Python packages ===")
    for mod, name in [("PySide6", "PySide6"), ("mutagen", "mutagen"),
                       ("numpy", "numpy")]:
        try:
            __import__(mod)
            ok(name)
        except ImportError:
            fail(f"{name} no encontrado", critical=True)
            errors += 1

    print("\n=== GStreamer ===")
    try:
        import gi
        gi.require_version("Gst", "1.0")
        from gi.repository import Gst
        Gst.init(None)
        ver = Gst.version_string()
        print(f"  GStreamer {ver}")
        ok("GStreamer")
    except Exception as e:
        fail(f"GStreamer: {e}", critical=True)
        errors += 1
        Gst = None

    if Gst:
        # Check essential elements
        essential = ["playbin", "decodebin", "audioconvert", "audioresample", "autoaudiosink", "volume"]
        for elem in essential:
            factory = Gst.ElementFactory.find(elem)
            if factory:
                ok(f"  Element: {elem}")
            else:
                warn(f"  Element: {elem} NO DISPONIBLE", critical=True)

        # Check audio sinks
        sinks = ["pipewiresink", "pulsesink", "alsasink"]
        for s in sinks:
            if Gst.ElementFactory.find(s):
                ok(f"  Audio sink: {s}")
            else:
                warn(f"  Audio sink: {s} no disponible", critical=False)

    print("\n=== Qt platform ===")
    try:
        from PySide6.QtCore import QCoreApplication
        if QCoreApplication.instance():
            plat = QCoreApplication.instance().platformName()
        else:
            plat = os.environ.get("QT_QPA_PLATFORM", "unknown")
        print(f"  Platform: {plat}")
        ok("Qt platform")
    except Exception as e:
        warn(f"Qt platform check: {e}")

    print("\n=== Optional: System audio ===")
    # dbus
    if importlib.util.find_spec("dbus"):
        ok("dbus-python (MPRIS)")
    else:
        warn("dbus-python no disponible (MPRIS deshabilitado)", critical=False)

    # pactl
    if shutil.which("pactl"):
        ok("pactl (PulseAudio/PipeWire)")
    else:
        warn("pactl no encontrado (Snapcast no disponible)", critical=False)

    # pipewire
    for bin_tool in ["pw-cli", "pipewire"]:
        if shutil.which(bin_tool):
            ok(f"  {bin_tool}")
            break
    else:
        warn("PipeWire binaries no encontrados", critical=False)

    print("\n=== Optional: Recognition ===")
    # fpcalc
    if shutil.which("fpcalc"):
        ok("fpcalc (AcoustID)")
    else:
        warn("fpcalc no encontrado (AcoustID deshabilitado)", critical=False)

    # pyaudio
    if importlib.util.find_spec("pyaudio"):
        ok("pyaudio")
    else:
        warn("pyaudio no encontrado (captura de audio deshabilitada)", critical=False)

    # shazamio
    if importlib.util.find_spec("shazamio"):
        ok("shazamio")
    else:
        warn("shazamio no encontrado (ShazamIO deshabilitado)", critical=False)

    print("\n=== Optional: Network / Discovery ===")
    for tool, name in [("avahi-publish-service", "avahi-publish-service (mDNS)"),
                        ("avahi-browse", "avahi-browse (Snapcast discovery)")]:
        if shutil.which(tool):
            ok(name)
        else:
            warn(f"{name} no encontrado", critical=False)

    print("\n=== Optional: Multiroom / Snapcast ===")
    for tool in ["snapserver", "snapclient"]:
        if shutil.which(tool):
            ok(tool)
        else:
            warn(f"{tool} no encontrado", critical=False)

    print("\n=== Resources ===")
    import pathlib
    repo_root = pathlib.Path(__file__).parent.parent
    icons_dir = repo_root / "icons"
    data_dir = repo_root / "data"
    desktop = data_dir / "michi-music-player.desktop"

    if icons_dir.exists() and list(icons_dir.rglob("*.svg")):
        ok(f"icons/ ({len(list(icons_dir.rglob('*.svg')))} SVGs)")
    else:
        warn("icons/ no encontrado o sin SVGs", critical=True)
        errors += 1

    if desktop.exists():
        ok("data/michi-music-player.desktop")
    else:
        warn("Desktop file no encontrado", critical=False)

    print("\n=== App entry point ===")
    # Test michi-music-player entry point
    if importlib.util.find_spec("main"):
        ok("main entry point")
    else:
        warn("Entry point main no encontrado", critical=True)
        errors += 1

    print(f"\n{'='*40}")
    if errors:
        print(f"⚠️  {errors} problema(s) crítico(s) detectado(s)")
        print("\nPara instalar dependencias:")
        print("  ./scripts/install.sh          (instalador unificado automático)")
        print("  ./scripts/install.sh --minimal (solo dependencias core)")
        print("  ./scripts/run_from_source.sh   (ejecutar sin instalar al sistema)")
    else:
        print("✅ Todo está listo. Ejecuta: python3 main.py")
    print()

    return errors


if __name__ == "__main__":
    sys.exit(check())
